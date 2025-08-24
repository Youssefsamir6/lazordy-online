import cloudinary
import cloudinary.uploader
from django.conf import settings
import time

cloudinary.config(
    cloud_name=settings.CLOUDINARY['cloud_name'],
    api_key=settings.CLOUDINARY['api_key'],
    api_secret=settings.CLOUDINARY['api_secret']
)

def upload_invoice_to_cloud(file_path, public_id=None, folder="lazordy_invoices/"):
    """
    Upload a PDF file to Cloudinary and return the secure URL.
    
    Args:
        file_path: Path to the PDF file
        public_id: Optional public ID for the file
        folder: Cloudinary folder path
    
    Returns:
        str: Secure URL of the uploaded file
    """
    try:
        # Remove timestamp parameter to fix stale request error
        response = cloudinary.uploader.upload(
            file_path,
            resource_type="raw",  # for PDFs
            public_id=public_id,
            folder=folder,
            overwrite=True,
            invalidate=True
        )
        return response.get("secure_url")
    except Exception as e:
        # Log the error for debugging
        print(f"Cloudinary upload error: {str(e)}")
        raise Exception(f"Cloudinary upload failed: {str(e)}")
