import os
import asyncio


# Pyrogram sync wrapper is incompatible with Python 3.14 default event loop behavior.
os.environ.setdefault("PYROGRAM_DISABLE_SYNC", "1")

try:
	asyncio.get_event_loop()
except RuntimeError:
	asyncio.set_event_loop(asyncio.new_event_loop())


try:
	from pyrogram.methods.advanced.save_file import SaveFile

	_ORIG_SAVE_FILE = SaveFile.save_file

	if not getattr(_ORIG_SAVE_FILE, "_teleblaster_me_patch", False):
		async def _save_file_with_me_guard(self, *args, **kwargs):
			# Pyrogram may access self.me.is_premium before self.me is initialized.
			if getattr(self, "me", None) is None:
				try:
					me = await self.get_me()
					self.me = me
				except Exception:
					class _MeFallback:
						is_premium = False

					self.me = _MeFallback()
			elif getattr(self.me, "is_premium", None) is None:
				try:
					self.me.is_premium = False
				except Exception:
					pass

			return await _ORIG_SAVE_FILE(self, *args, **kwargs)

		_save_file_with_me_guard._teleblaster_me_patch = True
		SaveFile.save_file = _save_file_with_me_guard
except Exception:
	# Keep app running even if internal API layout changes in future Pyrogram versions.
	pass
