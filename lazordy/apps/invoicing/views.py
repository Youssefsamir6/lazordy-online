from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from .models import Invoice
import io


def invoice_list(request):
    invoices = Invoice.objects.select_related('customer').all().order_by('-created_at')
    return render(request, 'invoicing/invoice_list.html', {"invoices": invoices})


def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    return render(request, 'invoicing/invoice_detail.html', {"invoice": invoice})


def invoice_share(request, token):
    invoice = get_object_or_404(Invoice, token=token)
    return render(request, 'invoicing/invoice_share.html', {"invoice": invoice})


def _render_invoice_html(invoice):
    return render_to_string('invoicing/invoice_pdf.html', {"invoice": invoice})


def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    html = _render_invoice_html(invoice)

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{invoice.number}.pdf"'
        return response
    except Exception:
        # Fallback to simple PDF via reportlab
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4

        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        textobject = p.beginText(40, 800)
        textobject.textLine(f"Invoice: {invoice.number}")
        textobject.textLine(f"Customer: {invoice.customer}")
        textobject.textLine(f"Total: {invoice.total}")
        p.drawText(textobject)
        p.showPage()
        p.save()
        buffer.seek(0)
        return HttpResponse(buffer.read(), content_type='application/pdf')
