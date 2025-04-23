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

        return dropdown, var

    def labeled_textarea(self, label, height=4, width=40):
        row = self.next_row()

        tk.Label(self.form_frame, text=label, anchor="w", justify="left").grid(row=row, column=0, sticky="nw", padx=5, pady=5)
        text_widget = tk.Text(self.form_frame, height=height, width=width)
        text_widget.grid(row=row, column=1, sticky="ew", padx=5, pady=5)

        self.form_frame.grid_columnconfigure(1, weight=1)
        return text_widget

    def create_button(self, text, command, columnspan=2, pady=5):
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
        self.submit_button = tk.Button(self.form_frame, text=submit_text, command=submit_command)
        self.submit_button.grid(row=row, column=0, pady=10, padx=5, sticky="e")

        self.cancel_button = tk.Button(self.form_frame, text=cancel_text, command=cancel_command)
        self.cancel_button.grid(row=row, column=1, pady=10, padx=5, sticky="w")

    def load_dropdown_data(self, dropdown, query, params=(), map_name=None):
        conn = connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()

        values = [row[0] for row in results]
        dropdown["values"] = values

        if map_name and results and len(results[0]) > 1:
            mapping = {row[1]: row[0] for row in results}
            setattr(self, f"{map_name}_map", mapping)
        else:
            setattr(self, f"{map_name}_map", {})
