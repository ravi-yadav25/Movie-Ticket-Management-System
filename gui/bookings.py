"""
gui/bookings.py
View Bookings screen: search, filter, sort, update customer info,
cancel/delete bookings, print/reprint tickets, and export to CSV.
"""

import tkinter as tk
from tkinter import ttk, messagebox

import config
from utils import validation
from utils.helpers import format_currency
from utils.csv_export import export_bookings_csv
from utils.receipt_generator import generate_full_receipt
from gui.widgets import StyledButton, style_ttk_treeview


class BookingsWindow(tk.Frame):
    def __init__(self, master, db, app):
        self.theme = config.DARK_THEME if db.get_setting("theme", "dark") == "dark" else config.LIGHT_THEME
        super().__init__(master, bg=self.theme["bg"])
        self.db = db
        self.app = app
        self.sort_column = "created_at"
        self.sort_reverse = True

        self.pack(fill="both", expand=True)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        theme = self.theme
        header = tk.Frame(self, bg=theme["surface"])
        header.pack(fill="x")
        tk.Label(header, text="📋  View Bookings", font=config.FONT_HEADING, bg=theme["surface"],
                 fg=theme["primary"]).pack(side="left", padx=16, pady=12)
        StyledButton(header, "⬅ Dashboard", command=self.app.show_dashboard, theme=theme,
                     kind="muted", width=18).pack(side="right", padx=16, pady=8)

        toolbar = tk.Frame(self, bg=theme["bg"])
        toolbar.pack(fill="x", padx=16, pady=(12, 0))

        tk.Label(toolbar, text="Search (name / phone / booking ID):", bg=theme["bg"], fg=theme["text_muted"],
                  font=config.FONT_SMALL).pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(toolbar, textvariable=self.search_var, font=config.FONT_NORMAL,
                                 bg=theme["entry_bg"], fg=theme["text"], insertbackground=theme["text"],
                                 relief="flat", width=28)
        search_entry.pack(side="left", padx=8, ipady=4)
        search_entry.bind("<Return>", lambda e: self.refresh())

        tk.Label(toolbar, text="Status:", bg=theme["bg"], fg=theme["text_muted"],
                  font=config.FONT_SMALL).pack(side="left", padx=(16, 4))
        self.status_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(toolbar, textvariable=self.status_var, state="readonly", width=14,
                                     values=["All", "Confirmed", "Cancelled"])
        status_combo.pack(side="left")
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        StyledButton(toolbar, "🔍 Search", command=self.refresh, theme=theme, kind="accent",
                     width=10).pack(side="left", padx=8)
        StyledButton(toolbar, "⤓ Export CSV", command=self._export_csv, theme=theme, kind="success",
                     width=14).pack(side="right")

        table_frame = tk.Frame(self, bg=theme["bg"])
        table_frame.pack(fill="both", expand=True, padx=16, pady=12)

        style_ttk_treeview(theme)
        columns = ("id", "code", "customer", "phone", "movie", "show", "seats", "amount", "status")
        headings = {
            "id": "#", "code": "Booking ID", "customer": "Customer", "phone": "Phone",
            "movie": "Movie", "show": "Show Date/Time", "seats": "Seats",
            "amount": "Amount", "status": "Status",
        }
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=headings[col], command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=110, anchor="center")
        self.tree.column("customer", width=140)
        self.tree.column("movie", width=160)
        self.tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        action_bar = tk.Frame(self, bg=theme["bg"])
        action_bar.pack(fill="x", padx=16, pady=(0, 16))

        StyledButton(action_bar, "✏ Update Customer Info", command=self._update_booking, theme=theme,
                     kind="accent", width=22).pack(side="left", padx=4)
        StyledButton(action_bar, "🚫 Cancel Booking", command=self._cancel_booking, theme=theme,
                     kind="warning" if "warning" in theme else "danger", width=18).pack(side="left", padx=4)
        StyledButton(action_bar, "🗑 Delete Booking", command=self._delete_booking, theme=theme,
                     kind="danger", width=18).pack(side="left", padx=4)
        StyledButton(action_bar, "🖨 Print Ticket", command=self._print_ticket, theme=theme,
                     kind="primary", width=16).pack(side="left", padx=4)
        StyledButton(action_bar, "🔁 Reprint", command=self._reprint_ticket, theme=theme,
                     kind="muted", width=14).pack(side="left", padx=4)
        StyledButton(action_bar, "👁 View Receipt", command=self._view_receipt, theme=theme,
                     kind="muted", width=16).pack(side="left", padx=4)

    # ------------------------------------------------------------------
    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        bookings = self.db.list_bookings(
            search_term=self.search_var.get().strip() or None,
            status=self.status_var.get(),
        )
        rows = [dict(b) for b in bookings]
        rows.sort(key=lambda r: (r.get(self.sort_column) is None, r.get(self.sort_column)),
                  reverse=self.sort_reverse)

        for b in rows:
            self.tree.insert("", "end", iid=str(b["id"]), values=(
                b["id"], b["booking_code"], b["customer_name"], b["phone"], b["movie_name"],
                f"{b['show_date']} {b['show_time']}", b["seats"], format_currency(b["total_amount"]),
                b["status"]
            ))

    def _sort_by(self, column):
        col_map = {"id": "id", "code": "booking_code", "customer": "customer_name", "phone": "phone",
                   "movie": "movie_name", "show": "show_date", "seats": "seats", "amount": "total_amount",
                   "status": "status"}
        db_col = col_map.get(column, "created_at")
        if self.sort_column == db_col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = db_col
            self.sort_reverse = False
        self.refresh()

    def _get_selected_booking_id(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a booking first.")
            return None
        return int(selection[0])

    def _update_booking(self):
        booking_id = self._get_selected_booking_id()
        if not booking_id:
            return
        booking = self.db.get_booking(booking_id)
        if not booking:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Update Customer Info")
        dialog.configure(bg=self.theme["surface"])
        dialog.geometry("360x220")

        tk.Label(dialog, text="Customer Name", bg=self.theme["surface"], fg=self.theme["text"]).pack(pady=(16, 2))
        name_entry = tk.Entry(dialog, bg=self.theme["entry_bg"], fg=self.theme["text"])
        name_entry.insert(0, booking["customer_name"])
        name_entry.pack(ipady=4, padx=20, fill="x")

        tk.Label(dialog, text="Phone Number", bg=self.theme["surface"], fg=self.theme["text"]).pack(pady=(12, 2))
        phone_entry = tk.Entry(dialog, bg=self.theme["entry_bg"], fg=self.theme["text"])
        phone_entry.insert(0, booking["phone"])
        phone_entry.pack(ipady=4, padx=20, fill="x")

        def save():
            name = name_entry.get().strip()
            phone = phone_entry.get().strip()
            ok, msg = validation.validate_not_empty(name, "Customer Name")
            if not ok:
                messagebox.showwarning("Validation Error", msg)
                return
            ok, msg = validation.validate_phone(phone)
            if not ok:
                messagebox.showwarning("Validation Error", msg)
                return
            self.db.update_booking_customer(booking_id, name, phone)
            messagebox.showinfo("Updated", "Booking updated successfully.")
            dialog.destroy()
            self.refresh()

        StyledButton(dialog, "Save Changes", command=save, theme=self.theme, kind="success",
                     width=20).pack(pady=20)

    def _cancel_booking(self):
        booking_id = self._get_selected_booking_id()
        if not booking_id:
            return
        if messagebox.askyesno("Confirm Cancellation", "Cancel this booking and release its seats?"):
            self.db.cancel_booking(booking_id)
            messagebox.showinfo("Cancelled", "Booking has been cancelled and seats released.")
            self.refresh()

    def _delete_booking(self):
        booking_id = self._get_selected_booking_id()
        if not booking_id:
            return
        if messagebox.askyesno("Confirm Delete", "Permanently delete this booking? This cannot be undone."):
            self.db.delete_booking(booking_id)
            messagebox.showinfo("Deleted", "Booking permanently deleted.")
            self.refresh()

    def _print_ticket(self):
        booking_id = self._get_selected_booking_id()
        if not booking_id:
            return
        self.app.show_receipt(booking_id)

    def _reprint_ticket(self):
        booking_id = self._get_selected_booking_id()
        if not booking_id:
            return
        booking = self.db.get_booking(booking_id)
        try:
            generate_full_receipt(dict(booking))
            messagebox.showinfo("Reprinted", "Receipt files regenerated in the receipts/ folder.")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not reprint receipt:\n{exc}")

    def _view_receipt(self):
        booking_id = self._get_selected_booking_id()
        if not booking_id:
            return
        self.app.show_receipt(booking_id)

    def _export_csv(self):
        bookings = self.db.list_bookings(
            search_term=self.search_var.get().strip() or None, status=self.status_var.get()
        )
        try:
            path = export_bookings_csv(bookings)
            messagebox.showinfo("Export Complete", f"Bookings exported to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))
