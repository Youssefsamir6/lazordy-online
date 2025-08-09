# Lazordy Inventory Desktop App

A PySide6 desktop application for inventory management, invoicing, and analytics with a black–gold theme to match the Lazordy brand.

## Quickstart

1. Ensure Python 3.10+ is installed.
2. Place your logo image at `assets/logo.png` (use the provided Lazordy logo). PNG recommended.
3. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Run the app:

```bash
python -m app.main
```

## Features
- Product catalog with categories, sizes (Many-to-Many), photos, status, and stock
- Inventory tracking, adjustments, and movement history
- Invoicing with auto numbering `LZR-YYYY-MM-XXXX`, discounts, payments, statuses
- PDF invoices (Arabic/English) via WeasyPrint with QR and optional Drive upload
- Dashboard metrics and analytics
- Role-based access control and token-protected PDF (password = token)

## Google Drive Upload (optional)
Place OAuth credentials at `secrets/credentials.json` (Desktop app). On first upload you will be prompted to authorize and a token will be saved at `secrets/token.json`.

## Localization
Switch language in Settings between English and Arabic. Arabic PDFs require an Arabic-capable font. The app bundles Noto fonts if available, otherwise install a system Arabic font.

## Theming
A black–gold theme is applied via `assets/theme.qss`. Update the palette there if needed.

## Data
SQLite database stored at `data/app.db`.