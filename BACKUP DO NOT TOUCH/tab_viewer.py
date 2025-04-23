import sqlite3
import tkinter as tk  # Ensure tkinter is imported as tk
from tkinter import ttk, simpledialog, messagebox
from models import User, Item, Source, Collection, BaseModel  # Assuming these models are defined in models.py
from db import connect, login, get_logged_in_user, is_admin  # Import the required functions from db.py

class TabViewer(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # Tabs are stored in a dictionary
        self.tabs_config = {
            "My Items": {
                "visible": lambda: True,
                "columns": (
                    "ItemName", "Collection", "User", "Source", "Status", 
                    "Description", "PricePaid", "CurrentValue", "Location", "Notes"
                ),
                "query": ""
            },
            "Users": {
                "visible": lambda: is_admin(),  # Visible only to admin
                "columns": ("Username", "Role", "Status"),
                "query": "SELECT Username, Role, Status FROM User"
            },
            "Items": {
                "visible": lambda: True,  # Always visible
                "columns": (
                    "ItemName", "Collection", "User", "Source", "Status", 
                    "Description", "PricePaid", "CurrentValue", "Location", "Notes"
                ),
                "query": self.get_filtered_query("Item", [
                    "ItemID", "ItemName", "Collection", "User", "Source", "Status", 
                    "Description", "PricePaid", "CurrentValue", "Location", "Notes"
                ])
            },
            "Collections": {
                "visible": lambda: True,  # Always visible
                "columns": ("CollectionName", "User", "Status"),
                "query": self.get_filtered_query("Collection", ["CollectionName", "User", "Status"])
            },
            "Sources": {
                "visible": lambda: True,  # Always visible
                "columns": (
                    "BusinessName", "FirstName", "LastName", "Phone", "Address", 
                    "City", "State", "Zip", "Email"
                ),
                "query": """
                    SELECT BusinessName, FirstName, LastName, Phone, Address, 
                    City, State, Zip, Email FROM Source
                """
            }
        }

        self.tabs = {}
        self.user_tree = None
        self.item_tree = None
        self.collection_tree = None
        self.source_tree = None

        self.setup_tabs()

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def get_filtered_query(self, table, columns):
        user = get_logged_in_user()
        # If the user is not an admin, limit the query to their own data
        if not is_admin() and "User" in columns:
            return f"SELECT {', '.join(columns)} FROM {table} WHERE User = '{user}'"
        
        # If user is an admin, return the unfiltered query
        return f"SELECT {', '.join(columns)} FROM {table}"

    def setup_tabs(self):
        for tab_name, config in self.tabs_config.items():
            if config["visible"]():
                tab_frame = ttk.Frame(self.notebook)
                self.notebook.add(tab_frame, text=tab_name)

                if tab_name == "My Items":
                    self.setup_my_items_tab(tab_frame, config["columns"])
                else:
                    treeview = self.create_treeview(tab_frame, config["columns"])
                    self.populate_treeview(treeview, config["query"])
                    setattr(self, f"{tab_name.lower()}_tree", treeview)

                    # Only bind double-click event for the 'Items' tab
                    if tab_name == "Items":
                        self.item_tree = treeview
                        self.item_tree.bind("<Double-1>", self.on_double_click)

    def setup_my_items_tab(self, parent, columns):
        from tkinter import StringVar

        # Label for the dropdown
        self.collection_label = ttk.Label(parent, text="Choose Your Collection")
        self.collection_label.pack(pady=5)

        # Dropdown for selecting collection
        self.collection_var = StringVar()
        self.collection_dropdown = ttk.Combobox(parent, textvariable=self.collection_var, state="readonly")
        self.collection_dropdown.pack(pady=5)
        self.collection_dropdown.bind("<<ComboboxSelected>>", self.on_collection_selected)

        # Treeview
        self.my_items_tree = self.create_treeview(parent, columns)
        self.item_tree = self.my_items_tree  # So double-click still works
        self.item_tree.bind("<Double-1>", self.on_double_click)

        # Load collections
        self.load_collection_dropdown()

    def load_collection_dropdown(self):
        user = get_logged_in_user()

        conn = sqlite3.connect("collections.sqlite")
        cursor = conn.cursor()

        if is_admin():
            cursor.execute("SELECT CollectionName FROM Collection")
        else:
            cursor.execute("SELECT CollectionName FROM Collection WHERE User = ?", (user,))
        
        collections = [row[0] for row in cursor.fetchall()]
        conn.close()

        self.collection_dropdown["values"] = collections
        if collections:
            self.collection_var.set(collections[0])
            self.load_items_for_collection(collections[0])

    def on_collection_selected(self, event):
        selected = self.collection_var.get()
        self.load_items_for_collection(selected)

    def load_items_for_collection(self, collection_name):
        user = get_logged_in_user()

        query = """
            SELECT ItemName, Collection, User, Source, Status,
                    Description, PricePaid, CurrentValue, Location, Notes
            FROM Item
            WHERE Collection = ?
        """
        params = (collection_name,)

        if not is_admin():
            query += " AND User = ?"
            params += (user,)

        self.my_items_tree.delete(*self.my_items_tree.get_children())
        self.populate_treeview(self.my_items_tree, query, params)

    def create_treeview(self, parent, columns):
        tree = ttk.Treeview(parent, columns=columns, show="headings")
        tree.bind("<Double-1>", self.on_double_click)
        for col in columns:
            tree.heading(col, text=col, command=lambda col=col: self.sort_items(tree, col))
            tree.column(col, anchor="center", width=100)
        tree.pack(fill="both", expand=True)
        return tree

    def populate_treeview(self, treeview, query=None, params=()):
        conn = sqlite3.connect("collections.sqlite")
        cursor = conn.cursor()

        # If no query is provided, try to get it from the treeview's name via tabs_config
        if query is None:
            tab_name = treeview.master.winfo_name()
            config = self.tabs_config.get(tab_name, {})
            query = config.get("query")
            if not query:
                print(f"[DEBUG] No query found for tab '{tab_name}'")
                return

        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            treeview.delete(*treeview.get_children())
            for row in rows:
                treeview.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
            print(f"[ERROR] populate_treeview failed: {e}")
        finally:
            conn.close()

    def sort_items(self, treeview, column):
        """Sort items in the treeview based on the selected column."""
        # Get current sorting order from the column heading
        current_order = treeview.heading(column, "text")
        reverse = False

        # Check if current column header contains an up or down chevron
        if '↑' in current_order:  # Up chevron means it's currently sorted in ascending order
            reverse = True
        elif '↓' in current_order:  # Down chevron means it's currently sorted in descending order
            reverse = False
        else:  # No chevron means the default is ascending
            reverse = True

        # Sort the treeview
        self.sort_treeview(treeview, column, reverse)

        # Update the heading to show the new sorting order with chevrons
        self.update_column_heading(treeview, column, reverse)

    def update_column_heading(self, treeview, column, reverse):
        """Update the column heading to show ascending/descending chevron."""
        if reverse:
            treeview.heading(column, text=f"{column} ↓", command=lambda: self.sort_items(treeview, column))
        else:
            treeview.heading(column, text=f"{column} ↑", command=lambda: self.sort_items(treeview, column))

    def show_item_details(self, identifier):
        active_tab = self.notebook.tab(self.notebook.select(), "text")
        
        model_map = {
            "Items": Item,
            "Users": User,
            "Collections": Collection,
            "Sources": Source
        }
        model_cls = model_map.get(active_tab)
        if not model_cls:
            messagebox.showerror("Error", f"No model defined for {active_tab}")
            return

        # Fetch item based on the identifier (e.g., ItemName, CollectionName, etc.)
        item = model_cls.get_by_identifier(identifier)
        if item:
            messagebox.showinfo(f"{active_tab[:-1]} Details", item.to_display_string())
        else:
            messagebox.showerror("Error", f"{active_tab[:-1]} not found.")

    def sort_treeview(self, treeview, column, reverse=False):
        """Sort the items in the treeview based on the selected column."""
        items = [(treeview.set(item, column), item) for item in treeview.get_children('')]
        
        # Sort items by column value
        items.sort(key=lambda x: x[0], reverse=reverse)
        
        # Rearrange the items in the treeview based on sorted order
        for index, (val, item) in enumerate(items):
            treeview.move(item, '', index)

    def on_tab_changed(self, event):
        active_tab = self.notebook.tab(self.notebook.select(), "text")
        self.master.update_buttons(active_tab)

    def refresh_all(self):
        for tab_name, config in self.tabs_config.items():
            if config["visible"]():
                treeview_name = tab_name.lower().replace(" ", "").replace(":", "") + "_tree"
                treeview = getattr(self, treeview_name, None)
                if treeview:
                    treeview.delete(*treeview.get_children())
                    self.populate_treeview(treeview, config["query"])

    def on_double_click(self, event):
        treeview = event.widget
        selected = treeview.selection()

        if not selected:
            return

        values = treeview.item(selected[0])["values"]
        tab_name = self.notebook.tab(self.notebook.select(), "text").strip(":")

        model_mapping = {
            "Items": Item,
            "Collections": Collection,
            "Users": User,
            "Sources": Source
        }

        model_cls = model_mapping.get(tab_name)
        if not model_cls:
            messagebox.showerror("Error", f"No model found for tab: {tab_name}")
            return

        # Special handling if ItemID is not in the table display but needed
        if tab_name == "Items":
            item_name = values[0]
            conn = sqlite3.connect("collections.sqlite")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Item WHERE ItemName = ?", (item_name,))
            row = cursor.fetchone()
            conn.close()

            if row:
                item = model_cls.from_row(row)
                item.show_detail_window(self.master)
            else:
                messagebox.showerror("Error", "Item not found in database.")
        else:
            # Reconstruct model from values assuming order matches model fields
            item = model_cls.from_list(values)
            item.show_detail_window(self.master)
