"""
gui/receipt.py
Displays a booking's receipt on screen with options to view/print the
PDF, reprint, or email (placeholder) the receipt to the customer.
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

import config
from utils.helpers import format_currency
from utils.receipt_generator import generate_full_receipt
from gui.widgets import StyledButton


class ReceiptWindow(tk.Frame):
    def __init__(self, master, db, app, booking_id):
        self.theme = config.DARK_THEME if db.get_setting("theme", "dark") == "dark" else config.LIGHT_THEME
        super().__init__(master, bg=self.theme["bg"])
        self.db = db
        self.app = app
        self.booking_id = booking_id
        self.booking = db.get_booking(booking_id)

        self.pack(fill="both", expand=True)
        self._build_ui()

    def _build_ui(self):
        theme = self.theme
        header = tk.Frame(self, bg=theme["surface"])
        header.pack(fill="x")
        tk.Label(header, text="🧾  Booking Receipt", font=config.FONT_HEADING, bg=theme["surface"],
                 fg=theme["primary"]).pack(side="left", padx=16, pady=12)
        StyledButton(header, "⬅ Dashboard", command=self.app.show_dashboard, theme=theme,
                     kind="muted", width=16).pack(side="right", padx=16, pady=8)
        StyledButton(header, "📋 Bookings", command=self.app.show_bookings, theme=theme,
                     kind="muted", width=16).pack(side="right", padx=4, pady=8)

        if not self.booking:
            tk.Label(self, text="Booking not found.", bg=theme["bg"], fg=theme["danger"],
                      font=config.FONT_HEADING).pack(pady=40)
            return

        b = self.booking
        card = tk.Frame(self, bg=theme["surface"], padx=30, pady=24)
        card.pack(padx=40, pady=30, fill="both", expand=True)

        tk.Label(card, text=config.APP_NAME, font=config.FONT_TITLE, bg=theme["surface"],
                  fg=theme["primary"]).pack()
        tk.Label(card, text=f"Booking ID: {b['booking_code']}", font=config.FONT_SUBHEADING,
                  bg=theme["surface"], fg=theme["text"]).pack(pady=(4, 16))

        details = [
            ("Customer", b["customer_name"]),
            ("Phone", b["phone"]),
            ("Movie", f"{b['movie_name']} ({b['language']} / {b['genre']})"),
            ("Show", f"{b['show_date']} at {b['show_time']} - Hall {b['hall_number']}"),
            ("Seats", b["seats"]),
            ("Quantity", str(b["quantity"])),
            ("Payment Method", b["payment_method"] or "-"),
            ("Discount", format_currency(b["discount"])),
            ("Tax (GST)", format_currency(b["tax"])),
            ("Total Amount", format_currency(b["total_amount"])),
            ("Status", b["status"]),
        ]
        for label, value in details:
            row = tk.Frame(card, bg=theme["surface"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, font=config.FONT_SMALL, bg=theme["surface"],
                      fg=theme["text_muted"], width=18, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=config.FONT_NORMAL, bg=theme["surface"],
                      fg=theme["text"], anchor="w").pack(side="left")

        btn_row = tk.Frame(card, bg=theme["surface"])
        btn_row.pack(pady=20)
        StyledButton(btn_row, "🖨  Print / Open PDF", command=self._open_pdf, theme=theme,
                     kind="primary", width=20).pack(side="left", padx=6)
        StyledButton(btn_row, "🔁  Reprint Receipt", command=self._reprint, theme=theme,
                     kind="accent", width=20).pack(side="left", padx=6)
        StyledButton(btn_row, "✉  Email Receipt", command=self._email_receipt, theme=theme,
                     kind="muted", width=20).pack(side="left", padx=6)

    def _pdf_path(self):
        return os.path.join(config.RECEIPTS_DIR, f"{self.booking['booking_code']}.pdf")

    def _open_pdf(self):
        path = self._pdf_path()
        if not os.path.exists(path):
            self._reprint()
        path = self._pdf_path()
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # noqa
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception:
            messagebox.showinfo("Receipt Location", f"Receipt saved at:\n{path}")

    def _reprint(self):
        try:
            generate_full_receipt(dict(self.booking))
            messagebox.showinfo("Receipt Regenerated", "Receipt files (TXT/PDF/QR) regenerated in the "
                                                          "receipts/ folder.")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not regenerate receipt:\n{exc}")

    def _email_receipt(self):
        # Placeholder implementation - no SMTP integration configured.
        messagebox.showinfo(
            "Email Receipt (Placeholder)",
            "Email delivery is not configured in this build.\n\n"
            "To enable it, integrate an SMTP client (e.g. smtplib) inside "
            "gui/receipt.py -> _email_receipt() and provide server credentials."
        )
