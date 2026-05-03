import os
import asyncio


# Pyrogram sync wrapper is incompatible with Python 3.14 default event loop behavior.
os.environ.setdefault("PYROGRAM_DISABLE_SYNC", "1")

try:
	asyncio.get_event_loop()
except RuntimeError:
	asyncio.set_event_loop(asyncio.new_event_loop())
