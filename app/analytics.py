from __future__ import annotations
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from .models import Invoice, InvoiceStatus, InvoiceItem


def revenue_last_days(db: Session, days: int = 30) -> list[tuple[str, float]]:
    start = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(func.strftime('%Y-%m-%d', Invoice.created_at), func.sum(Invoice.total))
        .filter(Invoice.status == InvoiceStatus.paid)
        .filter(Invoice.created_at >= start)
        .group_by(func.strftime('%Y-%m-%d', Invoice.created_at))
        .order_by(func.strftime('%Y-%m-%d', Invoice.created_at))
        .all()
    )
    return [(d, r or 0.0) for d, r in rows]


def best_selling_products(db: Session, limit: int = 10) -> list[tuple[str, int]]:
    rows = (
        db.query(InvoiceItem.product_id, func.sum(InvoiceItem.quantity))
        .join(Invoice)
        .filter(Invoice.status == InvoiceStatus.paid)
        .group_by(InvoiceItem.product_id)
        .order_by(func.sum(InvoiceItem.quantity).desc())
        .limit(limit)
        .all()
    )
    # resolve product names lazily to avoid circular import
    from .models import Product
    result = []
    for pid, qty in rows:
        result.append((db.get(Product, pid).name, int(qty or 0)))
    return result