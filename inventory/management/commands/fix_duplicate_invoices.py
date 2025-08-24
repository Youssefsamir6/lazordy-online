from django.core.management.base import BaseCommand
from inventory.models import Invoice
from django.db import transaction
from django.utils import timezone

class Command(BaseCommand):
    help = 'Fix duplicate invoice numbers in the database'

    def handle(self, *args, **options):
        """Fix any existing duplicate invoice numbers."""
        self.stdout.write("Checking for duplicate invoice numbers...")
        
        # Find duplicates
        invoice_numbers = {}
        
        for invoice in Invoice.objects.all():
            if invoice.invoice_number in invoice_numbers:
                invoice_numbers[invoice.invoice_number].append(invoice)
            else:
                invoice_numbers[invoice.invoice_number] = [invoice]
        
        # Filter to only actual duplicates
        duplicates = {k: v for k, v in invoice_numbers.items() if len(v) > 1}
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS("No duplicate invoice numbers found."))
            return
        
        self.stdout.write(
            self.style.WARNING(f"Found {len(duplicates)} duplicate invoice numbers:")
        )
        
        with transaction.atomic():
            for invoice_number, invoices in duplicates.items():
                self.stdout.write(f"\nProcessing duplicates for: {invoice_number}")
                
                # Keep the first invoice with this number
                first_invoice = invoices[0]
                self.stdout.write(f"  Keeping invoice ID {first_invoice.id} with number {invoice_number}")
                
                # Rename the rest
                for i, invoice in enumerate(invoices[1:], 1):
                    now = timezone.now()
                    year = now.strftime("%Y")
                    month = now.strftime("%m")
                    timestamp = now.strftime("%H%M%S")
                    new_number = f"{invoice_number}-FIX-{year}{month}{timestamp}-{i}"
                    
                    invoice.invoice_number = new_number
                    invoice.save(update_fields=['invoice_number'])
                    self.stdout.write(f"  Renamed invoice ID {invoice.id} to {new_number}")
        
        self.stdout.write(
            self.style.SUCCESS("\nDuplicate invoice numbers have been fixed successfully!")
        )
