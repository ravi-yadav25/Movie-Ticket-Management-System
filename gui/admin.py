"""
gui/admin.py
Admin Panel: manage Movies, Shows, Users, Prices/Discounts, Coupons,
Tax settings, and Seat Layout capacity defaults. Also hosts CSV
import/export for the movie catalog.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import config
from utils import validation
from utils.csv_export import export_movies_csv, import_movies_csv
from gui.widgets import StyledButton, style_ttk_treeview


class AdminWindow(tk.Frame):
    def __init__(self, master, db, app):
        self.theme = config.DARK_THEME if db.get_setting("theme", "dark") == "dark" else config.LIGHT_THEME
        super().__init__(master, bg=self.theme["bg"])
        self.db = db
        self.app = app

        self.pack(fill="both", expand=True)
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        theme = self.theme
        header = tk.Frame(self, bg=theme["surface"])
        header.pack(fill="x")
        tk.Label(header, text="⚙  Admin Panel", font=config.FONT_HEADING, bg=theme["surface"],
                 fg=theme["primary"]).pack(side="left", padx=16, pady=12)
        StyledButton(header, "⬅ Dashboard", command=self.app.show_dashboard, theme=theme,
                     kind="muted", width=18).pack(side="right", padx=16, pady=8)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=theme["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=theme["surface_alt"], foreground=theme["text"],
                         padding=[14, 8], font=config.FONT_SMALL)
        style.map("TNotebook.Tab", background=[("selected", theme["primary"])],
                  foreground=[("selected", "#ffffff")])

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=16)

        self._build_movies_tab(notebook)
        self._build_shows_tab(notebook)
        self._build_users_tab(notebook)
        self._build_coupons_tab(notebook)
        self._build_settings_tab(notebook)

    # ------------------------------------------------------------------
    # MOVIES TAB
    # ------------------------------------------------------------------
    def _build_movies_tab(self, notebook):
        theme = self.theme
        tab = tk.Frame(notebook, bg=theme["bg"])
        notebook.add(tab, text="Movies")

        form = tk.Frame(tab, bg=theme["surface"], padx=16, pady=16)
        form.pack(side="left", fill="y")

        entries = {}
        fields = [("Movie Name", "name"), ("Language", "language"), ("Genre", "genre"),
                  ("Duration (mins)", "duration"), ("Price", "price"), ("Poster Path", "poster_path")]
        for label, key in fields:
            tk.Label(form, text=label, font=config.FONT_SMALL, bg=theme["surface"],
                      fg=theme["text_muted"], anchor="w").pack(fill="x", pady=(6, 0))
            entry = tk.Entry(form, bg=theme["entry_bg"], fg=theme["text"], insertbackground=theme["text"],
                              relief="flat", highlightthickness=1, highlightbackground=theme["border"])
            entry.pack(fill="x", ipady=4)
            entries[key] = entry
        self.movie_entries = entries

        tk.Label(form, text="Status", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"], anchor="w").pack(fill="x", pady=(6, 0))
        self.movie_status_var = tk.StringVar(value="Active")
        ttk.Combobox(form, textvariable=self.movie_status_var, state="readonly",
                     values=["Active", "Inactive"]).pack(fill="x", ipady=2)

        btns = tk.Frame(form, bg=theme["surface"])
        btns.pack(fill="x", pady=14)
        StyledButton(btns, "➕ Add", command=self._add_movie, theme=theme, kind="success",
                     width=10).grid(row=0, column=0, padx=2, pady=2)
        StyledButton(btns, "✏ Update", command=self._update_movie, theme=theme, kind="accent",
                     width=10).grid(row=0, column=1, padx=2, pady=2)
        StyledButton(btns, "🗑 Delete", command=self._delete_movie, theme=theme, kind="danger",
                     width=10).grid(row=1, column=0, padx=2, pady=2)
        StyledButton(btns, "♻ Clear", command=self._clear_movie_form, theme=theme, kind="muted",
                     width=10).grid(row=1, column=1, padx=2, pady=2)

        io_btns = tk.Frame(form, bg=theme["surface"])
        io_btns.pack(fill="x")
        StyledButton(io_btns, "⤓ Export CSV", command=self._export_movies, theme=theme, kind="success",
                     width=22).pack(fill="x", pady=2)
        StyledButton(io_btns, "⤒ Import CSV", command=self._import_movies, theme=theme, kind="accent",
                     width=22).pack(fill="x", pady=2)

        # Table
        table_frame = tk.Frame(tab, bg=theme["bg"])
        table_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        style_ttk_treeview(theme)
        cols = ("id", "name", "language", "genre", "duration", "price", "status")
        self.movies_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        headers = {"id": "#", "name": "Name", "language": "Language", "genre": "Genre",
                   "duration": "Duration", "price": "Price", "status": "Status"}
        for c in cols:
            self.movies_tree.heading(c, text=headers[c])
            self.movies_tree.column(c, width=110, anchor="center")
        self.movies_tree.pack(fill="both", expand=True)
        self.movies_tree.bind("<<TreeviewSelect>>", self._on_movie_select)

        self._refresh_movies()

    def _refresh_movies(self):
        for row in self.movies_tree.get_children():
            self.movies_tree.delete(row)
        for m in self.db.list_movies():
            self.movies_tree.insert("", "end", iid=str(m["id"]), values=(
                m["id"], m["name"], m["language"], m["genre"], m["duration"], m["price"], m["status"]
            ))

    def _on_movie_select(self, event=None):
        sel = self.movies_tree.selection()
        if not sel:
            return
        movie = self.db.get_movie(int(sel[0]))
        if not movie:
            return
        for key, entry in self.movie_entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, movie[key] if movie[key] is not None else "")
        self.movie_status_var.set(movie["status"])

    def _get_movie_form_values(self):
        return {k: e.get().strip() for k, e in self.movie_entries.items()}

    def _add_movie(self):
        values = self._get_movie_form_values()
        ok, msg = validation.validate_not_empty(values["name"], "Movie Name")
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        ok, msg = validation.validate_positive_number(values["price"] or 0, "Price")
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        ok, msg = validation.validate_integer(values["duration"] or 0, "Duration")
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return

        self.db.add_movie(values["name"], values["language"], values["genre"],
                           int(values["duration"] or 0), float(values["price"] or 0),
                           values["poster_path"] or None, self.movie_status_var.get())
        messagebox.showinfo("Movie Added", f"{values['name']} added successfully.")
        self._refresh_movies()
        self._clear_movie_form()

    def _update_movie(self):
        sel = self.movies_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a movie to update.")
            return
        values = self._get_movie_form_values()
        ok, msg = validation.validate_not_empty(values["name"], "Movie Name")
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        self.db.update_movie(int(sel[0]), values["name"], values["language"], values["genre"],
                              int(values["duration"] or 0), float(values["price"] or 0),
                              values["poster_path"] or None, self.movie_status_var.get())
        messagebox.showinfo("Updated", "Movie updated successfully.")
        self._refresh_movies()

    def _delete_movie(self):
        sel = self.movies_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a movie to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Delete this movie? Related shows will also be removed."):
            self.db.delete_movie(int(sel[0]))
            self._refresh_movies()
            self._clear_movie_form()

    def _clear_movie_form(self):
        for entry in self.movie_entries.values():
            entry.delete(0, tk.END)
        self.movie_status_var.set("Active")

    def _export_movies(self):
        try:
            path = export_movies_csv(self.db.list_movies())
            messagebox.showinfo("Export Complete", f"Movies exported to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    def _import_movies(self):
        path = filedialog.askopenfilename(title="Select Movies CSV", filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        try:
            movies = import_movies_csv(path)
            for m in movies:
                self.db.add_movie(**m)
            messagebox.showinfo("Import Complete", f"{len(movies)} movie(s) imported successfully.")
            self._refresh_movies()
        except Exception as exc:
            messagebox.showerror("Import Failed", str(exc))

    # ------------------------------------------------------------------
    # SHOWS TAB
    # ------------------------------------------------------------------
    def _build_shows_tab(self, notebook):
        theme = self.theme
        tab = tk.Frame(notebook, bg=theme["bg"])
        notebook.add(tab, text="Shows")

        form = tk.Frame(tab, bg=theme["surface"], padx=16, pady=16)
        form.pack(side="left", fill="y")

        tk.Label(form, text="Movie", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"], anchor="w").pack(fill="x", pady=(6, 0))
        self.show_movie_var = tk.StringVar()
        self.show_movie_combo = ttk.Combobox(form, textvariable=self.show_movie_var, state="readonly")
        self.show_movie_combo.pack(fill="x", ipady=2)

        show_entries = {}
        for label, key, default in [("Date (YYYY-MM-DD)", "show_date", ""), ("Time (HH:MM)", "show_time", ""),
                                     ("Hall Number", "hall_number", ""), ("Seat Capacity", "seat_capacity", "40")]:
            tk.Label(form, text=label, font=config.FONT_SMALL, bg=theme["surface"],
                      fg=theme["text_muted"], anchor="w").pack(fill="x", pady=(6, 0))
            entry = tk.Entry(form, bg=theme["entry_bg"], fg=theme["text"], insertbackground=theme["text"],
                              relief="flat", highlightthickness=1, highlightbackground=theme["border"])
            entry.insert(0, default)
            entry.pack(fill="x", ipady=4)
            show_entries[key] = entry
        self.show_entries = show_entries

        btns = tk.Frame(form, bg=theme["surface"])
        btns.pack(fill="x", pady=14)
        StyledButton(btns, "➕ Add", command=self._add_show, theme=theme, kind="success",
                     width=10).grid(row=0, column=0, padx=2, pady=2)
        StyledButton(btns, "✏ Update", command=self._update_show, theme=theme, kind="accent",
                     width=10).grid(row=0, column=1, padx=2, pady=2)
        StyledButton(btns, "🗑 Delete", command=self._delete_show, theme=theme, kind="danger",
                     width=10).grid(row=1, column=0, padx=2, pady=2)
        StyledButton(btns, "♻ Clear", command=self._clear_show_form, theme=theme, kind="muted",
                     width=10).grid(row=1, column=1, padx=2, pady=2)

        table_frame = tk.Frame(tab, bg=theme["bg"])
        table_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        style_ttk_treeview(theme)
        cols = ("id", "movie", "date", "time", "hall", "capacity")
        self.shows_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        headers = {"id": "#", "movie": "Movie", "date": "Date", "time": "Time", "hall": "Hall",
                   "capacity": "Capacity"}
        for c in cols:
            self.shows_tree.heading(c, text=headers[c])
            self.shows_tree.column(c, width=120, anchor="center")
        self.shows_tree.pack(fill="both", expand=True)
        self.shows_tree.bind("<<TreeviewSelect>>", self._on_show_select)

        self._refresh_show_movie_list()
        self._refresh_shows()

    def _refresh_show_movie_list(self):
        self.movies_by_name = {m["name"]: m["id"] for m in self.db.list_movies()}
        self.show_movie_combo["values"] = list(self.movies_by_name.keys())

    def _refresh_shows(self):
        for row in self.shows_tree.get_children():
            self.shows_tree.delete(row)
        for s in self.db.list_shows():
            self.shows_tree.insert("", "end", iid=str(s["id"]), values=(
                s["id"], s["movie_name"], s["show_date"], s["show_time"], s["hall_number"], s["seat_capacity"]
            ))

    def _on_show_select(self, event=None):
        sel = self.shows_tree.selection()
        if not sel:
            return
        show = self.db.get_show(int(sel[0]))
        if not show:
            return
        self.show_movie_var.set(show["movie_name"])
        self.show_entries["show_date"].delete(0, tk.END)
        self.show_entries["show_date"].insert(0, show["show_date"])
        self.show_entries["show_time"].delete(0, tk.END)
        self.show_entries["show_time"].insert(0, show["show_time"])
        self.show_entries["hall_number"].delete(0, tk.END)
        self.show_entries["hall_number"].insert(0, show["hall_number"])
        self.show_entries["seat_capacity"].delete(0, tk.END)
        self.show_entries["seat_capacity"].insert(0, show["seat_capacity"])

    def _validate_show_form(self):
        movie_name = self.show_movie_var.get()
        if movie_name not in self.movies_by_name:
            return False, "Please select a valid movie.", None
        date_v = self.show_entries["show_date"].get().strip()
        time_v = self.show_entries["show_time"].get().strip()
        hall_v = self.show_entries["hall_number"].get().strip()
        cap_v = self.show_entries["seat_capacity"].get().strip()

        ok, msg = validation.validate_date_format(date_v)
        if not ok:
            return False, msg, None
        ok, msg = validation.validate_time_format(time_v)
        if not ok:
            return False, msg, None
        ok, msg = validation.validate_not_empty(hall_v, "Hall Number")
        if not ok:
            return False, msg, None
        ok, msg = validation.validate_integer(cap_v, "Seat Capacity")
        if not ok:
            return False, msg, None

        return True, "", {
            "movie_id": self.movies_by_name[movie_name], "show_date": date_v, "show_time": time_v,
            "hall_number": hall_v, "seat_capacity": int(cap_v)
        }

    def _add_show(self):
        ok, msg, data = self._validate_show_form()
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        self.db.add_show(**data)
        messagebox.showinfo("Show Added", "Show added successfully.")
        self._refresh_shows()
        self._clear_show_form()

    def _update_show(self):
        sel = self.shows_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a show to update.")
            return
        ok, msg, data = self._validate_show_form()
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        self.db.update_show(int(sel[0]), **data)
        messagebox.showinfo("Updated", "Show updated successfully.")
        self._refresh_shows()

    def _delete_show(self):
        sel = self.shows_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a show to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Delete this show?"):
            self.db.delete_show(int(sel[0]))
            self._refresh_shows()
            self._clear_show_form()

    def _clear_show_form(self):
        self.show_movie_var.set("")
        for key, entry in self.show_entries.items():
            entry.delete(0, tk.END)
        self.show_entries["seat_capacity"].insert(0, "40")

    # ------------------------------------------------------------------
    # USERS TAB
    # ------------------------------------------------------------------
    def _build_users_tab(self, notebook):
        theme = self.theme
        tab = tk.Frame(notebook, bg=theme["bg"])
        notebook.add(tab, text="Users")

        form = tk.Frame(tab, bg=theme["surface"], padx=16, pady=16)
        form.pack(side="left", fill="y")

        tk.Label(form, text="New Username", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"]).pack(fill="x", pady=(6, 0))
        self.new_username_entry = tk.Entry(form, bg=theme["entry_bg"], fg=theme["text"], relief="flat")
        self.new_username_entry.pack(fill="x", ipady=4)

        tk.Label(form, text="Password", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"]).pack(fill="x", pady=(6, 0))
        self.new_password_entry = tk.Entry(form, bg=theme["entry_bg"], fg=theme["text"], relief="flat", show="*")
        self.new_password_entry.pack(fill="x", ipady=4)

        tk.Label(form, text="Role", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"]).pack(fill="x", pady=(6, 0))
        self.new_role_var = tk.StringVar(value="staff")
        ttk.Combobox(form, textvariable=self.new_role_var, state="readonly",
                     values=["admin", "staff"]).pack(fill="x", ipady=2)

        StyledButton(form, "➕ Add User", command=self._add_user, theme=theme, kind="success",
                     width=20).pack(fill="x", pady=(14, 4))
        StyledButton(form, "🗑 Delete Selected User", command=self._delete_user, theme=theme, kind="danger",
                     width=20).pack(fill="x", pady=4)

        tk.Frame(form, bg=theme["border"], height=1).pack(fill="x", pady=14)

        tk.Label(form, text="Change My Password", font=config.FONT_SUBHEADING, bg=theme["surface"],
                  fg=theme["text"]).pack(anchor="w")
        tk.Label(form, text="New Password", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"]).pack(fill="x", pady=(6, 0))
        self.change_pw_entry = tk.Entry(form, bg=theme["entry_bg"], fg=theme["text"], relief="flat", show="*")
        self.change_pw_entry.pack(fill="x", ipady=4)
        StyledButton(form, "🔒 Update Password", command=self._change_password, theme=theme, kind="accent",
                     width=20).pack(fill="x", pady=8)

        table_frame = tk.Frame(tab, bg=theme["bg"])
        table_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        style_ttk_treeview(theme)
        cols = ("id", "username", "role", "created_at")
        self.users_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c, h in zip(cols, ["#", "Username", "Role", "Created At"]):
            self.users_tree.heading(c, text=h)
            self.users_tree.column(c, width=140, anchor="center")
        self.users_tree.pack(fill="both", expand=True)

        self._refresh_users()

    def _refresh_users(self):
        for row in self.users_tree.get_children():
            self.users_tree.delete(row)
        for u in self.db.list_users():
            self.users_tree.insert("", "end", iid=str(u["id"]), values=(
                u["id"], u["username"], u["role"], u["created_at"]
            ))

    def _add_user(self):
        username = self.new_username_entry.get().strip()
        password = self.new_password_entry.get().strip()
        ok, msg = validation.validate_not_empty(username, "Username")
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        ok, msg = validation.validate_not_empty(password, "Password")
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        try:
            self.db.add_user(username, password, self.new_role_var.get())
            messagebox.showinfo("User Added", f"User '{username}' created.")
            self._refresh_users()
            self.new_username_entry.delete(0, tk.END)
            self.new_password_entry.delete(0, tk.END)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not create user:\n{exc}")

    def _delete_user(self):
        sel = self.users_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a user to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Delete this user account?"):
            self.db.delete_user(int(sel[0]))
            self._refresh_users()

    def _change_password(self):
        new_pw = self.change_pw_entry.get().strip()
        ok, msg = validation.validate_not_empty(new_pw, "Password")
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        self.db.change_password(self.app.current_user["username"], new_pw)
        messagebox.showinfo("Password Updated", "Your password has been updated successfully.")
        self.change_pw_entry.delete(0, tk.END)

    # ------------------------------------------------------------------
    # COUPONS TAB
    # ------------------------------------------------------------------
    def _build_coupons_tab(self, notebook):
        theme = self.theme
        tab = tk.Frame(notebook, bg=theme["bg"])
        notebook.add(tab, text="Coupons & Discounts")

        form = tk.Frame(tab, bg=theme["surface"], padx=16, pady=16)
        form.pack(side="left", fill="y")

        tk.Label(form, text="Coupon Code", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"]).pack(fill="x", pady=(6, 0))
        self.coupon_code_entry = tk.Entry(form, bg=theme["entry_bg"], fg=theme["text"], relief="flat")
        self.coupon_code_entry.pack(fill="x", ipady=4)

        tk.Label(form, text="Discount %", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"]).pack(fill="x", pady=(6, 0))
        self.coupon_discount_entry = tk.Entry(form, bg=theme["entry_bg"], fg=theme["text"], relief="flat")
        self.coupon_discount_entry.pack(fill="x", ipady=4)

        StyledButton(form, "➕ Add Coupon", command=self._add_coupon, theme=theme, kind="success",
                     width=20).pack(fill="x", pady=(14, 4))
        StyledButton(form, "🔁 Toggle Active/Inactive", command=self._toggle_coupon, theme=theme,
                     kind="accent", width=20).pack(fill="x", pady=4)
        StyledButton(form, "🗑 Delete Coupon", command=self._delete_coupon, theme=theme, kind="danger",
                     width=20).pack(fill="x", pady=4)

        table_frame = tk.Frame(tab, bg=theme["bg"])
        table_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        style_ttk_treeview(theme)
        cols = ("id", "code", "discount", "active")
        self.coupons_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c, h in zip(cols, ["#", "Code", "Discount %", "Active"]):
            self.coupons_tree.heading(c, text=h)
            self.coupons_tree.column(c, width=130, anchor="center")
        self.coupons_tree.pack(fill="both", expand=True)

        self._refresh_coupons()

    def _refresh_coupons(self):
        for row in self.coupons_tree.get_children():
            self.coupons_tree.delete(row)
        for c in self.db.list_coupons():
            self.coupons_tree.insert("", "end", iid=str(c["id"]), values=(
                c["id"], c["code"], c["discount_percent"], "Yes" if c["active"] else "No"
            ))

    def _add_coupon(self):
        code = self.coupon_code_entry.get().strip()
        discount = self.coupon_discount_entry.get().strip()
        ok, msg = validation.validate_not_empty(code, "Coupon Code")
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        ok, msg = validation.validate_positive_number(discount, "Discount %")
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        try:
            self.db.add_coupon(code, float(discount))
            messagebox.showinfo("Coupon Added", f"Coupon '{code.upper()}' created.")
            self._refresh_coupons()
            self.coupon_code_entry.delete(0, tk.END)
            self.coupon_discount_entry.delete(0, tk.END)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not add coupon (it may already exist):\n{exc}")

    def _toggle_coupon(self):
        sel = self.coupons_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a coupon.")
            return
        coupon_id = int(sel[0])
        current = self.coupons_tree.item(sel[0])["values"][3] == "Yes"
        self.db.toggle_coupon(coupon_id, not current)
        self._refresh_coupons()

    def _delete_coupon(self):
        sel = self.coupons_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a coupon to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Delete this coupon?"):
            self.db.delete_coupon(int(sel[0]))
            self._refresh_coupons()

    # ------------------------------------------------------------------
    # SETTINGS TAB (Tax + Seat Layout)
    # ------------------------------------------------------------------
    def _build_settings_tab(self, notebook):
        theme = self.theme
        tab = tk.Frame(notebook, bg=theme["bg"])
        notebook.add(tab, text="Tax & Seat Layout")

        card = tk.Frame(tab, bg=theme["surface"], padx=24, pady=24)
        card.pack(padx=30, pady=30, anchor="nw")

        tk.Label(card, text="GST / Tax Percentage", font=config.FONT_SUBHEADING, bg=theme["surface"],
                  fg=theme["text"]).pack(anchor="w")
        self.tax_entry = tk.Entry(card, bg=theme["entry_bg"], fg=theme["text"], relief="flat", width=20)
        self.tax_entry.insert(0, self.db.get_setting("tax_percent", config.DEFAULT_TAX_PERCENT))
        self.tax_entry.pack(anchor="w", ipady=4, pady=(4, 12))

        StyledButton(card, "💾 Save Tax Setting", command=self._save_tax, theme=theme, kind="success",
                     width=22).pack(anchor="w")

        tk.Frame(card, bg=theme["border"], height=1).pack(fill="x", pady=16)

        tk.Label(card, text="Default Seat Layout", font=config.FONT_SUBHEADING, bg=theme["surface"],
                  fg=theme["text"]).pack(anchor="w")
        tk.Label(card, text=f"Rows: {', '.join(config.SEAT_ROWS)}   |   Seats per row: "
                             f"{config.SEATS_PER_ROW}\n(Configured in config.py — restart after changing.)",
                  font=config.FONT_SMALL, bg=theme["surface"], fg=theme["text_muted"],
                  justify="left").pack(anchor="w", pady=(4, 0))

        tk.Frame(card, bg=theme["border"], height=1).pack(fill="x", pady=16)

        tk.Label(card, text="Cinema Name", font=config.FONT_SUBHEADING, bg=theme["surface"],
                  fg=theme["text"]).pack(anchor="w")
        self.cinema_name_entry = tk.Entry(card, bg=theme["entry_bg"], fg=theme["text"], relief="flat", width=30)
        self.cinema_name_entry.insert(0, self.db.get_setting("cinema_name", "Cineplex Multiplex"))
        self.cinema_name_entry.pack(anchor="w", ipady=4, pady=(4, 12))
        StyledButton(card, "💾 Save Cinema Name", command=self._save_cinema_name, theme=theme,
                     kind="success", width=22).pack(anchor="w")

    def _save_tax(self):
        value = self.tax_entry.get().strip()
        ok, msg = validation.validate_non_negative_number(value, "Tax Percentage")
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        self.db.set_setting("tax_percent", float(value))
        messagebox.showinfo("Saved", "Tax percentage updated successfully.")

    def _save_cinema_name(self):
        value = self.cinema_name_entry.get().strip()
        ok, msg = validation.validate_not_empty(value, "Cinema Name")
        if not ok:
            messagebox.showwarning("Validation Error", msg)
            return
        self.db.set_setting("cinema_name", value)
        messagebox.showinfo("Saved", "Cinema name updated successfully.")
