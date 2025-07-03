// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Google Drive Attachment Config', {
    refresh: function(frm) {
        // Check if Google Settings are enabled
        frm.dashboard.clear_headline();

        if (!frm.doc.enable_google_drive_upload) {
            frm.dashboard.set_headline(
                __("To use Google Drive attachments, enable Google Drive upload above.")
            );
        }
        
        // Check for Google Settings and Google Drive dependency
        frappe.db.get_single_value("Google Settings", "enable").then(enabled => {
            if (!enabled) {
                frm.dashboard.set_headline(
                    __("To use Google Drive, enable {0}.", [
                        `<a href='/app/google-settings'>${__("Google Settings")}</a>`,
                    ])
                );
            }
        });
        
        // frappe.db.get_single_value("Google Drive", "enable").then(enabled => {
        //     if (!enabled) {
        //         frm.dashboard.set_headline(
        //             __("To use Google Drive attachments, you must also enable {0}.", [
        //                 `<a href='/app/google-drive'>${__("Google Drive")}</a>`,
        //             ])
        //         );
        //     }
        // });
        
        // Add custom buttons
        frm.add_custom_button(__('Test Connection'), function() {
            test_gdrive_connection(frm);
        });
        
        frm.add_custom_button(__('View Usage'), function() {
            show_usage_info(frm);
        });
        
        // Show authorization status
        if (frm.doc.enable_google_drive_upload && frm.doc.refresh_token && frm.doc.authorization_code) {
            frm.page.set_indicator("Authorized", "green");
        } else if (frm.doc.enable_google_drive_upload && !frm.doc.refresh_token) {
            frm.dashboard.set_headline(
                __("Click on <b>Authorize Google Drive Access</b> to authorize Google Drive Access.")
            );
        }
        
    },
    
    authorize_google_drive_access: function(frm) {
        frappe.call({
            method: "frappe_gdrive_attachments.controller.authorize_access",
            args: {
                reauthorize: frm.doc.authorization_code ? 1 : 0,
            },
            callback: function(r) {
                if (!r.exc) {
                    if (r.message && r.message.url) {
                        console.log("this is r.message ",r.message);
                        frm.save();
                        window.open(r.message.url);
                    } else if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Authorization successful!'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            }
        });
    },
    
    migrate_existing_files: function(frm) {
        if (!frm.doc.enable_google_drive_upload) {
            frappe.msgprint(__('Please enable Google Drive upload first'));
            return;
        }
        
        if (!frm.doc.refresh_token) {
            frappe.msgprint(__('Please authorize Google Drive access first'));
            return;
        }
        
        frappe.confirm(
            __('This will migrate all existing local files to Google Drive. This process cannot be undone. Continue?'),
            function() {
                frappe.show_alert(__('Migration started. This may take a few minutes...'), 10);
                
                frappe.call({
                    method: "frappe_gdrive_attachment.controller.migrate_existing_files",
                    freeze: true,
                    freeze_message: __('Migrating files to Google Drive...'),
                    callback: function(r) {
                        if (r.message) {
                            const result = r.message;
                            frappe.msgprint({
                                title: __('Migration Complete'),
                                message: __('Successfully migrated {0} files. {1} errors occurred out of {2} total files.', 
                                    [result.migrated, result.errors, result.total]),
                                indicator: result.errors > 0 ? 'orange' : 'green'
                            });
                            
                            if (result.errors > 0) {
                                frappe.msgprint(__('Check Error Log for details about failed migrations'));
                            }
                        } else {
                            frappe.msgprint(__('Migration failed. Please check the error log.'));
                        }
                    },
                    error: function(r) {
                        frappe.msgprint(__('Migration failed: {0}', [r.message]));
                    }
                });
            }
        );
    },
    
    enable_google_drive_upload: function(frm) {
        if (frm.doc.enable_google_drive_upload && !frm.doc.refresh_token) {
            frappe.msgprint(__('Please authorize Google Drive access to enable file upload'));
        }
    },
    
    file_sharing_permission: function(frm) {
        if (frm.doc.file_sharing_permission === 'Specific people') {
            frappe.msgprint(__('Make sure to add email addresses in the "Specific Emails" field'));
        }
    }
});

function test_gdrive_connection(frm) {
    if (!frm.doc.refresh_token) {
        frappe.msgprint(__('Please authorize Google Drive access first'));
        return;
    }
    
    frappe.call({
        method: "frappe_gdrive_attachment.controller.test_gdrive_connection",
        freeze: true,
        freeze_message: __('Testing Google Drive connection...'),
        callback: function(r) {
            if (r.message) {
                if (r.message.success) {
                    frappe.show_alert({
                        message: __('Google Drive connection successful!'),
                        indicator: 'green'
                    });
                } else {
                    frappe.msgprint({
                        title: __('Connection Failed'),
                        message: __('Error: {0}', [r.message.message]),
                        indicator: 'red'
                    });
                }
            }
        }
    });
}

function show_usage_info(frm) {
    const usage_html = `
        <div class="row">
            <div class="col-md-12">
                <h4>Google Drive Integration Setup Guide</h4>
                <br>
                <h5>1. Enable Google Settings</h5>
                <ul>
                    <li>Go to <a href="/app/google-settings" target="_blank">Google Settings</a></li>
                    <li>Enable Google integration and configure OAuth credentials</li>
                    <li>Add your OAuth Client ID and Client Secret</li>
                    <li>Ensure Google Drive scope is included: <code>https://www.googleapis.com/auth/drive</code></li>
                </ul>
                
                <h5>2. Enable Google Drive</h5>
                <ul>
                    <li>Go to <a href="/app/google-drive" target="_blank">Google Drive</a></li>
                    <li>Enable the Google Drive integration</li>
                    <li>This is required for the OAuth flow to work properly</li>
                </ul>
                
                <h5>3. Configure Google Drive Attachments</h5>
                <ul>
                    <li>Enable "Google Drive Upload" in this form</li>
                    <li>Click "Authorize Google Drive Access" button</li>
                    <li>Complete the OAuth authorization flow</li>
                    <li>Verify that authorization is successful (green indicator)</li>
                </ul>
                
                <h5>4. Configure Upload Settings</h5>
                <ul>
                    <li><strong>Parent Folder ID:</strong> Optional Google Drive folder ID where all files will be uploaded</li>
                    <li><strong>Folder Name Prefix:</strong> Optional prefix to add to filenames</li>
                </ul>
                
                <h5>5. File Organization</h5>
                <p>All files are uploaded to the parent folder with descriptive filenames: <code>[DocType]_[DocumentName]_[OriginalFilename]</code></p>
                
                <h5>6. Sharing Permissions</h5>
                <ul>
                    <li><strong>Private:</strong> Only authorized users can access</li>
                    <li><strong>Anyone with link can view:</strong> Anyone with the link can view the file</li>
                    <li><strong>Anyone with link can edit:</strong> Anyone with the link can edit the file</li>
                    <li><strong>Specific people:</strong> Only specified email addresses can access</li>
                </ul>
                
                <h5>7. Benefits of OAuth vs Service Account</h5>
                <ul>
                    <li>Uses Frappe's built-in Google integration</li>
                    <li>Easier setup - no JSON key files needed</li>
                    <li>Better security with token refresh</li>
                    <li>Integrated with existing Google Settings</li>
                </ul>
            </div>
        </div>
    `;
    
    frappe.msgprint({
        title: __('Google Drive Integration Usage'),
        message: usage_html,
        wide: true
    });
}        