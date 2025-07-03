from __future__ import unicode_literals

import os
import re
import mimetypes
from io import BytesIO

import frappe
from frappe.utils import get_site_path
from frappe.integrations.google_oauth import GoogleOAuth

try:
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from googleapiclient.errors import HttpError
except ImportError:
    frappe.throw(frappe._("Google API Client libraries not installed. Please install google-api-python-client and google-auth packages."))


class GoogleDriveOperations(object):
    """Class to handle Google Drive operations using Frappe's Google OAuth"""
    
    def __init__(self):
        """Initialize Google Drive settings from configuration doctype"""
        self.config = frappe.get_doc(
            'Google Drive Attachment Config',
            'Google Drive Attachment Config'
        )
        
        if not self.config.enable_google_drive_upload:
            frappe.throw(frappe._("Google Drive upload is disabled in configuration"))
            
        # Get Google Drive service using Frappe's OAuth
        self.drive_service, self.account = self.get_google_drive_object()
    
    def get_google_drive_object(self):
        """Get Google Drive service object using Frappe's Google OAuth"""
        try:
            # Check if Google Drive is configured in Google Settings
            google_settings = frappe.get_doc("Google Settings")
            if not google_settings.enable:
                frappe.throw(frappe._("Google Settings are not enabled. Please enable Google Settings first."))
            
            # Use Frappe's Google OAuth for Drive
            oauth_obj = GoogleOAuth("drive")
            
            # Get access token from our config
            access_token = self.get_access_token()
            
            # Get Google Drive service object
            google_drive = oauth_obj.get_google_service_object(access_token)
            
            return google_drive, self.config
            
        except Exception as e:
            frappe.throw(frappe._("Error initializing Google Drive service: {0}").format(str(e)))
    
    def get_access_token(self):
        """Get access token for Google Drive API"""
        if not self.config.refresh_token:
            button_label = frappe.bold(frappe._("Authorize Google Drive Access"))
            frappe.throw(frappe._("Click on {0} to generate Refresh Token.").format(button_label))

        oauth_obj = GoogleOAuth("drive")
        try:
            r = oauth_obj.refresh_access_token(
                self.config.get_password(fieldname="refresh_token", raise_exception=False)
            )
            return r.get("access_token")
        except Exception as e:
            frappe.throw(frappe._("Error getting access token: {0}").format(str(e)))
    
    def strip_special_chars(self, file_name):
        """Strip special characters from file name"""
        # Keep alphanumeric, dots, hyphens, underscores and spaces
        regex = re.compile('[^0-9a-zA-Z._\-\s]')
        file_name = regex.sub('', file_name)
        return file_name.strip()
    
    def get_upload_folder_id(self):
        """Get the folder ID where files should be uploaded"""
        return self.config.parent_folder_id or 'root'
    
    def upload_file_to_drive(self, file_path, file_name, parent_doctype, parent_name=None):
        """Upload file to Google Drive directly to parent folder"""
        try:
            # Get the upload folder ID (parent folder only, no nested structure)
            folder_id = self.get_upload_folder_id()
            
            # Clean file name and add metadata to make it unique and identifiable
            clean_file_name = self.strip_special_chars(file_name)
            
            # Optionally add doctype/document info to filename to maintain organization
            if parent_doctype and parent_name:
                # Add doctype and document name as prefix to filename
                base_name, ext = os.path.splitext(clean_file_name)
                clean_file_name = "{0}_{1}_{2}{3}".format(
                    parent_doctype, 
                    self.strip_special_chars(parent_name), 
                    base_name, 
                    ext
                )
            elif parent_doctype:
                # Add just doctype as prefix
                base_name, ext = os.path.splitext(clean_file_name)
                clean_file_name = "{0}_{1}{2}".format(parent_doctype, base_name, ext)
            
            # Get mime type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # File metadata
            file_metadata = {
                'name': clean_file_name,
                'parents': [folder_id],
                'description': "Uploaded from {0}: {1}".format(parent_doctype, parent_name) if parent_name else "Uploaded from {0}".format(parent_doctype)
            }
            
            # Upload file
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            file_result = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink'
            ).execute()
            
            # Set file permissions based on configuration
            self.set_file_permissions(file_result.get('id'))
            
            return file_result
            
        except HttpError as e:
            frappe.throw(frappe._("Error uploading file to Google Drive: {0}").format(str(e)))
        except Exception as e:
            frappe.log_error("Error uploading file to Google Drive: {0}".format(str(e)))
            frappe.throw(frappe._("Error uploading file to Google Drive: {0}").format(str(e)))
    
    def set_file_permissions(self, file_id):
        """Set file permissions based on configuration"""
        try:
            permission_type = self.config.file_sharing_permission
            
            if permission_type == "Anyone with link can view":
                permission = {
                    'type': 'anyone',
                    'role': 'reader'
                }
                self.drive_service.permissions().create(
                    fileId=file_id,
                    body=permission
                ).execute()
                
            elif permission_type == "Anyone with link can edit":
                permission = {
                    'type': 'anyone',
                    'role': 'writer'
                }
                self.drive_service.permissions().create(
                    fileId=file_id,
                    body=permission
                ).execute()
                
            elif permission_type == "Specific people" and self.config.specific_emails:
                emails = [email.strip() for email in self.config.specific_emails.split(',')]
                for email in emails:
                    if email:
                        permission = {
                            'type': 'user',
                            'role': 'reader',
                            'emailAddress': email
                        }
                        self.drive_service.permissions().create(
                            fileId=file_id,
                            body=permission
                        ).execute()
                        
        except HttpError as e:
            frappe.log_error("Error setting file permissions: {0}".format(str(e)))
    
    def delete_file_from_drive(self, file_id):
        """Delete file from Google Drive"""
        if not self.config.delete_file_from_drive:
            return
        
        try:
            self.drive_service.files().delete(fileId=file_id).execute()
            
        except HttpError as e:
            frappe.log_error("Error deleting file from Google Drive: {0}".format(str(e)))
    
    def download_file_from_drive(self, file_id):
        """Download file from Google Drive"""
        try:
            request = self.drive_service.files().get_media(fileId=file_id)
            file_io = BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            file_io.seek(0)
            return file_io
            
        except HttpError as e:
            frappe.throw(frappe._("Error downloading file from Google Drive: {0}").format(str(e)))
    
    def get_file_info(self, file_id):
        """Get file information from Google Drive"""
        try:
            file_info = self.drive_service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, size, webViewLink, webContentLink, createdTime, modifiedTime'
            ).execute()
            
            return file_info
            
        except HttpError as e:
            frappe.log_error("Error getting file info: {0}".format(str(e)))
            return None


def gdrive_file_regex_match(file_url):
    """Check if file URL is a Google Drive URL"""
    return re.match(
        r'^(/api/method/frappe_gdrive_attachment\.controller\.serve_file|https://drive\.google\.com)',
        file_url
    )


@frappe.whitelist()
def authorize_access(reauthorize=False, code=None):
    """Authorize Google Drive access using Frappe's OAuth"""
    try:
        config = frappe.get_doc('Google Drive Attachment Config', 'Google Drive Attachment Config')
        
        oauth_code = config.authorization_code if not code else code
        oauth_obj = GoogleOAuth("drive")

        if not oauth_code or reauthorize:
            if reauthorize:
                frappe.db.set_single_value("Google Drive Attachment Config", "parent_folder_id", "")
            
            # Generate authorization URL
            return oauth_obj.get_authentication_url({
                "redirect": "/app/Form/Google%20Drive%20Attachment%20Config",
            })

        # Exchange authorization code for tokens
        r = oauth_obj.authorize(oauth_code)
        
        # Update config with tokens
        frappe.db.set_single_value("Google Drive Attachment Config", {
            "authorization_code": oauth_code,
            "refresh_token": r.get("refresh_token")
        })
        
        return {"success": True, "message": "Authorization successful"}
        
    except Exception as e:
        frappe.throw(frappe._("Error during authorization: {0}").format(str(e)))


@frappe.whitelist()
def file_upload_to_gdrive(doc, method):
    """Upload file to Google Drive after File doc creation"""
    try:
        # Check if Google Drive upload is enabled
        config = frappe.get_doc('Google Drive Attachment Config', 'Google Drive Attachment Config')
        if not config.enable_google_drive_upload:
            return
        
        # Skip if already uploaded to Google Drive
        if doc.file_url and gdrive_file_regex_match(doc.file_url):
            return
        
        # Initialize Google Drive operations
        gdrive = GoogleDriveOperations()
        
        # Get file path
        site_path = get_site_path()
        parent_doctype = doc.attached_to_doctype or 'File'
        parent_name = doc.attached_to_name
        
        # Check if doctype should be ignored
        ignore_gdrive_upload_for_doctype = frappe.local.conf.get('ignore_gdrive_upload_for_doctype') or ['Data Import']
        if parent_doctype in ignore_gdrive_upload_for_doctype:
            return
        
        # Construct file path
        if not doc.is_private:
            file_path = site_path + '/public' + doc.file_url
        else:
            file_path = site_path + doc.file_url
        
        # Check if file exists
        if not os.path.exists(file_path):
            frappe.log_error("File not found: {0}".format(file_path))
            return
        
        # Upload to Google Drive
        drive_file = gdrive.upload_file_to_drive(
            file_path, 
            doc.file_name, 
            parent_doctype, 
            parent_name
        )
        
        # Update file URL based on privacy
        if doc.is_private:
            # Private files served through our API
            file_url = "/api/method/frappe_gdrive_attachment.controller.serve_file?file_id={0}&file_name={1}".format(
                drive_file.get('id'), doc.file_name
            )
        else:
            # Public files use direct Google Drive links
            file_url = drive_file.get('webViewLink')
        
        # Remove local file
        try:
            os.remove(file_path)
        except OSError:
            pass
        
        # Update File document
        frappe.db.sql("""
            UPDATE `tabFile` 
            SET file_url=%s, folder=%s, old_parent=%s, content_hash=%s 
            WHERE name=%s
        """, (
            file_url, 
            'Home/Attachments', 
            'Home/Attachments', 
            drive_file.get('id'), 
            doc.name
        ))
        
        # Update the doc object
        doc.file_url = file_url
        doc.content_hash = drive_file.get('id')
        
        # Update image field if applicable
        if parent_doctype and frappe.get_meta(parent_doctype).get('image_field'):
            frappe.db.set_value(
                parent_doctype, 
                parent_name, 
                frappe.get_meta(parent_doctype).get('image_field'), 
                file_url
            )
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error("Error in file_upload_to_gdrive: {0}".format(str(e)))


@frappe.whitelist()
def serve_file(file_id=None, file_name=None):
    """Serve file from Google Drive"""
    if not file_id:
        frappe.throw(frappe._("File ID is required"))
    
    try:
        gdrive = GoogleDriveOperations()
        file_stream = gdrive.download_file_from_drive(file_id)
        
        # Set response headers
        frappe.local.response.filename = file_name or "download"
        frappe.local.response.filecontent = file_stream.read()
        frappe.local.response.type = "download"
        
    except Exception as e:
        frappe.throw(frappe._("Error serving file: {0}").format(str(e)))


@frappe.whitelist()
def migrate_existing_files():
    """Migrate existing local files to Google Drive"""
    try:
        # Get all files that are not yet on Google Drive
        files_list = frappe.get_all(
            'File',
            fields=['name', 'file_url', 'file_name', 'attached_to_doctype', 'attached_to_name', 'is_private'],
            filters={'file_url': ['not like', '%drive.google.com%']}
        )
        
        migrated_count = 0
        error_count = 0
        
        for file_doc in files_list:
            if file_doc.get('file_url') and not gdrive_file_regex_match(file_doc.get('file_url')):
                try:
                    upload_existing_file_to_gdrive(file_doc)
                    migrated_count += 1
                except Exception as e:
                    error_count += 1
                    frappe.log_error("Error migrating file {0}: {1}".format(file_doc.get('name'), str(e)))
        
        return {
            'migrated': migrated_count,
            'errors': error_count,
            'total': len(files_list)
        }
        
    except Exception as e:
        frappe.throw(frappe._("Error during migration: {0}").format(str(e)))


def upload_existing_file_to_gdrive(file_doc):
    """Upload existing file to Google Drive"""
    try:
        # Get file document
        doc = frappe.get_doc('File', file_doc.get('name'))
        
        # Initialize Google Drive operations
        gdrive = GoogleDriveOperations()
        
        # Get file path
        site_path = get_site_path()
        parent_doctype = doc.attached_to_doctype or 'File'
        parent_name = doc.attached_to_name
        
        # Construct file path
        if not doc.is_private:
            file_path = site_path + '/public' + doc.file_url
        else:
            file_path = site_path + doc.file_url
        
        # Check if file exists
        if not os.path.exists(file_path):
            frappe.log_error("File not found during migration: {0}".format(file_path))
            return
        
        # Upload to Google Drive
        drive_file = gdrive.upload_file_to_drive(
            file_path, 
            doc.file_name, 
            parent_doctype, 
            parent_name
        )
        
        # Update file URL
        if doc.is_private:
            file_url = "/api/method/frappe_gdrive_attachment.controller.serve_file?file_id={0}&file_name={1}".format(
                drive_file.get('id'), doc.file_name
            )
        else:
            file_url = drive_file.get('webViewLink')
        
        # Remove local file
        try:
            os.remove(file_path)
        except OSError:
            pass
        
        # Update File document
        frappe.db.sql("""
            UPDATE `tabFile` 
            SET file_url=%s, folder=%s, old_parent=%s, content_hash=%s 
            WHERE name=%s
        """, (
            file_url, 
            'Home/Attachments', 
            'Home/Attachments', 
            drive_file.get('id'), 
            doc.name
        ))
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error("Error uploading existing file to Google Drive: {0}".format(str(e)))
        raise


@frappe.whitelist()
def delete_from_gdrive(doc, method):
    """Delete file from Google Drive when File doc is deleted"""
    try:
        if doc.content_hash and gdrive_file_regex_match(doc.file_url):
            gdrive = GoogleDriveOperations()
            gdrive.delete_file_from_drive(doc.content_hash)
            
    except Exception as e:
        frappe.log_error("Error deleting file from Google Drive: {0}".format(str(e)))


@frappe.whitelist()
def get_drive_file_info(file_id):
    """Get file information from Google Drive"""
    try:
        gdrive = GoogleDriveOperations()
        return gdrive.get_file_info(file_id)
        
    except Exception as e:
        frappe.throw(frappe._("Error getting file info: {0}").format(str(e)))


@frappe.whitelist()
def test_gdrive_connection():
    """Test Google Drive connection"""
    try:
        gdrive = GoogleDriveOperations()
        
        # Try to list files in root folder to test connection
        results = gdrive.drive_service.files().list(
            pageSize=1,
            fields="files(id, name)"
        ).execute()
        
        return {
            'success': True,
            'message': 'Google Drive connection successful'
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }


@frappe.whitelist()
def ping():
    """Test API endpoint"""
    return "pong"