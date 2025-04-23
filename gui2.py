import sqlite3
import tkinter as tk  # Ensure tkinter is imported as tk
from tkinter import ttk, simpledialog, messagebox
from models import User, Item, Source, Collection, BaseModel  # Assuming these models are defined in models.py
from db import connect, login, get_logged_in_user, is_admin  # Import the required functions from db.py
from log import log
# import ttkbootstrap as ttk # Nicetohave if we have time!
# from ttkbootstrap.constants import *
 
def main():
    # Initialize root window
    root = tk.Tk()
    root.withdraw() # hide main window until logged in.

    login_window = LoginWindow(master=root)
    login_window.mainloop()

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
        log(f"[DEBUG] Logged in user in MainApplication: {logged_in_user}")

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
class LoginWindow(tk.Toplevel):
    """Login window where users can log in."""

    def __init__(self, master=None):
        super().__init__(master)
        self.title("Login")
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

            # Use your `login()` function to validate credentials
            if login(username, password):
                # ✅ Get full user row here
                conn = connect()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM User WHERE Username = ?", (username,))
                user = cursor.fetchone()

                if user:
                    global logged_in_user
                    logged_in_user = user  # ✅ full sqlite3.Row object

                    print(f"[DEBUG] Logged in user: {logged_in_user['Username']}")
                    message = f"Welcome, {logged_in_user['Username']}!"
                    messagebox.showinfo("Login Success", message)
                    log(message)
                    self.destroy()
                    self.open_main_application()
                else:
                    messagebox.showerror("Error", "Could not retrieve user info.")
            else:
                messagebox.showerror("Login Failed", "Invalid username or password.")

        except Exception as e:
            log(f"[ERROR] {e}")
            messagebox.showerror("Error", str(e))
            log(str(e))
            

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

            "My Items": {
                "visible": lambda: True,
                "columns": (
                    "ItemName", "Collection", "User", "Source", "Status",
                    "Description", "PricePaid", "CurrentValue", "Location", "Notes"
                ),
                "query": ""  # Query handled dynamically via dropdown
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
            ,

            "Activiy Log": 
            {"visible": lambda:is_admin(), # Visible only to admin
             "columns": ("User", "Message", "Timestamp"),
             "query": """
                        SELECT User, Message, Timestamp FROM Log
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
        else:
            return f"SELECT {', '.join(columns)} FROM {table}"

    def setup_tabs(self):
        logged_in_user = get_logged_in_user()

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

        self.my_items_tab = parent

        self.collection_var = StringVar()

        # Frame to hold label and dropdown in a row
        dropdown_frame = tk.Frame(parent)
        dropdown_frame.pack(anchor="w", padx=10, pady=(10, 5))  # Left-aligned

        # Label
        collection_label = tk.Label(dropdown_frame, text="Choose a Collection:")
        collection_label.pack(side="left")

        # Dropdown
        self.collection_dropdown = ttk.Combobox(dropdown_frame, textvariable=self.collection_var, state="readonly")
        self.collection_dropdown.pack(side="left", padx=(5, 0))
        self.collection_dropdown.bind("<<ComboboxSelected>>", self.on_collection_selected)

        # Treeview
        self.my_items_tree = self.create_treeview(parent, columns)
        self.item_tree = self.my_items_tree  # So double-click still works
        self.item_tree.bind("<Double-1>", self.on_double_click)

        # Load collections
        self.load_collection_dropdown()

    def load_collection_dropdown(self):
            
            global logged_in_user
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
        global logged_in_user
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
                if tab_name == "My Items":
                    treeview = self.my_items_tree  # Directly access the attribute for "My Items"
                else:
                    treeview = getattr(self, f"{tab_name.lower()}_tree")  # Use dynamic access for other tabs
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
            "My Items": Item,  # ✅ Handle "My Items"
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
                # Use a more reliable lookup (e.g., by name/user/collection)
                query_columns = self.tabs_config["My Items"]["columns"]
                item_name = values[query_columns.index("ItemName")]
                collection = values[query_columns.index("Collection")]
                user = values[query_columns.index("User")]

                item = model_cls.get_by_fields(item_name=item_name, collection=collection, user=user)
            else:
                # Use the first column as identifier for non-item tabs
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
            self.add_button("Edit User", self.edit_user)
            self.add_button("Deactivate User", self.deactivate_user)
            self.add_button("Reactivate User", self.reactivate_user)
            self.add_button("Delete User", self.delete_user)

        elif active_tab == "My Items":            
            self.add_button("Add Item", self.add_item)
            self.add_button("Edit Item", self.edit_item)
            self.add_button("Delete Item", self.delete_item)
            self.add_button("Add Collection", self.add_collection)
            self.add_button("Edit Collection", self.edit_collection)
            self.add_button("Deactivate Collection", self.deactivate_collection)
            self.add_button("Reactivate Collection", self.reactivate_collection)
            # self.add_button("Delete Collection", self.delete_collection)


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

    def edit_user(self):
        messagebox.showinfo("Edit User", "Edit user functionality not implemented yet.")

    def delete_user(self):
        DeleteUserWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()  

    # --- Item actions ---
    def add_item(self):
        AddItemWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()

    def edit_item(self):
        EditItemWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()
        

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

    def delete_collection(self):
        DeleteCollectionWindow(self.master, refresh_callback=self.master.tab_viewer.refresh_all).grab_set()


    def edit_collection(self):
        messagebox.showinfo("Edit Collection", "Edit collection functionality not implemented yet.")

    # --- Source actions ---
    def add_source(self):
        business_name = simpledialog.askstring("Add Source", "Enter business name:")
        first_name = simpledialog.askstring("Add Source", "Enter first name:")
        phone = simpledialog.askstring("Add Source", "Enter phone number:")
        email = simpledialog.askstring("Add Source", "Enter email:")
        if business_name and first_name and phone and email:
            source = Source(BusinessName=business_name, FirstName=first_name, Phone=phone, Email=email)
            source.save()
            message="Source added successfully!"
            messagebox.showinfo("Success", message)
            log(message)
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
            message="Username and password cannot be empty."
            messagebox.showerror("Input Error", messagebox)
            log(message)
            return

        try:
            user = User(Username=username, Password=password, Role=role)
            user.save()
            message = "User added successfully."
            messagebox.showinfo("Success", message)
            log(message)

            if self.refresh_callback:
                self.refresh_callback()

            self.destroy()  # Close the window
        except Exception as e:
            message=f"Failed to add user: {e}"
            messagebox.showerror("Database Error", message)
            log(message)

        



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
                message=f"User '{selected_user}' has been deactivated."
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
                user.update_status("Active")
                message=f"User '{selected_user}' has been reactivated."
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
            message=f"Collection '{collectionname}' added successfully."
            messagebox.showinfo("Success", message)
            log(message)

            if self.refresh_callback:
                self.refresh_callback()

            self.destroy()
        except Exception as e:
            message=f"Failed to add collection: {e}"
            messagebox.showerror("Database Error", message)
            log(message)

    def cancel(self):
        self.destroy()


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


### ITEM ###

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
            message=f"Item '{itemname}' added successfully."
            messagebox.showinfo("Success", message)
            log(message)

            if self.refresh_callback:
                self.refresh_callback()

            self.destroy()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to add item: {e}")


class EditItemWindow(tk.Toplevel):
    def __init__(self, master, refresh_callback=None):
        super().__init__(master)
        self.refresh_callback = refresh_callback
        self.title("Edit Item")
        self.geometry("400x550")

        self.item_data = {}
        self.selected_item_id = None

        # Dropdown to select item
        ttk.Label(self, text="Select Item to Edit:").pack(pady=(10, 0))
        self.item_var = tk.StringVar()
        self.item_dropdown = ttk.Combobox(self, textvariable=self.item_var, state="readonly")
        self.item_dropdown.pack(pady=(0, 10))
        self.item_dropdown.bind("<<ComboboxSelected>>", self.on_item_selected)

        # Form fields
        self.name_var = tk.StringVar()
        self.price_var = tk.StringVar()
        self.desc_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        self.collection_var = tk.StringVar()
        self.source_var = tk.StringVar()

        ttk.Label(self, text="Item Name").pack()
        self.name_entry = ttk.Entry(self, textvariable=self.name_var)
        self.name_entry.pack()

        ttk.Label(self, text="Collection").pack()
        self.collection_dropdown = ttk.Combobox(self, textvariable=self.collection_var, state="readonly")
        self.collection_dropdown.pack()

        ttk.Label(self, text="Source").pack()
        self.source_dropdown = ttk.Combobox(self, textvariable=self.source_var, state="readonly")
        self.source_dropdown.pack()

        ttk.Label(self, text="Price").pack()
        self.price_entry = ttk.Entry(self, textvariable=self.price_var)
        self.price_entry.pack()

        ttk.Label(self, text="Description").pack()
        self.desc_entry = ttk.Entry(self, textvariable=self.desc_var)
        self.desc_entry.pack()

        ttk.Label(self, text="Notes").pack()
        self.notes_entry = ttk.Entry(self, textvariable=self.notes_var)
        self.notes_entry.pack()

        # Update button
        self.update_button = ttk.Button(self, text="Update", command=self.update_item)
        self.update_button.pack(pady=20)

        self.load_collections()
        self.load_sources()
        self.load_items()

    def load_items(self):
        from db import connect
        conn = connect()
        cursor = conn.cursor()

        global logged_in_user
        user = logged_in_user if isinstance(logged_in_user, dict) else {"Username": logged_in_user, "Role": "user"}

        if user["Role"] == "admin":
            cursor.execute("SELECT * FROM Item")
        else:
            cursor.execute("SELECT * FROM Item WHERE Username = ?", (user["Username"],))

        rows = cursor.fetchall()
        self.item_data = {f'{row["ItemName"]} (ID {row["ItemID"]})': row for row in rows}
        self.item_dropdown["values"] = list(self.item_data.keys())

        conn.close()

    def load_collections(self):
        from db import connect
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT CollectionName FROM Collection")
        self.collection_dropdown["values"] = [row["CollectionName"] for row in cursor.fetchall()]
        conn.close()

    def load_sources(self):
        from db import connect
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT SourceName FROM Source")
        self.source_dropdown["values"] = [row["SourceName"] for row in cursor.fetchall()]
        conn.close()

    def on_item_selected(self, event):
        item_name = self.item_var.get()
        item = self.item_data[item_name]
        self.selected_item_id = item["ItemID"]
        self.name_var.set(item["ItemName"])
        self.price_var.set(item["Price"])
        self.desc_var.set(item["Description"])
        self.notes_var.set(item["Notes"])
        self.collection_var.set(item["CollectionName"])
        self.source_var.set(item["SourceName"])

    def update_item(self):
        from db import connect
        conn = connect()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE Item SET
                    ItemName = ?,
                    CollectionName = ?,
                    SourceName = ?,
                    Price = ?,
                    Description = ?,
                    Notes = ?
                WHERE ItemID = ?
            """, (
                self.name_var.get(),
                self.collection_var.get(),
                self.source_var.get(),
                self.price_var.get(),
                self.desc_var.get(),
                self.notes_var.get(),
                self.selected_item_id
            ))
            conn.commit()
            messagebox.showinfo("Success", "Item updated successfully.")
            if self.refresh_callback:
                self.refresh_callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update item: {e}")
        finally:
            conn.close()
