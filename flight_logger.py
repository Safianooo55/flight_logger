"""
Flight Logger (Integrated)
- GUI with Tkinter
- Per-aircraft CSV logs in "aircraft_logs/<TAIL>/flights.csv"
- Overlap detection
- View history table
- Plot monthly flight hours
- Export CSV / Excel
"""

import os
import csv
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------
# Configuration / Helpers
# -------------------------
BASE_DIR = "aircraft_logs"   # folder where each aircraft has its own folder

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)


def aircraft_folder(tail_number: str) -> str:
    """Return folder path for a tail number (uppercased)."""
    tn = tail_number.strip().upper()
    path = os.path.join(BASE_DIR, tn)
    os.makedirs(path, exist_ok=True)
    return path


def flights_csv_path(tail_number: str) -> str:
    return os.path.join(aircraft_folder(tail_number), "flights.csv")


def read_flights_df(tail_number: str) -> pd.DataFrame:
    path = flights_csv_path(tail_number)
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            return df
        except Exception:
            # If corrupted, return empty with correct columns
            pass
    # create empty with correct columns
    cols = [
        "Date", "Tail Number", "Takeoff Time", "Landing Time",
        "Flight Duration (hrs)", "Landings This Flight",
        "Total Hours After Flight", "Total Landings After Flight"
    ]
    return pd.DataFrame(columns=cols)


def write_flights_df(tail_number: str, df: pd.DataFrame):
    path = flights_csv_path(tail_number)
    df.to_csv(path, index=False)


def parse_datetime(date_str: str, time_str: str) -> datetime:
    """Parse YYYY-MM-DD and HH:MM into a datetime."""
    return datetime.strptime(f"{date_str.strip()} {time_str.strip()}", "%Y-%m-%d %H:%M")


def calc_duration_hours(date_str: str, takeoff: str, landing: str) -> float:
    """Calculate hours between takeoff and landing; handle overnight flights."""
    t1 = parse_datetime(date_str, takeoff)
    t2 = parse_datetime(date_str, landing)
    if t2 < t1:
        # landing after midnight -> add 1 day
        t2 += timedelta(days=1)
    seconds = (t2 - t1).total_seconds()
    hours = seconds / 3600.0
    # round to 2 decimals (digit-by-digit exactness principle)
    return round(hours, 2)


def detect_overlap(tail_number: str, date_str: str, takeoff: str, landing: str) -> bool:
    """Return True if (date,takeoff-landing) overlaps any existing flight for same tail_number."""
    df = read_flights_df(tail_number)
    if df.empty:
        return False

    # Compute new interval
    new_start = parse_datetime(date_str, takeoff)
    new_end = parse_datetime(date_str, landing)
    if new_end < new_start:
        new_end += timedelta(days=1)

    # iterate existing flights for same date (and possible overlaps if previous entry crosses midnight)
    for _, row in df.iterrows():
        try:
            existing_start = parse_datetime(row["Date"], row["Takeoff Time"])
            existing_end = parse_datetime(row["Date"], row["Landing Time"])
            if existing_end < existing_start:
                existing_end += timedelta(days=1)
        except Exception:
            continue

        # Overlap if intervals intersect:
        if (new_start < existing_end) and (new_end > existing_start):
            return True
    return False


# -------------------------
# Core operations
# -------------------------
def add_flight_record(date_str: str, tail: str, takeoff: str, landing: str, landings_this: int) -> (bool, str):
    """Adds a flight; returns (success, message)."""
    tail = tail.strip().upper()
    # basic validations
    if not tail:
        return False, "Tail number required."
    try:
        # parse to ensure valid format
        duration = calc_duration_hours(date_str, takeoff, landing)
    except Exception as e:
        return False, f"Date/time parse error: {e}"

    # overlap detection
    if detect_overlap(tail, date_str, takeoff, landing):
        return False, "Overlap detected with existing flight."

    df = read_flights_df(tail)
    if df.empty:
        prev_hours = 0.0
        prev_landings = 0
    else:
        # last totals
        prev_hours = float(df["Total Hours After Flight"].iloc[-1])
        prev_landings = int(df["Total Landings After Flight"].iloc[-1])

    new_total_hours = round(prev_hours + duration, 2)
    new_total_landings = prev_landings + int(landings_this)

    new_row = {
        "Date": date_str,
        "Tail Number": tail,
        "Takeoff Time": takeoff,
        "Landing Time": landing,
        "Flight Duration (hrs)": duration,
        "Landings This Flight": int(landings_this),
        "Total Hours After Flight": new_total_hours,
        "Total Landings After Flight": new_total_landings
    }

    df = df.append(new_row, ignore_index=True)
    write_flights_df(tail, df)
    return True, "Flight added successfully."


# -------------------------
# GUI
# -------------------------
class FlightLoggerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Flight Logger")
        self._build_widgets()
        self._populate_aircraft_list()

    def _build_widgets(self):
        frm = ttk.Frame(self.root, padding=12)
        frm.grid(sticky="NSEW")

        # labels + entries
        ttk.Label(frm, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="e")
        self.date_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.date_var, width=20).grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="Tail Number:").grid(row=1, column=0, sticky="e")
        self.tail_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.tail_var, width=20).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Takeoff Time (HH:MM):").grid(row=2, column=0, sticky="e")
        self.takeoff_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.takeoff_var, width=20).grid(row=2, column=1, sticky="w")

        ttk.Label(frm, text="Landing Time (HH:MM):").grid(row=3, column=0, sticky="e")
        self.landing_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.landing_var, width=20).grid(row=3, column=1, sticky="w")

        ttk.Label(frm, text="Number of Landings:").grid(row=4, column=0, sticky="e")
        self.landings_var = tk.StringVar(value="1")
        ttk.Entry(frm, textvariable=self.landings_var, width=20).grid(row=4, column=1, sticky="w")

        # Buttons row
        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0))

        ttk.Button(btn_frame, text="Add Flight", command=self._on_add_flight).grid(row=0, column=0, padx=4)
        ttk.Button(btn_frame, text="View History", command=self._on_view_history).grid(row=0, column=1, padx=4)
        ttk.Button(btn_frame, text="Plot Monthly Hours", command=self._on_plot_hours).grid(row=0, column=2, padx=4)
        ttk.Button(btn_frame, text="Export CSV/Excel", command=self._on_export).grid(row=0, column=3, padx=4)

        # Aircraft list and quick select
        ttk.Label(frm, text="Saved Aircraft:").grid(row=6, column=0, sticky="ne", pady=(12, 0))
        self.aircraft_list = tk.Listbox(frm, height=6)
        self.aircraft_list.grid(row=6, column=1, sticky="w", pady=(12, 0))
        self.aircraft_list.bind("<<ListboxSelect>>", self._on_aircraft_select)

        # status area
        self.status = tk.StringVar()
        ttk.Label(frm, textvariable=self.status, foreground="blue").grid(row=7, column=0, columnspan=2, pady=(10, 0), sticky="w")

    def _populate_aircraft_list(self):
        self.aircraft_list.delete(0, tk.END)
        try:
            for name in sorted(os.listdir(BASE_DIR)):
                full = os.path.join(BASE_DIR, name)
                if os.path.isdir(full):
                    self.aircraft_list.insert(tk.END, name)
        except FileNotFoundError:
            pass

    def _on_aircraft_select(self, event=None):
        sel = self.aircraft_list.curselection()
        if sel:
            tail = self.aircraft_list.get(sel[0])
            self.tail_var.set(tail)

    def _on_add_flight(self):
        date = self.date_var.get().strip()
        tail = self.tail_var.get().strip()
        takeoff = self.takeoff_var.get().strip()
        landing = self.landing_var.get().strip()
        landings = self.landings_var.get().strip()

        # validate
        if not all([date, tail, takeoff, landing, landings]):
            messagebox.showerror("Missing fields", "Please fill in all fields.")
            return
        try:
            int(landings)
        except ValueError:
            messagebox.showerror("Invalid input", "Number of landings must be an integer.")
            return

        success, msg = add_flight_record(date, tail, takeoff, landing, int(landings))
        if success:
            self.status.set(msg)
            self._populate_aircraft_list()
        else:
            messagebox.showwarning("Not added", msg)

    def _on_view_history(self):
        tail = self.tail_var.get().strip().upper()
        if not tail:
            messagebox.showerror("No Tail Number", "Enter or select a tail number to view history.")
            return
        df = read_flights_df(tail)
        if df.empty:
            messagebox.showinfo("No Data", f"No flights found for {tail}.")
            return
        # show in a treeview
        win = tk.Toplevel(self.root)
        win.title(f"History - {tail}")
        tv = ttk.Treeview(win, columns=list(df.columns), show="headings")
        tv.pack(fill="both", expand=True)
        for col in df.columns:
            tv.heading(col, text=col)
            tv.column(col, anchor="center")
        for _, row in df.iterrows():
            tv.insert("", "end", values=list(row))
        # add a scrollbar
        vsb = ttk.Scrollbar(win, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")

    def _on_plot_hours(self):
        tail = self.tail_var.get().strip().upper()
        if not tail:
            messagebox.showerror("No Tail Number", "Enter or select a tail number to plot.")
            return
        df = read_flights_df(tail)
        if df.empty:
            messagebox.showinfo("No Data", f"No flights found for {tail}.")
            return
        # prepare monthly aggregation
        try:
            df["Date"] = pd.to_datetime(df["Date"])
            df["Month"] = df["Date"].dt.to_period("M")
            monthly = df.groupby("Month")["Flight Duration (hrs)"].sum().reset_index()
            # plot
            plt.figure(figsize=(8, 4))
            plt.bar(monthly["Month"].astype(str), monthly["Flight Duration (hrs)"])
            plt.xlabel("Month")
            plt.ylabel("Total Flight Hours")
            plt.title(f"Monthly Flight Hours — {tail}")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            messagebox.showerror("Plot Error", f"Could not prepare chart: {e}")

    def _on_export(self):
        tail = self.tail_var.get().strip().upper()
        if not tail:
            messagebox.showerror("No Tail Number", "Enter or select a tail number to export.")
            return
        df = read_flights_df(tail)
        if df.empty:
            messagebox.showinfo("No Data", f"No flights found for {tail}.")
            return

        filetypes = [("CSV file", "*.csv"), ("Excel file", "*.xlsx")]
        out_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=filetypes,
                                                title="Export flight history")
        if not out_path:
            return
        try:
            if out_path.lower().endswith(".csv"):
                df.to_csv(out_path, index=False)
            else:
                df.to_excel(out_path, index=False)
            messagebox.showinfo("Exported", f"Saved to: {out_path}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))


# -------------------------
# Run
# -------------------------
def main():
    root = tk.Tk()
    root.geometry("520x420")
    app = FlightLoggerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
