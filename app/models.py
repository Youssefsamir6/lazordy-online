from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Enum as SAEnum, ForeignKey, Boolean, Table, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .database import Base

class ProductStatus(str, Enum):
    available = "available"
    sold = "sold"
    reserved = "reserved"
    out_of_stock = "out_of_stock"

class PaymentMethod(str, Enum):
    cash = "cash"
    visa = "visa"
    instapay = "instapay"

class InvoiceStatus(str, Enum):
    draft = "draft"
    sent = "sent"
    uncompleted = "uncompleted"
    paid = "paid"
    cancelled = "cancelled"

product_sizes = Table(
    "product_sizes",
    Base.metadata,
    Column("product_id", ForeignKey("products.id"), primary_key=True),
    Column("size_id", ForeignKey("sizes.id"), primary_key=True),
)

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)

    parent: Mapped["Category"] = relationship("Category", remote_side=[id], backref="children")

class Size(Base):
    __tablename__ = "sizes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

class ProductPhoto(Base):
    __tablename__ = "product_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    item_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    color: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    measurements: Mapped[Optional[str]] = mapped_column(String(120), default=None)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[ProductStatus] = mapped_column(SAEnum(ProductStatus), default=ProductStatus.available, nullable=False)

    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    category: Mapped[Category] = relationship("Category", backref="products")

    sizes: Mapped[list[Size]] = relationship("Size", secondary=product_sizes, backref="products")
    photos: Mapped[list[ProductPhoto]] = relationship("ProductPhoto", cascade="all, delete-orphan", backref="product")

class StockMovementType(str, Enum):
    incoming = "incoming"
    outgoing = "outgoing"
    adjustment = "adjustment"

class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    movement_type: Mapped[StockMovementType] = mapped_column(SAEnum(StockMovementType), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    product: Mapped[Product] = relationship("Product", backref="stock_movements")

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    email: Mapped[Optional[str]] = mapped_column(String(120), default=None)
    address: Mapped[Optional[str]] = mapped_column(String(255), default=None)

class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("invoice_number", name="uq_invoice_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(32), nullable=False)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"))
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    discount_regular: Mapped[float] = mapped_column(Float, default=0.0)
    discount_manager: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(SAEnum(PaymentMethod), default=None)
    status: Mapped[InvoiceStatus] = mapped_column(SAEnum(InvoiceStatus), default=InvoiceStatus.draft)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    share_token: Mapped[str] = mapped_column(String(64), nullable=True)
    drive_file_id: Mapped[Optional[str]] = mapped_column(String(128), default=None)
    drive_share_link: Mapped[Optional[str]] = mapped_column(String(512), default=None)

    customer: Mapped[Customer] = relationship("Customer", backref="invoices")
    items: Mapped[list["InvoiceItem"]] = relationship("InvoiceItem", cascade="all, delete-orphan", backref="invoice")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    product: Mapped[Product] = relationship("Product")

class Role(str, Enum):
    admin = "admin"
    manager = "manager"
    cashier = "cashier"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[Role] = mapped_column(SAEnum(Role), default=Role.cashier, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)