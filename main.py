"""Application entry point."""

import tkinter as tk

import database as db
from gui import ClinicApp


def main():
    db.init_db()
    root = tk.Tk()
    ClinicApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
