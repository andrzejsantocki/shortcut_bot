import tkinter as tk
import json
import logging
import time
from pynput import keyboard
import threading
import os
import sys
from tkinter import messagebox
import traceback
import textwrap
import subprocess

# --- Monkey-patch tk.Tk to log window creation ---
original_tk_init = tk.Tk.__init__
def patched_tk_init(self, *args, **kwargs):
    logging.warning("A new tk.Tk() window is being created.")
    logging.warning("Stack trace:\n" + "".join(traceback.format_stack()))
    original_tk_init(self, *args, **kwargs)
tk.Tk.__init__ = patched_tk_init
# --- End of patch ---

# --- Logging Configuration ---
DEBUG = True
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='shortcuts_app.log',
    filemode='w' # Overwrite the log file on each run
)
if DEBUG:
    logging.info("Debug mode is ON.")

# --- Configuration ---
HOTKEY = "<ctrl>+<shift>+h"
LOCK_FILE = "shortcuts_app.lock"
WRAP_AT_CHARS = 40

class ShortcutApp:
    def __init__(self, root):
        logging.info("Application starting.")
        self.root = root
        self.root.title("Shortcut Viewer")
        self.root.configure(bg='black')
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self.toggle_window)

        # Set up the main frame
        main_frame = tk.Frame(root, bg='black')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # App list
        self.app_list = tk.Listbox(main_frame, width=20, bg='black', fg='white', selectbackground='gray30', selectforeground='white', highlightthickness=0, borderwidth=0)
        self.app_list.pack(side=tk.LEFT, fill=tk.Y)
        self.app_list.bind("<<ListboxSelect>>", self.show_shortcuts)
        self.app_list.bind("<MouseWheel>", self.on_app_list_scroll)

        # Shortcut display
        self.shortcut_display = tk.Text(main_frame, width=40, wrap=tk.WORD, bg='black', fg='white', highlightthickness=0, borderwidth=0)
        self.shortcut_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self.shortcut_display.bind("<MouseWheel>", self.on_shortcut_display_scroll)

        # Button frame
        button_frame = tk.Frame(root, bg='black')
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Close button
        close_button = tk.Button(button_frame, text="Close", command=self.close_app, bg='gray20', fg='white', borderwidth=0, highlightthickness=0)
        close_button.pack(side=tk.RIGHT)

        # Sync button
        sync_button = tk.Button(button_frame, text="Sync", command=self.manual_sync_and_refresh, bg='gray20', fg='white', borderwidth=0, highlightthickness=0)
        sync_button.pack(side=tk.RIGHT, padx=(0, 5))

        # Agent button
        agent_button = tk.Button(button_frame, text="Agent", command=self.run_agent_manual_mode, bg='gray20', fg='white', borderwidth=0, highlightthickness=0)
        agent_button.pack(side=tk.RIGHT, padx=(0, 5))

        self.run_sync_script()  # Initial sync on startup
        self.shortcuts = self.load_shortcuts_from_local()
        self.populate_apps()
        self.resizable_labels = []
        self.item_frames = []
        logging.info("Application initialized.")

    def run_sync_script(self):
        logging.info("Executing sync_cloud_to_local.py script.")
        try:
            subprocess.run([sys.executable, "sync_cloud_to_local.py"], check=True, capture_output=True, text=True)
            logging.info("Sync script finished successfully.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Sync script failed with error: {e.stderr}")
        except FileNotFoundError:
            logging.error("Sync script 'sync_cloud_to_local.py' not found.")

    def manual_sync_and_refresh(self):
        logging.info("Manual sync triggered by user.")
        self.run_sync_script()
        self.shortcuts = self.load_shortcuts_from_local()
        self.populate_apps()
        self.shortcut_display.config(state=tk.NORMAL)
        self.shortcut_display.delete(1.0, tk.END)
        self.shortcut_display.config(state=tk.DISABLED)
        messagebox.showinfo("Sync Complete", "Successfully synced with the cloud.", parent=self.root)
        logging.info("Manual sync and UI refresh complete.")

    def run_agent_manual_mode(self):
        logging.info("Agent button pressed. Launching agent.py in manual mode.")
        self.root.withdraw() # Hide the app while agent.py runs

        def run_agent():
            python_exe_path = sys.executable.replace("pythonw.exe", "python.exe")
            if not os.path.exists(python_exe_path):
                logging.error(f"python.exe not found at expected path: {python_exe_path}. Cannot launch agent.py.")
                messagebox.showerror("Error", "python.exe not found. Cannot launch agent.py.", parent=self.root)
                return

            try:
                subprocess.run([python_exe_path, "agent.py", "manual"], check=True, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
                logging.info("agent.py manual mode finished.")
            except subprocess.CalledProcessError as e:
                logging.error(f"agent.py manual mode failed with error: {e}")
            finally:
                self.root.deiconify()
                self.shortcuts = self.load_shortcuts_from_local()
                self.populate_apps()
                self.app_list.selection_clear(0, tk.END)
                self.shortcut_display.config(state=tk.NORMAL)
                self.shortcut_display.delete(1.0, tk.END)
                self.shortcut_display.config(state=tk.DISABLED)

        agent_thread = threading.Thread(target=run_agent, daemon=True)
        agent_thread.start()

    def toggle_window(self):
        logging.info("Toggling window.")
        if self.root.winfo_viewable():
            logging.info("Hiding window.")
            self.root.withdraw()
        else:
            logging.info("Showing window and reloading shortcuts.")
            self.shortcuts = self.load_shortcuts_from_local()
            self.populate_apps()
            self.app_list.selection_clear(0, tk.END)
            self.shortcut_display.config(state=tk.NORMAL)
            self.shortcut_display.delete(1.0, tk.END)
            self.shortcut_display.config(state=tk.DISABLED)
            self.root.deiconify()

    def close_app(self):
        logging.info("Closing application.")
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        self.root.destroy()

    def on_app_list_scroll(self, event):
        self.app_list.yview_scroll(-1 * (event.delta // 120), "units")

    def on_shortcut_display_scroll(self, event):
        self.shortcut_display.yview_scroll(-1 * (event.delta // 120), "units")
        return "break"

    def bind_all(self, widget, event, callback):
        widget.bind(event, callback)
        for child in widget.winfo_children():
            self.bind_all(child, event, callback)

    def load_shortcuts_from_local(self):
        logging.info("Loading shortcuts from local shortcuts.json.")
        try:
            with open('shortcuts.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                logging.info("Successfully loaded shortcuts from local file.")
                return data
        except FileNotFoundError:
            logging.error("shortcuts.json not found. Returning empty dictionary.")
            messagebox.showerror("Error", "shortcuts.json not found. Please ensure the file exists.", parent=self.root)
            return {"Error": "shortcuts.json not found."}
        except json.JSONDecodeError:
            logging.error("Failed to decode shortcuts.json. Returning empty dictionary.")
            messagebox.showerror("Error", "Could not parse shortcuts.json. The file may be corrupted.", parent=self.root)
            return {"Error": "Could not parse shortcuts.json."}
        except Exception as e:
            logging.error(f"An unexpected error occurred while loading local shortcuts: {e}")
            return {"Error": str(e)}

    def populate_apps(self):
        logging.info("Populating app list.")
        self.app_list.delete(0, tk.END)
        for app_name in self.shortcuts.keys():
            self.app_list.insert(tk.END, app_name)

    def show_shortcuts(self, event=None):
        selection = self.app_list.curselection()
        if not selection:
            return

        app_name = self.app_list.get(selection[0])
        shortcuts = self.shortcuts.get(app_name, [])

        self.shortcut_display.config(state=tk.NORMAL)
        self.shortcut_display.delete(1.0, tk.END)

        if isinstance(shortcuts, list):
            for i, item in enumerate(shortcuts, 1):
                wrapper_frame = tk.Frame(self.shortcut_display, bg="black", padx=0, pady=5)
                item_frame = tk.Frame(wrapper_frame, bg="gray10", relief="solid", borderwidth=1)
                item_frame.pack(fill="both", expand=True)

                def create_wrapped_label(parent, key_text, key_color, value_text):
                    frame = tk.Frame(parent, bg="gray10")
                    key_label = tk.Label(frame, text=key_text, bg="gray10", fg=key_color, font=("Segoe UI", 9, "bold"))
                    key_label.pack(side="left", anchor="n")
                    
                    value_text_str = str(value_text)
                    wrapped_value = '\n'.join(textwrap.wrap(value_text_str, width=WRAP_AT_CHARS))
                    
                    value_label = tk.Label(frame, text=wrapped_value, bg="gray10", fg="white", font=("Segoe UI", 9), justify="left")
                    value_label.pack(side="left", fill="x", expand=True, anchor="w")
                    frame.pack(anchor="w", padx=5, pady=2, fill="x")

                if 'shortcut' in item:
                    create_wrapped_label(item_frame, f"Shortcut {i}:", "magenta", item['shortcut'])
                if 'command' in item:
                    create_wrapped_label(item_frame, f"Command {i}:", "magenta", item['command'])

                usage = item.get('usage') or item.get('usage example')
                if usage:
                    create_wrapped_label(item_frame, "Usage:", "yellow", usage)

                description = item.get('action') or item.get('description')
                if description:
                    create_wrapped_label(item_frame, "Description:", "cyan", description)

                self.shortcut_display.window_create(tk.END, window=wrapper_frame)
                self.shortcut_display.insert(tk.END, "\n")
                self.bind_all(item_frame, "<MouseWheel>", self.on_shortcut_display_scroll)
        else:
            wrapped_shortcuts = '\n'.join(textwrap.wrap(str(shortcuts), width=WRAP_AT_CHARS))
            self.shortcut_display.insert(tk.END, wrapped_shortcuts)
            
        self.shortcut_display.config(state=tk.DISABLED)

def is_pid_running(pid):
    """Check if a process with the given PID is running."""
    if pid is None:
        return False
    try:
        pid = int(pid)
        if pid <= 0:
            return False
    except (ValueError, TypeError):
        return False

    if sys.platform.startswith('win'):
        try:
            # Use CREATE_NO_WINDOW to prevent a console window from flashing.
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            # If the PID is in the output, the process is running.
            return str(pid) in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            # CalledProcessError occurs if tasklist returns a non-zero exit code (e.g., process not found)
            # FileNotFoundError if tasklist is not on the system's PATH.
            return False
    else:  # for Linux/macOS
        try:
            # os.kill with signal 0 doesn't kill the process but checks for its existence.
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True

def on_hotkey_press():
    logging.info("Hotkey pressed.")
    app.toggle_window()

def start_hotkey_listener():
    logging.info("Hotkey listener started.")
    with keyboard.GlobalHotKeys({
        HOTKEY: on_hotkey_press
    }) as h:
        h.join()

# --- Application Setup ---
root = tk.Tk()
root.withdraw()

if os.path.exists(LOCK_FILE):
    pid = None
    try:
        with open(LOCK_FILE, "r") as f:
            pid_str = f.read().strip()
            if pid_str:
                pid = int(pid_str)
    except (IOError, ValueError) as e:
        logging.warning(f"Could not read or parse PID from lock file: {e}")
        pid = None # Treat as stale

    if pid and is_pid_running(pid):
        logging.error("Another instance is already running.")
        messagebox.showerror("Error", "Another instance of the application is already running.", parent=root)
        root.destroy()
        sys.exit(1)
    else:
        if pid:
            logging.info(f"Stale lock file for PID {pid} found. Removing it.")
        else:
            logging.info(f"Stale lock file found (no valid PID). Removing it.")
        try:
            os.remove(LOCK_FILE)
        except OSError as e:
            logging.error(f"Error removing stale lock file: {e}")


with open(LOCK_FILE, "w") as f:
    f.write(str(os.getpid()))

logging.info("Starting application.")
app = ShortcutApp(root)

# --- Main Execution Block ---
if __name__ == "__main__":
    listener_thread = threading.Thread(target=start_hotkey_listener, daemon=True)
    listener_thread.start()

    logging.info("Application main loop started.")
    root.mainloop()
    logging.info("Application closed.")
