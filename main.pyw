import tkinter as tk
from tkinter import scrolledtext
from functools import partial

import sys
from pystray import Icon as TrayIcon, MenuItem as item, Menu as menu
from PIL import Image

original_stdout = sys.stdout  # Save a reference to the original standard output
from main import Listener, press_key_callback


class Application(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title("Detect Sound")
		self.iconbitmap("app.ico")

		self.tray_icon: TrayIcon = None

		self.listener = Listener()
		self.listener_thread = None

		self.create_widgets()
		self.update()  # Update the window to make sure all widgets are accounted for
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
		self.key_entry.insert(0, "pagedown")

	def toggle_listening(self):
		if self.listener.listening:
			self.listener.stop_listening()

			self.toggle_button.config(text="Start Listening")
			self.key_entry.config(
				state="normal"
			)  # Enable key_entry when listening stops
			self.log("Listening stopped.")
		else:
			self.start_listening_thread()

			self.toggle_button.config(text="Stop Listening")
			self.key_entry.config(
				state="disabled"
			)  # Disable key_entry when listening starts
			self.log("Listening started.")

	def start_listening_thread(self):
		key = self.key_entry.get()
		callback = partial(press_key_callback, key)
		self.listener.listen(callback)

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
