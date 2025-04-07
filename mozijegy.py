import os
import sqlite3
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import Meter
import plotly.graph_objects as go
from fpdf import FPDF
import datetime

DB_FILE = "mozijegy.db"

def initialize_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            total_seats INTEGER NOT NULL,
            booked_seats INTEGER NOT NULL DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TicketTypes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL UNIQUE,
            price REAL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL,
            ticket_type_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY(movie_id) REFERENCES Movies(id),
            FOREIGN KEY(ticket_type_id) REFERENCES TicketTypes(id)
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM Movies")
    if cursor.fetchone()[0] == 0:
        movies = [
            ("Film 1", "Ez az első film leírása.", 100, 0),
            ("Film 2", "Ez a második film leírása.", 80, 0),
            ("Film 3", "Ez a harmadik film leírása.", 120, 0)
        ]
        cursor.executemany("INSERT INTO Movies (title, description, total_seats, booked_seats) VALUES (?, ?, ?, ?)", movies)
    
    cursor.execute("SELECT COUNT(*) FROM TicketTypes")
    if cursor.fetchone()[0] == 0:
        ticket_types = [
            ("Felnőtt", 3000),
            ("Gyermek", 2000),
            ("Diák", 2500),
        ]
        cursor.executemany("INSERT INTO TicketTypes (type, price) VALUES (?, ?)", ticket_types)
    
    conn.commit()
    conn.close()

class MovieTicketSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Mozi Jegyfoglaló")
        self.conn = sqlite3.connect(DB_FILE)
        
        self.create_main_widgets()
        self.load_movies()
    
    def create_main_widgets(self):
        self.movie_frame = ttkb.Frame(self.root, padding=10)
        self.movie_frame.pack(fill=tk.BOTH, expand=True)
        
        self.movie_list_label = ttkb.Label(self.movie_frame, text="Választható filmek:", font=("Segoe UI", 12, "bold"))
        self.movie_list_label.pack(pady=(0, 5))
        
        self.movie_listbox = tk.Listbox(self.movie_frame, height=10, font=("Segoe UI", 10))
        self.movie_listbox.pack(fill=tk.BOTH, expand=True)
        self.movie_listbox.bind("<<ListboxSelect>>", self.on_movie_select)
    
    def load_movies(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title FROM Movies")
        self.movies = cursor.fetchall() 
        self.movie_listbox.delete(0, tk.END)
        for movie in self.movies:
            self.movie_listbox.insert(tk.END, movie[1])
    
    def on_movie_select(self, event):
        if not self.movie_listbox.curselection():
            return
        index = self.movie_listbox.curselection()[0]
        movie_id, movie_title = self.movies[index]
        cursor = self.conn.cursor()
        cursor.execute("SELECT description, total_seats, booked_seats FROM Movies WHERE id=?", (movie_id,))
        result = cursor.fetchone()
        if result:
            description, total_seats, booked_seats = result
            available_seats = total_seats - booked_seats
            DetailWindow(self.root, movie_id, movie_title, description, available_seats, self.conn, self)
    
    def refresh_movies(self):
        self.load_movies()

class DetailWindow:
    def __init__(self, master, movie_id, title, description, available_seats, conn, app):
        self.master = master
        self.movie_id = movie_id
        self.title = title
        self.description = description
        self.available_seats = available_seats
        self.conn = conn
        self.app = app
        
        self.win = ttkb.Toplevel(master)
        self.win.title(f"{title} - Részletek")
        
        self.create_widgets()
    
    def create_widgets(self):
        frame = ttkb.Frame(self.win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttkb.Label(frame, text=self.title, font=("Segoe UI", 16, "bold")).pack(pady=(0,5))
        ttkb.Label(frame, text=self.description, wraplength=300, font=("Segoe UI", 10)).pack(pady=(0,5))
        self.seats_label = ttkb.Label(frame, text=f"Elérhető ülőhelyek: {self.available_seats}", font=("Segoe UI", 10, "bold"))
        self.seats_label.pack(pady=(0,5))
        
        book_button = ttkb.Button(frame, text="Jegyfoglalás", bootstyle=PRIMARY, command=self.open_booking_window)
        book_button.pack(pady=(10,0))
    
    def open_booking_window(self):
        BookingWindow(self.win, self.movie_id, self.title, self.available_seats, self.conn, self)

class BookingWindow:
    def __init__(self, master, movie_id, movie_title, available_seats, conn, detail_window):
        self.master = master
        self.movie_id = movie_id
        self.movie_title = movie_title
        self.available_seats = available_seats
        self.conn = conn
        self.detail_window = detail_window
        
        self.selected_tickets = []
        
        self.win = ttkb.Toplevel(master)
        self.win.title(f"Jegyfoglalás - {movie_title}")
        self.create_widgets()
    
    def create_widgets(self):
        frame = ttkb.Frame(self.win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        percent = round((self.conn.execute("SELECT booked_seats, total_seats FROM Movies WHERE id=?", (self.movie_id,)).fetchone()[0] / self.conn.execute("SELECT total_seats FROM Movies WHERE id=?", (self.movie_id,)).fetchone()[0]) * 100)
        color = "success" if percent < 40 else "warning" if percent < 90 else "danger"
        
        self.meter = Meter(
            frame,
            bootstyle=color,
            subtext="Foglaltság",
            amountused=percent,
            amounttotal=100,
            meterthickness=15,
            textfont=("Helvetica", 12, "bold"),
            subtextfont=("Helvetica", 10)
        )
        self.meter.grid(row=0, column=2, rowspan=5, padx=(20, 0), pady=10)
        
        ttkb.Label(frame, text="Jegytípus:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.ticket_type_var = tk.StringVar()
        self.ticket_types = self.get_ticket_types()
        self.ticket_type_dropdown = ttkb.Combobox(frame, textvariable=self.ticket_type_var, state="readonly", bootstyle=INFO)
        self.ticket_type_dropdown['values'] = [tt[1] for tt in self.ticket_types]
        self.ticket_type_dropdown.grid(row=0, column=1, sticky=tk.W, pady=5)
        if self.ticket_types:
            self.ticket_type_dropdown.current(0)
        
        ttkb.Label(frame, text="Mennyiség:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.quantity_entry = ttkb.Entry(frame, bootstyle=SECONDARY)
        self.quantity_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        add_button = ttkb.Button(frame, text="Jegy hozzáadása", bootstyle=SUCCESS, command=self.add_ticket)
        add_button.grid(row=2, column=0, columnspan=2, pady=5)
        
        ttkb.Label(frame, text="Hozzáadott jegyek:").grid(row=3, column=0, columnspan=2, pady=(10, 5))
        self.tickets_listbox = tk.Listbox(frame, height=5, width=40, font=("Segoe UI", 10))
        self.tickets_listbox.grid(row=4, column=0, columnspan=2, pady=5)
        
        confirm_button = ttkb.Button(frame, text="Foglalás véglegesítése", bootstyle=PRIMARY, command=self.confirm_booking)
        confirm_button.grid(row=5, column=0, columnspan=2, pady=(10,0))
        
        delete_btn = ttkb.Button(frame, text="Foglalás törlése", command=self.delete_booking_window, bootstyle="danger")
        delete_btn.grid(row=3, column=0, columnspan=2, pady=(5, 10))

        stat_btn = ttkb.Button(frame, text="Statisztika megtekintése", command=self.show_statistics, bootstyle="info")
        stat_btn.grid(row=6, column=0, columnspan=2, pady=(5, 0))
    
    def get_ticket_types(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, type, price FROM TicketTypes")
        return cursor.fetchall()
    
    def add_ticket(self):
        ticket_type_name = self.ticket_type_var.get()
        try:
            quantity = int(self.quantity_entry.get())
        except ValueError:
            messagebox.showerror("Hiba", "A mennyiségnek egész számnak kell lennie!")
            return
        
        if quantity <= 0:
            messagebox.showerror("Hiba", "A mennyiségnek legalább 1-nek kell lennie!")
            return
        
        ticket_type_id = None
        for tt in self.ticket_types:
            if tt[1] == ticket_type_name:
                ticket_type_id = tt[0]
                break
        
        if ticket_type_id is None:
            messagebox.showerror("Hiba", "Érvénytelen jegytípus!")
            return
        
        self.selected_tickets.append((ticket_type_id, ticket_type_name, quantity))
        self.tickets_listbox.insert(tk.END, f"{ticket_type_name}: {quantity} db")
        self.quantity_entry.delete(0, tk.END)

    def delete_booking_window(self):
        def delete():
            try:
                booking_id = int(entry.get())
                cursor = self.conn.cursor()
                cursor.execute("SELECT movie_id, quantity FROM Bookings WHERE id=?", (booking_id,))
                result = cursor.fetchone()
                if not result:
                    messagebox.showerror("Hiba", "Nincs ilyen foglalás.")
                    return
                movie_id, quantity = result
                cursor.execute("DELETE FROM Bookings WHERE id=?", (booking_id,))
                cursor.execute("UPDATE Movies SET booked_seats = booked_seats - ? WHERE id=?", (quantity, movie_id))
                self.conn.commit()
                messagebox.showinfo("Siker", "Foglalás törölve.")
                top.destroy()
                self.win.destroy()
                self.detail_window.app.refresh_movies()
            except Exception as e:
                messagebox.showerror("Hiba", f"Hiba történt: {e}")

        top = tk.Toplevel(self.master)
        top.title("Foglalás törlése")
        ttkb.Label(top, text="Foglalási szám:").pack(padx=10, pady=5)
        entry = tk.Entry(top)
        entry.pack(padx=10, pady=5)
        ttkb.Button(top, text="Törlés", command=delete, bootstyle="danger").pack(padx=10, pady=10)
    
    def confirm_booking(self):
        total_tickets = sum(item[2] for item in self.selected_tickets)
        if total_tickets == 0:
            messagebox.showerror("Hiba", "Nem adtál meg jegyet!")
            return
        
        if total_tickets > self.available_seats:
            messagebox.showerror("Hiba", f"Nem elég hely! Elérhető ülőhelyek: {self.available_seats}")
            return
        
        cursor = self.conn.cursor()
        try:
            for ticket in self.selected_tickets:
                ticket_type_id, ticket_type, quantity = ticket
                cursor.execute("""
                    INSERT INTO Bookings (movie_id, ticket_type_id, quantity)
                    VALUES (?, ?, ?)
                """, (self.movie_id, ticket_type_id, quantity))
            cursor.execute("""
                UPDATE Movies
                SET booked_seats = booked_seats + ?
                WHERE id = ?
            """, (total_tickets, self.movie_id))

            output_dir = "tickets"
            os.makedirs(output_dir, exist_ok=True)

            pdf = FPDF()
            pdf.add_page()

            font_path = "DejaVuSans.ttf"
            pdf.add_font("DejaVu", "", font_path, uni=True)
            pdf.set_font("DejaVu", size=12)

            pdf.cell(200, 10, txt="Mozi Jegy", ln=True, align='C')
            pdf.ln(10)
            pdf.cell(200, 10, txt=f"Film címe: {self.movie_title}", ln=True)
            pdf.cell(200, 10, txt=f"Dátum: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)

            pdf.ln(5)
            for idx, ticket in enumerate(self.selected_tickets, 1):
                pdf.cell(200, 10, txt=f"{idx}. Jegytípus: {ticket[1]} - {ticket[2]} db", ln=True)

            last_id = cursor.execute("SELECT MAX(id) FROM Bookings").fetchone()[0]
            pdf.ln(5)
            pdf.cell(200, 10, txt=f"Foglalási szám: {last_id}", ln=True)

            file_path = os.path.join(output_dir, f"jegy_{last_id}.pdf")
            pdf.output(file_path)

            self.conn.commit()
            messagebox.showinfo("Siker", "A foglalás sikeresen rögzítésre került!")
            self.win.destroy()
            self.detail_window.available_seats -= total_tickets
            self.detail_window.seats_label.config(text=f"Elérhető ülőhelyek: {self.detail_window.available_seats}")
            self.detail_window.app.refresh_movies()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Hiba", f"Adatbázis hiba: {e}")

    def show_statistics(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT title, total_seats, booked_seats FROM Movies")
        data = cursor.fetchall()

        titles = [row[0] for row in data]
        occupancy = [round((row[2] / row[1]) * 100) if row[1] > 0 else 0 for row in data]

        fig = go.Figure(data=[
            go.Bar(x=titles, y=occupancy, marker_color='lightskyblue')
        ])
        fig.update_layout(title="Terem foglaltsági arányok", xaxis_title="Film", yaxis_title="Foglaltság (%)", yaxis_range=[0, 100])
        fig.show()

if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
        initialize_db()
    
    root = ttkb.Window(themename="superhero")
    app = MovieTicketSystem(root)
    root.mainloop()
