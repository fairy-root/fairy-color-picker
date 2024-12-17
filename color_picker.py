import customtkinter as ctk
import pyperclip
from datetime import datetime
import json
import os
import keyboard
import random
import re
import pystray
from PIL import Image
import threading
import time
import win32gui
import win32con
import sys
import tempfile
import atexit

def show_already_running_message():
    root = ctk.CTk()
    root.withdraw()  # Hide the main window
    
    dialog = ctk.CTkToplevel(root)
    dialog.title("Fairy Color Picker")
    dialog.geometry("300x100")
    
    # Center the dialog
    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()
    x = (screen_width - 300) // 2
    y = (screen_height - 100) // 2
    dialog.geometry(f"300x100+{x}+{y}")
    
    label = ctk.CTkLabel(dialog, text="Fairy Color Picker is already running in the tray!")
    label.pack(pady=20)
    
    def close_dialog():
        dialog.destroy()
        root.destroy()
        sys.exit()
    
    button = ctk.CTkButton(dialog, text="OK", command=close_dialog)
    button.pack(pady=5)
    
    dialog.protocol('WM_DELETE_WINDOW', close_dialog)
    dialog.attributes('-topmost', True)
    
    root.mainloop()

def check_running_instance():
    lock_file = os.path.join(tempfile.gettempdir(), 'color_picker.lock')
    
    if os.path.exists(lock_file):
        try:
            # Check if the process is actually running
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Try to find the process
            import psutil
            if psutil.pid_exists(pid):
                show_already_running_message()
                return False
            else:
                # Process doesn't exist, remove the stale lock file
                os.remove(lock_file)
        except (ValueError, FileNotFoundError, PermissionError):
            # If there's any error reading the file, remove it
            try:
                os.remove(lock_file)
            except:
                pass
    
    # Create lock file with current process ID
    try:
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        
        # Register cleanup function
        def cleanup():
            try:
                os.remove(lock_file)
            except:
                pass
        atexit.register(cleanup)
        
        return True
    except:
        return True  # If we can't create the lock file, still allow the app to run

class ColorPicker(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("Fairy Color Picker")
        self.geometry("750x685")
        self.resizable(False, False)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Variables
        self.red_var = ctk.IntVar(value=0)
        self.green_var = ctk.IntVar(value=0)
        self.blue_var = ctk.IntVar(value=0)
        self.color_input_var = ctk.StringVar(value="")
        self.history = []
        self.history_file = "color_history.json"
        self.config_file = "config.json"
        self.view_mode = ctk.StringVar(value="list")  # 'list' or 'grid'
        self.shortcut_presets = [
            "ctrl+shift+p",
            "ctrl+alt+c",
            "ctrl+shift+c",
            "alt+shift+c",
            "ctrl+alt+p"
        ]
        
        # Load config or set default shortcut
        self.load_config()
        
        # Window state tracking
        self.was_in_tray = False  # Track if window was in tray
        self.is_minimized = False
        
        # System tray setup
        self.setup_system_tray()
        self.setup_keyboard_shortcut()
        
        # Protocol handler for window close button
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        
        self.create_widgets()
        self.load_history()
        self.set_initial_color()
        
    def setup_system_tray(self):
        # Create a simple icon with the default color (red)
        self.icon_image = Image.new('RGB', (64, 64), color='red')
        
        def create_shortcut_handler(preset):
            return lambda: self.change_shortcut(preset)
            
        def create_shortcut_checker(preset):
            return lambda item: self.shortcut == preset
        
        # Create shortcut submenu
        shortcut_menu = []
        for preset in self.shortcut_presets:
            shortcut_menu.append(
                pystray.MenuItem(
                    preset,
                    create_shortcut_handler(preset),
                    radio=True,
                    checked=create_shortcut_checker(preset)
                )
            )

        # Create system tray icon with menu
        self.icon = pystray.Icon(
            "color_picker",
            self.icon_image,
            "Fairy Color Picker",
            menu=pystray.Menu(
                pystray.MenuItem("Pick Color", self.start_color_pick),
                pystray.MenuItem("Show Window", self.show_window),
                pystray.MenuItem("Keyboard Shortcut", pystray.Menu(*shortcut_menu)),
                pystray.MenuItem("Exit", self.quit_app)
            )
        )
        
        threading.Thread(target=self.icon.run, daemon=True).start()

    def setup_keyboard_shortcut(self):
        keyboard.add_hotkey(self.shortcut, self.start_color_pick)

    def start_color_pick(self):
        # Don't show main window, directly start color picking
        self.pick_color_from_screen()

    def pick_color_from_screen(self):
        try:
            import pyautogui
            
            # Store current window state
            self.was_in_tray = self.is_minimized
            
            # Create a small toplevel window for instructions
            instruction = ctk.CTkToplevel()
            instruction.geometry("300x100")
            instruction.title("Fairy Color Picker")
            instruction.attributes('-topmost', True)
            
            # Center the instruction window
            screen_width = instruction.winfo_screenwidth()
            screen_height = instruction.winfo_screenheight()
            x = (screen_width - 300) // 2
            y = (screen_height - 100) // 2
            instruction.geometry(f"300x100+{x}+{y}")
            
            label = ctk.CTkLabel(instruction, 
                text="Move mouse to desired color and press Space.\nPress Esc to cancel.")
            label.pack(pady=20)
            
            def check_keys():
                if keyboard.is_pressed('space'):
                    x, y = pyautogui.position()
                    color = pyautogui.pixel(x, y)
                    self.red_var.set(color[0])
                    self.green_var.set(color[1])
                    self.blue_var.set(color[2])
                    self.update_color()
                    instruction.destroy()
                    # Always show window after picking color
                    self.show_window()
                elif keyboard.is_pressed('escape'):
                    instruction.destroy()
                    # Return to previous state
                    if self.was_in_tray:
                        self.hide_window()
                    else:
                        self.show_window()
                else:
                    instruction.after(100, check_keys)
            
            check_keys()
            
        except Exception as e:
            error_window = ctk.CTkToplevel()
            error_window.geometry("300x100")
            error_window.title("Error")
            error_window.attributes('-topmost', True)
            
            # Center the error window
            screen_width = error_window.winfo_screenwidth()
            screen_height = error_window.winfo_screenheight()
            x = (screen_width - 300) // 2
            y = (screen_height - 100) // 2
            error_window.geometry(f"300x100+{x}+{y}")
            
            error_label = ctk.CTkLabel(error_window, 
                text=f"Error picking color:\n{str(e)}")
            error_label.pack(pady=20)
            
            def close_error():
                error_window.destroy()
                # Return to previous state
                if self.was_in_tray:
                    self.hide_window()
                else:
                    self.show_window()
            
            error_window.after(3000, close_error)  # Close error after 3 seconds

    def show_window(self):
        if self.is_minimized:
            self.deiconify()
            self.is_minimized = False
            # Bring window to front and give it focus
            self.lift()
            self.focus_force()
            try:
                hwnd = self.winfo_id()
                # Try to force the window to front
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass  # Fail silently if window operations fail

    def hide_window(self):
        self.withdraw()
        self.is_minimized = True

    def on_close(self):
        self.hide_window()

    def quit_app(self):
        self.icon.stop()
        self.quit()

    def create_widgets(self):
        # Color preview frame
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.color_preview = ctk.CTkFrame(self.preview_frame, width=360, height=100)
        self.color_preview.pack(pady=10)
        
        # Shades frame
        self.shades_frame = ctk.CTkFrame(self.preview_frame)
        self.shades_frame.pack(fill="x", padx=10, pady=10)
        
        # Create a frame to center the shade buttons
        self.shades_container = ctk.CTkFrame(self.shades_frame)
        self.shades_container.pack(expand=True)
        
        # Create shade buttons
        self.shade_buttons = []
        for i in range(5):
            shade_button = ctk.CTkButton(self.shades_container, text="", width=50, height=25,
                                       command=lambda x=i: self.copy_shade(x))
            shade_button.grid(row=0, column=i, padx=2, pady=2)
            self.shade_buttons.append(shade_button)
        
        # Color picker button
        self.picker_button = ctk.CTkButton(self.preview_frame, text="Pick Color from Screen",
                                         command=self.start_color_pick)
        self.picker_button.pack(pady=10)
        
        # Color input frame
        self.input_frame = ctk.CTkFrame(self.preview_frame)
        self.input_frame.pack(fill="x", padx=10, pady=5)
        
        self.color_input = ctk.CTkEntry(self.input_frame, placeholder_text="Enter HEX, RGB, or values (e.g. #FF0000, 255,0,0)",
                                      textvariable=self.color_input_var)
        self.color_input.pack(side="left", padx=5, fill="x", expand=True)
        
        self.update_color_button = ctk.CTkButton(self.input_frame, text="Update",
                                               command=self.update_from_input, width=70)
        self.update_color_button.pack(side="right", padx=5)
        
        # Add description label
        self.input_description = ctk.CTkLabel(self.preview_frame, 
                                            text="  RGB: rgb(255,0,0), HEX: #FF0000, Values: 255,0,0",
                                            text_color="Gray",
                                            wraplength=300,
                                            justify="left",
                                            anchor="w")
        self.input_description.pack(padx=10, pady=(0, 5), anchor="w", fill="x")
        
        # Sliders frame
        self.sliders_frame = ctk.CTkFrame(self)
        self.sliders_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        # RGB Sliders
        # Red slider and label
        self.red_frame = ctk.CTkFrame(self.sliders_frame)
        self.red_frame.pack(pady=10, padx=20, fill="x")
        self.red_label = ctk.CTkLabel(self.red_frame, text="Red:")
        self.red_label.pack(side="left", padx=(0, 10))
        self.red_slider = ctk.CTkSlider(self.red_frame, from_=0, to=255, variable=self.red_var,
                                      command=self.update_color, width=300,
                                      progress_color="red", button_color="red", button_hover_color="#cc0000")
        self.red_slider.pack(side="left", padx=(0, 10))
        self.red_value_label = ctk.CTkLabel(self.red_frame, text=str(self.red_var.get()))
        self.red_value_label.pack(side="left")

        # Green slider and label
        self.green_frame = ctk.CTkFrame(self.sliders_frame)
        self.green_frame.pack(pady=10, padx=20, fill="x")
        self.green_label = ctk.CTkLabel(self.green_frame, text="Green:")
        self.green_label.pack(side="left", padx=(0, 10))
        self.green_slider = ctk.CTkSlider(self.green_frame, from_=0, to=255, variable=self.green_var,
                                        command=self.update_color, width=300,
                                        progress_color="green", button_color="green", button_hover_color="#00cc00")
        self.green_slider.pack(side="left", padx=(0, 10))
        self.green_value_label = ctk.CTkLabel(self.green_frame, text=str(self.green_var.get()))
        self.green_value_label.pack(side="left")

        # Blue slider and label
        self.blue_frame = ctk.CTkFrame(self.sliders_frame)
        self.blue_frame.pack(pady=10, padx=20, fill="x")
        self.blue_label = ctk.CTkLabel(self.blue_frame, text="Blue:")
        self.blue_label.pack(side="left", padx=(0, 10))
        self.blue_slider = ctk.CTkSlider(self.blue_frame, from_=0, to=255, variable=self.blue_var,
                                       command=self.update_color, width=300,
                                       progress_color="blue", button_color="blue", button_hover_color="#0000cc")
        self.blue_slider.pack(side="left", padx=(0, 10))
        self.blue_value_label = ctk.CTkLabel(self.blue_frame, text=str(self.blue_var.get()))
        self.blue_value_label.pack(side="left")
        
        # Color codes
        self.hex_label = ctk.CTkLabel(self.sliders_frame, text="HEX: #000000")
        self.hex_label.pack(pady=10)
        
        self.rgb_label = ctk.CTkLabel(self.sliders_frame, text="RGB: (0, 0, 0)")
        self.rgb_label.pack(pady=5)
        
        # Copy buttons frame
        self.copy_frame = ctk.CTkFrame(self.sliders_frame)
        self.copy_frame.pack(pady=5)
        
        self.copy_hex_button = ctk.CTkButton(self.copy_frame, text="Copy HEX",
                                           command=self.copy_hex, width=70)
        self.copy_hex_button.grid(row=0, column=0, padx=5, pady=5)
        
        self.copy_rgb_button = ctk.CTkButton(self.copy_frame, text="Copy RGB",
                                           command=self.copy_rgb, width=70)
        self.copy_rgb_button.grid(row=0, column=1, padx=5, pady=5)
        
        self.copy_values_button = ctk.CTkButton(self.copy_frame, text="Copy Values",
                                              command=self.copy_values, width=70)
        self.copy_values_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Save to history button
        self.save_button = ctk.CTkButton(self.sliders_frame, text="Save to History",
                                       command=self.save_to_history)
        self.save_button.pack(pady=5)
        
        # History section
        self.history_frame = ctk.CTkFrame(self)
        self.history_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew")
        
        # View mode selection
        self.view_mode_frame = ctk.CTkFrame(self.history_frame)
        self.view_mode_frame.pack(fill="x", padx=10, pady=5)
        
        self.list_view_btn = ctk.CTkButton(self.view_mode_frame, text="List View",
                                         command=lambda: self.change_view_mode("list"))
        self.list_view_btn.pack(side="left", padx=5)
        
        self.grid_view_btn = ctk.CTkButton(self.view_mode_frame, text="Grid View",
                                         command=lambda: self.change_view_mode("grid"))
        self.grid_view_btn.pack(side="left", padx=5)
        
        # History content frame
        self.history_content = ctk.CTkScrollableFrame(self.history_frame, height=200)
        self.history_content.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Clear history button
        self.clear_history_button = ctk.CTkButton(self.history_frame, text="Clear History",
                                                command=self.clear_history)
        self.clear_history_button.pack(pady=10)
        
    def update_color(self, _=None):
        r, g, b = self.red_var.get(), self.green_var.get(), self.blue_var.get()
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        
        # Update preview
        self.color_preview.configure(fg_color=hex_color)
        
        # Update shades
        self.update_shades(r, g, b)
        
        # Update value labels
        self.red_value_label.configure(text=str(r))
        self.green_value_label.configure(text=str(g))
        self.blue_value_label.configure(text=str(b))
        
        # Update color code labels
        self.hex_label.configure(text=f"HEX: {hex_color}")
        self.rgb_label.configure(text=f"RGB: ({r}, {g}, {b})")
        
        # Update tray icon color
        self.icon_image = Image.new('RGB', (64, 64), color=(r, g, b))
        self.icon.icon = self.icon_image
    
    def update_shades(self, r, g, b):
        # Generate shades (darker to lighter)
        shades = []
        for i in range(5):
            factor = 0.5 + (i * 0.25)  # 0.5, 0.75, 1.0, 1.25, 1.5
            new_r = min(255, int(r * factor))
            new_g = min(255, int(g * factor))
            new_b = min(255, int(b * factor))
            hex_color = f"#{new_r:02x}{new_g:02x}{new_b:02x}"
            shades.append((hex_color, (new_r, new_g, new_b)))
        
        # Update shade buttons
        for i, (hex_color, _) in enumerate(shades):
            self.shade_buttons[i].configure(fg_color=hex_color)
            self.shade_buttons[i].hex_color = hex_color
            self.shade_buttons[i].rgb_values = _
    
    def copy_shade(self, index):
        hex_color = self.shade_buttons[index].hex_color
        r, g, b = self.shade_buttons[index].rgb_values
        
        # Update sliders and preview
        self.red_var.set(r)
        self.green_var.set(g)
        self.blue_var.set(b)
        self.update_color()
        
        # Copy hex color to clipboard
        pyperclip.copy(hex_color)
    
    def copy_hex(self):
        hex_color = f"#{self.red_var.get():02x}{self.green_var.get():02x}{self.blue_var.get():02x}"
        pyperclip.copy(hex_color)
        
    def copy_rgb(self):
        rgb = f"rgb({self.red_var.get()}, {self.green_var.get()}, {self.blue_var.get()})"
        pyperclip.copy(rgb)
        
    def copy_values(self):
        values = f"{self.red_var.get()}, {self.green_var.get()}, {self.blue_var.get()}"
        pyperclip.copy(values)
        
    def save_to_history(self):
        hex_color = f"#{self.red_var.get():02x}{self.green_var.get():02x}{self.blue_var.get():02x}"
        color_data = {
            "color": hex_color,
            "rgb": [self.red_var.get(), self.green_var.get(), self.blue_var.get()],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Check if color exists in history
        color_exists = False
        for i, item in enumerate(self.history):
            if item["color"] == hex_color:
                # Update timestamp of existing color and move it to the end
                self.history.pop(i)
                self.history.append(color_data)
                color_exists = True
                break
        
        # Add new color if it doesn't exist
        if not color_exists:
            self.history.append(color_data)
            
        self.save_history()
        self.update_history_display()
        
    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
                self.update_history_display()
            except:
                self.history = []
                
    def save_history(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f)
            
    def update_history_display(self):
        # Clear existing content
        for widget in self.history_content.winfo_children():
            widget.destroy()
            
        if self.view_mode.get() == "list":
            for i, color_data in enumerate(reversed(self.history)):
                color_frame = ctk.CTkFrame(self.history_content)
                color_frame.pack(fill="x", padx=5, pady=2)
                
                # Color preview
                preview = ctk.CTkFrame(color_frame, width=50, height=25)
                preview.configure(fg_color=color_data["color"])
                preview.pack(side="left", padx=5, pady=5)
                preview.bind("<Button-1>", lambda e, rgb=color_data["rgb"]: self.set_color_values(*rgb))
                
                # Color information
                info_text = f"HEX: {color_data['color']} | RGB: {color_data['rgb']} | {color_data['timestamp']}"
                info_label = ctk.CTkLabel(color_frame, text=info_text)
                info_label.pack(side="left", padx=5)
                info_label.bind("<Button-1>", lambda e, rgb=color_data["rgb"]: self.set_color_values(*rgb))
                
                # Copy button
                copy_btn = ctk.CTkButton(color_frame, text="Copy", width=60,
                                       command=lambda c=color_data["color"]: pyperclip.copy(c))
                copy_btn.pack(side="right", padx=5)
        else:  # Grid view
            grid_frame = ctk.CTkFrame(self.history_content)
            grid_frame.pack(fill="both", expand=True)
            
            # Configure grid columns to be evenly spaced
            for i in range(6):  
                grid_frame.grid_columnconfigure(i, weight=1)
            
            for i, color_data in enumerate(reversed(self.history)):
                row = i // 6  
                col = i % 6
                
                # Create a container frame for each color cell to help with centering
                container = ctk.CTkFrame(grid_frame, fg_color="transparent")
                container.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
                container.grid_columnconfigure(0, weight=1)  # Center the color cell horizontally
                
                color_cell = ctk.CTkFrame(container)
                color_cell.grid(row=0, column=0)
                
                # Color preview
                preview = ctk.CTkFrame(color_cell, width=80, height=60)
                preview.configure(fg_color=color_data["color"])
                preview.pack(padx=5, pady=5)
                preview.bind("<Button-1>", lambda e, rgb=color_data["rgb"]: self.set_color_values(*rgb))
                
                # RGB values
                rgb_text = f"RGB: {color_data['rgb']}"
                rgb_label = ctk.CTkLabel(color_cell, text=rgb_text)
                rgb_label.pack(pady=2)
                rgb_label.bind("<Button-1>", lambda e, rgb=color_data["rgb"]: self.set_color_values(*rgb))
                
                # Copy button
                copy_btn = ctk.CTkButton(color_cell, text="Copy", width=60,
                                       command=lambda c=color_data["color"]: pyperclip.copy(c))
                copy_btn.pack(pady=2)
        
    def change_view_mode(self, mode):
        self.view_mode.set(mode)
        self.update_history_display()
        
    def clear_history(self):
        self.history = []
        self.save_history()
        self.update_history_display()
        
    def set_initial_color(self):
        if self.history:
            # Use the last color from history
            last_color = self.history[-1]
            if 'rgb' in last_color:
                r, g, b = last_color['rgb']
            else:
                # Convert hex to rgb for older history entries
                hex_color = last_color['color'].lstrip('#')
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
        else:
            # Generate random color
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
        
        self.red_var.set(r)
        self.green_var.set(g)
        self.blue_var.set(b)
        self.update_color()
    
    def update_from_input(self):
        color_text = self.color_input_var.get().strip()
        
        # Try parsing as HEX
        hex_match = re.match(r'^#?([A-Fa-f0-9]{6})$', color_text)
        if hex_match:
            hex_color = hex_match.group(1)
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            self.set_color_values(r, g, b)
            return
        
        # Try parsing as RGB
        rgb_match = re.match(r'^(?:rgb)?\(?(\d+),\s*(\d+),\s*(\d+)\)?$', color_text)
        if rgb_match:
            r, g, b = map(int, rgb_match.groups())
            if all(0 <= x <= 255 for x in (r, g, b)):
                self.set_color_values(r, g, b)
                return
        
        # Try parsing as space/comma-separated values
        try:
            values = [int(x.strip()) for x in color_text.split(',')]
            if len(values) == 3 and all(0 <= x <= 255 for x in values):
                r, g, b = values
                self.set_color_values(r, g, b)
                return
        except ValueError:
            pass
        
        # Show error if no valid format was found
        self.show_error("Invalid color format. Please use HEX (#RRGGBB), RGB (r,g,b), or comma-separated values.")
    
    def set_color_values(self, r, g, b):
        self.red_var.set(r)
        self.green_var.set(g)
        self.blue_var.set(b)
        self.update_color()
    
    def show_error(self, message):
        error_window = ctk.CTkToplevel(self)
        error_window.geometry("400x100")
        error_window.title("Error")
        error_window.attributes('-topmost', True)
        
        error_label = ctk.CTkLabel(error_window, text=message, wraplength=350)
        error_label.pack(pady=20)
        
        def close_error():
            error_window.destroy()
        
        error_window.after(3000, close_error)  # Auto-close after 3 seconds

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.shortcut = config.get('shortcut', 'ctrl+shift+p')
            else:
                self.shortcut = 'ctrl+shift+p'  # Default shortcut
                self.save_config()
        except Exception:
            self.shortcut = 'ctrl+shift+p'  # Fallback to default if any error
            self.save_config()

    def save_config(self):
        try:
            config = {
                'shortcut': self.shortcut
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception:
            pass  # Silently fail if unable to save config

    def change_shortcut(self, new_shortcut):
        try:
            # Remove old shortcut if it exists
            try:
                keyboard.remove_hotkey(self.shortcut)
            except:
                pass
            # Set new shortcut
            self.shortcut = new_shortcut
            keyboard.add_hotkey(self.shortcut, self.start_color_pick)
            # Update the icon to refresh the menu state
            self.icon.update_menu()
            # Save the new shortcut to config
            self.save_config()
        except Exception as e:
            self.after(0, lambda: self.show_error(f"Failed to set shortcut: {str(e)}"))

if __name__ == "__main__":
    if check_running_instance():
        app = ColorPicker()
        app.mainloop()
