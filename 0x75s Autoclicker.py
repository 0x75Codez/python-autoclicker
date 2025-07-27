import threading
import time
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pynput import keyboard, mouse
import platform
from ttkthemes import ThemedTk
import random

# Global state
spamming = False

kb_controller = keyboard.Controller()
mouse_controller = mouse.Controller()

# Constants for colors and fonts
DARK_BG = '#121212'
PRIMARY_RED = '#e53935'
TEXT_COLOR = '#eeeeee'
GREY_BG = '#222222'
GREY_DARK = '#1b1b1b'
FONT_NAME = 'Segoe UI'
FONT_SIZE = 11

# Tooltip utility
class CreateToolTip(object):
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        widget.bind("<Enter>", self.enter)
        widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def showtip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert") if hasattr(self.widget, "bbox") else (0, 0, 0, 0)
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#333", foreground="white",
                         relief=tk.SOLID, borderwidth=1,
                         font=(FONT_NAME, 9))
        label.pack(ipadx=5, ipady=3)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class MacroClickerApp(ThemedTk):
    def __init__(self):
        super().__init__(theme="black")
        self.title("0x75's MacroClicker - Modern Edition")
        self.geometry("500x570")
        self.minsize(480, 500)
        self.configure(bg=DARK_BG)
        self.attributes("-topmost", True)
        
        # Dark title bar on Windows 10/11
        if platform.system() == "Windows":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                                                           ctypes.byref(ctypes.c_int(1)), 4)
            except Exception:
                pass

        self.style = ttk.Style(self)
        self.style.theme_use("black")

        # Label style
        self.style.configure('TLabel', background=DARK_BG, foreground=TEXT_COLOR, font=(FONT_NAME, FONT_SIZE))
        # Button style with red background and no border
        self.style.configure('TButton',
                             font=(FONT_NAME, FONT_SIZE, 'bold'),
                             foreground=TEXT_COLOR,
                             background=PRIMARY_RED,
                             borderwidth=0,
                             focusthickness=3,
                             focuscolor='none')
        self.style.map('TButton',
                       background=[('active', '#b71c1c'), ('disabled', '#4a0000')])
        # Entry style
        self.style.configure('TEntry',
                             fieldbackground=GREY_BG,
                             foreground=TEXT_COLOR,
                             bordercolor=GREY_DARK)
        # Combobox style with black dropdown and white text
        self.style.configure('TCombobox',
                             fieldbackground=GREY_BG,
                             background=GREY_BG,
                             foreground=TEXT_COLOR,
                             arrowcolor=TEXT_COLOR,
                             bordercolor=GREY_DARK,
                             relief="flat",
                             padding=5)
        self.style.map('TCombobox',
                       fieldbackground=[('readonly', GREY_BG)],
                       background=[('readonly', GREY_BG)],
                       foreground=[('readonly', TEXT_COLOR)])
        # Checkbutton style
        self.style.configure('TCheckbutton', background=DARK_BG, foreground=TEXT_COLOR)
        # Set dropdown listbox colors globally
        self.option_add('*TCombobox*Listbox.background', GREY_BG)
        self.option_add('*TCombobox*Listbox.foreground', TEXT_COLOR)
        self.option_add('*TCombobox*Listbox.selectBackground', PRIMARY_RED)
        self.option_add('*TCombobox*Listbox.selectForeground', TEXT_COLOR)

        self.option_add('*TCombobox*Listbox.font', (FONT_NAME, FONT_SIZE))

        self.input_mode = tk.StringVar(value="Keyboard")
        self.continuous_mode = tk.BooleanVar(value=False)
        self.random_delay_mode = tk.BooleanVar(value=False)
        self.input_hold_mode = tk.BooleanVar(value=False)
        self.delay_ms = tk.StringVar(value="50")
        self.inputs_per_burst = tk.StringVar(value="100")
        self.burst_pause_sec = tk.StringVar(value="2")
        self.key_sequence = tk.StringVar(value="")
        self.mouse_button = tk.StringVar(value="")
        self.input_count = 0
        self.target_input_count = tk.StringVar(value="0")
        self.log_text = None
        self.spam_thread = None
        self.stop_event = threading.Event()

        self.create_widgets()
        self.bind_hotkeys()

        self.after(100, self.update_counter)

    def create_widgets(self):
        padding = {'padx': 10, 'pady': 6}

        ttk.Label(self, text="Input Mode:").grid(row=0, column=0, sticky="w", **padding)
        mode_combo = ttk.Combobox(self, values=["Keyboard", "Mouse"], state="readonly", textvariable=self.input_mode)
        mode_combo.grid(row=0, column=1, sticky="ew", **padding)
        mode_combo.bind("<<ComboboxSelected>>", self.on_mode_change)

        ttk.Label(self, text="Key(s) or Mouse Button(s) to Spam:").grid(row=1, column=0, sticky="w", **padding)

        self.key_entry = ttk.Entry(self, textvariable=self.key_sequence)
        self.key_entry.grid(row=1, column=1, sticky="ew", **padding)

        self.mouse_button_combo = ttk.Combobox(self, textvariable=self.mouse_button,
                                               values=[
                                                   "1 - Left Button",
                                                   "2 - Right Button",
                                                   "3 - Middle Button",
                                                   "4 - X1 Button",
                                                   "5 - X2 Button"],
                                               state="readonly")
        self.mouse_button_combo.grid(row=1, column=1, sticky="ew", **padding)
        self.mouse_button_combo.grid_remove()

        ttk.Label(self, text="Delay Between Inputs (ms):").grid(row=2, column=0, sticky="w", **padding)
        self.delay_entry = ttk.Entry(self, textvariable=self.delay_ms)
        self.delay_entry.grid(row=2, column=1, sticky="ew", **padding)
        CreateToolTip(self.delay_entry, "Delay in milliseconds between each input.")

        self.random_delay_check = ttk.Checkbutton(self, text="Randomize delay ±10ms", variable=self.random_delay_mode)
        self.random_delay_check.grid(row=3, column=0, columnspan=2, sticky="w", **padding)

        # Burst Inputs and Pause Labels/Entries (store original grid info for restoring)
        self.burst_label = ttk.Label(self, text="Inputs Per Burst:")
        self.burst_label.grid(row=4, column=0, sticky="w", **padding)
        self.burst_entry = ttk.Entry(self, textvariable=self.inputs_per_burst)
        self.burst_entry.grid(row=4, column=1, sticky="ew", **padding)
        CreateToolTip(self.burst_entry, "How many inputs to send before pausing.")

        self.pause_label = ttk.Label(self, text="Burst Pause Duration (sec):")
        self.pause_label.grid(row=5, column=0, sticky="w", **padding)
        self.pause_entry = ttk.Entry(self, textvariable=self.burst_pause_sec)
        self.pause_entry.grid(row=5, column=1, sticky="ew", **padding)
        CreateToolTip(self.pause_entry, "Pause duration between bursts.")

        self.continuous_check = ttk.Checkbutton(self, text="Continuous mode (no bursts)", variable=self.continuous_mode,
                                                command=self.toggle_burst_fields)
        self.continuous_check.grid(row=6, column=0, columnspan=2, sticky="w", **padding)
        CreateToolTip(self.continuous_check, "If checked, spams continuously without bursts or pauses.")

        self.input_hold_check = ttk.Checkbutton(self, text="Hold inputs instead of tapping", variable=self.input_hold_mode)
        self.input_hold_check.grid(row=7, column=0, columnspan=2, sticky="w", **padding)
        CreateToolTip(self.input_hold_check, "Hold key/mouse button down instead of pressing/releasing.")

        ttk.Label(self, text="Target Input Count (0 for unlimited):").grid(row=8, column=0, sticky="w", **padding)
        self.target_input_entry = ttk.Entry(self, textvariable=self.target_input_count)
        self.target_input_entry.grid(row=8, column=1, sticky="ew", **padding)

        self.counter_label = ttk.Label(self, text="Inputs Sent: 0")
        self.counter_label.grid(row=9, column=0, columnspan=2, sticky="w", **padding)

        # Buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=10, column=0, columnspan=2, sticky="ew", **padding)
        btn_frame.columnconfigure((0, 1, 2), weight=1)

        self.start_button = ttk.Button(btn_frame, text="Start (F6)", command=self.start_spamming)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=5)

        self.stop_button = ttk.Button(btn_frame, text="Stop (F7)", command=self.stop_spamming, state="disabled")
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=5)

        self.clear_button = ttk.Button(btn_frame, text="Clear Log", command=self.clear_log)
        self.clear_button.grid(row=0, column=2, sticky="ew", padx=5)

        # Log textbox
        self.log_text = tk.Text(self, height=10, bg=GREY_DARK, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
                                font=(FONT_NAME, FONT_SIZE), state="disabled", relief="flat")
        self.log_text.grid(row=11, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))

        # Configure grid weights
        self.grid_rowconfigure(11, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def toggle_burst_fields(self):
        continuous = self.continuous_mode.get()
        if continuous:
            # Hide burst fields
            self.burst_label.grid_remove()
            self.burst_entry.grid_remove()
            self.pause_label.grid_remove()
            self.pause_entry.grid_remove()
        else:
            # Show burst fields back at original grid positions
            self.burst_label.grid(row=4, column=0, sticky="w", padx=10, pady=6)
            self.burst_entry.grid(row=4, column=1, sticky="ew", padx=10, pady=6)
            self.pause_label.grid(row=5, column=0, sticky="w", padx=10, pady=6)
            self.pause_entry.grid(row=5, column=1, sticky="ew", padx=10, pady=6)

    def on_mode_change(self, event=None):
        mode = self.input_mode.get()
        if mode == "Keyboard":
            self.key_entry.grid()
            self.mouse_button_combo.grid_remove()
        else:
            self.key_entry.grid_remove()
            self.mouse_button_combo.grid()

    def bind_hotkeys(self):
        def on_press(key):
            try:
                if key == keyboard.Key.f6:
                    if not spamming:
                        self.start_spamming()
                elif key == keyboard.Key.f7:
                    if spamming:
                        self.stop_spamming()
            except Exception:
                pass

        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def update_counter(self):
        self.counter_label.config(text=f"Inputs Sent: {self.input_count}")
        self.after(100, self.update_counter)

    def start_spamming(self):
        global spamming
        if spamming:
            return

        try:
            delay = int(self.delay_ms.get())
            if delay < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid input", "Delay must be a non-negative integer.")
            return

        if not self.continuous_mode.get():
            try:
                burst = int(self.inputs_per_burst.get())
                if burst <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Invalid input", "Inputs per burst must be a positive integer.")
                return
            try:
                pause = float(self.burst_pause_sec.get())
                if pause < 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Invalid input", "Burst pause duration must be a non-negative number.")
                return

        # Validate target input count
        try:
            target = int(self.target_input_count.get())
            if target < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid input", "Target input count must be zero or a positive integer.")
            return

        # Validate key/mouse button input
        if self.input_mode.get() == "Keyboard":
            keys_str = self.key_sequence.get().strip()
            if not keys_str:
                messagebox.showerror("Invalid input", "Please enter at least one key to spam.")
                return
            keys = [k.strip() for k in keys_str.split(',')]
        else:
            btn_str = self.mouse_button.get()
            if not btn_str:
                messagebox.showerror("Invalid input", "Please select a mouse button to spam.")
                return
            # Map to int button
            try:
                btn_num = int(btn_str.split(' ')[0])
            except Exception:
                messagebox.showerror("Invalid input", "Invalid mouse button selection.")
                return

        # Reset state
        self.input_count = 0
        self.log(f"Starting spamming in {self.input_mode.get()} mode...")
        spamming = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

        self.stop_event.clear()

        # Start spam thread
        if self.input_mode.get() == "Keyboard":
            self.spam_thread = threading.Thread(target=self.spam_keyboard,
                                                args=(keys, delay, self.random_delay_mode.get(),
                                                      self.input_hold_mode.get(),
                                                      target,
                                                      self.continuous_mode.get(),
                                                      int(self.inputs_per_burst.get()) if not self.continuous_mode.get() else None,
                                                      float(self.burst_pause_sec.get()) if not self.continuous_mode.get() else None))
        else:
            self.spam_thread = threading.Thread(target=self.spam_mouse,
                                                args=(btn_num, delay, self.random_delay_mode.get(),
                                                      self.input_hold_mode.get(),
                                                      target,
                                                      self.continuous_mode.get(),
                                                      int(self.inputs_per_burst.get()) if not self.continuous_mode.get() else None,
                                                      float(self.burst_pause_sec.get()) if not self.continuous_mode.get() else None))
        self.spam_thread.daemon = True
        self.spam_thread.start()

    def stop_spamming(self):
        global spamming
        if not spamming:
            return
        spamming = False
        self.stop_event.set()
        self.log("Stopping spamming...")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def spam_keyboard(self, keys, delay_ms, random_delay, hold_mode, target_count, continuous, burst_count, burst_pause):
        try:
            keys_to_press = []
            for k in keys:
                # Support special keys by name from keyboard.Key or just simple chars
                try:
                    # Check if it matches special key attribute
                    key_obj = getattr(keyboard.Key, k.lower())
                except AttributeError:
                    # Fallback to character
                    if len(k) == 1:
                        key_obj = k
                    else:
                        self.log(f"Warning: Unknown key '{k}'. Using as literal.")
                        key_obj = k
                keys_to_press.append(key_obj)

            def send_input(key):
                if hold_mode:
                    kb_controller.press(key)
                    time.sleep(delay_ms / 1000)
                    kb_controller.release(key)
                else:
                    kb_controller.press(key)
                    kb_controller.release(key)

            count = 0
            while not self.stop_event.is_set():
                if target_count != 0 and count >= target_count:
                    break
                if continuous:
                    for key in keys_to_press:
                        send_input(key)
                        count += 1
                        self.input_count = count
                        if target_count != 0 and count >= target_count:
                            break
                        sleeptime = delay_ms / 1000
                        if random_delay:
                            sleeptime += random.uniform(-0.01, 0.01)
                            sleeptime = max(0, sleeptime)
                        time.sleep(sleeptime)
                else:
                    # Burst mode
                    for _ in range(burst_count):
                        for key in keys_to_press:
                            send_input(key)
                            count += 1
                            self.input_count = count
                            if target_count != 0 and count >= target_count:
                                break
                            sleeptime = delay_ms / 1000
                            if random_delay:
                                sleeptime += random.uniform(-0.01, 0.01)
                                sleeptime = max(0, sleeptime)
                            time.sleep(sleeptime)
                        if target_count != 0 and count >= target_count:
                            break
                    self.log(f"Completed burst of {burst_count} inputs, pausing for {burst_pause} seconds.")
                    time.sleep(burst_pause)

            self.log("Keyboard spamming finished.")
        except Exception as e:
            self.log(f"Error during keyboard spamming: {e}")
        finally:
            self.stop_spamming()

    def spam_mouse(self, button_num, delay_ms, random_delay, hold_mode, target_count, continuous, burst_count, burst_pause):
        try:
            btn_map = {
                1: mouse.Button.left,
                2: mouse.Button.right,
                3: mouse.Button.middle,
                4: mouse.Button.x1,
                5: mouse.Button.x2,
            }
            btn = btn_map.get(button_num, mouse.Button.left)

            def send_input():
                if hold_mode:
                    mouse_controller.press(btn)
                    time.sleep(delay_ms / 1000)
                    mouse_controller.release(btn)
                else:
                    mouse_controller.click(btn)

            count = 0
            while not self.stop_event.is_set():
                if target_count != 0 and count >= target_count:
                    break
                if continuous:
                    send_input()
                    count += 1
                    self.input_count = count
                    sleeptime = delay_ms / 1000
                    if random_delay:
                        sleeptime += random.uniform(-0.01, 0.01)
                        sleeptime = max(0, sleeptime)
                    time.sleep(sleeptime)
                else:
                    for _ in range(burst_count):
                        send_input()
                        count += 1
                        self.input_count = count
                        if target_count != 0 and count >= target_count:
                            break
                        sleeptime = delay_ms / 1000
                        if random_delay:
                            sleeptime += random.uniform(-0.01, 0.01)
                            sleeptime = max(0, sleeptime)
                        time.sleep(sleeptime)
                    self.log(f"Completed burst of {burst_count} inputs, pausing for {burst_pause} seconds.")
                    time.sleep(burst_pause)

            self.log("Mouse spamming finished.")
        except Exception as e:
            self.log(f"Error during mouse spamming: {e}")
        finally:
            self.stop_spamming()


if __name__ == "__main__":
    app = MacroClickerApp()
    app.mainloop()
