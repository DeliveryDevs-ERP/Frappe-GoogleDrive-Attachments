# Frappe Google Drive Attachment

A Frappe app that automatically uploads file attachments to Google Drive, providing seamless cloud storage integration for your Frappe applications.

## Features

1. **Automatic Upload**: Automatically uploads files to Google Drive when attachments are added
2. **Flexible Organization**: Organizes files in customizable folder structures
3. **Privacy Controls**: Supports both private and public file sharing
4. **Batch Migration**: Migrate existing local files to Google Drive
5. **Service Account Integration**: Uses Google Cloud Service Account for secure authentication
6. **Customizable Permissions**: Configure file sharing permissions (private, public, specific users)
7. **Date-based Folders**: Optional automatic date-based folder organization
8. **File Streaming**: Stream files directly from Google Drive
9. **Automatic Cleanup**: Optionally delete files from Google Drive when removed from Frappe

## Installation

1. **Install the app**:
   ```bash
   bench get-app https://github.com/your-repo/frappe-gdrive-attachment.git
   bench install-app frappe_gdrive_attachment
   ```

2. **Install Python dependencies**:
   ```bash
   pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
   ```

## Configuration

### 1. Google Cloud Setup

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Drive API

2. **Create Service Account**:
   - Navigate to "IAM & Admin" → "Service Accounts"
   - Create a new service account
   - Download the JSON key file
   - Grant necessary permissions to the service account

3. **Configure Drive Access**:
   - Share your Google Drive folder with the service account email
   - Or use the root drive if you have domain-wide delegation

### 2. Frappe Configuration

1. **Access Configuration**:
   - Go to "Google Drive Configuration" in your Frappe system
   - This is a single doctype accessible to System Managers

2. **Basic Settings**:
   - **Enable Google Drive Upload**: Check to activate the integration
   - **Delete file from Google Drive**: Check to delete files from Drive when deleted in Frappe

3. **Google Drive Credentials**:
   - **Service Account Email**: Auto-populated from JSON key
   - **Service Account Key (JSON)**: Paste the complete JSON key file content
   - **Parent Folder ID**: Optional - Google Drive folder ID where files will be uploaded
   - **Folder Name Prefix**: Optional prefix for organizing files
   - **Create Date-based Folders**: Enable automatic YYYY/MM/DD folder structure

4. **Sharing Settings**:
   - **Private**: Only service account can access
   - **Anyone with link can view**: Public read access
   - **Anyone with link can edit**: Public edit access
   - **Specific people**: Restricted access to specified email addresses

## File Organization

All files are uploaded directly to the configured parent folder without creating nested folder structures. Files are organized using filename prefixes for easy identification:

**Filename Structure:**
```
[DocType]_[DocumentName]_[OriginalFilename]
```

**Examples:**
- `Customer_ABC Corp_contract.pdf`
- `Project_Website Redesign_mockup.jpg`
- `Task_Fix Bug 123_screenshot.png`

This approach keeps all files in a single folder while maintaining clear organization through descriptive filenames.

## Usage

### Automatic Upload

Once configured, the app automatically:
1. Intercepts file uploads in Frappe
2. Uploads files to Google Drive
3. Updates file URLs to point to Google Drive
4. Removes local files to save server space

### Manual Migration

To migrate existing files:
1. Go to "Google Drive Configuration"
2. Click "Migrate Existing Files to Google Drive"
3. Confirm the migration process
4. Monitor the progress and check for any errors

### File Access

- **Private files**: Accessed through Frappe's secure endpoint
- **Public files**: Direct Google Drive links
- **Specific users**: Shared with configured email addresses

## API Methods

### Controller Methods

```python
# Test Google Drive connection
frappe.call({
    method: "frappe_gdrive_attachment.controller.test_gdrive_connection"
})

# Get file information
frappe.call({
    method: "frappe_gdrive_attachment.controller.get_drive_file_info",
    args: { file_id: "your_file_id" }
})

# Migrate existing files
frappe.call({
    method: "frappe_gdrive_attachment.controller.migrate_existing_files"
})
```

### Configuration Methods

```python
# Get Google Drive settings
from frappe_gdrive_attachment.frappe_gdrive_attachment.doctype.google_drive_configuration.google_drive_configuration import get_google_drive_config

config = get_google_drive_config()
```

## Customization

### Custom Folder Structure

You can customize the folder structure by creating a hook:

```python
# In your custom app's hooks.py
doc_events = {
    "File": {
        "before_insert": "your_app.utils.custom_gdrive_folder_structure"
    }
}
```

### Ignore Specific DocTypes

Configure doctypes to ignore in `site_config.json`:

```json
{
    "ignore_gdrive_upload_for_doctype": ["Data Import", "Error Log"]
}
```

## Security Considerations

1. **Service Account Security**: Store service account keys securely
2. **Folder Permissions**: Ensure proper Google Drive folder permissions
3. **Data Privacy**: Configure appropriate file sharing settings
4. **Access Control**: Limit System Manager access to configuration

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify service account JSON key format
   - Check Google Drive API is enabled
   - Ensure service account has Drive access

2. **Upload Failures**:
   - Check service account permissions
   - Verify parent folder exists and is accessible
   - Check network connectivity

3. **File Access Issues**:
   - Verify file sharing permissions
   - Check if files exist in Google Drive
   - Ensure proper folder structure

### Error Logs

Check Frappe error logs for detailed error messages:
- Navigate to "Error Log" in Frappe
- Look for Google Drive related errors
- Check the full stack trace for debugging

## Development

### Testing

```bash
# Run tests
bench run-tests --app frappe_gdrive_attachment

# Test specific functionality
bench execute frappe_gdrive_attachment.controller.test_gdrive_connection
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License

## Support

For issues and support:
1. Check the troubleshooting section
2. Review error logs
3. Create an issue on GitHub
4. Contact support team

## Changelog

### Version 1.0.0
- Initial release
- Basic Google Drive integration
- File upload and organization
- Migration support
- Sharing permissions
- Service account authentication