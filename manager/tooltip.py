# manager/tooltip.py
import tkinter as tk

class ToolTip:
    """Attaches a borderless hovering hint window to one or more Tkinter widgets."""
    def __init__(self, widgets, text):
        # Handle a single widget or a list/tuple of widgets uniformly
        self.widgets = widgets if isinstance(widgets, (list, tuple)) else [widgets]
        self.text = text
        self.tip_window = None

        # Bind mouse enter/leave events to every widget passed in
        for widget in self.widgets:
            widget.bind("<Enter>", self.show_tip)
            widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event):
        if self.tip_window or not self.text:
            return

        # Get the specific widget that triggered the hover event
        active_widget = event.widget

        # Calculate screen coordinates relative to the widget bounding box
        x = active_widget.winfo_rootx() + 25
        y = active_widget.winfo_rooty() + active_widget.winfo_height() + 5

        self.tip_window = tw = tk.Toplevel(active_widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(tw, text=self.text, justify="left", background="#FFFFE1",
                         relief="solid", borderwidth=1, font=("TkDefaultFont", 9, "normal"), padx=6, pady=4)
        label.pack(fill="both")

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

def bind_tooltip(widgets, text):
    """Utility wrapper to attach a single hover string description to widgets safely."""
    return ToolTip(widgets, text)
