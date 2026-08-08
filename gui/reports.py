"""
gui/reports.py
Reports & Analytics screen: revenue (today/monthly/yearly), movie-wise
and show-wise revenue, seat occupancy, top movies, most booked shows,
and CSV export for each report.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import config
from utils.helpers import format_currency, today_str
from utils.csv_export import export_report_csv
from gui.widgets import StyledButton, style_ttk_treeview


class ReportsWindow(tk.Frame):
    def __init__(self, master, db, app):
        self.theme = config.DARK_THEME if db.get_setting("theme", "dark") == "dark" else config.LIGHT_THEME
        super().__init__(master, bg=self.theme["bg"])
        self.db = db
        self.app = app

        self.pack(fill="both", expand=True)
        self._build_ui()

    def _build_ui(self):
        theme = self.theme
        header = tk.Frame(self, bg=theme["surface"])
        header.pack(fill="x")
        tk.Label(header, text="📊  Reports & Analytics", font=config.FONT_HEADING, bg=theme["surface"],
                 fg=theme["primary"]).pack(side="left", padx=16, pady=12)
        StyledButton(header, "⬅ Dashboard", command=self.app.show_dashboard, theme=theme,
                     kind="muted", width=18).pack(side="right", padx=16, pady=8)

        # Revenue summary cards
        summary_frame = tk.Frame(self, bg=theme["bg"])
        summary_frame.pack(fill="x", padx=16, pady=16)

        today = today_str()
        month_start = datetime.now().strftime("%Y-%m-01")
        year_start = datetime.now().strftime("%Y-01-01")

        today_rev = self.db.revenue_between(today, today)
        month_rev = self.db.revenue_between(month_start, today)
        year_rev = self.db.revenue_between(year_start, today)

        for label, value in [("Today's Revenue", today_rev), ("Monthly Revenue", month_rev),
                              ("Yearly Revenue", year_rev)]:
            card = tk.Frame(summary_frame, bg=theme["surface"], padx=16, pady=12,
                             highlightbackground=theme["border"], highlightthickness=1)
            card.pack(side="left", expand=True, fill="both", padx=6)
            tk.Label(card, text=format_currency(value), font=(config.FONT_FAMILY, 18, "bold"),
                      bg=theme["surface"], fg=theme["success"]).pack(anchor="w")
            tk.Label(card, text=label, font=config.FONT_SMALL, bg=theme["surface"],
                      fg=theme["text_muted"]).pack(anchor="w")

        # Notebook of report tabs
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=theme["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=theme["surface_alt"], foreground=theme["text"],
                         padding=[14, 8], font=config.FONT_SMALL)
        style.map("TNotebook.Tab", background=[("selected", theme["primary"])],
                  foreground=[("selected", "#ffffff")])

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self._build_tab(notebook, "Movie-wise Revenue", self.db.movie_wise_revenue(),
                         ["movie_name", "bookings_count", "seats_sold", "revenue"],
                         ["Movie", "Bookings", "Seats Sold", "Revenue"], "movie_wise_revenue")

        self._build_tab(notebook, "Show-wise Revenue", self.db.show_wise_revenue(),
                         ["movie_name", "show_date", "show_time", "hall_number", "bookings_count", "revenue"],
                         ["Movie", "Date", "Time", "Hall", "Bookings", "Revenue"], "show_wise_revenue")

        self._build_occupancy_tab(notebook)

        self._build_tab(notebook, "Top Movies", self.db.top_movies(10),
                         ["movie_name", "seats_sold", "revenue"],
                         ["Movie", "Seats Sold", "Revenue"], "top_movies")

        self._build_tab(notebook, "Most Booked Shows", self.db.most_booked_shows(10),
                         ["movie_name", "show_date", "show_time", "total_bookings"],
                         ["Movie", "Date", "Time", "Total Bookings"], "most_booked_shows")

        self._build_closing_tab(notebook)

    def _build_tab(self, notebook, title, rows, keys, headers_display, report_name):
        theme = self.theme
        tab = tk.Frame(notebook, bg=theme["bg"])
        notebook.add(tab, text=title)

        style_ttk_treeview(theme)
        tree = ttk.Treeview(tab, columns=keys, show="headings")
        for key, display in zip(keys, headers_display):
            tree.heading(key, text=display)
            tree.column(key, width=140, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        for row in rows:
            values = []
            for k in keys:
                v = row[k]
                if k in ("revenue",):
                    v = format_currency(v)
                values.append(v)
            tree.insert("", "end", values=values)

        StyledButton(tab, "⤓ Export CSV", theme=theme, kind="success", width=16,
                     command=lambda: self._export(rows, keys, report_name)).pack(pady=8)

    def _build_occupancy_tab(self, notebook):
        theme = self.theme
        tab = tk.Frame(notebook, bg=theme["bg"])
        notebook.add(tab, text="Seat Occupancy")

        style_ttk_treeview(theme)
        keys = ("movie_name", "show_date", "show_time", "seat_capacity", "seats_booked", "occupancy")
        headers = ["Movie", "Date", "Time", "Capacity", "Booked", "Occupancy %"]
        tree = ttk.Treeview(tab, columns=keys, show="headings")
        for k, h in zip(keys, headers):
            tree.heading(k, text=h)
            tree.column(k, width=140, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        rows = self.db.seat_occupancy()
        export_rows = []
        for row in rows:
            capacity = row["seat_capacity"] or 1
            occupancy_pct = round((row["seats_booked"] / capacity) * 100, 1)
            values = (row["movie_name"], row["show_date"], row["show_time"], row["seat_capacity"],
                      row["seats_booked"], f"{occupancy_pct}%")
            tree.insert("", "end", values=values)
            export_rows.append({
                "movie_name": row["movie_name"], "show_date": row["show_date"], "show_time": row["show_time"],
                "seat_capacity": row["seat_capacity"], "seats_booked": row["seats_booked"],
                "occupancy": occupancy_pct
            })

        StyledButton(tab, "⤓ Export CSV", theme=theme, kind="success", width=16,
                     command=lambda: self._export(export_rows, list(keys[:-1]) + ["occupancy"],
                                                   "seat_occupancy")).pack(pady=8)

    def _build_closing_tab(self, notebook):
        theme = self.theme
        tab = tk.Frame(notebook, bg=theme["bg"])
        notebook.add(tab, text="Daily Closing Report")

        report = self.db.daily_closing_report()
        card = tk.Frame(tab, bg=theme["surface"], padx=24, pady=24)
        card.pack(padx=40, pady=40)

        tk.Label(card, text=f"Daily Closing Report — {today_str()}", font=config.FONT_HEADING,
                  bg=theme["surface"], fg=theme["primary"]).pack(pady=(0, 16))

        for label, value in [
            ("Total Bookings", report["total_bookings"]),
            ("Total Seats Sold", report["total_seats"]),
            ("Total Revenue", format_currency(report["total_revenue"])),
        ]:
            row = tk.Frame(card, bg=theme["surface"])
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, font=config.FONT_NORMAL, bg=theme["surface"],
                      fg=theme["text_muted"], width=20, anchor="w").pack(side="left")
            tk.Label(row, text=str(value), font=config.FONT_SUBHEADING, bg=theme["surface"],
                      fg=theme["text"]).pack(side="left")

        StyledButton(card, "⤓ Export CSV", theme=theme, kind="success", width=18,
                     command=lambda: self._export(
                         [dict(report)], ["total_bookings", "total_seats", "total_revenue"],
                         "daily_closing")).pack(pady=(16, 0))

    def _export(self, rows, keys, report_name):
        try:
            path = export_report_csv(rows, keys, report_name)
            messagebox.showinfo("Export Complete", f"Report exported to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))
