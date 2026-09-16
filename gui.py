"""Tkinter interface for the hospital management application."""

import sqlite3
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

import database as db


class ClinicApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hospital Management System")
        self.root.geometry("950x650")
        self.root.minsize(850, 550)
        self.patient_options = {}

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill="both", padx=15, pady=15)

        self.registration_tab = ttk.Frame(self.notebook)
        self.booking_tab = ttk.Frame(self.notebook)
        self.status_tab = ttk.Frame(self.notebook)
        self.records_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.registration_tab, text="Patient Registration")
        self.notebook.add(self.booking_tab, text="Book Appointment")
        self.notebook.add(self.status_tab, text="Appointment Status")
        self.notebook.add(self.records_tab, text="Patient Records")

        self.setup_registration_tab()
        self.setup_booking_tab()
        self.setup_status_tab()
        self.setup_records_tab()
        self.refresh_patient_views()

    @staticmethod
    def show_database_error(error):
        messagebox.showerror(
            "Database Error", f"The change could not be saved.\n\n{error}"
        )

    def setup_registration_tab(self):
        self.registration_tab.columnconfigure(1, weight=1)
        ttk.Label(
            self.registration_tab,
            text="Patient Registration",
            font=("Arial", 18, "bold"),
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(25, 30), sticky="w")
        self.name_entry = self.add_labeled_entry(self.registration_tab, "Full Name:", 1)
        self.contact_entry = self.add_labeled_entry(
            self.registration_tab, "Contact:", 2
        )
        self.age_entry = self.add_labeled_entry(self.registration_tab, "Age:", 3)
        buttons = ttk.Frame(self.registration_tab)
        buttons.grid(row=4, column=0, columnspan=2, pady=30)
        ttk.Button(buttons, text="Register Patient", command=self.save_patient).grid(
            row=0, column=0, padx=10
        )
        ttk.Button(buttons, text="Clear", command=self.clear_patient_form).grid(
            row=0, column=1, padx=10
        )

    @staticmethod
    def add_labeled_entry(parent, label, row):
        ttk.Label(parent, text=label).grid(
            row=row, column=0, padx=20, pady=12, sticky="w"
        )
        entry = ttk.Entry(parent, width=40)
        entry.grid(row=row, column=1, padx=20, pady=12, sticky="w")
        return entry

    def save_patient(self):
        name = self.name_entry.get().strip()
        contact = self.contact_entry.get().strip()
        age_text = self.age_entry.get().strip()
        if not name or not age_text:
            messagebox.showwarning("Missing Information", "Name and age are required.")
            return
        try:
            age = int(age_text)
            if age <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Invalid Age", "Enter a positive whole number for age."
            )
            return
        try:
            db.add_patient(name, contact, age)
        except sqlite3.Error as error:
            self.show_database_error(error)
            return
        self.clear_patient_form()
        self.refresh_patient_views()
        messagebox.showinfo("Success", "Patient registered successfully.")

    def clear_patient_form(self):
        for entry in (self.name_entry, self.contact_entry, self.age_entry):
            entry.delete(0, tk.END)
        self.name_entry.focus()

    def setup_booking_tab(self):
        self.booking_tab.columnconfigure(1, weight=1)
        ttk.Label(
            self.booking_tab, text="Appointment Booking", font=("Arial", 18, "bold")
        ).grid(row=0, column=0, columnspan=3, padx=20, pady=(25, 30), sticky="w")
        ttk.Label(self.booking_tab, text="Select Patient:").grid(
            row=1, column=0, padx=15, pady=12, sticky="w"
        )
        self.booking_patient_combo = ttk.Combobox(
            self.booking_tab, state="readonly", width=35
        )
        self.booking_patient_combo.grid(row=1, column=1, padx=15, pady=12, sticky="w")
        ttk.Button(
            self.booking_tab,
            text="Refresh Patients",
            command=self.refresh_patient_views,
        ).grid(row=1, column=2, padx=10, pady=12)
        self.doctor_entry = self.add_labeled_entry(self.booking_tab, "Doctor Name:", 2)
        self.date_entry = self.add_labeled_entry(
            self.booking_tab, "Date (YYYY-MM-DD):", 3
        )
        buttons = ttk.Frame(self.booking_tab)
        buttons.grid(row=4, column=0, columnspan=3, pady=30)
        ttk.Button(buttons, text="Book Appointment", command=self.save_booking).grid(
            row=0, column=0, padx=10
        )
        ttk.Button(buttons, text="Clear", command=self.clear_booking_form).grid(
            row=0, column=1, padx=10
        )

    def clear_booking_form(self):
        self.booking_patient_combo.set("")
        self.doctor_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.booking_patient_combo.focus()

    def setup_status_tab(self):
        self.status_tab.rowconfigure(2, weight=1)
        self.status_tab.columnconfigure(0, weight=1)
        ttk.Label(
            self.status_tab, text="Appointment Status", font=("Arial", 18, "bold")
        ).grid(row=0, column=0, columnspan=4, padx=20, pady=(25, 20), sticky="w")
        ttk.Label(self.status_tab, text="Select Patient:").grid(
            row=1, column=0, padx=10, pady=10, sticky="e"
        )
        self.status_patient_combo = ttk.Combobox(
            self.status_tab, state="readonly", width=25
        )
        self.status_patient_combo.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        ttk.Button(
            self.status_tab, text="Refresh Patients", command=self.refresh_patient_views
        ).grid(row=1, column=2, padx=5, pady=10)
        ttk.Button(
            self.status_tab,
            text="View Appointments",
            command=self.view_patient_appointments,
        ).grid(row=1, column=3, padx=5, pady=10)

        columns = ("Appointment ID", "Name", "Contact", "Doctor", "Date", "Status")
        table = ttk.Frame(self.status_tab)
        table.grid(row=2, column=0, columnspan=4, padx=20, pady=10, sticky="nsew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.status_tree = ttk.Treeview(table, columns=columns, show="headings")
        for column, width, anchor in zip(
            columns,
            (110, 180, 120, 170, 120, 120),
            ("center", "w", "center", "w", "center", "center"),
        ):
            self.status_tree.heading(column, text=column)
            self.status_tree.column(column, width=width, anchor=anchor)
        self.add_scrollbar(table, self.status_tree)
        buttons = ttk.Frame(self.status_tab)
        buttons.grid(row=3, column=0, columnspan=4, pady=15)
        ttk.Button(
            buttons,
            text="Mark Completed",
            command=lambda: self.set_selected_appointment_status("Completed"),
        ).grid(row=0, column=0, padx=8)
        ttk.Button(
            buttons,
            text="Cancel Appointment",
            command=lambda: self.set_selected_appointment_status("Cancelled"),
        ).grid(row=0, column=1, padx=8)
        ttk.Button(
            buttons, text="Refresh", command=self.view_patient_appointments
        ).grid(row=0, column=2, padx=8)

    @staticmethod
    def add_scrollbar(parent, tree):
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.grid(row=0, column=0, sticky="nsew")
        tree.configure(yscrollcommand=scrollbar.set)

    def refresh_patient_views(self):
        patients = db.get_all_patients()
        self.patient_options = {
            f"{name} (ID: {patient_id})": patient_id
            for patient_id, name, _contact, _age in patients
        }
        options = list(self.patient_options)
        self.booking_patient_combo["values"] = options
        self.status_patient_combo["values"] = options
        self.refresh_patient_records(patients)

    def save_booking(self):
        patient_id = self.patient_options.get(self.booking_patient_combo.get())
        doctor = self.doctor_entry.get().strip()
        appointment_date = self.date_entry.get().strip()
        if not patient_id or not doctor or not appointment_date:
            messagebox.showwarning("Missing Information", "All fields are required.")
            return
        try:
            date.fromisoformat(appointment_date)
        except ValueError:
            messagebox.showwarning("Invalid Date", "Use the YYYY-MM-DD date format.")
            return
        try:
            db.add_appointment(patient_id, doctor, appointment_date)
        except sqlite3.Error as error:
            self.show_database_error(error)
            return
        self.clear_booking_form()
        messagebox.showinfo("Success", "Appointment booked successfully.")

    def view_patient_appointments(self):
        self.clear_tree(self.status_tree)
        patient_id = self.patient_options.get(self.status_patient_combo.get())
        if not patient_id:
            messagebox.showwarning("Missing Selection", "Select a patient first.")
            return
        try:
            appointments = db.get_appointments_by_patient(patient_id)
        except sqlite3.Error as error:
            self.show_database_error(error)
            return
        if not appointments:
            messagebox.showinfo(
                "No Appointments", "No appointments found for this patient."
            )
            return
        for appointment in appointments:
            self.status_tree.insert("", tk.END, values=appointment)

    def set_selected_appointment_status(self, status):
        selection = self.status_tree.selection()
        if not selection:
            messagebox.showwarning(
                "Missing Selection", "Select an appointment from the table first."
            )
            return
        appointment_id = self.status_tree.item(selection[0], "values")[0]
        if not messagebox.askyesno(
            "Confirm Update", f"Mark appointment #{appointment_id} as {status}?"
        ):
            return
        try:
            if not db.update_appointment_status(appointment_id, status):
                messagebox.showwarning(
                    "Appointment Not Found",
                    "The selected appointment no longer exists.",
                )
                return
        except sqlite3.Error as error:
            self.show_database_error(error)
            return
        messagebox.showinfo(
            "Updated", f"Appointment #{appointment_id} marked as {status}."
        )
        self.view_patient_appointments()

    def setup_records_tab(self):
        self.records_tab.rowconfigure(1, weight=1)
        self.records_tab.columnconfigure(0, weight=1)
        ttk.Label(
            self.records_tab, text="Patient Records", font=("Arial", 18, "bold")
        ).grid(row=0, column=0, padx=20, pady=(25, 20), sticky="w")
        table = ttk.Frame(self.records_tab)
        table.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        columns = ("ID", "Name", "Contact", "Age")
        self.records_tree = ttk.Treeview(table, columns=columns, show="headings")
        for column, width, anchor in zip(
            columns, (80, 250, 180, 100), ("center", "w", "center", "center")
        ):
            self.records_tree.heading(column, text=column)
            self.records_tree.column(column, width=width, anchor=anchor)
        self.add_scrollbar(table, self.records_tree)
        ttk.Button(
            self.records_tab, text="Refresh Data", command=self.refresh_patient_views
        ).grid(row=2, column=0, pady=15)

    @staticmethod
    def clear_tree(tree):
        for item in tree.get_children():
            tree.delete(item)

    def refresh_patient_records(self, patients=None):
        patients = db.get_all_patients() if patients is None else patients
        self.clear_tree(self.records_tree)
        for patient in patients:
            self.records_tree.insert("", tk.END, values=patient)
