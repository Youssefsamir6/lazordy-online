import cloudinary
import cloudinary.uploader
from django.conf import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY['cloud_name'],
    api_key=settings.CLOUDINARY['api_key'],
    api_secret=settings.CLOUDINARY['api_secret']
)

def upload_invoice_to_cloud(file_path, public_id=None):
    response = cloudinary.uploader.upload(
        file_path,
        resource_type="raw",  # for PDFs
        public_id=public_id,
        folder="lazordy_invoices/"
    )
    return response.get("secure_url")
