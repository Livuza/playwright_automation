// Copyright (c) 2025, Livuza and contributors
// For license information, please see license.txt

frappe.ui.form.on("Playwright Test", {
    refresh(frm) {
        frm.add_custom_button("Run Login Test", () => {
            if (frm.is_new()) {
                frappe.msgprint("Please save the document before running the Playwright test.");
                return;
            }

            frappe.call({
                method: "playwright.playwright.doctype.playwright_test.playwright_test.run_login",
                args: { docname: frm.doc.name },
                freeze: true,
                freeze_message: "Running Playwright test...",
                callback: function(response) {
                    frm.reload_doc();
                    frappe.msgprint(response.message);
                }
            });
        });
    }
});