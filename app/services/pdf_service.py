from __future__ import annotations
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS
from pypdf import PdfReader, PdfWriter
from ..config import TEMPLATES_DIR, DATA_DIR
from .qr_service import generate_qr_png


env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_invoice_pdf(context: dict, share_link: str | None, token: str | None) -> Path:
    template = env.get_template("invoice.html")
    html_str = template.render(**context, share_link=share_link)
    html = HTML(string=html_str, base_url=str(TEMPLATES_DIR))
    css = CSS(filename=str(TEMPLATES_DIR / "invoice.css"))
    out_pdf_path = DATA_DIR / f"invoice_{context['invoice_number']}.pdf"
    html.write_pdf(target=str(out_pdf_path), stylesheets=[css])

    if token:
        # Apply password protection so the token works as a secure sharing secret
        reader = PdfReader(str(out_pdf_path))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(user_password=token, owner_password=token)
        protected_path = DATA_DIR / f"invoice_{context['invoice_number']}_protected.pdf"
        with protected_path.open("wb") as f:
            writer.write(f)
        out_pdf_path.unlink(missing_ok=True)
        out_pdf_path = protected_path

    # Generate QR for the link if present
    if share_link:
        qr_path = generate_qr_png(share_link, context['invoice_number'])
        # Re-render with QR embedded
        html_str = template.render(**context, share_link=share_link, qr_path=str(qr_path))
        html = HTML(string=html_str, base_url=str(TEMPLATES_DIR))
        html.write_pdf(target=str(out_pdf_path), stylesheets=[css])
        if token:
            reader = PdfReader(str(out_pdf_path))
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(user_password=token, owner_password=token)
            with out_pdf_path.open("wb") as f:
                writer.write(f)

    return out_pdf_path