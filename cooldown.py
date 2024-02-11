import functools
import time


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
