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
