# Copyright (c) 2025, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.integrations.google_oauth import GoogleOAuth


class GoogleDriveAttachmentConfig(Document):
    def validate(self):
        """Validate Google Drive configuration"""
        if self.enable_google_drive_upload:
            self.validate_google_settings()
            self.validate_specific_emails()
    
    def validate_google_settings(self):
        """Validate that Google Settings are enabled"""
        google_settings = frappe.get_doc("Google Settings")
        if not google_settings.enable:
            frappe.throw(_("Google Settings must be enabled before using Google Drive integration. Please go to Google Settings and enable it."))
    
    def validate_specific_emails(self):
        """Validate specific emails format"""
        if self.file_sharing_permission == 'Specific people' and self.specific_emails:
            emails = [email.strip() for email in self.specific_emails.split(',')]
            invalid_emails = []
            
            for email in emails:
                if email and not self.is_valid_email(email):
                    invalid_emails.append(email)
            
            if invalid_emails:
                frappe.throw(_("Invalid email addresses: {0}").format(', '.join(invalid_emails)))
    
    def is_valid_email(self, email):
        """Check if email is valid"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def get_access_token(self):
        """Get access token for Google Drive API"""
        if not self.refresh_token:
            button_label = frappe.bold(_("Authorize Google Drive Access"))
            frappe.throw(_("Click on {0} to generate Refresh Token.").format(button_label))

        oauth_obj = GoogleOAuth("drive")
        try:
            r = oauth_obj.refresh_access_token(
                self.get_password(fieldname="refresh_token", raise_exception=False)
            )
            return r.get("access_token")
        except Exception as e:
            frappe.throw(_("Error getting access token: {0}").format(str(e)))
    
    def on_update(self):
        """Handle configuration updates"""
        # Clear cache when configuration changes
        frappe.cache().delete_key("google_drive_config")
        
        # Log configuration changes
        frappe.logger().info("Google Drive Configuration updated")


def get_google_drive_config():
    """Get Google Drive configuration with caching"""
    config = frappe.cache().get_value("google_drive_config")
    
    if not config:
        try:
            config = frappe.get_doc('Google Drive Attachment Config', 'Google Drive Attachment Config')
            frappe.cache().set_value("google_drive_config", config, expires_in_sec=300)  # Cache for 5 minutes
        except frappe.DoesNotExistError:
            # Create default configuration if it doesn't exist
            config = frappe.new_doc('Google Drive Configuration')
            config.insert(ignore_permissions=True)
            frappe.cache().set_value("google_drive_config", config, expires_in_sec=300)
    
    return config


@frappe.whitelist()
def get_drive_settings():
    """Get Google Drive settings for frontend"""
    config = get_google_drive_config()
    
    return {
        'enabled': config.enable_google_drive_upload,
        'has_authorization': bool(config.refresh_token),
        'folder_prefix': config.folder_name_prefix,
        'sharing_permission': config.file_sharing_permission,
        'parent_folder_id': config.parent_folder_id
    }