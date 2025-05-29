import tkinter as tk
from tkinter import filedialog, messagebox
import os
import numpy as np
from PIL import Image, ImageTk
import nes_py

# --- NESSystem Class (robust for nes-py) ---
class NESSystem:
    def __init__(self, rom_path):
        self.rom_path = rom_path
        self.env = None
        try:
            self.env = nes_py.NESEnv(self.rom_path)
            self.env.reset()
            print(f"[NESSystem] Initialized with ROM: {os.path.basename(self.rom_path)}")
        except Exception as e:
            print(f"[NESSystem] Error initializing nes-py: {e}")
            raise

    def reset(self):
        if self.env:
            self.env.reset()
            print("[NESSystem] ROM reset")

    def step(self, action):
        try:
            # Advance the emulator by one step, then grab the frame
            self.env.step(action)
            frame = self.env.screen  # Guaranteed shape (240, 256, 3)
            if frame is None:
                print("[NESSystem] WARNING: Frame is None!")
            return frame, False
        except Exception as e:
            print(f"[NESSystem] step() failed: {e}")
            return None, True

    def close(self):
        if self.env:
            self.env.close()
            print("[NESSystem] Closed NES environment")
            self.env = None

# --- Tkinter Application ---
class NesticleTkApp:
    def __init__(self, master):
        self.master = master
        self.master.title("NESTICLE-TK")
        self.master.geometry("600x480")
        self.master.configure(bg="#1a1a1a")
        self.master.resizable(False, False)

        self.nes = None
        self.current_action = 0
        self.after_id = None
        self.frame_image = None

        # Key to NES controller mapping
        self.keymap = {
            'Right': 1,  'Left': 2,  'Down': 4,  'Up': 8,
            'Return': 16, 'Shift_L': 32, 'x': 64, 'z': 128
        }
        self.keys_pressed = set()

        # UI
        ctrl_frame = tk.Frame(master, bg="#2e2e2e")
        ctrl_frame.pack(fill=tk.X, pady=5)

        btn_style = {"bg": "#4a4a4a", "fg": "#fff", "font": ("Fixedsys", 9), "bd": 1}
        tk.Button(ctrl_frame, text="Load ROM", command=self.load_rom, **btn_style).pack(side=tk.LEFT, padx=5)
        self.start_btn = tk.Button(ctrl_frame, text="Start", command=self.toggle_run, state=tk.DISABLED, **btn_style)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.reset_btn = tk.Button(ctrl_frame, text="Reset", command=self.reset_rom, state=tk.DISABLED, **btn_style)
        self.reset_btn.pack(side=tk.LEFT, padx=5)

        self.canvas = tk.Canvas(master, width=256, height=240, bg="black", highlightthickness=1, highlightbackground="#fff")
        self.canvas.pack(pady=10)

        self.status = tk.Label(master, text="No ROM loaded", bg="#1e1e1e", fg="#0f0", anchor="w")
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

        master.bind('<KeyPress>', self.on_key_press)
        master.bind('<KeyRelease>', self.on_key_release)
        master.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_rom(self):
        path = filedialog.askopenfilename(title="Select NES ROM", filetypes=[("NES ROM", "*.nes"), ("All", "*.*")])
        if not path:
            return
        if self.nes:
            self.nes.close()
            self.nes = None
        try:
            self.nes = NESSystem(path)
            # Try to get first frame
            frame = self.nes.env.screen
            if frame is not None:
                self.render_frame(frame)
                print(f"[App] Got initial frame: {frame.shape}")
            else:
                print("[App] Initial frame is None")
            self.status.config(text=f"Loaded: {os.path.basename(path)}")
            self.start_btn.config(state=tk.NORMAL)
            self.reset_btn.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ROM: {e}")
            self.status.config(text="Load failed")

    def on_key_press(self, event):
        if event.keysym in self.keymap:
            self.keys_pressed.add(event.keysym)
            self.update_action()

    def on_key_release(self, event):
        if event.keysym in self.keymap and event.keysym in self.keys_pressed:
            self.keys_pressed.remove(event.keysym)
            self.update_action()

    def update_action(self):
        action = 0
        for k in self.keys_pressed:
            action |= self.keymap.get(k, 0)
        self.current_action = action

    def toggle_run(self):
        if not self.nes:
            return
        if self.after_id:
            self.master.after_cancel(self.after_id)
            self.after_id = None
            self.start_btn.config(text="Start")
            self.status.config(text="Paused")
        else:
            self.start_btn.config(text="Pause")
            self.status.config(text="Running")
            self.schedule_frame()

    def schedule_frame(self):
        frame, done = self.nes.step(self.current_action)
        if frame is not None:
            self.render_frame(frame)
        else:
            print("[App] Frame from step() is None")
            self.status.config(text="Frame error")
            self.after_id = None
            return
        if not done:
            self.after_id = self.master.after(16, self.schedule_frame)
        else:
            self.status.config(text="Game Over")
            self.start_btn.config(text="Start")
            self.after_id = None

    def render_frame(self, frame):
        try:
            img = Image.fromarray(frame)
            self.frame_image = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor='nw', image=self.frame_image)
        except Exception as e:
            print(f"[App] Render frame failed: {e}")

    def reset_rom(self):
        if not self.nes:
            return
        if self.after_id:
            self.master.after_cancel(self.after_id)
            self.after_id = None
        self.nes.reset()
        frame = self.nes.env.screen
        if frame is not None:
            self.render_frame(frame)
        self.start_btn.config(text="Start")
        self.status.config(text="Reset")

    def on_close(self):
        if self.after_id:
            self.master.after_cancel(self.after_id)
        if self.nes:
            self.nes.close()
        self.master.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = NesticleTkApp(root)
    root.mainloop()
