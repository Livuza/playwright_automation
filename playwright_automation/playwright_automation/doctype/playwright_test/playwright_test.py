# Copyright (c) 2025, Livuza and contributors
# For license information, please see license.txt

import frappe
import tempfile
import shutil
import time
import io
from frappe.model.document import Document
from frappe.rate_limiter import rate_limit

try:
	from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
	sync_playwright = None


class PlaywrightTest(Document):
	pass


@frappe.whitelist()
@rate_limit(limit=30, seconds=60)
def run_login(docname: str) -> str:
	"""Run a Playwright login test with optimized flow, clear logs, and proper cleanup."""
	if not sync_playwright:
		frappe.throw(
			"Playwright is not installed.<br>"
			"Please run: <code>pip install playwright && python3 -m playwright install</code>"
		)

	doc = frappe.get_doc("Playwright Test", docname)
	temp_dir = tempfile.mkdtemp(prefix="playwright_user_data_")
	browser = None
	context = None

	try:
		with sync_playwright() as p:
			frappe.logger().info("Launching Chromium browser for Playwright test...")

			# ✅ Launch Chromium headlessly with safe defaults
			browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
			context = browser.new_context()
			page = context.new_page()

			load_page(page, "https://practicetestautomation.com/practice-test-login/")

			# ✅ Handle cookie popup gracefully
			click_if_exists(page, "text=Accept", "Cookie popup accepted.")

			# ✅ Fill in credentials and submit
			fill_login_form(page)

			# ✅ Wait for success confirmation
			result = get_login_result(page)

			# ✅ Save status and logs
			doc.status = "Success" if result else "Failed"
			doc.log_output = result or "Login attempt completed but success text not found."
			frappe.logger().info(f"Playwright test completed for {docname}: {doc.status} -> {doc.log_output}")

	except Exception as e:
		doc.status = "Failed"
		doc.log_output = f"Playwright error: {str(e)}"
		frappe.logger().error(f"Playwright test failed for {docname}: {e}")

	finally:
		cleanup(browser, context, temp_dir)
		doc.save(ignore_permissions=True)
		frappe.db.commit()

	return f"Playwright test completed: {doc.status}"


# -----------------------
# 🔧 HELPER FUNCTIONS
# -----------------------

def load_page(page, url, timeout=30_000):
	"""Load the given URL and wait until idle."""
	frappe.logger().info(f"Loading page: {url}")
	page.goto(url, timeout=timeout)
	try:
		page.wait_for_load_state("networkidle", timeout=5_000)
	except PlaywrightTimeout:
		frappe.logger().warning("Network idle wait timed out – proceeding anyway.")


def click_if_exists(page, selector, log_message=None, timeout=3_000):
	"""Click an element if it exists."""
	try:
		page.click(selector, timeout=timeout)
		if log_message:
			frappe.logger().info(log_message)
	except Exception:
		pass


def fill_login_form(page):
	"""Fill and submit the login form."""
	page.wait_for_selector("input#username", timeout=5_000)
	page.fill("input#username", "student")
	page.fill("input#password", "Password123")

	try:
		page.click("button[type='submit']", timeout=2_000, force=True)
	except Exception as e:
		frappe.logger().warning(f"Standard button click failed: {e}. Retrying via XPath.")
		page.click("xpath=//button[contains(., 'Submit')]", timeout=2_000, force=True)

	page.wait_for_load_state("networkidle", timeout=5_000)
	time.sleep(2)


def get_login_result(page):
	"""Check for login success message."""
	selectors = [".post-title", "text=Logged In Successfully"]
	for sel in selectors:
		try:
			text = page.text_content(sel, timeout=2_000)
			if text:
				return text.strip()
		except Exception:
			continue
	return None


def cleanup(browser, context, temp_dir):
	"""Safely close browser and remove temp directory."""
	try:
		if context:
			context.close()
		if browser:
			browser.close()
		frappe.logger().info("Browser and context closed successfully.")
	except Exception:
		frappe.logger().warning("Error closing browser or context.")

	shutil.rmtree(temp_dir, ignore_errors=True)
	frappe.logger().info("Temporary user data directory cleaned up.")
