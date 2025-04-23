import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# Initialize the root window with a theme
root = ttk.Window(themename="darkly")

# Create buttons with different bootstyles
b1 = ttk.Button(root, text='primary', bootstyle=PRIMARY)
b1.pack(side="left", padx=5, pady=5)

b2 = ttk.Button(root, text='secondary')
b2.pack(side="left", padx=5, pady=5)

b3 = ttk.Button(root, text='success', bootstyle=SUCCESS)
b3.pack(side="left", padx=5, pady=5)

b4 = ttk.Button(root, text='info', bootstyle=INFO)
b4.pack(side="left", padx=5, pady=5)

b5 = ttk.Button(root, text='warning', bootstyle=WARNING)
b5.pack(side="left", padx=5, pady=5)

b6 = ttk.Button(root, text='danger', bootstyle=DANGER)
b6.pack(side="left", padx=5, pady=5)

b7 = ttk.Button(root, text='light', bootstyle=LIGHT)
b7.pack(side="left", padx=5, pady=5)

b8 = ttk.Button(root, text='dark', bootstyle=DARK)
b8.pack(side="left", padx=5, pady=5)

# Start the main event loop
root.mainloop()