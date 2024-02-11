import functools
from dataclasses import dataclass
from typing import Callable, Optional

import click
import numpy as np
import sounddevice as sd
import threading
import time
import pyautogui

from pynput import keyboard

from cooldown import cooldown


def get_default_input_device_name():
	# Get a list of all audio devices
	device = sd.query_devices(kind="input")

	# Find the device ID of the selected device
	return device["name"]


class Listener:
	@dataclass(frozen=True)
	class ListenerConfing:
		threshold: float
		time_threshold: float
		time_expired: float

	def __init__(self):
		self.oldest_succesfull_check_time: float | None = None
		self.succesfull_check_times: list[float] = []
		self.last_volume_ticks: list[float] = []
		self.listening = False
		self.audio_handler_enabled = True
		self.input_device_id = get_default_input_device_name()

		# The `audio_callback` method should only call the `callback` method if the
		# threshold is higher than the volume for at least TIME_THRESHOLD second.
		self.threshold = 25.0
		self.time_threshold = 0.08
		self.time_expired = 0.2

	def audio_handler(self, callback: Callable, indata, *_):
		if not self.audio_handler_enabled:
			return

		volume_norm = np.linalg.norm(indata) * 10

		self.last_volume_ticks.append(volume_norm)
		if len(self.last_volume_ticks) > 10:
			self.last_volume_ticks.pop(0)

		if volume_norm > self.threshold:
			self.succesfull_check_times.append(time.time())

			# remove all the times that are older than TIME_EXPIRED + TIME_THRESHOLD
			old_length = len(self.succesfull_check_times)
			diffs = [f"{time.time() - tick:.2f}" for tick in self.succesfull_check_times]
			click.secho(click.style(f"\r{diffs=}", fg="bright_black"))
			self.succesfull_check_times = [
				tick
				for tick in self.succesfull_check_times
				if (time.time() - tick) <= (self.time_expired + self.time_threshold)
			]
			if old_length - len(self.succesfull_check_times) > 0:
				print(
					f"\rRemoved {old_length - len(self.succesfull_check_times)} "
					f"old ticks out of {old_length}"
				)

			# grab the oldest non-expired succesfull check time
			oldest_succesfull_check_time = self.succesfull_check_times[0]

			# if the volume is not higher than the threshold for at least TIME_THRESHOLD
			if time.time() - oldest_succesfull_check_time < self.time_threshold:
				return

			# remove calls that are older than TIME_EXPIRED
			self.succesfull_check_times = [
				tick
				for tick in self.succesfull_check_times
				if (time.time() - tick) <= self.time_threshold
			]

			click.echo(
				click.style(
					f"\rCallback function called with diff: "
					f"{time.time() - oldest_succesfull_check_time:.2f} "
					f"and the volume: {volume_norm:.2f}",
					fg="yellow",
				),
			)

			last_volume_ticks_str = " ".join(
				[f"{tick:.2f}" for tick in self.last_volume_ticks]
			)
			click.echo(
				click.style(f"\rLast ticks: {last_volume_ticks_str}", fg="yellow")
			)
			callback()

	def with_config(self, config: ListenerConfing):
		self.threshold = config.threshold
		self.time_threshold = config.time_threshold
		self.time_expired = config.time_expired

	def listen(self, callback: Callable, config: Optional[ListenerConfing] = None):
		self.listening = True
		self.audio_handler_enabled = True

		if config:
			self.with_config(config)

		while self.listening:
			stream = sd.InputStream(
				device=self.input_device_id,
				callback=functools.partial(self.audio_handler, callback),
			)
			with stream:
				sd.sleep(60000)


def toggle_listening_on_hotkey(key_char: str, listener: Listener):
	def on_press(key):
		if key == keyboard.KeyCode.from_char(key_char):
			listener.audio_handler_enabled = not listener.audio_handler_enabled
			click.echo(
				click.style(
					f"\raudio_handler_enabled is now {listener.audio_handler_enabled}",
					fg="yellow",
				)
			)

	def listener_callback():
		with keyboard.Listener(on_press=on_press) as listener:
			listener.join()

	listener_thread = threading.Thread(target=listener_callback)
	listener_thread.start()


if __name__ == "__main__":

	@cooldown(0.3)
	def callback():
		# press page down key
		pyautogui.press("pagedown")
		# print a colored message to the console
		click.echo(click.style("Callback function executed", fg="green"))

	listener = Listener()
	toggle_listening_on_hotkey(key_char="a", listener=listener)
	listener.listen(callback)
