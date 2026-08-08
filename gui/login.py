"""
gui/login.py
Login window shown at application start. Validates credentials against
the `users` table and launches the Dashboard on success.
"""

import tkinter as tk
from tkinter import messagebox
import os

import config


class LoginWindow(tk.Frame):
    def __init__(self, master, db, on_success):
        theme = config.DARK_THEME
        super().__init__(master, bg=theme["bg"])
        self.db = db
        self.on_success = on_success
        self.theme = theme

        self.pack(fill="both", expand=True)
        self._build_ui()

    def _build_ui(self):
        theme = self.theme
        container = tk.Frame(self, bg=theme["bg"])
        container.place(relx=0.5, rely=0.5, anchor="center")

        card = tk.Frame(container, bg=theme["surface"], padx=40, pady=36,
                         highlightbackground=theme["border"], highlightthickness=1)
        card.pack()

        tk.Label(card, text="🎬", font=(config.FONT_FAMILY, 40), bg=theme["surface"],
                  fg=theme["primary"]).pack()
        tk.Label(card, text=config.APP_NAME, font=config.FONT_TITLE, bg=theme["surface"],
                  fg=theme["text"]).pack(pady=(4, 0))
        tk.Label(card, text="Please sign in to continue", font=config.FONT_NORMAL,
                  bg=theme["surface"], fg=theme["text_muted"]).pack(pady=(0, 20))

        tk.Label(card, text="Username", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"], anchor="w").pack(fill="x")
        self.username_entry = tk.Entry(card, font=config.FONT_NORMAL, bg=theme["entry_bg"],
                                        fg=theme["text"], insertbackground=theme["text"],
                                        relief="flat", highlightthickness=1,
                                        highlightbackground=theme["border"])
        self.username_entry.pack(fill="x", pady=(2, 12), ipady=6)
        self.username_entry.insert(0, config.DEFAULT_USERNAME)

        tk.Label(card, text="Password", font=config.FONT_SMALL, bg=theme["surface"],
                  fg=theme["text_muted"], anchor="w").pack(fill="x")
        self.password_entry = tk.Entry(card, font=config.FONT_NORMAL, bg=theme["entry_bg"],
                                        fg=theme["text"], insertbackground=theme["text"],
                                        relief="flat", show="*", highlightthickness=1,
                                        highlightbackground=theme["border"])
        self.password_entry.pack(fill="x", pady=(2, 20), ipady=6)

        login_btn = tk.Button(
            card, text="LOGIN", command=self._attempt_login, bg=theme["primary"], fg="#ffffff",
            activebackground=theme["primary_dark"], activeforeground="#ffffff",
            font=config.FONT_BUTTON, relief="flat", bd=0, cursor="hand2", pady=10
        )
        login_btn.pack(fill="x")

        hint = tk.Label(card, text=f"Default: {config.DEFAULT_USERNAME} / {config.DEFAULT_PASSWORD}",
                         font=config.FONT_SMALL, bg=theme["surface"], fg=theme["text_muted"])
        hint.pack(pady=(14, 0))

        self.password_entry.bind("<Return>", lambda e: self._attempt_login())
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        self.username_entry.focus()

    def _attempt_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("Missing Fields", "Please enter both username and password.")
            return

        try:
            user = self.db.verify_login(username, password)
        except Exception as exc:
            messagebox.showerror("Login Error", f"An unexpected error occurred:\n{exc}")
            return

        if user:
            self.destroy()
            self.on_success(user)
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")
            self.password_entry.delete(0, tk.END)
