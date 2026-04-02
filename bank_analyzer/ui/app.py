# * Main application window

import ttkbootstrap as ttk

# * Application

class App(ttk.Window):
    def __init__(self) -> None:
        super().__init__(title="Bank Statement Analyzer")
        ttk.Label(self, text="Hello World").pack(pady=20)

# * Entry point

def run() -> None:
    app = App()
    app.mainloop()
