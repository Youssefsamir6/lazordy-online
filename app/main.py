from __future__ import annotations
import sys
from datetime import datetime
from pathlib import Path
from typing import List
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QTableWidget, QTableWidgetItem, QSpinBox, QDoubleSpinBox, QTextEdit,
    QFileDialog, QMessageBox, QComboBox
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt

from .config import APP_NAME, LOGO_PATH, THEME_QSS_PATH
from .database import engine, Base, SessionLocal
from .models import (
    Product, Category, Size, ProductPhoto, StockMovement, StockMovementType,
    ProductStatus, Customer, Invoice, InvoiceItem, PaymentMethod, InvoiceStatus
)
from .services.auth_service import ensure_default_admin, hash_password, verify_password, generate_share_token, can_apply_manager_discount
from .services.pdf_service import render_invoice_pdf
from .services.drive_service import upload_file as drive_upload
from .ui_utils import load_translations, set_language, t


class LoginDialog(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t("login"))
        layout = QFormLayout(self)
        self.username = QLineEdit()
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password)
        self.submit = QPushButton(t("login"))
        layout.addRow(t("username"), self.username)
        layout.addRow(t("password"), self.password)
        layout.addRow(self.submit)


class DashboardTab(QWidget):
    def __init__(self, parent: 'MainWindow'):
        super().__init__()
        self.parent = parent
        self.layout = QVBoxLayout(self)
        self.metrics_label = QLabel("Loading metrics…")
        self.layout.addWidget(self.metrics_label)
        self.refresh()

    def refresh(self):
        db = SessionLocal()
        try:
            total_products = db.query(Product).count()
            total_customers = db.query(Customer).count()
            total_invoices = db.query(Invoice).count()
            total_revenue = sum((inv.total or 0.0) for inv in db.query(Invoice).filter(Invoice.status == InvoiceStatus.paid))
            self.metrics_label.setText(
                f"Products: {total_products} | Customers: {total_customers} | Invoices: {total_invoices} | Revenue: {total_revenue:.2f}"
            )
        finally:
            db.close()


class ProductsTab(QWidget):
    def __init__(self, parent: 'MainWindow'):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)

        # Controls
        controls = QHBoxLayout()
        self.add_btn = QPushButton(t("add_product"))
        self.adjust_btn = QPushButton(t("stock_adjustment"))
        controls.addWidget(self.add_btn)
        controls.addWidget(self.adjust_btn)
        layout.addLayout(controls)

        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Code", "Qty", "Price", "Status", t("low_stock")])
        layout.addWidget(self.table)

        self.add_btn.clicked.connect(self.add_product)
        self.adjust_btn.clicked.connect(self.adjust_stock)
        self.refresh()

    def refresh(self):
        db = SessionLocal()
        try:
            products: List[Product] = db.query(Product).all()
            self.table.setRowCount(0)
            for p in products:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(p.id)))
                self.table.setItem(row, 1, QTableWidgetItem(p.name))
                self.table.setItem(row, 2, QTableWidgetItem(p.item_code))
                self.table.setItem(row, 3, QTableWidgetItem(str(p.quantity)))
                self.table.setItem(row, 4, QTableWidgetItem(f"{p.price:.2f}"))
                self.table.setItem(row, 5, QTableWidgetItem(p.status))
                low_flag = "YES" if p.quantity <= (p.low_stock_threshold or 1) else ""
                self.table.setItem(row, 6, QTableWidgetItem(low_flag))
        finally:
            db.close()

    def add_product(self):
        dialog = QWidget(); dialog.setWindowTitle(t("add_product"))
        form = QFormLayout(dialog)
        name = QLineEdit(); code = QLineEdit(); price = QDoubleSpinBox(); price.setMaximum(1e9); price.setDecimals(2)
        cost = QDoubleSpinBox(); cost.setMaximum(1e9); cost.setDecimals(2)
        qty = QSpinBox(); qty.setMaximum(100000)
        color = QLineEdit(); measurements = QLineEdit()
        threshold = QSpinBox(); threshold.setRange(0, 100000); threshold.setValue(1)
        status = QComboBox(); status.addItems([s.value for s in ProductStatus])
        form.addRow("Name", name)
        form.addRow("Code", code)
        form.addRow("Price", price)
        form.addRow("Cost", cost)
        form.addRow("Quantity", qty)
        form.addRow("Color", color)
        form.addRow("Measurements", measurements)
        form.addRow(t("low_stock"), threshold)
        form.addRow("Status", status)
        save = QPushButton(t("save")); form.addRow(save)

        def do_save():
            db = SessionLocal()
            try:
                p = Product(
                    name=name.text(), item_code=code.text(), price=float(price.value()), cost=float(cost.value()),
                    quantity=int(qty.value()), color=color.text() or None, measurements=measurements.text() or None,
                    low_stock_threshold=int(threshold.value()), status=ProductStatus(status.currentText())
                )
                db.add(p)
                # Record stock movement
                if p.quantity:
                    mv = StockMovement(product=p, quantity_change=p.quantity, movement_type=StockMovementType.incoming, reason="Initial stock")
                    db.add(mv)
                db.commit()
                dialog.close(); self.refresh(); self.parent.dashboard.refresh()
            except Exception as e:
                db.rollback(); QMessageBox.critical(self, "Error", str(e))
            finally:
                db.close()

        save.clicked.connect(do_save)
        dialog.setLayout(form); dialog.setWindowModality(Qt.ApplicationModal); dialog.show()
        self._dialog = dialog

    def adjust_stock(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "", "Select a product row first."); return
        product_id = int(self.table.item(row, 0).text())
        dialog = QWidget(); dialog.setWindowTitle(t("stock_adjustment"))
        form = QFormLayout(dialog)
        qty = QSpinBox(); qty.setRange(-100000, 100000)
        reason = QLineEdit()
        save = QPushButton(t("save"))
        form.addRow("Quantity change", qty)
        form.addRow("Reason", reason)
        form.addRow(save)

        def do_adjust():
            db = SessionLocal()
            try:
                p = db.get(Product, product_id)
                change = int(qty.value())
                p.quantity += change
                if p.quantity <= 0:
                    p.status = ProductStatus.out_of_stock
                mv = StockMovement(product=p, quantity_change=change, movement_type=StockMovementType.adjustment, reason=reason.text() or None)
                db.add(mv); db.commit(); dialog.close(); self.refresh(); self.parent.dashboard.refresh()
            except Exception as e:
                db.rollback(); QMessageBox.critical(self, "Error", str(e))
            finally:
                db.close()

        save.clicked.connect(do_adjust)
        dialog.setLayout(form); dialog.setWindowModality(Qt.ApplicationModal); dialog.show()
        self._dialog = dialog


class InvoicesTab(QWidget):
    def __init__(self, parent: 'MainWindow'):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self.create_btn = QPushButton(t("create_invoice"))
        self.pay_btn = QPushButton(t("pay"))
        self.pdf_btn = QPushButton(t("generate_pdf"))
        self.drive_btn = QPushButton(t("upload_drive"))
        controls.addWidget(self.create_btn); controls.addWidget(self.pay_btn); controls.addWidget(self.pdf_btn); controls.addWidget(self.drive_btn)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Number", "Customer", "Total", "Status", "Created"])
        layout.addWidget(self.table)

        self.create_btn.clicked.connect(self.create_invoice)
        self.pay_btn.clicked.connect(self.pay_invoice)
        self.pdf_btn.clicked.connect(self.generate_pdf)
        self.drive_btn.clicked.connect(self.upload_drive)
        self.refresh()

    def refresh(self):
        db = SessionLocal()
        try:
            invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
            self.table.setRowCount(0)
            for inv in invoices:
                row = self.table.rowCount(); self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(inv.id)))
                self.table.setItem(row, 1, QTableWidgetItem(inv.invoice_number))
                self.table.setItem(row, 2, QTableWidgetItem(inv.customer.name if inv.customer else ""))
                self.table.setItem(row, 3, QTableWidgetItem(f"{inv.total:.2f}"))
                self.table.setItem(row, 4, QTableWidgetItem(inv.status))
                self.table.setItem(row, 5, QTableWidgetItem(inv.created_at.strftime("%Y-%m-%d %H:%M")))
        finally:
            db.close()

    def _next_invoice_number(self, db) -> str:
        now = datetime.now()
        prefix = f"LZR-{now.year:04d}-{now.month:02d}-"
        count = db.query(Invoice).filter(Invoice.invoice_number.like(prefix + "%")).count()
        return f"{prefix}{count+1:04d}"

    def create_invoice(self):
        dialog = QWidget(); dialog.setWindowTitle(t("create_invoice"))
        form = QFormLayout(dialog)
        customer_name = QLineEdit()
        product_code = QLineEdit(); qty = QSpinBox(); qty.setRange(1, 100000);
        disc_reg = QDoubleSpinBox(); disc_reg.setDecimals(2); disc_reg.setMaximum(1e9)
        disc_mgr = QDoubleSpinBox(); disc_mgr.setDecimals(2); disc_mgr.setMaximum(1e9)
        payment = QComboBox(); payment.addItems([m.value for m in PaymentMethod])
        save = QPushButton(t("save"))
        form.addRow("Customer name", customer_name)
        form.addRow("Item code", product_code)
        form.addRow("Qty", qty)
        form.addRow("Discount", disc_reg)
        form.addRow(t("manager_discount"), disc_mgr)
        form.addRow("Payment", payment)
        form.addRow(save)

        def do_create():
            db = SessionLocal()
            try:
                # customer
                cust = None
                if customer_name.text():
                    cust = db.query(Customer).filter_by(name=customer_name.text()).first()
                    if not cust:
                        cust = Customer(name=customer_name.text())
                        db.add(cust); db.flush()
                # product
                prod = db.query(Product).filter_by(item_code=product_code.text()).first()
                if not prod:
                    raise ValueError("Product code not found")
                if prod.quantity < qty.value():
                    raise ValueError("Insufficient stock")
                inv = Invoice(
                    invoice_number=self._next_invoice_number(db),
                    customer=cust,
                    status=InvoiceStatus.uncompleted,
                    payment_method=PaymentMethod(payment.currentText())
                )
                item = InvoiceItem(invoice=inv, product=prod, quantity=int(qty.value()), unit_price=prod.price, subtotal=float(qty.value()) * prod.price)
                inv.subtotal = item.subtotal
                inv.discount_regular = float(disc_reg.value())
                # Manager discount requires permission; UI does not enforce who is logged in, so keep simple here
                inv.discount_manager = float(disc_mgr.value())
                inv.total = max(0.0, inv.subtotal - inv.discount_regular - inv.discount_manager)
                # reserve stock
                prod.quantity -= int(qty.value())
                mv = StockMovement(product=prod, quantity_change=-int(qty.value()), movement_type=StockMovementType.outgoing, reason=f"Invoice {inv.invoice_number}")
                db.add_all([inv, item, mv]); db.commit(); dialog.close(); self.refresh(); self.parent.dashboard.refresh()
            except Exception as e:
                db.rollback(); QMessageBox.critical(self, "Error", str(e))
            finally:
                db.close()

        save.clicked.connect(do_create)
        dialog.setLayout(form); dialog.setWindowModality(Qt.ApplicationModal); dialog.show(); self._dialog = dialog

    def _current_invoice(self, db):
        row = self.table.currentRow()
        if row < 0:
            return None
        inv_id = int(self.table.item(row, 0).text())
        return db.get(Invoice, inv_id)

    def pay_invoice(self):
        db = SessionLocal()
        try:
            inv = self._current_invoice(db)
            if not inv:
                QMessageBox.information(self, "", "Select an invoice."); return
            inv.status = InvoiceStatus.paid
            db.commit(); self.refresh(); self.parent.dashboard.refresh()
        finally:
            db.close()

    def generate_pdf(self):
        db = SessionLocal()
        try:
            inv = self._current_invoice(db)
            if not inv:
                QMessageBox.information(self, "", "Select an invoice."); return
            ctx = {
                "invoice_number": inv.invoice_number,
                "created_at": inv.created_at.strftime("%Y-%m-%d %H:%M"),
                "customer": inv.customer,
                "items": [
                    {"name": it.product.name, "quantity": it.quantity, "unit_price": it.unit_price, "subtotal": it.subtotal}
                    for it in inv.items
                ],
                "subtotal": inv.subtotal,
                "discount_regular": inv.discount_regular,
                "discount_manager": inv.discount_manager,
                "total": inv.total,
                "status": inv.status,
                "payment_method": inv.payment_method,
            }
            token = inv.share_token or generate_share_token()
            inv.share_token = token
            pdf_path = render_invoice_pdf(ctx, share_link=None, token=token)
            db.commit()
            QMessageBox.information(self, "PDF", f"Saved: {pdf_path}")
        except Exception as e:
            db.rollback(); QMessageBox.critical(self, "Error", str(e))
        finally:
            db.close()

    def upload_drive(self):
        db = SessionLocal()
        try:
            inv = self._current_invoice(db)
            if not inv:
                QMessageBox.information(self, "", "Select an invoice."); return
            ctx = {
                "invoice_number": inv.invoice_number,
                "created_at": inv.created_at.strftime("%Y-%m-%d %H:%M"),
                "customer": inv.customer,
                "items": [
                    {"name": it.product.name, "quantity": it.quantity, "unit_price": it.unit_price, "subtotal": it.subtotal}
                    for it in inv.items
                ],
                "subtotal": inv.subtotal,
                "discount_regular": inv.discount_regular,
                "discount_manager": inv.discount_manager,
                "total": inv.total,
                "status": inv.status,
                "payment_method": inv.payment_method,
            }
            token = inv.share_token or generate_share_token()
            inv.share_token = token
            pdf_path = render_invoice_pdf(ctx, share_link=f"Invoice {inv.invoice_number}", token=token)
            try:
                file_id, link = drive_upload(pdf_path, filename=pdf_path.name)
                inv.drive_file_id = file_id; inv.drive_share_link = link
                # Re-render with actual link + QR
                pdf_path = render_invoice_pdf(ctx, share_link=link, token=token)
                db.commit()
                QMessageBox.information(self, "Drive", f"Uploaded: {link}")
            except Exception as e:
                QMessageBox.warning(self, "Drive", f"Upload skipped: {e}")
                db.commit()
        except Exception as e:
            db.rollback(); QMessageBox.critical(self, "Error", str(e))
        finally:
            db.close()


class CustomersTab(QWidget):
    def __init__(self, parent: 'MainWindow'):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)

        controls = QHBoxLayout(); self.add_btn = QPushButton("Add Customer"); controls.addWidget(self.add_btn)
        layout.addLayout(controls)
        self.table = QTableWidget(0, 3); self.table.setHorizontalHeaderLabels(["ID", "Name", "Phone"])
        layout.addWidget(self.table)
        self.add_btn.clicked.connect(self.add_customer)
        self.refresh()

    def refresh(self):
        db = SessionLocal();
        try:
            customers = db.query(Customer).all(); self.table.setRowCount(0)
            for c in customers:
                r = self.table.rowCount(); self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(str(c.id)))
                self.table.setItem(r, 1, QTableWidgetItem(c.name))
                self.table.setItem(r, 2, QTableWidgetItem(c.phone or ""))
        finally:
            db.close()

    def add_customer(self):
        dialog = QWidget(); dialog.setWindowTitle("Add Customer"); form = QFormLayout(dialog)
        name = QLineEdit(); phone = QLineEdit(); save = QPushButton(t("save"))
        form.addRow("Name", name); form.addRow("Phone", phone); form.addRow(save)
        def do_save():
            db = SessionLocal();
            try:
                db.add(Customer(name=name.text(), phone=phone.text() or None)); db.commit(); dialog.close(); self.refresh()
            except Exception as e:
                db.rollback(); QMessageBox.critical(self, "Error", str(e))
            finally:
                db.close()
        save.clicked.connect(do_save)
        dialog.setLayout(form); dialog.setWindowModality(Qt.ApplicationModal); dialog.show(); self._dialog = dialog


class SettingsTab(QWidget):
    def __init__(self, parent: 'MainWindow'):
        super().__init__()
        layout = QFormLayout(self)
        self.lang = QComboBox(); self.lang.addItems(["en", "ar"])
        self.save = QPushButton(t("save"))
        layout.addRow(t("language"), self.lang)
        layout.addRow(self.save)
        self.save.clicked.connect(self.apply)

    def apply(self):
        set_language(self.lang.currentText())
        QMessageBox.information(self, "", "Language switched. Restart app to fully apply.")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1000, 700)
        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))

        self.tabs = QTabWidget()
        self.dashboard = DashboardTab(self)
        self.products = ProductsTab(self)
        self.invoices = InvoicesTab(self)
        self.customers = CustomersTab(self)
        self.settings = SettingsTab(self)
        self.tabs.addTab(self.dashboard, t("dashboard"))
        self.tabs.addTab(self.products, t("products"))
        self.tabs.addTab(self.invoices, t("invoices"))
        self.tabs.addTab(self.customers, t("customers"))
        self.tabs.addTab(self.settings, t("settings"))
        self.setCentralWidget(self.tabs)


def main():
    load_translations()
    app = QApplication(sys.argv)
    if THEME_QSS_PATH.exists():
        app.setStyleSheet(THEME_QSS_PATH.read_text())

    # DB setup
    Base.metadata.create_all(bind=engine)
    db = SessionLocal(); ensure_default_admin(db); db.close()

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())