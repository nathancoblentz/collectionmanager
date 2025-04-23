import sqlite3
import tkinter as tk  # Ensure tkinter is imported as tk
from tkinter import ttk, simpledialog, messagebox
from gui2 import LoginWindow

if __name__ == "__main__":
    # Initialize root window
    root = tk.Tk()
    root.withdraw() # hide main window until logged in.

    login_window = LoginWindow(master=root)
    login_window.mainloop()