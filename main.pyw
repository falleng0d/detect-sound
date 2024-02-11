import contextlib
import tkinter as tk
from tkinter import scrolledtext
from functools import partial

import sys
import keyboard
from pystray import Icon as TrayIcon, MenuItem as item, Menu as menu
from PIL import Image

from easysettings import EasySettings

original_stdout = sys.stdout  # Save a reference to the original standard output
from main import Listener, press_key_callback


class Application(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title("Detect Sound")
		self.iconbitmap("app.ico")

		self.settings = EasySettings("app_settings.conf")
		self.tray_icon: TrayIcon = None

		self.listener = Listener()
		self.listener_thread = None

		self.create_widgets()
		self.update()  # Update the window to make sure all widgets are accounted for
		self.bind_keyboard_shortcuts()
		self.minsize(self.winfo_width(), self.winfo_height())  # Set minimum window size

		sys.stdout = TextRedirector(self.log_box)
		self.override_minimize()

	def create_widgets(self):
		self.log_box = scrolledtext.ScrolledText(self, state="disabled", height=10)
		self.log_box.grid(row=0, column=0, columnspan=1, sticky="nsew")
		self.grid_rowconfigure(0, weight=1)
		self.grid_columnconfigure(0, weight=1)

		self.toggle_button = tk.Button(
			self, text="Start Listening", command=self.toggle_listening
		)
		self.toggle_button.grid(row=1, column=0, sticky="ew")

		self.key_label = tk.Label(self, text="Key to press:")
		self.key_label.grid(row=2, column=0, sticky="w")

		self.key_entry = tk.Entry(self)
		self.key_entry.grid(row=3, column=0, sticky="ew")
		self.key_entry.insert(0, self.settings.get("key", "pagedown"))

		self.threshold_label = tk.Label(self, text="Threshold:")
		self.threshold_label.grid(row=4, column=0, sticky="w")
		self.threshold_entry = tk.Scale(self, from_=1, to=100, orient="horizontal")
		self.threshold_entry.grid(row=5, column=0, sticky="ew")
		self.threshold_entry.set(self.settings.get("threshold", "25.0"))

		self.time_threshold_label = tk.Label(self, text="Time Threshold:")
		self.time_threshold_label.grid(row=6, column=0, sticky="w")
		self.time_threshold_entry = tk.Spinbox(self, from_=0, to=1, increment=0.01)
		self.time_threshold_entry.grid(row=7, column=0, sticky="ew")
		self.time_threshold_entry.delete(0, "end")
		self.time_threshold_entry.insert(0, self.settings.get("time_threshold", "0.08"))

		self.time_expired_label = tk.Label(self, text="Time Expired:")
		self.time_expired_label.grid(row=8, column=0, sticky="w")
		self.time_expired_entry = tk.Spinbox(self, from_=0, to=1, increment=0.01)
		self.time_expired_entry.grid(row=9, column=0, sticky="ew")
		self.time_expired_entry.delete(0, "end")
		self.time_expired_entry.insert(0, self.settings.get("time_expired", "0.20"))

		self.shortcut_label = tk.Label(self, text="Keyboard Shortcut:")
		self.shortcut_label.grid(row=10, column=0, sticky="w")
		self.shortcut_entry = tk.Entry(self)
		self.shortcut_entry.grid(row=11, column=0, sticky="ew")
		self.shortcut_entry.insert(0, self.settings.get("keyboard_shortcut", "a"))
		self.shortcut_entry.bind(
			"<FocusOut>", lambda e: self.rebind_keyboard_shortcuts()
		)

	def rebind_keyboard_shortcuts(self):
		old_shortcut = self.settings.get("keyboard_shortcut", "a")

		with contextlib.suppress(KeyError):
			keyboard.remove_hotkey(old_shortcut)

		new_shortcut = self.shortcut_entry.get()

		try:
			keyboard.add_hotkey(new_shortcut, self.toggle_listening)
		except ValueError:
			print(f"Failed to bind keyboard shortcut {new_shortcut}")
			return

		if old_shortcut != new_shortcut:
			self.settings.set("keyboard_shortcut", new_shortcut)
			print(f"Rebound keyboard shortcut to {new_shortcut}")

	def bind_keyboard_shortcuts(self):
		keyboard.add_hotkey(self.shortcut_entry.get(), self.toggle_listening)

	def unbind_keyboard_shortcuts(self):
		keyboard.remove_hotkey(self.shortcut_entry.get())

	def save_settings(self):
		self.settings.set("key", self.key_entry.get())
		self.settings.set("threshold", self.threshold_entry.get())
		self.settings.set("time_threshold", self.time_threshold_entry.get())
		self.settings.set("time_expired", self.time_expired_entry.get())
		self.settings.save()

	def toggle_listening(self):
		if self.listener.listening:
			self.listener.stop_listening()

			self.toggle_button.config(text="Start Listening")
			self.key_entry.config(
				state="normal"
			)  # Enable key_entry when listening stops
			self.threshold_entry.config(state="normal")
			self.time_threshold_entry.config(state="normal")
			self.time_expired_entry.config(state="normal")
			self.shortcut_entry.config(state="normal")

			self.log("Listening stopped.")
		else:
			self.start_listening_thread()

			self.save_settings()

			self.toggle_button.config(text="Stop Listening")
			self.key_entry.config(
				state="disabled",
			)
			self.threshold_entry.config(state="disabled")
			self.time_threshold_entry.config(state="disabled")
			self.shortcut_entry.config(state="disabled")
			self.time_expired_entry.config(state="disabled")

			self.log("Listening started.")

	def start_listening_thread(self):
		threshold = float(self.threshold_entry.get())
		time_threshold = float(self.time_threshold_entry.get())
		time_expired = float(self.time_expired_entry.get())
		config = Listener.ListenerConfing(
			threshold=threshold, time_threshold=time_threshold, time_expired=time_expired
		)
		callback = partial(press_key_callback, self.key_entry.get())
		self.listener.listen(callback, config)

	def log(self, message):
		self.log_box.configure(state="normal")
		self.log_box.insert(tk.END, message + "\n")
		self.log_box.configure(state="disabled")
		self.log_box.yview(tk.END)

	def create_system_tray_icon(self):
		# Load icon from app.ico
		icon_image = Image.open("app.ico")

		# Create the system tray icon
		self.tray_icon = TrayIcon(
			name="Detect Sound",
			icon=icon_image.resize((32, 32)),
			menu=menu(
				item("Show", self.restore_from_tray, default=True),
				item("Exit", self.destroy),
			),
		)

	def restore_from_tray(self):
		self.tray_icon.stop()
		self.deiconify()  # Show the window

	def on_minimize(self):
		self.create_system_tray_icon()
		self.withdraw()  # Hide the window
		self.tray_icon.run()

	def destroy(self):
		self.tray_icon.stop()
		super().destroy()

	def override_minimize(self):
		self.protocol("WM_DELETE_WINDOW", self.on_minimize)


class TextRedirector(object):
	def __init__(self, widget):
		self.widget = widget

	def write(self, string):
		original_stdout.write(string)  # Write to the original stdout
		self.widget.configure(state="normal")
		self.widget.insert(tk.END, string)
		self.widget.configure(state="disabled")
		self.widget.yview(tk.END)
		self.widget.yview(tk.END)

	def flush(self):
		pass


if __name__ == "__main__":
	app = Application()
	app.mainloop()
