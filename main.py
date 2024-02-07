import functools

import click
import numpy as np
import sounddevice as sd
import threading
import time
import pyautogui

from pynput import keyboard

# Global variable to control the execution of audio_handler
audio_handler_enabled = True


def on_press(key):
	global audio_handler_enabled
	if key == keyboard.KeyCode.from_char("a"):
		# Toggle audio_handler_enabled
		audio_handler_enabled = not audio_handler_enabled
		click.echo(
			click.style(
				f"\raudio_handler_enabled is now {audio_handler_enabled}", fg="yellow"
			)
		)


def start_listener():
	with keyboard.Listener(on_press=on_press) as listener:
		listener.join()


listener_thread = threading.Thread(target=start_listener)
listener_thread.start()


def cooldown(wait):
	"""
	Decorator that will block new function
	executions until after `wait` seconds
	have elapsed since the last time it was succesfully invoked.

	Attempts to invoke the function before `wait` seconds
	have elapsed will reset the timer.
	"""

	def decorator(fn):
		@functools.wraps(fn)
		def cooldowned(*args, **kwargs):
			def call_it():
				fn(*args, **kwargs)

			if (
				not hasattr(cooldowned, "last_called")
				or time.time() - cooldowned.last_called > wait
			):
				call_it()

			cooldowned.last_called = time.time()

		return cooldowned

	return decorator


@cooldown(0.3)
def callback():
	# press page down key
	pyautogui.press("pagedown")
	# print a colored message to the console
	click.echo(click.style("Callback function executed", fg="green"))


oldest_succesfull_check_time: float | None = None
succesfull_check_times: list[float] = []


def audio_handler(indata, *_):
	global oldest_succesfull_check_time
	global succesfull_check_times

	if not audio_handler_enabled:
		return

	volume_norm = np.linalg.norm(indata) * 10
	THRESHOLD = 20

	# The `audio_callback` method should only call the `callback` method if the threshold
	# is higher than the volume for at least TIME_THRESHOLD second.
	TIME_THRESHOLD = 0.08
	TIME_EXPIRED = 0.2

	if volume_norm > THRESHOLD:
		succesfull_check_times.append(time.time())

		# remove all the times that are older than TIME_EXPIRED + TIME_THRESHOLD
		old_length = len(succesfull_check_times)
		diffs = [f"{time.time() - tick:.2f}" for tick in succesfull_check_times]
		print(f"\r{diffs=}")
		succesfull_check_times = [
			tick
			for tick in succesfull_check_times
			if (time.time() - tick) <= (TIME_EXPIRED + TIME_THRESHOLD)
		]
		if old_length - len(succesfull_check_times) > 0:
			print(
				f"\rRemoved {old_length - len(succesfull_check_times)} old ticks out of {old_length}"
			)

		# grab the oldest non-expired succesfull check time
		oldest_succesfull_check_time = succesfull_check_times[0]

		# if the volume is not higher than the threshold for at least TIME_THRESHOLD secs
		if time.time() - oldest_succesfull_check_time < TIME_THRESHOLD:
			return

		# remove calls that are older than TIME_EXPIRED
		succesfull_check_times = [
			tick
			for tick in succesfull_check_times
			if (time.time() - tick) <= TIME_THRESHOLD
		]

		print(
			f"\rCallback function called with diff: "
			f"{time.time() - oldest_succesfull_check_time:.2f}"
		)
		callback()


# Function to print "Listening..." with alternating dots
def print_listening():
	i = 0
	while listening:
		print("\rListening" + "." * (i % 3 + 1), end="")
		time.sleep(1)
		i += 1


def setup_device():
	# Get a list of all audio devices
	device = sd.query_devices(kind="input")

	# Find the device ID of the selected device
	return device["name"]


input_device_id = setup_device()

# Set up the audio input stream with the selected device

# Global variable to control the listening thread
listening = True

# Start the listening thread
listening_thread = threading.Thread(target=print_listening)
listening_thread.start()

while listening:
	stream = sd.InputStream(device=input_device_id, callback=audio_handler)
	with stream:
		sd.sleep(10000)  # Listen for 10 seconds

# Stop the listening thread
listening = False
listening_thread.join()
