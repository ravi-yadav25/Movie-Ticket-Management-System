"""
gui/widgets.py
Reusable, theme-aware widgets shared across the GUI screens:
styled buttons, cards, seat buttons, and a scrollable frame.
"""

import tkinter as tk
from tkinter import ttk

import config


class StyledButton(tk.Button):
    """A flat, modern-looking button that follows the active theme."""

    def __init__(self, master, text, command=None, theme=None, kind="primary", width=16, **kwargs):
        theme = theme or config.DARK_THEME
        colors_map = {
            "primary": (theme["primary"], "#ffffff", theme["primary_dark"]),
            "accent": (theme["accent"], "#ffffff", theme["accent"]),
            "success": (theme["success"], "#ffffff", theme["success"]),
            "danger": (theme["danger"], "#ffffff", theme["danger"]),
            "muted": (theme["surface_alt"], theme["text"], theme["surface_alt"]),
        }
        bg, fg, active_bg = colors_map.get(kind, colors_map["primary"])

        super().__init__(
            master, text=text, command=command, bg=bg, fg=fg,
            activebackground=active_bg, activeforeground=fg,
            font=config.FONT_BUTTON, relief="flat", bd=0,
            cursor="hand2", width=width, padx=8, pady=8, **kwargs
        )
        self.bind("<Enter>", lambda e: self.config(bg=active_bg))
        self.bind("<Leave>", lambda e: self.config(bg=bg))


class Card(tk.Frame):
    """A simple elevated-looking card used on the dashboard."""

    def __init__(self, master, title, value, theme=None, accent_color=None, **kwargs):
        theme = theme or config.DARK_THEME
        super().__init__(master, bg=theme["surface"], highlightbackground=theme["border"],
                          highlightthickness=1, **kwargs)
        accent_color = accent_color or theme["primary"]

        bar = tk.Frame(self, bg=accent_color, height=4)
        bar.pack(fill="x", side="top")

        body = tk.Frame(self, bg=theme["surface"])
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self.value_label = tk.Label(
            body, text=str(value), font=(config.FONT_FAMILY, 22, "bold"),
            bg=theme["surface"], fg=theme["text"]
        )
        self.value_label.pack(anchor="w")

        tk.Label(
            body, text=title, font=config.FONT_SMALL, bg=theme["surface"], fg=theme["text_muted"]
        ).pack(anchor="w")

    def set_value(self, value):
        self.value_label.config(text=str(value))


class SeatButton(tk.Button):
    """A single seat in the seat-selection grid."""

    def __init__(self, master, seat_label, theme, on_toggle, status="available", **kwargs):
        self.theme = theme
        self.seat_label = seat_label
        self.status = status  # available | booked | selected
        self.on_toggle = on_toggle

        super().__init__(
            master, text=seat_label, width=4, height=2, relief="flat", bd=0,
            font=config.FONT_SMALL, cursor="hand2" if status != "booked" else "X_cursor",
            command=self._handle_click, **kwargs
        )
        self._refresh_color()

    def _refresh_color(self):
        color_key = {
            "available": "seat_available",
            "booked": "seat_booked",
            "selected": "seat_selected",
        }[self.status]
        self.config(bg=self.theme[color_key], fg="#ffffff",
                    state="disabled" if self.status == "booked" else "normal",
                    disabledforeground="#ffffff")

    def _handle_click(self):
        if self.status == "booked":
            return
        self.status = "selected" if self.status == "available" else "available"
        self._refresh_color()
        if self.on_toggle:
            self.on_toggle(self.seat_label, self.status)

    def force_status(self, status):
        self.status = status
        self._refresh_color()


class ScrollableFrame(tk.Frame):
    """A vertically scrollable frame; place child widgets inside `.scrollable_frame`."""

    def __init__(self, master, theme=None, **kwargs):
        theme = theme or config.DARK_THEME
        super().__init__(master, bg=theme["bg"], **kwargs)

        canvas = tk.Canvas(self, bg=theme["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=theme["bg"])

        self.scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)


def style_ttk_treeview(theme):
    """Apply a dark/light themed style to ttk.Treeview widgets globally."""
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Treeview", background=theme["surface"], foreground=theme["text"],
        fieldbackground=theme["surface"], rowheight=28, font=config.FONT_NORMAL, borderwidth=0
    )
    style.configure(
        "Treeview.Heading", background=theme["surface_alt"], foreground=theme["text"],
        font=config.FONT_SUBHEADING, relief="flat"
    )
    style.map("Treeview", background=[("selected", theme["primary"])], foreground=[("selected", "#ffffff")])
    style.map("Treeview.Heading", background=[("active", theme["surface_alt"])])
    return style
