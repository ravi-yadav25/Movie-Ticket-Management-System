"""
gui/dashboard.py
Main application hub shown after a successful login. Displays live stats,
provides navigation to Booking / Bookings / Reports / Admin, and hosts the
menu bar, toolbar and status bar for the whole app.
"""

import tkinter as tk
from tkinter import messagebox

import config
from utils.helpers import format_currency, now_timestamp
from gui.widgets import Card, StyledButton


class Dashboard(tk.Frame):
    def __init__(self, master, db, user, app):
        self.theme = config.DARK_THEME if db.get_setting("theme", "dark") == "dark" else config.LIGHT_THEME
        super().__init__(master, bg=self.theme["bg"])
        self.db = db
        self.user = user
        self.app = app  # reference to root App controller for navigation

        self.pack(fill="both", expand=True)
        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()
        self.refresh_stats()

    # ------------------------------------------------------------------
    def _build_menu(self):
        menubar = tk.Menu(self.app.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Backup Database", command=self._backup_db)
        file_menu.add_command(label="Restore Database", command=self._restore_db)
        file_menu.add_separator()
        file_menu.add_command(label="Logout", command=self._logout, accelerator="Ctrl+L")
        file_menu.add_command(label="Exit", command=self.app.root.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=file_menu)

        nav_menu = tk.Menu(menubar, tearoff=0)
        nav_menu.add_command(label="Book Ticket", command=lambda: self.app.show_booking())
        nav_menu.add_command(label="View Bookings", command=lambda: self.app.show_bookings())
        nav_menu.add_command(label="Reports", command=lambda: self.app.show_reports())
        nav_menu.add_command(label="Admin Panel", command=lambda: self.app.show_admin())
        menubar.add_cascade(label="Navigate", menu=nav_menu)

        theme_menu = tk.Menu(menubar, tearoff=0)
        theme_menu.add_command(label="Dark Mode", command=lambda: self._switch_theme("dark"))
        theme_menu.add_command(label="Light Mode", command=lambda: self._switch_theme("light"))
        menubar.add_cascade(label="Theme", menu=theme_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Help", command=self._show_help)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.app.root.config(menu=menubar)
        self.app.root.bind("<Control-l>", lambda e: self._logout())
        self.app.root.bind("<Control-q>", lambda e: self.app.root.quit())

    def _build_toolbar(self):
        theme = self.theme
        toolbar = tk.Frame(self, bg=theme["surface"], height=56)
        toolbar.pack(fill="x", side="top")

        tk.Label(toolbar, text=f"🎬  {config.APP_NAME}", font=config.FONT_HEADING,
                 bg=theme["surface"], fg=theme["primary"]).pack(side="left", padx=16, pady=10)

        tk.Label(toolbar, text=f"Signed in as: {self.user['username']} ({self.user['role']})",
                 font=config.FONT_SMALL, bg=theme["surface"], fg=theme["text_muted"]).pack(side="right", padx=16)

    def _build_body(self):
        theme = self.theme
        body = tk.Frame(self, bg=theme["bg"])
        body.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(body, text="Dashboard Overview", font=config.FONT_HEADING, bg=theme["bg"],
                  fg=theme["text"]).pack(anchor="w", pady=(0, 12))

        cards_frame = tk.Frame(body, bg=theme["bg"])
        cards_frame.pack(fill="x")
        for i in range(5):
            cards_frame.grid_columnconfigure(i, weight=1, uniform="cards")

        self.card_revenue = Card(cards_frame, "Today's Revenue", format_currency(0), theme=theme,
                                  accent_color=theme["success"])
        self.card_bookings = Card(cards_frame, "Today's Bookings", "0", theme=theme,
                                   accent_color=theme["accent"])
        self.card_movies = Card(cards_frame, "Total Movies", "0", theme=theme, accent_color=theme["primary"])
        self.card_seats = Card(cards_frame, "Seats Sold Today", "0", theme=theme, accent_color=theme["warning"])
        self.card_shows = Card(cards_frame, "Available Shows", "0", theme=theme, accent_color=theme["accent"])

        for idx, card in enumerate(
            [self.card_revenue, self.card_bookings, self.card_movies, self.card_seats, self.card_shows]
        ):
            card.grid(row=0, column=idx, sticky="nsew", padx=6)

        # Quick actions
        actions_frame = tk.Frame(body, bg=theme["bg"])
        actions_frame.pack(fill="x", pady=30)

        tk.Label(actions_frame, text="Quick Actions", font=config.FONT_HEADING, bg=theme["bg"],
                  fg=theme["text"]).pack(anchor="w", pady=(0, 12))

        btn_row = tk.Frame(actions_frame, bg=theme["bg"])
        btn_row.pack(fill="x")

        StyledButton(btn_row, "🎟  Book Ticket", command=self.app.show_booking, theme=theme,
                     kind="primary", width=18).pack(side="left", padx=6, ipady=6)
        StyledButton(btn_row, "📋  View Bookings", command=self.app.show_bookings, theme=theme,
                     kind="accent", width=18).pack(side="left", padx=6, ipady=6)
        StyledButton(btn_row, "📊  Reports", command=self.app.show_reports, theme=theme,
                     kind="success", width=18).pack(side="left", padx=6, ipady=6)
        StyledButton(btn_row, "⚙  Admin", command=self.app.show_admin, theme=theme,
                     kind="muted", width=18).pack(side="left", padx=6, ipady=6)
        StyledButton(btn_row, "🚪  Logout", command=self._logout, theme=theme,
                     kind="danger", width=18).pack(side="left", padx=6, ipady=6)

        # Recent bookings preview
        recent_frame = tk.Frame(body, bg=theme["bg"])
        recent_frame.pack(fill="both", expand=True)
        tk.Label(recent_frame, text="Recent Bookings", font=config.FONT_HEADING, bg=theme["bg"],
                  fg=theme["text"]).pack(anchor="w", pady=(0, 8))

        from tkinter import ttk
        from gui.widgets import style_ttk_treeview
        style_ttk_treeview(theme)

        columns = ("code", "customer", "movie", "seats", "amount", "status")
        self.recent_tree = ttk.Treeview(recent_frame, columns=columns, show="headings", height=8)
        headings = {"code": "Booking ID", "customer": "Customer", "movie": "Movie",
                    "seats": "Seats", "amount": "Amount", "status": "Status"}
        for col in columns:
            self.recent_tree.heading(col, text=headings[col])
            self.recent_tree.column(col, width=140, anchor="center")
        self.recent_tree.pack(fill="both", expand=True)

    def _build_statusbar(self):
        theme = self.theme
        self.status_var = tk.StringVar(value=f"Ready | {now_timestamp()}")
        status_bar = tk.Label(self, textvariable=self.status_var, bg=theme["surface_alt"],
                               fg=theme["text_muted"], font=config.FONT_SMALL, anchor="w", padx=10, pady=4)
        status_bar.pack(fill="x", side="bottom")

    # ------------------------------------------------------------------
    def refresh_stats(self):
        self.card_revenue.set_value(format_currency(self.db.today_revenue()))
        self.card_bookings.set_value(self.db.count_today_bookings())
        self.card_movies.set_value(self.db.count_movies())
        self.card_seats.set_value(self.db.total_seats_sold_today())
        self.card_shows.set_value(self.db.count_upcoming_shows())

        for row in self.recent_tree.get_children():
            self.recent_tree.delete(row)
        for b in self.db.list_bookings()[:10]:
            self.recent_tree.insert("", "end", values=(
                b["booking_code"], b["customer_name"], b["movie_name"],
                b["seats"], format_currency(b["total_amount"]), b["status"]
            ))
        self.status_var.set(f"Ready | Last refreshed: {now_timestamp()}")

    def _switch_theme(self, mode):
        self.db.set_setting("theme", mode)
        messagebox.showinfo("Theme Changed", "Theme will apply the next time you open a screen.\n"
                                              "Refreshing dashboard now.")
        self.app.show_dashboard()

    def _backup_db(self):
        try:
            path = self.db.backup_database()
            messagebox.showinfo("Backup Complete", f"Database backed up to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Backup Failed", str(exc))

    def _restore_db(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(title="Select Backup File", filetypes=[("SQLite DB", "*.db")])
        if not path:
            return
        if messagebox.askyesno("Confirm Restore", "This will overwrite the current database. Continue?"):
            try:
                self.db.restore_database(path)
                messagebox.showinfo("Restore Complete", "Database restored successfully.")
                self.app.show_dashboard()
            except Exception as exc:
                messagebox.showerror("Restore Failed", str(exc))

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.app.show_login()

    def _show_help(self):
        messagebox.showinfo(
            "Help",
            "Movie Ticket Management System - Quick Help\n\n"
            "• Book Ticket: Create a new booking with seat selection.\n"
            "• View Bookings: Search, filter, update, cancel or print bookings.\n"
            "• Reports: Revenue, occupancy and top-movie analytics.\n"
            "• Admin: Manage movies, shows, users, coupons, tax and seat layout.\n\n"
            "Keyboard shortcuts: Ctrl+L Logout, Ctrl+Q Exit."
        )

    def _show_about(self):
        messagebox.showinfo(
            "About",
            f"{config.APP_NAME}\nVersion {config.APP_VERSION}\n\n"
            f"Built with Python, Tkinter & SQLite.\n© {config.APP_AUTHOR}"
        )
