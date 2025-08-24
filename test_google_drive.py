#!/usr/bin/env python
import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from inventory.google_drive_upload import GoogleDriveUploader
from inventory.models import Invoice
from django.conf import settings

def test_google_drive_setup():
    """Test Google Drive configuration and upload functionality."""
    print("🔍 Testing Google Drive Integration...")
    
    # Test 1: Check if credentials file exists
    credentials_path = os.path.join(settings.BASE_DIR, 'google-drive-credentials.json')
    if not os.path.exists(credentials_path):
        print("❌ google-drive-credentials.json not found in project root")
        print("   Please download your service account credentials and save as google-drive-credentials.json")
        return False
    
    print("✅ google-drive-credentials.json found")
    
    # Test 2: Check if folder ID is configured
    folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
    if not folder_id or folder_id == '1OH1h3PF5HxxyqBxG7yu2n8fTTAScKJtg':
        print("❌ GOOGLE_DRIVE_FOLDER_ID not configured in settings")
        print("   Please set GOOGLE_DRIVE_FOLDER_ID in your .env file or settings.py")
        return False
    
    print(f"✅ Google Drive folder ID configured: {folder_id}")
    
    # Test 3: Test GoogleDriveUploader initialization
    try:
        uploader = GoogleDriveUploader()
        print("✅ GoogleDriveUploader initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize GoogleDriveUploader: {e}")
        return False
    
    # Test 4: Test with a sample file (create a simple test PDF)
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import tempfile
        
        # Create a simple test PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            c = canvas.Canvas(tmp_file.name, pagesize=letter)
            c.drawString(100, 750, "Test PDF for Google Drive Upload")
            c.drawString(100, 730, "This is a test file to verify Google Drive integration")
            c.save()
            
            # Test upload
            uploaded_url = uploader.upload_pdf(tmp_file.name, "test_upload.pdf")
            
            if uploaded_url:
                print(f"✅ Test upload successful! URL: {uploaded_url}")
                
                # Clean up test file
                os.unlink(tmp_file.name)
                return True
            else:
                print("❌ Upload failed - no URL returned")
                return False
                
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        return False

def test_invoice_model():
    """Test if Invoice model has required fields."""
    print("\n🔍 Testing Invoice Model...")
    
    # Check if Invoice model has cloud_pdf_url field
    try:
        invoice = Invoice.objects.first()
        if invoice:
            print("✅ Invoice model accessible")
            print(f"   Sample invoice: #{invoice.invoice_number}")
            print(f"   Current cloud_pdf_url: {invoice.cloud_pdf_url}")
        else:
            print("⚠️  No invoices found in database")
            print("   Create a test invoice to verify functionality")
        return True
    except Exception as e:
        print(f"❌ Invoice model test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Google Drive Integration Test Suite")
    print("=" * 50)
    
    success = True
    
    # Test Google Drive setup
    success &= test_google_drive_setup()
    
    # Test Invoice model
    success &= test_invoice_model()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Google Drive integration is ready.")
        print("\nNext steps:")
        print("1. Place google-drive-credentials.json in project root")
        print("2. Set GOOGLE_DRIVE_FOLDER_ID in .env file")
        print("3. Install required packages: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        print("4. Test with actual invoice generation")
    else:
        print("⚠️  Some tests failed. Please address the issues above.")
