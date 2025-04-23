import sqlite3
import tkinter as tk  # Ensure tkinter is imported as tk
from tkinter import ttk, simpledialog, messagebox, StringVar
from models import User, Item, Source, Collection, BaseModel  # Assuming these models are defined in models.py
from db import connect, get_user_status, login, get_logged_in_user, set_logged_in_user, is_admin  # Import the required functions from db.py
from log import log

from ttkbootstrap import Style
from ttkbootstrap.widgets import Button, Label, OptionMenu
from ttkbootstrap.constants import *


style = Style("vapor")
# from windows import BaseWindow, FormWindow, MainApplication, LoginWindow

# import ttkbootstrap as ttk # Nicetohave if we have time!
# from ttkbootstrap.constants import *
 
def main():
    # Initialize root window
    root = tk.Tk()
    root.withdraw() # hide main window until logged in.

    login_window = LoginWindow(master=root)
    login_window.mainloop()

##### BUILDING BLOCKS FOR GUI COMPONENTS #####

# TOOLKIT

# LABELED FORM FIELD.  Example usage:
# self.itemname_entry = self.labeled_entry("Item Name:")

# LABELED DROPDOWN.  Example usage:
# self.collection_dropdown, self.collection_var = self.labeled_dropdown("Collection:")
# self.load_collections()  # Populate dropdown (function to populate the menu)

# LABELED TEXT BOX.  Example usage:
# self.notes_text = self.labeled_textarea("Notes:")

# CREATE BUTTON.  Example usage:
# self.create_button("Add Collection", self.open_add_collection_window)

# ADD Submit/Cancel buttons


# Form labels/fields
class LabeledEntry(tk.Frame):
    def __init__(self, master, label_text, **kwargs):
        super().__init__(master)
        self.label = tk.Label(self, text=label_text)
        self.label.pack(side="left", padx=(0, 10))
        self.entry = tk.Entry(self, **kwargs)
        self.entry.pack(side="left")

    def get(self):
        return self.entry.get()

    def set(self, value):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)

# Base window for consistency

class BaseWindow(tk.Toplevel):
    def __init__(self, master=None, title="Window"):
        super().__init__(master)
        self.title(title)
        self.geometry("400x300")
        self.configure(padx=20, pady=20)
        self.entries = {}

    # def add_field(self, label):
    #     field = LabeledEntry(self, label)
    #     field.pack(pady=5)
    #     self.entries[label] = field
    #     return field

    # def get_data(self):
    #     return {key.replace(":", "").strip(): entry.get() for key, entry in self.entries.items()}
    
class FormWindow(BaseWindow):
    def __init__(self, master=None, title="Form Window", submit_callback=None, cancel_callback=None):
        super().__init__(master, title)
        self.submit_callback = submit_callback
        self.cancel_callback = cancel_callback

        self.form_frame = tk.Frame(self)
        self.form_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)

        self.row = 0  # Tracks grid rows

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def next_row(self):
        current = self.row
        self.row += 1
        return current

    def labeled_entry(self, label, entry_width=40):
        row = self.next_row()
        tk.Label(self.form_frame, text=label, anchor="w", justify="left").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        entry = tk.Entry(self.form_frame, width=entry_width)
        entry.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        self.form_frame.grid_columnconfigure(1, weight=1)
        return entry

    def labeled_dropdown(self, label_text, query, params=(), map_name=None):
        row = self.next_row()
        tk.Label(self.form_frame, text=label_text).grid(row=row, column=0, sticky="w", padx=5, pady=5)

        var = tk.StringVar()
        dropdown = ttk.Combobox(self.form_frame, textvariable=var, state="readonly")
        dropdown.grid(row=row, column=1, sticky="ew", padx=5, pady=5)

        self.form_frame.grid_columnconfigure(1, weight=1)
        self.load_dropdown_data(dropdown, query, params, map_name)

        return dropdown, var  # ✅ This must be present


    def labeled_static_dropdown(self, label_text, values, default_index=0):
        row = self.next_row()

        label = tk.Label(self.form_frame, text=label_text)
        label.grid(row=row, column=0, sticky="w", pady=5, padx=5)

        var = tk.StringVar()
        dropdown = ttk.Combobox(self.form_frame, textvariable=var, state="readonly", values=values)
        dropdown.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        dropdown.current(default_index)

        return dropdown, var

        

    def labeled_textarea(self, label, height=4, width=40):
        row = self.next_row()

        tk.Label(self.form_frame, text=label, anchor="w", justify="left").grid(row=row, column=0, sticky="nw", padx=5, pady=5)
        text_widget = tk.Text(self.form_frame, height=height, width=width)
        text_widget.grid(row=row, column=1, sticky="ew", padx=5, pady=5)

        self.form_frame.grid_columnconfigure(1, weight=1)
        return text_widget

    def create_button(self, text, command, bootstyle="primary", columnspan=2, pady=5):
        row = self.next_row()
        button = tk.Button(self.form_frame, text=text, command=command)
        button.grid(row=row, column=0, columnspan=columnspan, pady=pady)
        return button

    def add_buttons(self, submit_text="Submit", cancel_text="Cancel", submit_command=None, cancel_command=None):
        if submit_command is None:
            submit_command = self.submit
        if cancel_command is None:
            cancel_command = self.cancel

        row = self.next_row()

        # Create a frame to hold buttons side-by-side
        button_frame = tk.Frame(self.form_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=15)

        self.submit_button = tk.Button(button_frame, text=submit_text, command=submit_command, width=12)
        self.submit_button.pack(side="left", padx=10)

        self.cancel_button = tk.Button(button_frame, text=cancel_text, command=cancel_command, width=12)
        self.cancel_button.pack(side="left", padx=10)

    def load_dropdown_data(self, dropdown, query, params=None, map_name=None):
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute(query, params or ())
            rows = cur.fetchall()

            if not rows:
                dropdown['values'] = []
                dropdown.set("No options available")
                return

            if len(rows[0]) == 1:  # 🟢 Only 1 column (like just BusinessName)
                values = [row[0] for row in rows]
                dropdown['values'] = values
                dropdown.set("Select an option")
            elif len(rows[0]) >= 2 and map_name:
                # 🟠 Two or more columns (map: Name -> ID)
                name_map = {row[1]: row[0] for row in rows}
                setattr(self, map_name, name_map)
                dropdown['values'] = list(name_map.keys())
                dropdown.set("Select an option")
            else:
                dropdown['values'] = [str(row) for row in rows]
                dropdown.set("Select an option")

        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load dropdown: {e}")
            log(f"[Dropdown Error] {e}")

# Main app window extends the BaseWindow class
class MainApplication(BaseWindow):  # Use tk.Tk
    """Main application window with a tabbed viewer and dynamic buttons."""

    def __init__(self):
        super().__init__()
        self.title("Collection Management System")
        self.geometry("1260x600")
        self.minsize(1260, 600)
        self.maxsize(1260, 600)
        self.configure(padx=10, pady=10)

        # Retrieve the logged-in user's username
        logged_in_user = get_logged_in_user()
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)  # 40% for the button panel
        self.grid_columnconfigure(1, weight=2)  # 60% for the tab viewer
        self.grid_rowconfigure(0, weight=1)

        # Create the dynamic button panel, on the left side of the app
        self.button_panel = DynamicButtonPanel(self)
        self.button_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Create the tab viewer on the right side of the app.
        self.tab_viewer = TabViewer(self)
        self.tab_viewer.grid(row=0, column=1, sticky="nsew")

        # Link the tab change event to update buttons
        self.tab_viewer.notebook.bind("<<NotebookTabChanged>>", self.update_buttons)

    def update_buttons(self, event=None):
        # Update the buttons based on the active tab.
        active_tab = self.tab_viewer.notebook.tab(self.tab_viewer.notebook.select(), "text")
        self.button_panel.update_buttons(active_tab)


class LoginWindow(FormWindow):
    """Login window where users can log in."""

    def __init__(self, master=None):
        super().__init__(master, title="Login")
        self.geometry("400x200")
        self.configure(padx=20, pady=20)

        # Username field        
        self.username_entry = self.labeled_entry("Username:")

        # Password field
        self.password_entry = self.labeled_entry("Password:")

        # Login button        
        self.create_button("Login", self.login)

    def login(self):

        # get form entries
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        # if a field is blank
        if not username or not password:
            messagebox.showerror("Error", "All fields are required.")
            return

        try:

            # if login matches
            if login(username, password):
                if get_user_status(username) != "Active":
                    messagebox.showerror("Login Failed", "This account is inactive. Contact an admin.")
                    return
                
                # update logged_in_user tracker
                set_logged_in_user(username)
                logged_in_user = get_logged_in_user()
                
                # confirmation window
                messagebox.showinfo("Login Success", f"Welcome, {logged_in_user}!")
                
                # log entry
                log(f"{username} has logged in successfully.")

                # close login window and open Main Application
                self.destroy()
                MainApplication().mainloop()

            # if username and password don't match
            else:

                # error window
                messagebox.showerror("Login Failed", "Invalid username or password.")
        
        # handle any database errors
        except Exception as e:
            print(f"[ERROR] {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")



# Tabbed viewer to toggle between User, Collection, Item and Source tables
class TabViewer(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # Define tab configurations
        self.tabs_config = {
            "Users": {
                "visible": lambda: is_admin(),
                "columns": ("Username", "Password", "Role", "Status"),
                "query": "SELECT Username, Password, Role, Status FROM User"
            },
            "My Items": {
                "visible": lambda: True,
                "columns": (
                    "ItemName", "Collection", "User", "Source", "Status",
                    "Description", "PricePaid", "CurrentValue", "Location", "Notes"
                ),
                "query": ""  # Dynamic query based on user/collection
            },
            "Sources": {
                "visible": lambda: True,
                "columns": (
                    "BusinessName", "FirstName", "LastName", "Phone", "Address",
                    "City", "State", "Zip", "Email"
                ),
                "query": """
                    SELECT BusinessName, FirstName, LastName, Phone, Address,
                    City, State, Zip, Email FROM Source
                """
            },
            "Activiy Log": {
                "visible": lambda: is_admin(),
                "columns": ("User", "Message", "Timestamp"),
                "query": "SELECT User, Message, Timestamp FROM Log"
            }
        }

        self.tabs = {}
        self.user_tree = None
        self.item_tree = None
        self.collection_tree = None
        self.source_tree = None

        # Build all visible tabs
        self.setup_tabs()

        # Update button layout when switching tabs
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def get_filtered_query(self, table, columns):
        """Returns a SELECT query filtered by user if not admin."""
        user = get_logged_in_user()
        if not is_admin() and "User" in columns:
            return f"SELECT {', '.join(columns)} FROM {table} WHERE User = '{user}'"
        else:
            return f"SELECT {', '.join(columns)} FROM {table}"

    def setup_tabs(self):
        """Creates tabs based on visibility rules."""
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

    def setup_my_items_tab(self, parent, columns):
        """Sets up the special 'My Items' tab with filtering controls."""
        self.my_items_tab = parent
        self.collection_var = StringVar()
        self.show_inactive_var = tk.BooleanVar()

        # Control panel: dropdown + checkbox
        control_frame = tk.Frame(parent)
        control_frame.pack(anchor="w", padx=10, pady=(10, 5))

        tk.Label(control_frame, text="Choose a Collection:").pack(side="left")
        self.collection_dropdown = ttk.Combobox(control_frame, textvariable=self.collection_var, state="readonly")
        self.collection_dropdown.pack(side="left", padx=(5, 10))
        self.collection_dropdown.bind("<<ComboboxSelected>>", self.on_collection_selected)

        # Checkbox for toggling inactive items
        tk.Checkbutton(
            control_frame,
            text="Show Inactive",
            variable=self.show_inactive_var,
            command=self.toggle_show_inactive
        ).pack(side="left")

        # Treeview to display items
        self.my_items_tree = self.create_treeview(parent, columns)
        self.item_tree = self.my_items_tree
        self.item_tree.bind("<Double-1>", self.on_double_click)
        self.load_collection_dropdown()

    def toggle_show_inactive(self):
        """Reload items when the 'Show Inactive' checkbox is toggled."""
        collection = self.collection_var.get()
        if collection:
            self.load_items_for_collection(collection)

    def load_collection_dropdown(self):
        """Populates the collection dropdown for current user/admin."""
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

    def refresh_collection_dropdown(self):
        """Refreshes the dropdown list of collections."""
        collections = Collection.get_all(User=get_logged_in_user())
        self.collection_dropdown['values'] = [c.CollectionName for c in collections]

    def on_collection_selected(self, event):
        """Handles dropdown selection event."""
        selected = self.collection_var.get()
        self.load_items_for_collection(selected)

    def load_items_for_collection(self, collection_name):
        """Loads and filters items for selected collection and status."""
        user = get_logged_in_user()
        query = """
            SELECT ItemName, Collection, User, Source, Status,
                Description, PricePaid, CurrentValue, Location, Notes
            FROM Item
            WHERE Collection = ?
        """
        params = [collection_name]

        if not is_admin():
            query += " AND User = ?"
            params.append(user)

        if not self.show_inactive_var.get():
            query += " AND Status = 'Active'"

        self.my_items_tree.delete(*self.my_items_tree.get_children())
        self.populate_treeview(self.my_items_tree, query, params)

    def create_treeview(self, parent, columns):
        """Creates a scrollable treeview widget with sortable columns."""
        tree = ttk.Treeview(parent, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col, command=lambda col=col: self.sort_items(tree, col))
            tree.column(col, anchor="w", width=100)
        tree.pack(fill="both", expand=True)
        return tree

    def populate_treeview(self, tree, query, params=()):
        """Fills treeview rows from database results."""
        conn = sqlite3.connect("collections.sqlite")
        cursor = conn.cursor()
        cursor.execute(query, params)
        for row in cursor.fetchall():
            tree.insert("", "end", values=row)
        conn.close()

    def sort_items(self, treeview, column):
        """Handles clicking on a column header to sort the treeview."""
        current_order = treeview.heading(column, "text")
        reverse = '↑' in current_order
        self.sort_treeview(treeview, column, reverse)
        self.update_column_heading(treeview, column, not reverse)

    def update_column_heading(self, treeview, column, reverse):
        """Adds ↑ or ↓ to column headers to show sort direction."""
        arrow = "↓" if reverse else "↑"
        treeview.heading(column, text=f"{column} {arrow}", command=lambda: self.sort_items(treeview, column))

    def sort_treeview(self, treeview, column, reverse=False):
        """Sorts treeview rows by a specific column."""
        items = [(treeview.set(item, column), item) for item in treeview.get_children('')]
        items.sort(key=lambda x: x[0], reverse=reverse)
        for index, (_, item) in enumerate(items):
            treeview.move(item, '', index)

    def on_tab_changed(self, event):
        """Handles tab switch event to update the sidebar buttons."""
        active_tab = self.notebook.tab(self.notebook.select(), "text")
        self.master.update_buttons(active_tab)

    def refresh_all(self):
        """Refreshes the data in all tabs."""
        for tab_name, config in self.tabs_config.items():
            if config["visible"]():
                if tab_name == "My Items":
                    treeview = self.my_items_tree
                else:
                    treeview = getattr(self, f"{tab_name.lower()}_tree")
                treeview.delete(*treeview.get_children())
                self.populate_treeview(treeview, config["query"])

    def on_double_click(self, event):
        """Handles double-clicking an item row to show details."""
        treeview = event.widget
        selected = treeview.selection()
        if not selected:
            return

        values = treeview.item(selected[0])["values"]
        tab_name = self.notebook.tab(self.notebook.select(), "text")

        model_mapping = {
            "Items": Item,
            "My Items": Item,
            "Collections": Collection,
            "Users": User,
            "Sources": Source
        }

        model_cls = model_mapping.get(tab_name)
        if not model_cls:
            messagebox.showerror("Error", f"No model found for tab: {tab_name}")
            return

        try:
            if tab_name in ("Items", "My Items"):
                query_columns = self.tabs_config["My Items"]["columns"]
                item_name = values[query_columns.index("ItemName")]
                collection = values[query_columns.index("Collection")]
                user = values[query_columns.index("User")]
                item = model_cls.get_by_fields(item_name=item_name, collection=collection, user=user)
            else:
                identifier = values[0]
                item = model_cls.get_by_identifier(identifier)

            if not item:
                messagebox.showerror("Error", f"{tab_name[:-1]} not found")
                return

            fields, vals = item.get_fields_and_values()
            details = "\n".join([f"{field}: {val}" for field, val in zip(fields, vals)])
            messagebox.showinfo(f"{tab_name[:-1]} Details", details)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

# Button panel on the left that displays buttons that correspond with the tab currently displayed
class DynamicButtonPanel(tk.Frame):
    """A panel with buttons that change dynamically based on the active tab."""

    def __init__(self, master):
        super().__init__(master)
        self.configure(padx=10, pady=10)
        self.buttons = []
        self.update_buttons("Users")

        # static logout button
        self.logout_button = tk.Button(self, text="Logout", command=self.logout)
        self.logout_button.pack(side="bottom", pady=10, fill="x")
        
    def update_buttons(self, active_tab):
        print(f"[DEBUG] Active Tab: {active_tab}")

        # Clear existing buttons
        for button in self.buttons:
            button.destroy()
        self.buttons.clear()

        if active_tab == "Users":
            self.add_button("Add User", self.add_user)
            self.add_button("Update User", self.update_user)
            self.add_button("Deactivate User", self.deactivate_user)
            self.add_button("Reactivate User", self.reactivate_user)
            self.add_button("Delete User", self.delete_user)

        elif active_tab == "My Items":            
            self.add_button("Add Item", self.add_item)
            self.add_button("Deactivate Item", self.deactivate_item)
            self.add_button("Update Item", self.update_item)
            # self.add_button("Delete Item", self.delete_item)
            self.add_button("Add Collection", self.add_collection)
            self.add_button("Edit Collection", self.edit_collection)
            self.add_button("Deactivate Collection", self.deactivate_collection)
            self.add_button("Reactivate Collection", self.reactivate_collection)
            self.add_button("Delete Collection", self.delete_collection)


        elif active_tab == "Sources":
            self.add_button("Add Source", self.add_source)
            self.add_button("Update Source", self.update_source)
            self.add_button("Delete Source", self.delete_source)

    def add_button(self, text, command):
        button = ttk.Button(self, text=text, command=command)
        button.pack(fill="x", pady=5)
        self.buttons.append(button)

    def logout(self):

        # Handle the logout process        
        confirm = messagebox.askyesno("Confirm Logout", "Are you sure you want to log out?")
        if not confirm:
            return
        # Close the application window, revert to the login window
        self.master.destroy()
        login_window = LoginWindow()

    # --- User actions ---
    def add_user(self):
        AddUserWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()

    def update_user(self):
        UpdateUserWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()

    def deactivate_user(self):
        DeactivateUserWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()        

    def reactivate_user(self):
        ReactivateUserWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()        

    def edit_user(self):
        messagebox.showinfo("Edit User", "Edit user functionality not implemented yet.")

    def delete_user(self):
        DeleteUserWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()  

    # --- Item actions ---
    def add_item(self):
        AddItemWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()

    def deactivate_item(self):
        DeactivateItemWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()
    
    
    def update_item(self):
        UpdateItemWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()
        

    # def delete_item(self):
    #     item_name = simpledialog.askstring("Delete Item", "Enter item name to delete:")
    #     if item_name:
    #         # Replace with actual deletion logic
    #         messagebox.showinfo("Delete Item", "Delete item functionality not implemented yet.")
    #         self.master.tab_viewer.refresh_all()

    # --- Collection actions ---
    def add_collection(self):
        AddCollectionWindow(self.master,refresh_callback=self.master.tab_viewer.refresh_collection_dropdown).grab_set()

    def deactivate_collection(self):
        DeactivateCollectionWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()

    def reactivate_collection(self):
        ReactivateCollectionWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()

    def delete_collection(self):
        DeleteCollectionWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()


    def edit_collection(self):
        messagebox.showinfo("Edit Collection", "Edit collection functionality not implemented yet.")

    # --- Source actions ---
    def add_source(self):
        AddSourceWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()

    def update_source(self):
        UpdateSourceWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()

    def delete_source(self):
        business_name = simpledialog.askstring("Delete Source", "Enter business name to delete:")
        if business_name:
            # Replace with actual deletion logic
            messagebox.showinfo("Delete Source", "Delete source functionality not implemented yet.")
            self.master.tab_viewer.refresh_all()

    def dummy_action(self):
        print("Button clicked!")

##### CRUD OPERATION WINDOWS #####
### ITEMS ###

# COMPLETED
class AddItemWindow(FormWindow):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master, title="Add Item")
        self.refresh_callback = refresh_callback

        # Set fixed size and minimum size
        self.geometry("450x450")
        self.minsize(450, 450)

        # --- FORM FIELDS ---

        # Field: Item Name (simple text entry)
        self.itemname_entry = self.labeled_entry("Item Name:")

        # Collection Dropdown: Choose a Collection
        collection_query = "SELECT CollectionName FROM Collection WHERE User = ?"
        self.collection_dropdown, self.collection_var = self.labeled_dropdown("Collection:", collection_query, (get_logged_in_user(),), map_name="collection")

        # "Add Collection" button below dropdown
        self.create_button("Add Collection", self.open_add_collection_window)

        # Source Dropdown (populated from database)
        source_query = "SELECT BusinessName FROM Source"
        self.source_dropdown, self.source_var = self.labeled_dropdown("Select Source:", query="SELECT SourceID, BusinessName FROM Source",map_name="source_map"
            
)

        # "Add Source" button below dropdown
        self.create_button("Add Source", self.open_add_source_window)

        # Price Paid (entry for numeric input)
        self.pricepaid_entry = self.labeled_entry("Price Paid:")

        # Current Value (entry for numeric input)
        self.currentvalue_entry = self.labeled_entry("Current Value:")

        # Notes field (multi-line input)
        self.notes_text = self.labeled_textarea("Notes:")

        # Submit and Cancel buttons
        self.add_buttons(submit_text="Add Item", cancel_text="Cancel")

        # Optional callback to refresh parent UI
        if self.refresh_callback:
            self.refresh_callback()

    # Cancel simply closes the window
    def cancel(self):
        self.destroy()

    # Open AddCollectionWindow and refresh the list after it's closed
    def open_add_collection_window(self):
        def refresh_collections():
            collection_query = "SELECT CollectionName FROM Collection WHERE User = ?"
            self.collection_dropdown, self.collection_var = self.labeled_dropdown("Collection:", collection_query, (get_logged_in_user(),), map_name="collection")
        AddCollectionWindow(self.master, refresh_callback=refresh_collections).grab_set()

    # Open AddSourceWindow and refresh the list after it's closed
    def open_add_source_window(self):
        def refresh_sources():
            source_query = "SELECT BusinessName FROM Source"
            self.source_dropdown, self.source_var = self.labeled_dropdown("Choose A Source:", source_query, map_name="source")
        AddSourceWindow(self.master, refresh_callback=refresh_sources).grab_set()

    # Add Submit and Cancel buttons with specific functions
        self.add_buttons(submit_text="Update Source", cancel_text="Cancel", 
                            submit_command=self.submit, cancel_command=self.cancel)

    
    
    # Called when user clicks Submit
    def submit(self):
        # Collect form input values
        itemname = self.itemname_entry.get().strip()
        collection_name = self.collection_var.get().strip()
        source_name = self.source_var.get().strip()
        pricepaid = self.pricepaid_entry.get().strip()
        currentvalue = self.currentvalue_entry.get().strip()
        notes = self.notes_text.get("1.0", "end").strip()
        user = get_logged_in_user()

        # Basic validation
        if not itemname:
            messagebox.showerror("Input Error", "Item Name cannot be empty.")
            return

        if not collection_name or not source_name:
            messagebox.showerror("Input Error", "Please select a collection and a source.")
            return

        try:
            pricepaid = BaseModel.validate_and_convert_numeric(pricepaid, "Price Paid")
            currentvalue = BaseModel.validate_and_convert_numeric(currentvalue, "Current Value")
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
            return

        # Confirm with user before saving
        confirm_message = (
            f"Is this information correct?\n\n"
            f"Item Name: {itemname}\n"
            f"Collection: {collection_name}\n"
            f"Source: {source_name}\n"
            f"Price Paid: ${pricepaid:.2f}\n"
            f"Current Value: ${currentvalue:.2f}\n"
            f"Notes: {notes or 'N/A'}"
        )
        confirm = messagebox.askyesno("Confirm Item Details", confirm_message)
        if not confirm:
            return

        try:
            # Create and save the item without any IDs
            new_item = Item(
                ItemName=itemname,
                CollectionName=collection_name,
                Source=source_name,
                User=user,
                PricePaid=pricepaid,
                CurrentValue=currentvalue,
                Notes=notes
            )
            new_item.save()

            messagebox.showinfo("Success", f"Item '{itemname}' added successfully.")

            if self.refresh_callback:
                self.refresh_callback()

            self.destroy()

        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to add item: {e}")


class DeactivateItemWindow(FormWindow):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master)
        self.title("Deactivate Item")
        self.refresh_callback = refresh_callback
        self.geometry("400x200")
        self.minsize(400, 200)

        # Get user role and build the query
        logged_in_username = get_logged_in_user()
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT Role FROM User WHERE Username = ?", (logged_in_username,))
        result = cursor.fetchone()
        role = result["Role"] if result else "User"
        cursor.close()

        if role == "Admin":
            self.query = "SELECT ItemID, ItemName FROM Item WHERE Status = 'Active'"
            self.params = None
        else:
            self.query = "SELECT ItemID, ItemName FROM Item WHERE Status = 'Active' AND User = ?"
            self.params = (logged_in_username,)

        # Initialize item_map to store ItemName -> ItemID mapping
        self.item_map = {}

        # Create dropdown using FormWindow's reusable method
        self.item_dropdown, self.item_var = self.labeled_dropdown("Select an Item:", self.query, self.params)

        # Add buttons
        self.add_buttons(submit_text="Deactivate Item", cancel_text="Cancel")

    def load_dropdown_data(self, dropdown, query, params=None, map_name=None):
        try:
            # Loading dropdown data and mapping ItemName to ItemID
            conn = connect()
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            items = cursor.fetchall()
            cursor.close()

            # Clear previous values
            dropdown.set("")
            dropdown['values'] = []

            if items:
                # Fill item map with ItemName -> ItemID
                self.item_map = {item["ItemName"]: item["ItemID"] for item in items}
                dropdown['values'] = list(self.item_map.keys())

            # If no items found
            if not dropdown['values']:
                dropdown.set("No items available")
                dropdown.config(state="disabled")
            else:
                dropdown.config(state="readonly")

        except Exception as e:
            messagebox.showerror("Error", f"Error loading dropdown data: {e}")
            log(f"Error loading dropdown data: {e}")

    def submit(self):
        selected_name = self.item_var.get().strip()
        if not selected_name:
            messagebox.showerror("Input Error", "Please select an item to deactivate.")
            return

        item_id = self.item_map.get(selected_name)
        if not item_id:
            messagebox.showerror("Error", f"Item '{selected_name}' not found.")
            return

        confirm = messagebox.askyesno("Confirm Deactivation", f"Are you sure you want to deactivate '{selected_name}'?")
        if not confirm:
            return

        try:
            conn = connect()
            cursor = conn.cursor()
            cursor.execute("UPDATE Item SET Status = 'Inactive' WHERE ItemID = ?", (item_id,))
            conn.commit()
            cursor.close()
            message = f"Item '{selected_name}' has been deactivated."
            messagebox.showinfo("Success", message)
            log(message)

            # Reload dropdown with updated values
            self.load_dropdown_data(self.item_dropdown, self.query, self.params)

            if self.refresh_callback:
                self.refresh_callback()

            self.cancel()

        except Exception as e:
            message = f"An error occurred: {e}"
            messagebox.showerror("Database Error", message)
            log(message)

    def cancel(self):
        self.destroy()


# TODO: Reactivate Item

# TODO: Update Item
class UpdateItemWindow(FormWindow):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master, title="Update Item")
        self.refresh_callback = refresh_callback
        self.geometry("400x500")
        self.minsize(400, 500)
        self.maxsize(400, 500)

        # Select Item to update
        item_query = "SELECT Name FROM Item WHERE Username = ? ORDER BY Name"
        self.item_dropdown, self.item_var = self.labeled_dropdown(
            "Select Item:", item_query, (get_logged_in_user(),), map_name="item"
        )
        self.item_dropdown.bind("<<ComboboxSelected>>", self.prefill_fields)

        # Item Name
        self.name_entry = self.labeled_entry("Name:")

        # Collection dropdown by name
        collection_query = "SELECT CollectionName FROM Collection WHERE Username = ? ORDER BY CollectionName"
        self.collection_dropdown, self.collection_var = self.labeled_dropdown(
            "Collection:", collection_query, (get_logged_in_user(),), map_name="collection"
        )

        # Source dropdown by business name
        source_query = "SELECT BusinessName FROM Source ORDER BY BusinessName"
        self.source_dropdown, self.source_var = self.labeled_dropdown(
            "Source:", source_query, map_name="source"
        )

        # Price
        self.price_entry = self.labeled_entry("Price:")

        # Description
        self.description_entry = self.labeled_entry("Description:")

        # Notes
        self.notes_entry = self.labeled_entry("Notes:")

        # Update + Cancel buttons
        self.add_buttons(submit_text="Update", cancel_text="Cancel")

    def prefill_fields(self, event=None):
        name = self.item_var.get()
        if not name:
            return

        item = Item.get_by_identifier("Name", name)
        if not item:
            return

        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, item.Name)

        self.collection_var.set(item.CollectionName)
        self.source_var.set(item.BusinessName)

        self.price_entry.delete(0, tk.END)
        self.price_entry.insert(0, item.Price or "")

        self.description_entry.delete(0, tk.END)
        self.description_entry.insert(0, item.Description or "")

        self.notes_entry.delete(0, tk.END)
        self.notes_entry.insert(0, item.Notes or "")

    def submit(self):
        selected_name = self.item_var.get()
        if not selected_name:
            messagebox.showerror("Input Error", "Please select an item to update.")
            return

        name = self.name_entry.get().strip()
        collection = self.collection_var.get().strip()
        source = self.source_var.get().strip()
        price = self.price_entry.get().strip()
        description = self.description_entry.get().strip()
        notes = self.notes_entry.get().strip()

        if not name:
            messagebox.showerror("Input Error", "Item name is required.")
            return

        try:
            updated_item = Item(
                Name=name,
                CollectionName=collection,
                BusinessName=source,
                Price=price,
                Description=description,
                Notes=notes,
                UserID=get_logged_in_user()
            )
            updated_item.update("Name", selected_name)

            messagebox.showinfo("Success", f"Item '{selected_name}' updated successfully.")
            if self.refresh_callback:
                self.refresh_callback()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to update item: {e}")

    def cancel(self):
        self.destroy()


### USER ###

class AddUserWindow(FormWindow):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master, title="Add User")
        self.refresh_callback = refresh_callback

        self.geometry("400x350")
        self.minsize(350, 350)
        self.maxsize(350, 350)

        # Username
        self.username_entry = self.labeled_entry("Username:")

        # Password
        self.password_entry = self.labeled_entry("Password:")
        self.password_entry.config(show="*")

        # Confirm Password
        self.confirm_password_entry = self.labeled_entry("Confirm Password:")
        self.confirm_password_entry.config(show="*")

        # Show/Hide password checkbox
        self.show_password_var = tk.BooleanVar()
        self.show_password_check = tk.Checkbutton(
            self.form_frame,
            text="Show Password",
            variable=self.show_password_var,
            command=self.toggle_password_visibility
        )
        row = self.next_row()
        self.show_password_check.grid(row=row, column=0, columnspan=2, pady=5, sticky="w")

        # Role dropdown
        self.role_dropdown, self.role_var = self.labeled_static_dropdown("Role:", ("Admin", "User"), default_index=0)

        # Add and Cancel buttons centered
        self.add_buttons(submit_text="Add User", cancel_text="Cancel")

        if self.refresh_callback:
            self.refresh_callback()

    def toggle_password_visibility(self):
        show_char = "" if self.show_password_var.get() else "*"
        self.password_entry.config(show=show_char)
        self.confirm_password_entry.config(show=show_char)

    def labeled_dropdown(self, label_text, values, default_index=0):
        row = self.next_row()

        label = tk.Label(self.form_frame, text=label_text)
        label.grid(row=row, column=0, sticky="w", pady=5, padx=5)

        var = tk.StringVar()
        dropdown = ttk.Combobox(self.form_frame, textvariable=var, state="readonly", values=values)
        dropdown.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
        dropdown.current(default_index)

        return dropdown, var

    def submit(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        confirm_password = self.confirm_password_entry.get().strip()
        role = self.role_var.get().strip()

        if not username or not password or not confirm_password:
            messagebox.showerror("Input Error", "All fields are required.")
            return

        if password != confirm_password:
            messagebox.showerror("Input Error", "Passwords do not match.")
            return

        try:
            user = User(Username=username, Password=password, Role=role)
            user.save()
            messagebox.showinfo("Success", f"User '{username}' added successfully.")

            if self.refresh_callback:
                self.refresh_callback()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to add user: {e}")

    def cancel(self):
        self.destroy()


class DeactivateUserWindow(tk.Toplevel):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master)
        self.title("Deactivate User")
        self.geometry("320x180")
        self.refresh_callback = refresh_callback

        # Label
        tk.Label(self, text="Select User to Deactivate:").grid(row=0, column=0, columnspan=2, pady=(10, 5), padx=10)

        # Dropdown
        self.user_var = tk.StringVar()
        self.user_dropdown = ttk.Combobox(self, textvariable=self.user_var, state="readonly")
        self.user_dropdown.grid(row=1, column=0, columnspan=2, padx=10, sticky="ew")

        # Buttons
        deactivate_btn = tk.Button(self, text="Deactivate User", command=self.submit)
        cancel_btn = tk.Button(self, text="Cancel", command=self.destroy)

        deactivate_btn.grid(row=2, column=0, pady=10, padx=10, sticky="e")
        cancel_btn.grid(row=2, column=1, pady=10, padx=10, sticky="w")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.load_users()

    def load_users(self):
        try:
            current_user = get_logged_in_user()
            all_users = User.get_all()
            # Filter out the logged-in user and any already inactive users
            filtered = [u for u in all_users if u.Username != current_user and u.Status == "Active"]

            if not filtered:
                self.user_dropdown['values'] = []
                self.user_dropdown.set("No users available")
                messagebox.showwarning("No Users", "No other active users found.")
            else:
                self.user_dropdown['values'] = [u.Username for u in filtered]
        except Exception as e:
            message = f"Failed to load users: {e}"
            messagebox.showerror("Error", message)
            log(message)

    def submit(self):
        selected_user = self.user_var.get().strip()
        if not selected_user:
            messagebox.showerror("Input Error", "Please select a user to deactivate.")
            return

        confirm = messagebox.askyesno("Confirm Deactivation", f"Are you sure you want to deactivate '{selected_user}'?")
        if not confirm:
            return

        try:
            user = User.get_by_identifier(selected_user)
            if not user:
                messagebox.showerror("Error", "User not found.")
                return

            user.update_status("Inactive")
            message = f"User '{selected_user}' deactivated."
            messagebox.showinfo("Success", message)
            log(message)
            self.load_users()
            if self.refresh_callback:
                self.refresh_callback()

        except Exception as e:
            message = f"An error occurred: {e}"
            messagebox.showerror("Database Error", message)
            log(message)

class ReactivateUserWindow(tk.Toplevel):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master)
        self.title("Reactivate User")
        self.geometry("320x180")
        self.refresh_callback = refresh_callback

        # Label
        tk.Label(self, text="Select User to Reactivate:").grid(row=0, column=0, columnspan=2, pady=(10, 5), padx=10)

        # Dropdown
        self.user_var = tk.StringVar()
        self.user_dropdown = ttk.Combobox(self, textvariable=self.user_var, state="readonly")
        self.user_dropdown.grid(row=1, column=0, columnspan=2, padx=10, sticky="ew")

        # Buttons
        reactivate_btn = tk.Button(self, text="Reactivate User", command=self.submit)
        cancel_btn = tk.Button(self, text="Cancel", command=self.destroy)

        reactivate_btn.grid(row=2, column=0, pady=10, padx=10, sticky="e")
        cancel_btn.grid(row=2, column=1, pady=10, padx=10, sticky="w")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.load_users()

    def load_users(self):
        try:
            current_user = get_logged_in_user()
            all_users = User.get_all()
            # Filter only inactive users, excluding the current user
            filtered = [u for u in all_users if u.Username != current_user and u.Status == "Inactive"]

            if not filtered:
                self.user_dropdown['values'] = []
                self.user_dropdown.set("No users available")
                messagebox.showwarning("No Users", "No inactive users found.")
            else:
                self.user_dropdown['values'] = [u.Username for u in filtered]
                self.user_dropdown.set("Select a user")

        except Exception as e:
            message = f"Failed to load users: {e}"
            messagebox.showerror("Error", message)
            log(message)

    def submit(self):
        selected_user = self.user_var.get().strip()
        if not selected_user:
            messagebox.showerror("Input Error", "Please select a user to reactivate.")
            return

        confirm = messagebox.askyesno("Confirm Reactivation", f"Are you sure you want to reactivate '{selected_user}'?")
        if not confirm:
            return

        try:
            user = User.get_by_identifier(selected_user)
            if not user:
                messagebox.showerror("Error", "User not found.")
                return

            user.update_status("Active")
            message = f"User '{selected_user}' has been reactivated."
            messagebox.showinfo("Success", message)
            log(message)
            self.load_users()
            if self.refresh_callback:
                self.refresh_callback()
            self.destroy()

        except Exception as e:
            message = f"An error occurred: {e}"
            messagebox.showerror("Database Error", message)
            log(message)

class DeleteUserWindow(tk.Toplevel):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master)
        self.title("Delete User")
        self.refresh_callback = refresh_callback
        self.geometry("300x150")
        self.minsize(300, 150)

        # Label
        self.user_label = tk.Label(self, text="Select User to Delete:")
        self.user_label.pack()

        # Dropdown
        self.user_var = tk.StringVar()
        self.user_dropdown = ttk.Combobox(self, textvariable=self.user_var, state="readonly")
        self.user_dropdown.pack()

        # Buttons
        self.submit_button = tk.Button(self, text="Delete User", command=self.submit)
        self.submit_button.pack(pady=10)

        self.cancel_button = tk.Button(self, text="Cancel", command=self.cancel)
        self.cancel_button.pack()

        self.load_users()  # 🔁 Populate dropdown

    def load_users(self):
        logged_in_user = get_logged_in_user()
        conn = connect()
        cursor = conn.cursor()
        query = "SELECT Username FROM User WHERE Username != ? "
        cursor.execute(query, (logged_in_user,))
        users = [row["Username"] for row in cursor.fetchall()]
        cursor.close()

        if not users:
            self.user_dropdown['values'] = []
            self.user_dropdown.set("No users available")
            self.user_dropdown.config(state="disabled")
        else:
            self.user_dropdown.config(state="readonly")
            self.user_dropdown['values'] = users
            self.user_dropdown.set(users[0])

    def submit(self):
        selected_user = self.user_var.get().strip()
        if not selected_user:
            messagebox.showerror("Input Error", "Please select a user to delete.")
            return

        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete '{selected_user}'?")
        if not confirm:
            return

        try:
            user = User.get_by_identifier(selected_user)
            if user:
                user.delete()
                message=f"User '{selected_user}' has been deleted."
                messagebox.showinfo("Success", message)
                log(message)
                self.load_users()  # 🔁 Refresh dropdown
                if self.refresh_callback:
                    self.refresh_callback()
            else:
                messagebox.showerror("Error", f"User '{selected_user}' not found.")
        except Exception as e:
            message=f"An error occurred: {e}"
            messagebox.showerror("Database Error", message)
            log(message)

    def cancel(self):
        self.destroy()


class UpdateUserWindow(FormWindow):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master, title="Edit User")
        self.refresh_callback = refresh_callback

        self.geometry("400x400")
        self.minsize(350, 400)
        self.maxsize(400, 400)

        # Dropdown to select existing user
        self.user_dropdown, self.user_var = self.labeled_dropdown(
            "Select User:",
            query="SELECT Username FROM User"
        )
        self.user_dropdown.bind("<<ComboboxSelected>>", self.prefill_fields)

        # Username
        self.username_entry = self.labeled_entry("Username:")

        # Password
        self.password_entry = self.labeled_entry("Password:")
        self.password_entry.config(show="*")

        # Confirm Password
        self.confirm_password_entry = self.labeled_entry("Confirm Password:")
        self.confirm_password_entry.config(show="*")

        # Show/Hide password checkbox
        self.show_password_var = tk.BooleanVar()
        self.show_password_check = tk.Checkbutton(
            self.form_frame,
            text="Show Password",
            variable=self.show_password_var,
            command=self.toggle_password_visibility
        )
        row = self.next_row()
        self.show_password_check.grid(row=row, column=0, columnspan=2, pady=5, sticky="w")

        # Role dropdown (Admin/User)
        self.role_dropdown, self.role_var = self.labeled_static_dropdown("Role:", ("Admin", "User"), default_index=1)

        # Buttons
        self.add_buttons(submit_text="Update User", cancel_text="Cancel")

    def toggle_password_visibility(self):
        show_char = "" if self.show_password_var.get() else "*"
        self.password_entry.config(show=show_char)
        self.confirm_password_entry.config(show=show_char)

    def prefill_fields(self, event=None):
        username = self.user_var.get().strip()
        if not username:
            return

        user = User.get_by_identifier(username)
        if not user:
            messagebox.showerror("Error", f"User '{username}' not found.")
            return

        self.username_entry.delete(0, tk.END)
        self.username_entry.insert(0, user.Username)

        self.password_entry.delete(0, tk.END)
        self.confirm_password_entry.delete(0, tk.END)

        self.role_var.set(user.Role or "User")

    def submit(self):
        selected_username = self.user_var.get().strip()
        new_username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        confirm_password = self.confirm_password_entry.get().strip()
        role = self.role_var.get().strip()

        if not selected_username or not new_username:
            messagebox.showerror("Input Error", "Username is required.")
            return

        if password and password != confirm_password:
            messagebox.showerror("Input Error", "Passwords do not match.")
            return

        try:
            user = User.get_by_identifier(selected_username)
            if not user:
                messagebox.showerror("Error", f"User '{selected_username}' not found.")
                return

            user.Username = new_username
            if password:
                user.Password = password
            user.Role = role

            user.update()  # Assuming your User class has an .update() method

            messagebox.showinfo("Success", f"User '{new_username}' updated successfully.")
            if self.refresh_callback:
                self.refresh_callback()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to update user: {e}")

    def cancel(self):
        self.destroy()

### Collections ###

class AddCollectionWindow(FormWindow):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master, title="Add Collection")
        self.refresh_callback = refresh_callback

        # Set fixed size and minimum size
        self.geometry("300x150")
        self.minsize(450, 150)

        # Field: Collection Name (remove key argument)
        self.collectionname_entry = self.labeled_entry("Collection Name")

        # Submit and Cancel buttons at the bottom
        self.add_buttons(submit_text="Submit", cancel_text="Cancel")

        # Optional callback for refreshing the view
        if self.refresh_callback:
            self.refresh_callback()

    def submit(self):
        # Retrieve input values
        collectionname = self.collectionname_entry.get().strip()
        user = get_logged_in_user()

        # Validate collection name
        if not collectionname:
            messagebox.showerror("Input Error", "Collection Name cannot be empty.")
            return

        # Check if a collection with the same name exists for the user
        collections = Collection.get_all(CollectionName=collectionname, User=user)
        if collections:
            messagebox.showerror(
                "Duplicate Collection",
                f"You already have a collection named '{collectionname}'."
            )
            return

        # Create and save the new collection
        try:
            new_collection = Collection(
                CollectionName=collectionname,
                User=user
            )
            new_collection.save()
            message = f"Collection '{collectionname}' added successfully."
            messagebox.showinfo("Success", message)
            log(message)

            if self.refresh_callback:
                self.refresh_callback()

            self.destroy()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to add collection: {e}")

class DeactivateCollectionWindow(tk.Toplevel):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master)
        self.title("Deactivate Collection")
        self.geometry("320x180")
        self.refresh_callback = refresh_callback

        # Label
        tk.Label(self, text="Select Collection to Deactivate:").pack(pady=(10, 5))

        # Dropdown
        self.collection_var = tk.StringVar()
        self.collection_dropdown = ttk.Combobox(self, textvariable=self.collection_var, state="readonly")
        self.collection_dropdown.pack()

        # Buttons
        tk.Button(self, text="Deactivate Collection", command=self.submit).pack(pady=10)
        tk.Button(self, text="Cancel", command=self.destroy).pack()

        self.load_collections()

    def load_collections(self):
        user = get_logged_in_user()
        collections = Collection.get_all(User=user)  # <- removed CollectionName filter
        if not collections:
            messagebox.showwarning("No Collections", "No collections found for the logged-in user.")
            self.collection_dropdown['values'] = []
            self.collection_dropdown.set("No collections available")
        else:
            self.collection_dropdown['values'] = [c.CollectionName for c in collections]

    def submit(self):
        selected_name = self.collection_var.get().strip()
        if not selected_name:
            messagebox.showerror("Input Error", "Please select a collection.")
            return

        # Extra warning prompt
        confirm = messagebox.askyesno(
            "Confirm Deactivation",
            f"Are you sure you want to deactivate the collection '{selected_name}'?\n\n"
            "This will deactivate every item in this collection. Continue?"
        )
        if not confirm:
            return

        try:
            # Get and deactivate the collection
            collection = Collection.get_by_identifier(selected_name)
            if not collection:
                messagebox.showerror("Error", "Collection not found.")
                return

            collection.update_status("Inactive")
            collection.update_all_items_status("Inactive")
            message=f"Collection '{selected_name}' and all its items have been deactivated."
            messagebox.showinfo("Success", message)
            log(message)
            self.load_collections()
            if self.refresh_callback:
                self.refresh_callback()

        except Exception as e:
            message=f"An error occurred: {e}"
            messagebox.showerror("Database Error", message)
            log(message)

class ReactivateCollectionWindow(tk.Toplevel):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master)
        self.title("Reactivate Collection")
        self.geometry("320x180")
        self.refresh_callback = refresh_callback

        # Label
        tk.Label(self, text="Select Collection to Reactivate:").pack(pady=(10, 5))

        # Dropdown
        self.collection_var = tk.StringVar()
        self.collection_dropdown = ttk.Combobox(self, textvariable=self.collection_var, state="readonly")
        self.collection_dropdown.pack()

        # Buttons
        tk.Button(self, text="Reactivate Collection", command=self.submit).pack(pady=10)
        tk.Button(self, text="Cancel", command=self.destroy).pack()

        self.load_collections()

    def load_collections(self):
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT CollectionName FROM Collection WHERE Status = 'Inactive'")
        collections = [row["CollectionName"] for row in cursor.fetchall()]
        cursor.close()

        if collections:
            self.collection_dropdown['values'] = collections
            self.collection_dropdown.set(collections[0])
        else:
            self.collection_dropdown['values'] = []
            self.collection_dropdown.set("No active collections")
            self.collection_dropdown.config(state="disabled")

    def submit(self):
        selected_name = self.collection_var.get().strip()
        if not selected_name:
            messagebox.showerror("Input Error", "Please select a collection.")
            return

        # Extra warning prompt
        confirm = messagebox.askyesno(
            "Confirm Reactivation",
            f"Are you sure you want to reactivate the collection '{selected_name}'?\n\n"
            "This will activate every item in this collection. Continue?"
        )
        if not confirm:
            return

        try:
            # Get and deactivate the collection
            collection = Collection.get_by_identifier(selected_name)
            if not collection:
                messagebox.showerror("Error", "Collection not found.")
                return

            collection.update_status("Active")
            collection.update_all_items_status("Active")
            message=f"Collection '{selected_name}' and all its items have been reactivated."
            messagebox.showinfo("Success", message)
            log(message)
            self.load_collections()
            if self.refresh_callback:
                self.refresh_callback()

        except Exception as e:
            message=f"An error occurred: {e}"
            messagebox.showerror("Database Error", message)
            log(message)

class DeleteCollectionWindow(tk.Toplevel):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master)
        self.title("Delete Collection")
        self.refresh_callback = refresh_callback
        self.geometry("300x150")
        self.minsize(300, 150)

        # Label
        self.collection_label = tk.Label(self, text="Select Collection to Delete:")
        self.collection_label.pack()

        # Dropdown
        self.collection_var = tk.StringVar()
        self.collection_dropdown = ttk.Combobox(self, textvariable=self.collection_var, state="readonly")
        self.collection_dropdown.pack()

        # Buttons
        self.submit_button = tk.Button(self, text="Delete Collection", command=self.submit)
        self.submit_button.pack(pady=10)

        self.cancel_button = tk.Button(self, text="Cancel", command=self.cancel)
        self.cancel_button.pack()

        self.load_collections()  # 🔁 Populate dropdown

    def load_collections(self):
        logged_in_user = get_logged_in_user()
        conn = connect()
        cursor = conn.cursor()
        query = "SELECT CollectionName FROM Collection WHERE User = ?"
        cursor.execute(query, (logged_in_user,))
        collections = [row["CollectionName"] for row in cursor.fetchall()]
        cursor.close()

        if not collections:
            self.collection_dropdown['values'] = []
            self.collection_dropdown.set("No collections available")
            self.collection_dropdown.config(state="disabled")
        else:
            self.collection_dropdown.config(state="readonly")
            self.collection_dropdown['values'] = collections
            self.collection_dropdown.set(collections[0])
            logged_in_user = get_logged_in_user()
            conn = connect()
            cursor = conn.cursor()
            query = "SELECT CollectionName FROM Collection WHERE User = ?"
            cursor.execute(query, (logged_in_user,))
            collections = [row["CollectionName"] for row in cursor.fetchall()]
            cursor.close()

            if not collections:
                self.collection_dropdown['values'] = []
                self.collection_dropdown.set("No collections available")
                self.collection_dropdown.config(state="disabled")
            else:
                self.collection_dropdown.config(state="readonly")
                self.collection_dropdown['values'] = collections
                self.collection_dropdown.set(collections[0])

    def submit(self):
        selected_collection = self.collection_var.get().strip()
        if not selected_collection:
            messagebox.showerror("Input Error", "Please select a collection to delete.")
            return

        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete collection '{selected_collection}'?")
        if not confirm:
            return

        try:
            collection = Collection.get_by_identifier(selected_collection)
            if collection:
                collection.delete()
                message=f"Collection '{selected_collection}' has been deleted."
                messagebox.showinfo("Success", message)
                log(message)
                self.load_collections()  # 🔁 Refresh dropdown
                if self.refresh_callback:
                    self.refresh_callback()
            else:
                messagebox.showerror("Error", f"Collection '{selected_collection}' not found.")
        except Exception as e:
            message=f"An error occurred: {e}"
            messagebox.showerror("Database Error", message)
            log(message)

    def cancel(self):
        self.destroy()

# TODO:EditCollectionWindow(FormWindow)








# TODO:ReactivateItemWindow(FormWindow)


### SOURCE ###

# TODO: AddSourceWindow(FormWindow)

class AddSourceWindow(FormWindow):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master, title="Add Source")
        self.refresh_callback = refresh_callback

        self.geometry("400x500")
        self.minsize(400, 500)
        self.maxsize(400, 500)

        # Define field names and their labels
        self.fields = {
            "BusinessName": "Business Name",
            "FirstName": "First Name",
            "LastName": "Last Name",
            "Email": "Email",
            "Phone": "Phone",
            "Address": "Address",
            "City": "City",
            "State": "State",
            "Zip": "ZIP"
        }

        # Dictionary to store Entry widgets
        self.entries = {}

        # Create label + entry for each field using grid
        for key, label in self.fields.items():
            row = self.next_row()

            lbl = tk.Label(self.form_frame, text=f"{label}:")
            lbl.grid(row=row, column=0, sticky="w", pady=5, padx=5)

            entry = tk.Entry(self.form_frame)
            entry.grid(row=row, column=1, sticky="ew", pady=5, padx=5)

            self.entries[key] = entry

        # Submit and Cancel buttons
        self.add_buttons(submit_text="Add Source", cancel_text="Cancel")

        if self.refresh_callback:
            self.refresh_callback()

    def submit(self):
        # Extract and strip data from entries
        data = {key: entry.get().strip() for key, entry in self.entries.items()}

        # Basic validation
        if not data["BusinessName"]:
            messagebox.showerror("Input Error", "Business Name cannot be empty.")
            return

        confirm_message = "Is this information correct?\n\n" + "\n".join(
            f"{self.fields[key]}: {data.get(key) or 'N/A'}" for key in self.fields
        )

        if not messagebox.askyesno("Confirm Source Details", confirm_message):
            return

        try:
            new_source = Source(**data)
            new_source.save()
            message = f"Source '{data['BusinessName']}' added successfully."
            messagebox.showinfo("Success", message)

            if self.refresh_callback:
                self.refresh_callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to add source: {e}")

    def cancel(self):
        self.destroy()



class UpdateSourceWindow(FormWindow):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master, title="Update Source")
        self.refresh_callback = refresh_callback
        self.geometry("400x550")
        self.minsize(400, 550)
        self.maxsize(400, 550)

        # Dropdown to select the source
        source_query = "SELECT BusinessName FROM Source ORDER BY BusinessName"
        self.source_dropdown, self.source_var = self.labeled_dropdown(
            "Select Source:", source_query, map_name="source"
        )
        self.source_dropdown.bind("<<ComboboxSelected>>", self.prefill_fields)

        # Fields to update
        self.fields = {
            "BusinessName": "Business Name",
            "FirstName": "First Name",
            "LastName": "Last Name",
            "Email": "Email",
            "Phone": "Phone",
            "Address": "Address",
            "City": "City",
            "State": "State",
            "Zip": "ZIP"
        }

        self.entries = {}
        for key, label in self.fields.items():
            row = self.next_row()
            tk.Label(self.form_frame, text=f"{label}:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
            entry = tk.Entry(self.form_frame)
            entry.grid(row=row, column=1, sticky="ew", pady=5, padx=5)
            self.entries[key] = entry

        # Buttons
        self.add_buttons(submit_text="Update Source", cancel_text="Cancel")

    def prefill_fields(self, event=None):
        identifier = self.source_var.get()
        if not identifier:
            return
        source = Source.get_by_identifier("BusinessName", identifier)
        if not source:
            return

        for key in self.fields:
            self.entries[key].delete(0, tk.END)
            self.entries[key].insert(0, getattr(source, key, ""))

    def submit(self):
        selected_source = self.source_var.get()
        if not selected_source:
            messagebox.showerror("Input Error", "Please select a source to update.")
            return

        data = {key: entry.get().strip() for key, entry in self.entries.items()}

        if not data["BusinessName"]:
            messagebox.showerror("Input Error", "Business Name cannot be empty.")
            return

        try:
            updated_source = Source(**data)
            updated_source.update("BusinessName", selected_source)
            messagebox.showinfo("Success", f"Source '{selected_source}' updated successfully.")

            if self.refresh_callback:
                self.refresh_callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to update source: {e}")

    def cancel(self):
        self.destroy()



if __name__ == "__main__":
    main()
