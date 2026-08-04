"""
PinkCat OCR Sort - Main entry point
Run this file to launch the app (no console window).
"""
import sys
import os
import traceback

# Make sure local modules can be found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        from ui.app import MainWindow
        app = MainWindow()
        app.mainloop()
    except Exception:
        # .pyw has no console, so an uncaught exception here would otherwise
        # just make the window vanish with no visible error. Write it to a
        # log file next to this script and show it in a message box.
        error_text = traceback.format_exc()
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_log.txt")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(error_text)
        except Exception:
            pass
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("PinkCat OCR Sort — Startup error",
                                  f"{error_text}\n\nSaved to: {log_path}")
        except Exception:
            pass
