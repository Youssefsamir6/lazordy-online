# Google Drive Integration Troubleshooting Guide

## Problem: "Insufficient permissions for the specified parent" Error

This error occurs when the Google Drive service account doesn't have proper permissions to upload files to the specified folder.

## Solution Steps

### 1. Verify Service Account Configuration

1. **Check credentials file**: Ensure `google-drive-credentials.json` exists in the project root
2. **Verify service account email**: The service account email must be added to the Google Drive folder with appropriate permissions

### 2. Fix Google Drive Folder Permissions

1. **Go to Google Drive**: Navigate to the folder specified in `GOOGLE_DRIVE_FOLDER_ID`
2. **Share the folder**: 
   - Right-click the folder → Share
   - Add the service account email (found in `google-drive-credentials.json` under `client_email`)
   - Grant "Editor" permissions
   - Click "Send"

### 3. Alternative: Create a New Folder with Correct Permissions

If sharing the existing folder doesn't work:

1. **Create a new folder** in Google Drive
2. **Get the new folder ID** from the URL
3. **Update settings.py** with the new folder ID:
   ```python
   GOOGLE_DRIVE_FOLDER_ID = 'your-new-folder-id-here'
   ```
4. **Share the new folder** with the service account email

### 4. Verify Service Account Permissions

1. **Check service account email**:
   ```bash
   python -c "import json; print(json.load(open('google-drive-credentials.json'))['client_email'])"
   ```

2. **Test folder access**:
   ```bash
   python -c "
   from inventory.google_drive_upload import GoogleDriveUploader
   uploader = GoogleDriveUploader()
   print('Connection test:', uploader.test_connection())
   "
   ```

### 5. Update Google Drive API Scopes

The current implementation uses the correct scope:
```python
scopes=['https://www.googleapis.com/auth/drive']
```

This provides full access to Google Drive, which is necessary for uploading to shared folders.

### 6. Test the Integration

After making changes, run the test:
```bash
python test_google_drive.py
```

## Common Issues and Solutions

### Issue: "File not found" for credentials
**Solution**: Ensure `google-drive-credentials.json` is in the project root directory

### Issue: "Insufficient permissions"
**Solution**: 
1. Verify the service account email is correct
2. Ensure the folder is shared with the service account
3. Check that the folder ID is correct

### Issue: "Invalid folder ID"
**Solution**: 
1. Navigate to the folder in Google Drive
2. Copy the folder ID from the URL (the string after `/folders/`)
3. Update `GOOGLE_DRIVE_FOLDER_ID` in settings

## Verification Steps

1. **Check credentials file exists**:
   ```bash
   ls -la google-drive-credentials.json
   ```

2. **Verify folder ID**:
   ```bash
   python -c "from django.conf import settings; print('Folder ID:', settings.GOOGLE_DRIVE_FOLDER_ID)"
   ```

3. **Test connection**:
   ```bash
   python -c "
   from inventory.google_drive_upload import GoogleDriveUploader
   uploader = GoogleDriveUploader()
   uploader.test_connection()
   "
   ```

## Next Steps

1. Share the Google Drive folder with the service account email
2. Update the folder ID in settings if needed
3. Run the test again to verify the fix
4. Test with actual invoice generation
