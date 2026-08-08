"""
gui/booking.py
The ticket booking screen: customer details, movie/show selection,
graphical seat map, coupon + tax calculation, and receipt generation.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

import config
from utils import validation, helpers
from utils.receipt_generator import generate_full_receipt
from gui.widgets import StyledButton, SeatButton


class BookingWindow(tk.Frame):
    def __init__(self, master, db, app):
        self.theme = config.DARK_THEME if db.get_setting("theme", "dark") == "dark" else config.LIGHT_THEME
        super().__init__(master, bg=self.theme["bg"])
        self.db = db
        self.app = app
        self.selected_seats = set()
        self.seat_buttons = {}
        self.current_show = None

        self.pack(fill="both", expand=True)
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        theme = self.theme
        header = tk.Frame(self, bg=theme["surface"])
        header.pack(fill="x")
        tk.Label(header, text="🎟  Book Ticket", font=config.FONT_HEADING, bg=theme["surface"],
                 fg=theme["primary"]).pack(side="left", padx=16, pady=12)
        StyledButton(header, "⬅ Back to Dashboard", command=self.app.show_dashboard, theme=theme,
                     kind="muted", width=20).pack(side="right", padx=16, pady=8)

        main = tk.Frame(self, bg=theme["bg"])
        main.pack(fill="both", expand=True, padx=16, pady=16)

        left = tk.Frame(main, bg=theme["surface"], padx=16, pady=16)
        left.pack(side="left", fill="y", padx=(0, 10))

        right = tk.Frame(main, bg=theme["surface"], padx=16, pady=16)
        right.pack(side="left", fill="both", expand=True)

        self._build_form(left)
        self._build_seat_map(right)

    def _labeled_entry(self, parent, label):
        theme = self.theme
        tk.Label(parent, text=label, font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"], anchor="w").pack(fill="x", pady=(8, 0))
        entry = tk.Entry(parent, font=config.FONT_NORMAL, bg=theme["entry_bg"], fg=theme["text"],
                          insertbackground=theme["text"], relief="flat", highlightthickness=1,
                          highlightbackground=theme["border"])
        entry.pack(fill="x", ipady=5)
        return entry

    def _build_form(self, parent):
        theme = self.theme
        tk.Label(parent, text="Customer Details", font=config.FONT_SUBHEADING, bg=theme["surface"],
                  fg=theme["text"]).pack(anchor="w")

        self.name_entry = self._labeled_entry(parent, "Customer Name")
        self.phone_entry = self._labeled_entry(parent, "Phone Number")

        tk.Label(parent, text="Movie", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"], anchor="w").pack(fill="x", pady=(8, 0))
        self.movie_var = tk.StringVar()
        self.movie_combo = ttk.Combobox(parent, textvariable=self.movie_var, state="readonly", width=28)
        self.movie_combo.pack(fill="x", ipady=3)
        self.movie_combo.bind("<<ComboboxSelected>>", self._on_movie_selected)

        tk.Label(parent, text="Show", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"], anchor="w").pack(fill="x", pady=(8, 0))
        self.show_var = tk.StringVar()
        self.show_combo = ttk.Combobox(parent, textvariable=self.show_var, state="readonly", width=28)
        self.show_combo.pack(fill="x", ipady=3)
        self.show_combo.bind("<<ComboboxSelected>>", self._on_show_selected)

        tk.Label(parent, text="Payment Method", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"], anchor="w").pack(fill="x", pady=(8, 0))
        self.payment_var = tk.StringVar(value="Cash")
        payment_combo = ttk.Combobox(parent, textvariable=self.payment_var, state="readonly", width=28,
                                      values=["Cash", "Credit Card", "Debit Card", "UPI", "Wallet"])
        payment_combo.pack(fill="x", ipady=3)

        self.coupon_entry = self._labeled_entry(parent, "Coupon Code (optional)")

        summary = tk.Frame(parent, bg=theme["surface"])
        summary.pack(fill="x", pady=(16, 0))
        self.summary_var = tk.StringVar(value="Select seats to see total")
        tk.Label(summary, textvariable=self.summary_var, font=config.FONT_NORMAL, bg=theme["surface"],
                  fg=theme["text"], justify="left", wraplength=260).pack(anchor="w")

        StyledButton(parent, "✅  Confirm Booking", command=self._confirm_booking, theme=theme,
                     kind="success", width=26).pack(fill="x", pady=(20, 4), ipady=6)
        StyledButton(parent, "♻  Reset Form", command=self._reset_form, theme=theme,
                     kind="muted", width=26).pack(fill="x", ipady=4)

        self._load_movies()

    def _build_seat_map(self, parent):
        theme = self.theme
        tk.Label(parent, text="Select Seats", font=config.FONT_SUBHEADING, bg=theme["surface"],
                  fg=theme["text"]).pack(anchor="w")

        screen = tk.Frame(parent, bg=theme["accent"], height=18)
        screen.pack(fill="x", padx=60, pady=(10, 4))
        tk.Label(parent, text="S C R E E N", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"]).pack()

        self.seat_grid_frame = tk.Frame(parent, bg=theme["surface"])
        self.seat_grid_frame.pack(pady=16)

        legend = tk.Frame(parent, bg=theme["surface"])
        legend.pack(pady=10)
        for label, key in [("Available", "seat_available"), ("Selected", "seat_selected"),
                            ("Booked", "seat_booked")]:
            box = tk.Label(legend, text="  ", bg=theme[key])
            box.pack(side="left", padx=(10, 2))
            tk.Label(legend, text=label, bg=theme["surface"], fg=theme["text_muted"],
                      font=config.FONT_SMALL).pack(side="left")

        self._render_empty_seat_placeholder()

    def _render_empty_seat_placeholder(self):
        for widget in self.seat_grid_frame.winfo_children():
            widget.destroy()
        theme = self.theme
        tk.Label(self.seat_grid_frame, text="Select a movie and show to load the seat map.",
                  bg=theme["surface"], fg=theme["text_muted"], font=config.FONT_NORMAL).pack()

    # ------------------------------------------------------------------
    def _load_movies(self):
        self.movies = {m["name"]: m for m in self.db.list_movies(active_only=True)}
        self.movie_combo["values"] = list(self.movies.keys())

    def _on_movie_selected(self, event=None):
        movie_name = self.movie_var.get()
        movie = self.movies.get(movie_name)
        if not movie:
            return
        shows = [s for s in self.db.list_shows() if s["movie_id"] == movie["id"]]
        self.shows_map = {f"{s['show_date']}  {s['show_time']}  Hall {s['hall_number']}": s for s in shows}
        self.show_combo["values"] = list(self.shows_map.keys())
        self.show_var.set("")
        self._render_empty_seat_placeholder()
        self.selected_seats.clear()

    def _on_show_selected(self, event=None):
        key = self.show_var.get()
        show = self.shows_map.get(key)
        if not show:
            return
        self.current_show = show
        self._render_seat_map(show)
        self.selected_seats.clear()
        self._update_summary()

    def _render_seat_map(self, show):
        for widget in self.seat_grid_frame.winfo_children():
            widget.destroy()
        self.seat_buttons = {}

        booked_seats = self.db.get_booked_seats(show["id"])
        seat_labels = helpers.generate_seat_grid()
        capacity = show["seat_capacity"]
        usable_seats = seat_labels[:capacity] if capacity < len(seat_labels) else seat_labels

        rows = {}
        for seat in usable_seats:
            rows.setdefault(seat[0], []).append(seat)

        for r_idx, (row_letter, seats) in enumerate(rows.items()):
            row_frame = tk.Frame(self.seat_grid_frame, bg=self.theme["surface"])
            row_frame.pack(pady=2)
            for seat in seats:
                status = "booked" if seat in booked_seats else "available"
                btn = SeatButton(row_frame, seat, self.theme, self._on_seat_toggle, status=status)
                btn.pack(side="left", padx=2)
                self.seat_buttons[seat] = btn

    def _on_seat_toggle(self, seat_label, new_status):
        if new_status == "selected":
            self.selected_seats.add(seat_label)
        else:
            self.selected_seats.discard(seat_label)
        self._update_summary()

    def _update_summary(self):
        if not self.current_show or not self.selected_seats:
            self.summary_var.set("Select seats to see total")
            return

        movie_name = self.movie_var.get()
        movie = self.movies.get(movie_name)
        price = movie["price"] if movie else 0
        quantity = len(self.selected_seats)

        discount_percent = 0.0
        coupon_code = self.coupon_entry.get().strip()
        if coupon_code:
            coupon = self.db.get_coupon(coupon_code)
            if coupon:
                discount_percent = coupon["discount_percent"]

        tax_percent = float(self.db.get_setting("tax_percent", config.DEFAULT_TAX_PERCENT))
        subtotal, discount_amt, tax_amt, total = helpers.calculate_total(
            price, quantity, discount_percent, tax_percent
        )

        self.summary_var.set(
            f"Seats: {', '.join(sorted(self.selected_seats))}\n"
            f"Quantity: {quantity}  x  {helpers.format_currency(price)}\n"
            f"Subtotal: {helpers.format_currency(subtotal)}\n"
            f"Discount: {helpers.format_currency(discount_amt)}\n"
            f"Tax (GST {tax_percent:.1f}%): {helpers.format_currency(tax_amt)}\n"
            f"TOTAL: {helpers.format_currency(total)}"
        )

    # ------------------------------------------------------------------
    def _confirm_booking(self):
        name = self.name_entry.get().strip()
        phone = self.phone_entry.get().strip()
        movie_name = self.movie_var.get()
        show_key = self.show_var.get()

        ok, msg = validation.validate_not_empty(name, "Customer Name")
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        ok, msg = validation.validate_phone(phone)
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        if not movie_name or movie_name not in self.movies:
            messagebox.showwarning("Validation Error", "Please select a movie.")
            return
        if not show_key or not self.current_show:
            messagebox.showwarning("Validation Error", "Please select a show.")
            return

        seats = sorted(self.selected_seats)
        ok, msg = validation.validate_seats_selected(seats)
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return

        show = self.current_show
        already_booked = self.db.get_booked_seats(show["id"])
        ok, msg = validation.validate_seats_available(seats, already_booked)
        if not ok:
            messagebox.showerror("Seat Conflict", msg)
            self._on_show_selected()
            return
        ok, msg = validation.validate_capacity(len(seats), len(already_booked), show["seat_capacity"])
        if not ok:
            messagebox.showerror("Overbooked", msg)
            return

        movie = self.movies[movie_name]
        price = movie["price"]
        quantity = len(seats)

        discount_percent = 0.0
        coupon_code = self.coupon_entry.get().strip() or None
        if coupon_code:
            coupon = self.db.get_coupon(coupon_code)
            if not coupon:
                messagebox.showwarning("Invalid Coupon", "The coupon code entered is invalid or inactive.")
                return
            discount_percent = coupon["discount_percent"]

        tax_percent = float(self.db.get_setting("tax_percent", config.DEFAULT_TAX_PERCENT))
        subtotal, discount_amt, tax_amt, total = helpers.calculate_total(
            price, quantity, discount_percent, tax_percent
        )

        booking_code = helpers.generate_booking_id()

        try:
            booking_id = self.db.create_booking(
                booking_code, name, phone, movie["id"], show["id"], seats,
                self.payment_var.get(), coupon_code, discount_amt, tax_amt, total
            )
        except sqlite3.IntegrityError:
            messagebox.showerror("Booking Failed", "One or more selected seats were just booked by "
                                                     "someone else. Please choose different seats.")
            self._on_show_selected()
            return
        except Exception as exc:
            messagebox.showerror("Booking Failed", f"An unexpected error occurred:\n{exc}")
            return

        booking_row = self.db.get_booking(booking_id)
        booking_dict = dict(booking_row)

        try:
            receipt_paths = generate_full_receipt(booking_dict)
        except Exception as exc:
            receipt_paths = None
            messagebox.showwarning("Receipt Warning",
                                    f"Booking was saved, but receipt generation failed:\n{exc}")

        messagebox.showinfo("Booking Confirmed",
                             f"Booking ID: {booking_code}\nTotal Paid: {helpers.format_currency(total)}")

        self.app.show_receipt(booking_id)

    def _reset_form(self):
        self.name_entry.delete(0, tk.END)
        self.phone_entry.delete(0, tk.END)
        self.movie_var.set("")
        self.show_var.set("")
        self.coupon_entry.delete(0, tk.END)
        self.selected_seats.clear()
        self.current_show = None
        self._render_empty_seat_placeholder()
        self._update_summary()
