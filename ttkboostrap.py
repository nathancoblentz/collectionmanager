import tkinter as tk
from ttkbootstrap import Style
from ttkbootstrap.widgets import Button, Label, OptionMenu
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import Button, Label, OptionMenu
from ttkbootstrap.constants import *

class ThemeSelectorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Theme Selector")
        self.geometry("400x200")

        # Bootstrap Style
        self.style = Style()
        self.available_themes = self.style.theme_names()
        self.current_theme = self.style.theme.name

        # Label (styled)
        Label(self, text="Select a Bootstrap Theme:", font=("Arial", 12)).pack(pady=(20, 10))

        # Dropdown menu (styled)
        self.theme_var = tk.StringVar(value=self.current_theme)
        OptionMenu(self, self.theme_var, *self.available_themes, command=self.change_theme).pack(pady=5)

        # Styled button
        Button(self, text="Sample Button", bootstyle="primary").pack(pady=(20, 0))

    def change_theme(self, theme_name):
        self.style.theme_use(theme_name)

if __name__ == "__main__":
    app = ThemeSelectorApp()
    app.mainloop()
