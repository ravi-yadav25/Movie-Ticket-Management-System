"""
main.py
Entry point for the Movie Ticket Management System.

Run with:
    python main.py

The App class acts as a lightweight controller/router that swaps the
current screen (Frame) inside the root Tkinter window: Login -> Dashboard
-> Booking / Bookings / Reports / Admin / Receipt.
"""

import tkinter as tk
from tkinter import messagebox
import traceback

import config
from database.database import Database
from gui.login import LoginWindow
from gui.dashboard import Dashboard
from gui.booking import BookingWindow
from gui.bookings import BookingsWindow
from gui.reports import ReportsWindow
from gui.admin import AdminWindow
from gui.receipt import ReceiptWindow


class App:
    """Top-level application controller that manages screen navigation."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(config.APP_NAME)
        self.root.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.root.minsize(1024, 650)

        try:
            self.db = Database()
        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to initialize database:\n{exc}")
            raise

        self.current_user = None
        self.current_frame = None

        self._apply_background()
        self.show_login()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    def _apply_background(self):
        theme = config.DARK_THEME if self.db.get_setting("theme", "dark") == "dark" else config.LIGHT_THEME
        self.root.configure(bg=theme["bg"])

    def _switch_frame(self, frame_class, *args, **kwargs):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self._apply_background()
        self.current_frame = frame_class(self.root, *args, **kwargs)

    # ------------------------------------------------------------------
    # Navigation methods used by all screens
    # ------------------------------------------------------------------
    def show_login(self):
        self.root.config(menu=tk.Menu(self.root))  # clear menu bar
        self._switch_frame(LoginWindow, self.db, self._on_login_success)

    def _on_login_success(self, user):
        self.current_user = user
        self.show_dashboard()

    def show_dashboard(self):
        self._switch_frame(Dashboard, self.db, self.current_user, self)

    def show_booking(self):
        self._switch_frame(BookingWindow, self.db, self)

    def show_bookings(self):
        self._switch_frame(BookingsWindow, self.db, self)

    def show_reports(self):
        self._switch_frame(ReportsWindow, self.db, self)

    def show_admin(self):
        self._switch_frame(AdminWindow, self.db, self)

    def show_receipt(self, booking_id):
        self._switch_frame(ReceiptWindow, self.db, self, booking_id)

    # ------------------------------------------------------------------
    def _on_close(self):
        try:
            self.db.close()
        finally:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    try:
        app = App()
        app.run()
    except Exception:
        # Last-resort crash guard so the user sees something useful
        # instead of a silent exit.
        error_text = traceback.format_exc()
        print(error_text)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fatal Error", f"The application encountered a fatal error:\n\n{error_text}")
        except Exception:
            pass


if __name__ == "__main__":
    main()
