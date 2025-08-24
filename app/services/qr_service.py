from __future__ import annotations
from pathlib import Path
import qrcode
from ..config import DATA_DIR


def generate_qr_png(data: str, filename_hint: str) -> Path:
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    out_path = DATA_DIR / f"qr_{filename_hint}.png"
    img.save(out_path)
    return out_path