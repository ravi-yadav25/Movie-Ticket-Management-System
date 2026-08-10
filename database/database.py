"""
database/database.py

Central Database access layer for the Movie Ticket Management System.
Wraps sqlite3 and exposes clean, typed methods for every table so that
GUI modules never need to write raw SQL themselves.
"""

import sqlite3
import hashlib
import os
import shutil
from datetime import datetime

import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class Database:
    """Handles all persistence for the application using SQLite."""

    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        self._seed_defaults()

    # ------------------------------------------------------------------
    # Low level helpers
    # ------------------------------------------------------------------
    def execute(self, query, params=(), commit=False):
        """Execute a single query and optionally commit."""
        cur = self.conn.cursor()
        cur.execute(query, params)
        if commit:
            self.conn.commit()
        return cur

    def fetchone(self, query, params=()):
        cur = self.execute(query, params)
        return cur.fetchone()

    def fetchall(self, query, params=()):
        cur = self.execute(query, params)
        return cur.fetchall()

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Schema creation
    # ------------------------------------------------------------------
    def _create_tables(self):
        c = self.conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'admin',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                language TEXT,
                genre TEXT,
                duration INTEGER,
                price REAL NOT NULL DEFAULT 0,
                poster_path TEXT,
                status TEXT DEFAULT 'Active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS shows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id INTEGER NOT NULL,
                show_date TEXT NOT NULL,
                show_time TEXT NOT NULL,
                hall_number TEXT NOT NULL,
                seat_capacity INTEGER NOT NULL DEFAULT 40,
                FOREIGN KEY (movie_id) REFERENCES movies (id) ON DELETE CASCADE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_code TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                movie_id INTEGER NOT NULL,
                show_id INTEGER NOT NULL,
                seats TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                payment_method TEXT,
                coupon_code TEXT,
                discount REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                total_amount REAL NOT NULL,
                status TEXT DEFAULT 'Confirmed',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (movie_id) REFERENCES movies (id),
                FOREIGN KEY (show_id) REFERENCES shows (id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS booked_seats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                show_id INTEGER NOT NULL,
                seat_label TEXT NOT NULL,
                booking_id INTEGER NOT NULL,
                UNIQUE(show_id, seat_label),
                FOREIGN KEY (show_id) REFERENCES shows (id) ON DELETE CASCADE,
                FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE CASCADE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                method TEXT NOT NULL,
                status TEXT DEFAULT 'Paid',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE CASCADE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                discount_percent REAL NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER,
                rating INTEGER,
                comments TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE CASCADE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS reports_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT,
                generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT
            )
        """)

        self.conn.commit()

    def _seed_defaults(self):
        """Insert default admin user and settings if the DB is fresh."""
        row = self.fetchone("SELECT COUNT(*) as cnt FROM users")
        if row["cnt"] == 0:
            self.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (config.DEFAULT_USERNAME, self.hash_password(config.DEFAULT_PASSWORD), "admin"),
                commit=True,
            )

        defaults = {
            "tax_percent": str(config.DEFAULT_TAX_PERCENT),
            "theme": "dark",
            "cinema_name": "Cineplex Multiplex",
        }
        for key, value in defaults.items():
            existing = self.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
            if existing is None:
                self.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value), commit=True)
        self.conn.commit()

    # ------------------------------------------------------------------
    # Users / Auth
    # ------------------------------------------------------------------
    def verify_login(self, username, password):
        row = self.fetchone("SELECT * FROM users WHERE username = ?", (username,))
        if row and row["password_hash"] == self.hash_password(password):
            return row
        return None

    def change_password(self, username, new_password):
        self.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (self.hash_password(new_password), username),
            commit=True,
        )

    def list_users(self):
        return self.fetchall("SELECT id, username, role, created_at FROM users ORDER BY id")

    def add_user(self, username, password, role="staff"):
        self.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, self.hash_password(password), role),
            commit=True,
        )

    def delete_user(self, user_id):
        self.execute("DELETE FROM users WHERE id = ?", (user_id,), commit=True)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def get_setting(self, key, default=None):
        row = self.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
            commit=True,
        )

    # ------------------------------------------------------------------
    # Movies
    # ------------------------------------------------------------------
    def add_movie(self, name, language, genre, duration, price, poster_path=None, status="Active"):
        cur = self.execute(
            "INSERT INTO movies (name, language, genre, duration, price, poster_path, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, language, genre, duration, price, poster_path, status),
            commit=True,
        )
        return cur.lastrowid

    def update_movie(self, movie_id, name, language, genre, duration, price, poster_path, status):
        self.execute(
            "UPDATE movies SET name=?, language=?, genre=?, duration=?, price=?, poster_path=?, status=? "
            "WHERE id=?",
            (name, language, genre, duration, price, poster_path, status, movie_id),
            commit=True,
        )

    def delete_movie(self, movie_id):
        self.execute("DELETE FROM movies WHERE id = ?", (movie_id,), commit=True)

    def list_movies(self, active_only=False):
        if active_only:
            return self.fetchall("SELECT * FROM movies WHERE status = 'Active' ORDER BY name")
        return self.fetchall("SELECT * FROM movies ORDER BY name")

    def get_movie(self, movie_id):
        return self.fetchone("SELECT * FROM movies WHERE id = ?", (movie_id,))

    def count_movies(self):
        return self.fetchone("SELECT COUNT(*) as cnt FROM movies")["cnt"]

    # ------------------------------------------------------------------
    # Shows
    # ------------------------------------------------------------------
    def add_show(self, movie_id, show_date, show_time, hall_number, seat_capacity):
        cur = self.execute(
            "INSERT INTO shows (movie_id, show_date, show_time, hall_number, seat_capacity) "
            "VALUES (?, ?, ?, ?, ?)",
            (movie_id, show_date, show_time, hall_number, seat_capacity),
            commit=True,
        )
        return cur.lastrowid

    def update_show(self, show_id, movie_id, show_date, show_time, hall_number, seat_capacity):
        self.execute(
            "UPDATE shows SET movie_id=?, show_date=?, show_time=?, hall_number=?, seat_capacity=? "
            "WHERE id=?",
            (movie_id, show_date, show_time, hall_number, seat_capacity, show_id),
            commit=True,
        )

    def delete_show(self, show_id):
        self.execute("DELETE FROM shows WHERE id = ?", (show_id,), commit=True)

    def list_shows(self):
        return self.fetchall("""
            SELECT shows.*, movies.name AS movie_name
            FROM shows
            JOIN movies ON shows.movie_id = movies.id
            ORDER BY shows.show_date, shows.show_time
        """)

    def get_show(self, show_id):
        return self.fetchone("""
            SELECT shows.*, movies.name AS movie_name, movies.price AS movie_price
            FROM shows JOIN movies ON shows.movie_id = movies.id
            WHERE shows.id = ?
        """, (show_id,))

    def count_upcoming_shows(self):
        today = datetime.now().strftime("%Y-%m-%d")
        return self.fetchone("SELECT COUNT(*) as cnt FROM shows WHERE show_date >= ?", (today,))["cnt"]

    # ------------------------------------------------------------------
    # Seats
    # ------------------------------------------------------------------
    def get_booked_seats(self, show_id):
        rows = self.fetchall("SELECT seat_label FROM booked_seats WHERE show_id = ?", (show_id,))
        return {row["seat_label"] for row in rows}

    def lock_seats(self, show_id, seats, booking_id):
        """Insert seats as booked; raises sqlite3.IntegrityError on collision."""
        for seat in seats:
            self.execute(
                "INSERT INTO booked_seats (show_id, seat_label, booking_id) VALUES (?, ?, ?)",
                (show_id, seat, booking_id),
            )
        self.conn.commit()

    def release_seats(self, show_id, seats):
        for seat in seats:
            self.execute(
                "DELETE FROM booked_seats WHERE show_id = ? AND seat_label = ?",
                (show_id, seat),
            )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Bookings
    # ------------------------------------------------------------------
    def create_booking(self, booking_code, customer_name, phone, movie_id, show_id, seats,
                        payment_method, coupon_code, discount, tax, total_amount):
        try:
            cur = self.execute(
                "INSERT INTO bookings (booking_code, customer_name, phone, movie_id, show_id, seats, "
                "quantity, payment_method, coupon_code, discount, tax, total_amount, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Confirmed')",
                (booking_code, customer_name, phone, movie_id, show_id, ",".join(seats),
                 len(seats), payment_method, coupon_code, discount, tax, total_amount),
            )
            booking_id = cur.lastrowid
            self.lock_seats(show_id, seats, booking_id)
            self.execute(
                "INSERT INTO payments (booking_id, amount, method, status) VALUES (?, ?, ?, 'Paid')",
                (booking_id, total_amount, payment_method),
            )
            self.conn.commit()
            return booking_id
        except sqlite3.IntegrityError:
            self.conn.rollback()
            raise

    def get_booking(self, booking_id):
        return self.fetchone("""
            SELECT bookings.*, movies.name AS movie_name, movies.language, movies.genre,
                   shows.show_date, shows.show_time, shows.hall_number
            FROM bookings
            JOIN movies ON bookings.movie_id = movies.id
            JOIN shows ON bookings.show_id = shows.id
            WHERE bookings.id = ?
        """, (booking_id,))

    def get_booking_by_code(self, booking_code):
        return self.fetchone("""
            SELECT bookings.*, movies.name AS movie_name, movies.language, movies.genre,
                   shows.show_date, shows.show_time, shows.hall_number
            FROM bookings
            JOIN movies ON bookings.movie_id = movies.id
            JOIN shows ON bookings.show_id = shows.id
            WHERE bookings.booking_code = ?
        """, (booking_code,))

    def list_bookings(self, search_term=None, status=None):
        query = """
            SELECT bookings.*, movies.name AS movie_name,
                   shows.show_date, shows.show_time, shows.hall_number
            FROM bookings
            JOIN movies ON bookings.movie_id = movies.id
            JOIN shows ON bookings.show_id = shows.id
            WHERE 1=1
        """
        params = []
        if search_term:
            query += (" AND (bookings.customer_name LIKE ? OR bookings.phone LIKE ? "
                      "OR bookings.booking_code LIKE ?)")
            like = f"%{search_term}%"
            params.extend([like, like, like])
        if status and status != "All":
            query += " AND bookings.status = ?"
            params.append(status)
        query += " ORDER BY bookings.created_at DESC"
        return self.fetchall(query, tuple(params))

    def update_booking_status(self, booking_id, status):
        self.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id), commit=True)

    def cancel_booking(self, booking_id):
        booking = self.get_booking(booking_id)
        if not booking:
            return False
        seats = booking["seats"].split(",")
        self.release_seats(booking["show_id"], seats)
        self.update_booking_status(booking_id, "Cancelled")
        return True

    def delete_booking(self, booking_id):
        booking = self.get_booking(booking_id)
        if booking:
            seats = booking["seats"].split(",")
            self.release_seats(booking["show_id"], seats)
        self.execute("DELETE FROM bookings WHERE id = ?", (booking_id,), commit=True)

    def update_booking_customer(self, booking_id, customer_name, phone):
        self.execute(
            "UPDATE bookings SET customer_name = ?, phone = ? WHERE id = ?",
            (customer_name, phone, booking_id),
            commit=True,
        )

    def count_today_bookings(self):
        today = datetime.now().strftime("%Y-%m-%d")
        row = self.fetchone(
            "SELECT COUNT(*) as cnt FROM bookings WHERE date(created_at) = ? AND status='Confirmed'",
            (today,),
        )
        return row["cnt"]

    def today_revenue(self):
        today = datetime.now().strftime("%Y-%m-%d")
        row = self.fetchone(
            "SELECT COALESCE(SUM(total_amount), 0) as total FROM bookings "
            "WHERE date(created_at) = ? AND status='Confirmed'",
            (today,),
        )
        return row["total"]

    def total_seats_sold_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        row = self.fetchone(
            "SELECT COALESCE(SUM(quantity), 0) as total FROM bookings "
            "WHERE date(created_at) = ? AND status='Confirmed'",
            (today,),
        )
        return row["total"]

    # ------------------------------------------------------------------
    # Coupons
    # ------------------------------------------------------------------
    def add_coupon(self, code, discount_percent):
        self.execute(
            "INSERT INTO coupons (code, discount_percent, active) VALUES (?, ?, 1)",
            (code.upper(), discount_percent),
            commit=True,
        )

    def get_coupon(self, code):
        return self.fetchone(
            "SELECT * FROM coupons WHERE code = ? AND active = 1", (code.upper(),)
        )

    def list_coupons(self):
        return self.fetchall("SELECT * FROM coupons ORDER BY id DESC")

    def toggle_coupon(self, coupon_id, active):
        self.execute("UPDATE coupons SET active = ? WHERE id = ?", (int(active), coupon_id), commit=True)

    def delete_coupon(self, coupon_id):
        self.execute("DELETE FROM coupons WHERE id = ?", (coupon_id,), commit=True)

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------
    def revenue_between(self, start_date, end_date):
        row = self.fetchone(
            "SELECT COALESCE(SUM(total_amount), 0) as total FROM bookings "
            "WHERE date(created_at) BETWEEN ? AND ? AND status='Confirmed'",
            (start_date, end_date),
        )
        return row["total"]

    def movie_wise_revenue(self):
        return self.fetchall("""
            SELECT movies.name AS movie_name, COUNT(bookings.id) AS bookings_count,
                   COALESCE(SUM(bookings.total_amount), 0) AS revenue,
                   COALESCE(SUM(bookings.quantity), 0) AS seats_sold
            FROM movies
            LEFT JOIN bookings ON bookings.movie_id = movies.id AND bookings.status = 'Confirmed'
            GROUP BY movies.id
            ORDER BY revenue DESC
        """)

    def show_wise_revenue(self):
        return self.fetchall("""
            SELECT movies.name AS movie_name, shows.show_date, shows.show_time, shows.hall_number,
                   COUNT(bookings.id) AS bookings_count,
                   COALESCE(SUM(bookings.total_amount), 0) AS revenue
            FROM shows
            JOIN movies ON shows.movie_id = movies.id
            LEFT JOIN bookings ON bookings.show_id = shows.id AND bookings.status = 'Confirmed'
            GROUP BY shows.id
            ORDER BY shows.show_date DESC, shows.show_time DESC
        """)

    def seat_occupancy(self):
        return self.fetchall("""
            SELECT shows.id AS show_id, movies.name AS movie_name, shows.show_date, shows.show_time,
                   shows.seat_capacity,
                   (SELECT COUNT(*) FROM booked_seats WHERE booked_seats.show_id = shows.id) AS seats_booked
            FROM shows
            JOIN movies ON shows.movie_id = movies.id
            ORDER BY shows.show_date DESC
        """)

    def top_movies(self, limit=5):
        return self.fetchall("""
            SELECT movies.name AS movie_name, COALESCE(SUM(bookings.quantity), 0) AS seats_sold,
                   COALESCE(SUM(bookings.total_amount), 0) AS revenue
            FROM movies
            LEFT JOIN bookings ON bookings.movie_id = movies.id AND bookings.status = 'Confirmed'
            GROUP BY movies.id
            ORDER BY seats_sold DESC
            LIMIT ?
        """, (limit,))

    def most_booked_shows(self, limit=5):
        return self.fetchall("""
            SELECT movies.name AS movie_name, shows.show_date, shows.show_time,
                   COUNT(bookings.id) AS total_bookings
            FROM shows
            JOIN movies ON shows.movie_id = movies.id
            LEFT JOIN bookings ON bookings.show_id = shows.id AND bookings.status = 'Confirmed'
            GROUP BY shows.id
            ORDER BY total_bookings DESC
            LIMIT ?
        """, (limit,))

    def daily_closing_report(self, date_str=None):
        date_str = date_str or datetime.now().strftime("%Y-%m-%d")
        row = self.fetchone("""
            SELECT COUNT(*) as total_bookings, COALESCE(SUM(total_amount), 0) as total_revenue,
                   COALESCE(SUM(quantity), 0) as total_seats
            FROM bookings WHERE date(created_at) = ? AND status = 'Confirmed'
        """, (date_str,))
        return row

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------
    def add_feedback(self, booking_id, rating, comments):
        self.execute(
            "INSERT INTO feedback (booking_id, rating, comments) VALUES (?, ?, ?)",
            (booking_id, rating, comments),
            commit=True,
        )

    # ------------------------------------------------------------------
    # Backup / Restore
    # ------------------------------------------------------------------
    def backup_database(self):
        os.makedirs(config.BACKUPS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(config.BACKUPS_DIR, f"movies_backup_{timestamp}.db")
        self.conn.commit()
        shutil.copyfile(self.db_path, backup_path)
        return backup_path

    def restore_database(self, backup_path):
        self.conn.close()
        shutil.copyfile(backup_path, self.db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self):
        self.conn.close()
