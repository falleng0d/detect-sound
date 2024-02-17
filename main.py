import functools
from dataclasses import dataclass
from typing import Callable, Optional

import click
import numpy as np
import sounddevice as sd
import time
import pyautogui


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

	@property
	def listening(self):
		return self._listening

	@property
	def last_volume_tick(self):
		return (
			self.last_volume_ticks[-1]
			if self._listening and len(self.last_volume_ticks) > 0
			else 0
		)

	def __init__(self):
		self.oldest_succesfull_check_time: float | None = None
		self.succesfull_check_times: list[float] = []
		self.last_volume_ticks: list[float] = []

		self._listening = False
		self._stream: sd.InputStream | None = None

		# The `audio_callback` method should only call the `callback` method if the
		# threshold is higher than the volume for at least TIME_THRESHOLD second.
		self.threshold = 25.0
		self.time_threshold = 0.08
		self.time_expired = 0.2

		self.input_device_id = get_default_input_device_name()

	def audio_handler(self, callback: Callable, indata, *_):
		if not self._listening:
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

	def configure(self, config: ListenerConfing):
		self.threshold = config.threshold
		self.time_threshold = config.time_threshold
		self.time_expired = config.time_expired

	def listen(self, callback: Callable, config: Optional[ListenerConfing] = None):
		if self.listening:
			raise ValueError("Already listening")

		if config:
			self.configure(config)

		self._stream = sd.InputStream(
			device=self.input_device_id,
			callback=functools.partial(self.audio_handler, callback),
		)

		self._stream.start()
		self._listening = True

		click.echo(
			click.style(
				f"Listening started with "
				f"{self.threshold=} {self.time_threshold=} {self.time_expired=}",
				fg="green",
			)
		)

	def stop_listening(self):
		self._listening = False

		if self._stream is None:
			return

		self._stream.stop()
		self._stream.close()
		self._stream = None


@cooldown(0.3)
def press_key_callback(key: str):
	is_mouse_key = key.lower() in {"mleft", "mright", "mmiddle"}
	if not is_mouse_key:
		# press the key
		pyautogui.press(key)
	else:
		# remove first character from the key
		key = key[1:]
		# press the mouse button
		pyautogui.click(button=key)

	# print a colored message to the console
	click.echo(click.style("Callback function executed", fg="green"))


if __name__ == "__main__":
	listener = Listener()
	listener.listen(functools.partial(press_key_callback, "pagedown"))

	try:
		while listener.listening:
			time.sleep(0.1)
	except KeyboardInterrupt:
		listener.stop_listening()
		print("Listener stopped")
