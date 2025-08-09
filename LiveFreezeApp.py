import ctypes
import mss
from PIL import Image, ImageTk
import keyboard
import tkinter as tk
import screeninfo
import queue

FREEZE_HOTKEY = "ctrl+alt+f"
EXIT_HOTKEY = "ctrl+alt+q"

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

class LiveFreezeApp:
    def __init__(self):
        self.frozen = False
        self.sct = mss.mss()

        monitors = screeninfo.get_monitors()
        print("Detected monitors:")
        for m in monitors:
            print(f"  {m}")

        primary = None
        for m in monitors:
            if getattr(m, 'is_primary', False):
                primary = m
                break
        if primary is None:
            primary = next((m for m in monitors if m.x == 0 and m.y == 0), monitors[0])

        print(f"Primary monitor: {primary}")

        extended = [m for m in monitors if m != primary]
        if not extended:
            print("No extended monitors detected, defaulting to primary")
            self.monitor = primary
        else:
            def get_side(ext, prim):
                if ext.x + ext.width <= prim.x:
                    return "left"
                elif ext.x >= prim.x + prim.width:
                    return "right"
                elif ext.y + ext.height <= prim.y:
                    return "top"
                elif ext.y >= prim.y + prim.height:
                    return "bottom"
                else:
                    return "overlap"

            sides = [(m, get_side(m, primary)) for m in extended]
            print("Extended monitors with sides relative to primary:")
            for m, side in sides:
                print(f"  {m} -> {side}")

            filtered = [m for m, s in sides if s != "overlap"]
            if filtered:
                self.monitor = filtered[0]
            else:
                self.monitor = extended[0]

        print(f"Selected monitor for freeze: {self.monitor}")

        self.mss_monitor_index = None
        for i, mon in enumerate(self.sct.monitors[1:], start=1):
            if (mon['left'] == self.monitor.x and
                mon['top'] == self.monitor.y and
                mon['width'] == self.monitor.width and
                mon['height'] == self.monitor.height):
                self.mss_monitor_index = i
                break

        if self.mss_monitor_index is None:
            print("Warning: Could not find exact mss monitor match, defaulting to primary monitor")
            self.mss_monitor_index = 1

        print(f"Using mss monitor index: {self.mss_monitor_index}")

        self.root = tk.Tk()
        self.root.attributes("-fullscreen", False)
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.withdraw()

        self.root.geometry(f"{self.monitor.width}x{self.monitor.height}+{self.monitor.x}+{self.monitor.y}")

        self.label = tk.Label(self.root, bg="black")
        self.label.pack(fill="both", expand=True)

        hwnd = self.root.winfo_id()
        ctypes.windll.user32.SetWindowPos(hwnd, 0,
                                          self.monitor.x, self.monitor.y,
                                          self.monitor.width, self.monitor.height,
                                          0x0004 | 0x0010)

        self.root.lift()
        self.root.focus_force()

        self.command_queue = queue.Queue()

        # Hotkey to toggle freeze/unfreeze
        keyboard.add_hotkey(FREEZE_HOTKEY, self.queue_toggle_freeze)
        # Hotkey to cleanly exit the app
        keyboard.add_hotkey(EXIT_HOTKEY, lambda: self.root.quit())

        print(f"LiveFreezeApp running. Press {FREEZE_HOTKEY} to toggle freeze/unfreeze.")
        print(f"Press {EXIT_HOTKEY} to exit the app.")

        self.root.after(100, self.process_queue)

    def queue_toggle_freeze(self):
        self.command_queue.put("toggle")

    def process_queue(self):
        try:
            while True:
                cmd = self.command_queue.get_nowait()
                if cmd == "toggle":
                    self.toggle_freeze()
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def capture_monitor(self):
        mon = self.sct.monitors[self.mss_monitor_index]
        img = self.sct.grab(mon)
        return Image.frombytes("RGB", img.size, img.rgb)

    def toggle_freeze(self):
        if not self.frozen:
            img = self.capture_monitor()
            img_tk = ImageTk.PhotoImage(img)
            self.label.config(image=img_tk)
            self.label.image = img_tk
            self.root.deiconify()
            self.frozen = True
        else:
            self.root.withdraw()
            self.frozen = False

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = LiveFreezeApp()
    app.run()
