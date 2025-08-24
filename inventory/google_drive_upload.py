import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class GoogleDriveUploader:
    def __init__(self):
        # Path to your service account credentials
        credentials_path = os.path.join(settings.BASE_DIR, 'google-drive-credentials.json')
        
        # Create credentials from service account file with broader scope
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # Build the Drive service
        self.service = build('drive', 'v3', credentials=credentials)
        
        # Google Drive folder ID where invoices will be uploaded
        self.folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
    
    def upload_pdf(self, file_path, filename):
        """Upload a PDF file to Google Drive and return the shareable link."""
        try:
            # First, let's check if we have access to the folder
            try:
                folder = self.service.files().get(fileId=self.folder_id).execute()
                logger.info(f"Successfully accessed folder: {folder.get('name', 'Unknown')}")
            except Exception as e:
                logger.error(f"Cannot access folder {self.folder_id}: {e}")
                raise Exception(f"Cannot access Google Drive folder. Please check folder permissions and ID.")
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Create file metadata
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id],
                'mimeType': 'application/pdf'
            }
            
            # Create media upload
            media = MediaIoBaseUpload(
                io.BytesIO(file_content),
                mimetype='application/pdf',
                resumable=True
            )
            
            # Upload file
            logger.info(f"Uploading {filename} to Google Drive folder {self.folder_id}")
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            logger.info(f"File uploaded successfully with ID: {file['id']}")
            
            # Make file publicly accessible
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            self.service.permissions().create(
                fileId=file['id'],
                body=permission
            ).execute()
            
            logger.info(f"File permissions set to public")
            
            # Return the shareable link
            return file['webViewLink']
            
        except Exception as e:
            logger.error(f"Error uploading to Google Drive: {e}")
            raise e
    
    def test_connection(self):
        """Test the Google Drive connection and permissions."""
        try:
            # Test folder access
            folder = self.service.files().get(fileId=self.folder_id).execute()
            logger.info(f"✅ Successfully connected to folder: {folder.get('name', 'Unknown')}")
            
            # Test file listing in folder
            results = self.service.files().list(
                q=f"'{self.folder_id}' in parents",
                pageSize=10,
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"✅ Found {len(files)} files in folder")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
