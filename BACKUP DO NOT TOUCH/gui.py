import sqlite3
import tkinter as tk  # Ensure tkinter is imported as tk
from tkinter import ttk, simpledialog, messagebox
from models import User, Item, Source, Collection, BaseModel  # Assuming these models are defined in models.py
from db import connect, login, get_logged_in_user, is_admin  # Import the required functions from db.py
from log import log
# import ttkbootstrap as ttk # Nicetohave if we have time!
# from ttkbootstrap.constants import *
 

##### BUILDING BLOCKS FOR GUI COMPONENTS #####

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

    def add_field(self, label):
        field = LabeledEntry(self, label)
        field.pack(pady=5)
        self.entries[label] = field
        return field

    def get_data(self):
        return {key.replace(":", "").strip(): entry.get() for key, entry in self.entries.items()}
    
# Form-based window with buttons
class FormWindow(BaseWindow):
    def __init__(self, master=None, title="Form Window", submit_callback=None, cancel_callback=None):
        super().__init__(master, title)
        self.submit_callback = submit_callback
        self.cancel_callback = cancel_callback

        self.form_frame = tk.Frame(self)
        self.form_frame.pack(fill="both", expand=True, padx=10, pady=(0))

        self.button_frame = tk.Frame(self)
        self.button_frame.pack(side="bottom", pady=10)  # Moved to bottom

        submit_btn = tk.Button(self.button_frame, text="Submit", command=self.submit)
        submit_btn.pack(side="left", padx=5)

        cancel_btn = tk.Button(self.button_frame, text="Cancel", command=self.cancel)
        cancel_btn.pack(side="left", padx=5)

##### APPLICATION INTERFACE WINDOWS #####

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
        print(f"[DEBUG] Logged in user in MainApplication: {logged_in_user}")

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)  # 40% for the button panel
        self.grid_columnconfigure(1, weight=2)  # 60% for the tab viewer
        self.grid_rowconfigure(0, weight=1)

        # Create the dynamic button panel
        self.button_panel = DynamicButtonPanel(self)
        self.button_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Create the tab viewer
        self.tab_viewer = TabViewer(self)
        self.tab_viewer.grid(row=0, column=1, sticky="nsew")

        # Link the tab change event to update buttons
        self.tab_viewer.notebook.bind("<<NotebookTabChanged>>", self.update_buttons)

    def update_buttons(self, event=None):
        """Update the buttons based on the active tab."""
        active_tab = self.tab_viewer.notebook.tab(self.tab_viewer.notebook.select(), "text")
        self.button_panel.update_buttons(active_tab)

    # def new_user(self):
    #     User.register()

# Login window extends the BaseWindow class
class LoginWindow(BaseWindow):
    """Login window where users can log in."""

    def __init__(self, master=None):
        super().__init__(master, title="Login")
        self.geometry("400x200")
        self.configure(padx=20, pady=20)

        # Username field
        self.username_entry = LabeledEntry(self, label_text="Username:")
        self.username_entry.pack(pady=10, fill="x")

        # Password field
        self.password_entry = LabeledEntry(self, label_text="Password:", show="*")
        self.password_entry.pack(pady=10, fill="x")

        # Login button
        self.login_button = tk.Button(self, text="Login", command=self.login)
        self.login_button.pack(pady=10)

    def login(self):
        try:
            username = self.username_entry.get()
            password = self.password_entry.get()

            if not username or not password:
                messagebox.showerror("Error", "All fields are required.")
                return

            # Call the `login` function from `db.py`
            if login(username, password):
                logged_in_user = get_logged_in_user()
                print(f"[DEBUG] Logged in user: {logged_in_user}")
                messagebox.showinfo("Login Success", f"Welcome, {logged_in_user}!")
                self.destroy()
                app = MainApplication()
                app.mainloop()
            else:
                messagebox.showerror("Login Failed", "Invalid username or password.")
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

        # Tabs are stored in a dictionary
        self.tabs_config = {
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
                "query": self.get_filtered_query("Collection", ["CollectionName", "User", "Status"])  # For non-admin users, show only logged in user's collection
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
        global logged_in_user
        user = get_logged_in_user()
        # If the user is not an admin, limit the query to their own data
        if not is_admin() and "User" in columns:
            return f"SELECT {', '.join(columns)} FROM {table} WHERE User = '{user}'"
        
        # If user is an admin, return the unfiltered query
        return f"SELECT {', '.join(columns)} FROM {table}"

    def setup_tabs(self):
        logged_in_user = get_logged_in_user()

        for tab_name, config in self.tabs_config.items():
            if config["visible"]():
                tab_frame = ttk.Frame(self.notebook)
                self.notebook.add(tab_frame, text=tab_name)

                treeview = self.create_treeview(tab_frame, config["columns"])
                self.populate_treeview(treeview, config["query"])
                setattr(self, f"{tab_name.lower()}_tree", treeview)

                # Only bind double-click event for the 'Items' tab
                if tab_name == "Items":
                    self.item_tree = treeview
                    self.item_tree.bind("<Double-1>", self.on_double_click)

    def create_treeview(self, parent, columns):
        tree = ttk.Treeview(parent, columns=columns, show="headings")
        tree.bind("<Double-1>", self.on_double_click)  # <-- bind here
        for col in columns:
            tree.heading(col, text=col, command=lambda col=col: self.sort_items(tree, col))
            tree.column(col, anchor="center", width=100)
        tree.pack(fill="both", expand=True)
        return tree

    def populate_treeview(self, tree, query, params=()):
        conn = sqlite3.connect("collections.sqlite")
        cursor = conn.cursor()
        cursor.execute(query, params)
        for row in cursor.fetchall():
            tree.insert("", "end", values=row)
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
        # Get all items (not the headers)
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
                treeview = getattr(self, f"{tab_name.lower()}_tree")
                treeview.delete(*treeview.get_children())
                self.populate_treeview(treeview, config["query"])
    
    def on_double_click(self, event):
        treeview = event.widget
        selected = treeview.selection()

        if not selected:
            return

        values = treeview.item(selected[0])["values"]
        tab_name = self.notebook.tab(self.notebook.select(), "text")

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

        # If ItemID is not part of the columns, fetch it from the database using ItemName or other unique identifiers
        if tab_name == "Items":
            identifier_column = "ItemID"  # Hardcode the column name for identifier
            query_columns = self.tabs_config[tab_name]["columns"]
            
            try:
                identifier_index = query_columns.index("ItemName")  # Using ItemName here as a substitute
                identifier_value = values[identifier_index]

                # Fetch the full object using ItemName or other identifier
                instance = model_cls.get_by_identifier(identifier_value)

                if not instance:
                    messagebox.showerror("Error", f"{tab_name[:-1]} not found")
                    return

                fields, vals = instance.get_fields_and_values()
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
            self.add_button("Edit User", self.edit_user)
            self.add_button("Deactivate User", self.deactivate_user)
            self.add_button("Reactivate User", self.reactivate_user)
        elif active_tab == "Items":
            self.add_button("Add Item", self.add_item)
            self.add_button("Edit Item", self.edit_item)
            self.add_button("Delete Item", self.delete_item)
        elif active_tab == "Collections":
            self.add_button("Add Collection", self.add_collection)
            self.add_button("Edit Collection", self.edit_collection)
            self.add_button("Deactivate Collection", self.deactivate_collection)
            self.add_button("Reactivate Collection", self.reactivate_collection)
        elif active_tab == "Sources":
            self.add_button("Add Source", self.add_source)
            self.add_button("Edit Source", self.edit_source)
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

    def edit_user(self):
        messagebox.showinfo("Edit User", "Edit user functionality not implemented yet.")

    def deactivate_user(self):
        DeactivateUserWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()        

    def reactivate_user(self):
        ReactivateUserWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()        


    def delete_user(self):
        messagebox.showinfo("Edit User", "Edit user functionality not implemented yet.")

    # --- Item actions ---
    def add_item(self):
        AddItemWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()

    def edit_item(self):
        messagebox.showinfo("Edit Item", "Edit item functionality not implemented yet.")

    def delete_item(self):
        item_name = simpledialog.askstring("Delete Item", "Enter item name to delete:")
        if item_name:
            # Replace with actual deletion logic
            messagebox.showinfo("Delete Item", "Delete item functionality not implemented yet.")
            self.master.tab_viewer.refresh_all()

    # --- Collection actions ---
    def add_collection(self):
        AddCollectionWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()

    def deactivate_collection(self):
        DeactivateCollectionWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()

    def reactivate_collection(self):
        ReactivateCollectionWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()


    def edit_collection(self):
        messagebox.showinfo("Edit Collection", "Edit collection functionality not implemented yet.")

    def delete_collection(self):
        collection_name = simpledialog.askstring("Delete Collection", "Enter collection name to delete:")
        if collection_name:
            # Replace with actual deletion logic
            messagebox.showinfo("Delete Collection", "Delete collection functionality not implemented yet.")
            self.master.tab_viewer.refresh_all()

    # --- Source actions ---
    def add_source(self):
        business_name = simpledialog.askstring("Add Source", "Enter business name:")
        first_name = simpledialog.askstring("Add Source", "Enter first name:")
        phone = simpledialog.askstring("Add Source", "Enter phone number:")
        email = simpledialog.askstring("Add Source", "Enter email:")
        if business_name and first_name and phone and email:
            source = Source(BusinessName=business_name, FirstName=first_name, Phone=phone, Email=email)
            source.save()
            messagebox.showinfo("Success", "Source added successfully!")
            self.master.tab_viewer.refresh_all()

    def edit_source(self):
        messagebox.showinfo("Edit Source", "Edit source functionality not implemented yet.")

    def delete_source(self):
        business_name = simpledialog.askstring("Delete Source", "Enter business name to delete:")
        if business_name:
            # Replace with actual deletion logic
            messagebox.showinfo("Delete Source", "Delete source functionality not implemented yet.")
            self.master.tab_viewer.refresh_all()

    def dummy_action(self):
        print("Button clicked!")

##### CRUD OPERATION WINDOWS #####

### USER ###

class AddUserWindow(FormWindow):    
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master, title="Add User")
        self.refresh_callback = refresh_callback
        self.geometry("400x350")

        # Username field
        self.username_label = tk.Label(self, text="Username:")
        self.username_label.pack()
        self.username_entry = tk.Entry(self)
        self.username_entry.pack()

        # Password field
        self.password_label = tk.Label(self, text="Password:")
        self.password_label.pack()
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack()

        # Confirm password field
        self.confirm_password_label = tk.Label(self, text="Confirm Password")
        self.confirm_password_label.pack()
        self.confirm_password_entry = tk.Entry(self, show="*")
        self.confirm_password_entry.pack()

        # Show/hide password checkbox
        self.show_password_var = tk.BooleanVar()
        self.show_password_check=tk.Checkbutton(
            self,
            text="Show Password",
            variable=self.show_password_var,
            command=self.toggle_password_visibility
        )
        self.show_password_check.pack()

        # Role dropdown
        self.role_label = tk.Label(self, text="Role:")
        self.role_label.pack()
        self.role_var = tk.StringVar()
        self.role_dropdown = ttk.Combobox(self, textvariable=self.role_var, state="readonly")
        self.role_dropdown["values"] = ("Admin", "User")
        self.role_dropdown.pack()
        self.role_dropdown.current(0)  # Default to Admin

        if self.refresh_callback:
            self.refresh_callback()

    def toggle_password_visibility(self):
        """Toggle visibility of password fields."""
        show_char = "" if self.show_password_var.get() else "*"
        self.password_entry.config(show=show_char)
        self.confirm_password_entry.config(show=show_char)

    def submit(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        role = self.role_var.get().strip()

        if not username or not password:
            messagebox.showerror("Input Error", "Username and password cannot be empty.")
            return

        try:
            user = User(Username=username, Password=password, Role=role)
            user.save()
            messagebox.showinfo("Success", "User added successfully.")

            if self.refresh_callback:
                self.refresh_callback()

            self.destroy()  # Close the window
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to add user: {e}")

        



    def cancel(self):
        self.destroy()

# TODO:DeactiveUserWindow(FormWindow)
class DeactivateUserWindow(tk.Toplevel):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master)
        self.title("Deactivate User")
        self.refresh_callback = refresh_callback
        self.geometry("300x150")
        self.minsize(300, 150)

        # Label
        self.user_label = tk.Label(self, text="Select User to Deactivate:")
        self.user_label.pack()

        # Dropdown
        self.user_var = tk.StringVar()
        self.user_dropdown = ttk.Combobox(self, textvariable=self.user_var, state="readonly")
        self.user_dropdown.pack()

        # Buttons
        self.submit_button = tk.Button(self, text="Deactivate User", command=self.submit)
        self.submit_button.pack(pady=10)

        self.cancel_button = tk.Button(self, text="Cancel", command=self.cancel)
        self.cancel_button.pack()

        self.load_users()  # 🔁 Populate dropdown

    def load_users(self):
        logged_in_user = get_logged_in_user()
        conn = connect()
        cursor = conn.cursor()
        query = "SELECT Username FROM User WHERE Username != ? AND Status = 'Active'"
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
            messagebox.showerror("Input Error", "Please select a user to deactivate.")
            return

        confirm = messagebox.askyesno("Confirm Deactivation", f"Are you sure you want to deactivate '{selected_user}'?")
        if not confirm:
            return

        try:
            user = User.get_by_identifier(selected_user)
            if user:
                user.update_status("Inactive")
                messagebox.showinfo("Success", f"User '{selected_user}' has been deactivated.")
                self.load_users()  # 🔁 Refresh dropdown
                if self.refresh_callback:
                    self.refresh_callback()
            else:
                messagebox.showerror("Error", f"User '{selected_user}' not found.")
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")

    def cancel(self):
        self.destroy()

class ReactivateUserWindow(tk.Toplevel):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master)
        self.title("Reactivate User")
        self.refresh_callback = refresh_callback
        self.geometry("300x150")
        self.minsize(300, 150)

        # Label
        self.user_label = tk.Label(self, text="Select User to Reactivate:")
        self.user_label.pack()

        # Dropdown
        self.user_var = tk.StringVar()
        self.user_dropdown = ttk.Combobox(self, textvariable=self.user_var, state="readonly")
        self.user_dropdown.pack()

        # Buttons
        self.submit_button = tk.Button(self, text="Reactivate User", command=self.submit)
        self.submit_button.pack(pady=10)

        self.cancel_button = tk.Button(self, text="Cancel", command=self.cancel)
        self.cancel_button.pack()

        self.load_users()  # 🔁 Populate dropdown

    def load_users(self):
        logged_in_user = get_logged_in_user()
        conn = connect()
        cursor = conn.cursor()
        query = "SELECT Username FROM User WHERE Username != ? AND Status = 'Inactive'"
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
            messagebox.showerror("Input Error", "Please select a user to reactivate.")
            return

        confirm = messagebox.askyesno("Confirm Reactivation", f"Are you sure you want to reactivate '{selected_user}'?")
        if not confirm:
            return

        try:
            user = User.get_by_identifier(selected_user)
            if user:
                user.updaate_status("Active")
                messagebox.showinfo("Success", f"User '{selected_user}' has been reactivated.")
                self.load_users()  # 🔁 Refresh dropdown
                if self.refresh_callback:
                    self.refresh_callback()
            else:
                messagebox.showerror("Error", f"User '{selected_user}' not found.")
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")

    def cancel(self):
        self.destroy()

# TODO:EditUserWindow(FormWindow)


### COLLECTION ###


class AddCollectionWindow(FormWindow):    
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master, title="Add Collection")
        self.refresh_callback = refresh_callback
        self.geometry("300x150")
        self.minsize(300, 150)
        self.maxsize(300,150)

        # CollectionName field
        self.collectionname_label = tk.Label(self, text="Collection Name:")
        self.collectionname_label.pack()
        self.collectionname_entry = tk.Entry(self)
        self.collectionname_entry.pack()

    def submit(self):
        collectionname = self.collectionname_entry.get().strip()
        user = get_logged_in_user()        

        if not collectionname:
            messagebox.showerror("Input Error", "Collection name cannot be empty.")
            return

        # Ask for confirmation
        confirm = messagebox.askyesno("Confirm", f"Are you sure you want to add the collection '{collectionname}'?")
        if not confirm:
            return

        try:
            conn = connect()
            cursor = conn.cursor()

            # Check if a collection already exists for this user with the same name (case-insensitive)
            cursor.execute("""
                SELECT * FROM Collection 
                WHERE LOWER(CollectionName) = LOWER(?) AND User = ?
            """, (collectionname, user))
            existing = cursor.fetchone()
            conn.close()

            if existing:
                messagebox.showerror("Validation Error", f"A collection named '{collectionname}' already exists.")
                return

            # If no duplicate, create and save the collection
            new_collection = Collection(CollectionName=collectionname, User=user)
            new_collection.save()

            messagebox.showinfo("Success", f"Collection '{collectionname}' added successfully.")

            if self.refresh_callback:
                self.refresh_callback()

            self.destroy()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to add collection: {e}")

    def cancel(self):
        self.destroy()

# TODO:DeactivateCollectionWindow(FormWindow)
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
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT CollectionName FROM Collection WHERE Status = 'Active'")
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

            messagebox.showinfo("Success", f"Collection '{selected_name}' and all its items have been deactivated.")
            self.load_collections()
            if self.refresh_callback:
                self.refresh_callback()

        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")


# TODO:ReactivateCollectionWindow(FormWindow)
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

            messagebox.showinfo("Success", f"Collection '{selected_name}' and all its items have been reactivated.")
            self.load_collections()
            if self.refresh_callback:
                self.refresh_callback()

        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")


# TODO:EditCollectionWindow(FormWindow)


### ITEM ###

# TODO: AddItemWindow(FormWindow)
class AddItemWindow(FormWindow):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master, title="Add Item")
        self.refresh_callback = refresh_callback
        self.geometry("400x500")
        self.minsize(400, 500)

        # Item Name
        self.itemname_label = tk.Label(self, text="Item Name:")
        self.itemname_label.pack()
        self.itemname_entry = tk.Entry(self)
        self.itemname_entry.pack()

        # Collection Dropdown
        self.collection_label = tk.Label(self, text="Collection:")
        self.collection_label.pack()
        self.collection_var = tk.StringVar()
        self.collection_dropdown = ttk.Combobox(self, textvariable=self.collection_var)
        self.load_collections()
        self.collection_dropdown.pack()

        # Add Collection Button
        self.add_collection_button = tk.Button(self, text="Add Collection", command=self.open_add_collection_window)
        self.add_collection_button.pack(pady=5)

        # Source Dropdown
        self.source_label = tk.Label(self, text="Source:")
        self.source_label.pack()
        self.source_var = tk.StringVar()
        self.source_dropdown = ttk.Combobox(self, textvariable=self.source_var)
        self.load_sources()
        self.source_dropdown.pack()

        # Description
        self.description_label = tk.Label(self, text="Item Description:")
        self.description_label.pack()
        self.description_entry = tk.Entry(self)
        self.description_entry.pack()

        # Price Paid
        self.pricepaid_label = tk.Label(self, text="Price Paid:")
        self.pricepaid_label.pack()
        self.pricepaid_entry = tk.Entry(self)
        self.pricepaid_entry.pack()

        # Current Value
        self.currentvalue_label = tk.Label(self, text="Current Value:")
        self.currentvalue_label.pack()
        self.currentvalue_entry = tk.Entry(self)
        self.currentvalue_entry.pack()

        # Notes
        self.notes_label = tk.Label(self, text="Notes:")
        self.notes_label.pack()
        self.notes_text = tk.Text(self, height=4, width=40)
        self.notes_text.pack()

        # Buttons
        self.submit_button = tk.Button(self, text="Add Item", command=self.submit)
        self.submit_button.pack(pady=10)

        self.cancel_button = tk.Button(self, text="Cancel", command=self.cancel)
        self.cancel_button.pack()

        if self.refresh_callback:
            self.refresh_callback()

    def cancel(self):
        """Close the AddItemWindow."""
        self.destroy()

    def load_collections(self):
        user = get_logged_in_user()
        collections = Collection.get_all(User=user)
        if not collections:
            messagebox.showwarning("No Collections", "No collections found for the logged-in user.")
            self.collection_dropdown['values'] = []
            self.collection_dropdown.set("No collections available")
        else:
            self.collection_dropdown['values'] = [c.CollectionName for c in collections]

    def load_sources(self):
        sources = Source.get_all()
        if not sources:
            messagebox.showwarning("No Sources", "No sources found.")
            self.source_dropdown['values'] = []
            self.source_dropdown.set("No sources available")
        else:
            self.source_dropdown['values'] = [s.BusinessName for s in sources]

    def open_add_collection_window(self):
        """Open the AddCollectionWindow and refresh collections after it closes."""
        def refresh_collections():
            self.load_collections()

        AddCollectionWindow(self.master, refresh_callback=refresh_collections).grab_set()

    def submit(self):
        itemname = self.itemname_entry.get().strip()
        collection_name = self.collection_var.get().strip()
        source_name = self.source_var.get().strip()
        description = self.description_entry.get().strip()
        pricepaid = self.pricepaid_entry.get().strip()
        currentvalue = self.currentvalue_entry.get().strip()
        notes = self.notes_text.get("1.0", "end").strip()
        user = get_logged_in_user()

        if not itemname:
            messagebox.showerror("Input Error", "Item Name cannot be empty.")
            return

        if not collection_name or not source_name:
            messagebox.showerror("Input Error", "Please select a collection and source.")
            return

        try:
            # Use the base method to validate and convert numeric fields
            pricepaid = BaseModel.validate_and_convert_numeric(pricepaid, "Price Paid")
            currentvalue = BaseModel.validate_and_convert_numeric(currentvalue, "Current Value")
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
            return
        
        # Display confirmation dialog with item details
        confirm_message = (
            f"Is this information correct?\n\n"
            f"Item Name: {itemname}\n"
            f"Collection: {collection_name}\n"
            f"Source: {source_name}\n"
            f"Description: {description or 'N/A'}\n"
            f"Price Paid: ${pricepaid:.2f}\n"
            f"Current Value: ${currentvalue:.2f}\n"
            f"Notes: {notes or 'N/A'}"
        )
        confirm = messagebox.askyesno("Confirm Item Details", confirm_message)
        if not confirm:
            return

        try:
            # Get collection and source
            collections = Collection.get_all(CollectionName=collection_name, User=user)
            collection = collections[0] if collections else None
            sources = Source.get_all(BusinessName=source_name)
            source = sources[0] if sources else None

            if not collection or not source:
                messagebox.showerror("Database Error", "Collection or source not found.")
                return

            # Create and save the item
            new_item = Item(
                ItemName=itemname,
                Collection=collection.CollectionName,
                Source=source.BusinessName,
                User=user,
                Description=description,
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
# TODO:DeactivateItemWindow(FormWindow)
# TODO:ReactivateItemWindow(FormWindow)
# TODO:EditItemWindow(FormWindow)

### SOURCE ###

# TODO: AddSourceWindow(FormWindow)

class AddSourceWindow(FormWindow):
    def __init__(self, master=None, refresh_callback=None):
        super().__init__(master, title="Add Source")
        self.refresh_callback = refresh_callback

        # Set width and maximum size
        self.geometry("450x750")
        self.minsize(450, 750)

        # Field: Business Name (simple text entry)
        self.businessname_entry = self.labeled_entry("Business Name:")

        # Field: First Name (simple text entry)
        self.firstname_entry = self.labeled_entry("First Name:")

        # Field: Last Name (simple text entry)
        self.lastname_entry = self.labeled_entry("Last Name:")

        # Field: Email (simple text entry)
        self.email_entry = self.labeled_entry("Email:")

        # Field:  (simple text entry)
        self.phone_entry = self.labeled_entry("Phone:")

        # Field: dAdress (simple text entry)
        self.address_entry = self.labeled_entry("Address:")

        # Field: Item Name (simple text entry)
        self.city_entry = self.labeled_entry("City:")

        # Field: Item Name (simple text entry)
        self.state_entry = self.labeled_entry("State:")

        # Field: Item Name (simple text entry)
        self.zip_entry = self.labeled_entry("Zip:")

        # Optional callback to refresh parent UI
        if self.refresh_callback:
            self.refresh_callback()

        # Submit and Cancel buttons
        self.add_buttons(submit_text="Add Item", cancel_text="Cancel")



        def submit(self): 
            businessname = self.businessname.get().strip()
            firstname = self.firstname.get().strip()
            lastname = self.lastname.get().strip()
            email = self.email.get().strip()
            phone = self.phone.get().strip()
            address = self.address.get().strip()
            city = self.city.get().strip()
            state = self.state.get().strip()
            zip = self.zip.get().strip()

        #TODO: Validations

            # Define field names and their labels
            self.fields = {
                
            }

            # Dictionary to store Entry widgets
            self.entries = {}

            # Create label + entry for each field
            for key, label in self.fields.items():
                lbl = tk.Label(self, text=f"{label}:")
                lbl.pack()
                entry = tk.Entry(self)
                entry.pack()
                self.entries[key] = entry

            # Buttons
            self.submit_button = tk.Button(self, text="Add Source", command=self.submit)
            self.submit_button.pack(pady=10)

            self.cancel_button = tk.Button(self, text="Cancel", command=self.cancel)
            self.cancel_button.pack()

            if self.refresh_callback:
                self.refresh_callback()

        def submit(self):
            data = {key: entry.get().strip() for key, entry in self.entries.items()}

            if not data["BusinessName"]:
                messagebox.showerror("Input Error", "Business Name cannot be empty.")
                return

            confirm_message = "Is this information correct?\n\n" + "\n".join(
                f"{label}: {data.get(key) or 'N/A'}" for key, label in self.fields.items()
            )
            if not messagebox.askyesno("Confirm Source Details", confirm_message):
                return

            try:
                new_source = Source(**data)
                new_source.save()
                message = f"Source '{data['BusinessName']}' added successfully."
                messagebox.showinfo("Success", message)
                log(message)
                if self.refresh_callback:
                    self.refresh_callback()
                self.destroy()
            except Exception as e:
                messagebox.showerror("Database Error", f"Failed to add item: {e}")

        def cancel(self):
            self.destroy()

# TODO:EditSourceWindow(FormWindow)

if __name__ == "__main__":
    app = LoginWindow()
    app.mainloop()
    