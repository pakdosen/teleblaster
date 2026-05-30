"""Tests untuk funcs.auth.cache."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from funcs.auth.cache import AuthCache, AuthState


class AuthStateTest(unittest.TestCase):
    def test_now_creates_iso_timestamp(self):
        state = AuthState.now(email="a@b.com", user_id=1, name="A")
        self.assertEqual(state.email, "a@b.com")
        # Parsing harus berhasil dan timezone-aware UTC.
        ts = datetime.fromisoformat(state.validated_at)
        self.assertIsNotNone(ts.tzinfo)

    def test_is_fresh_returns_true_when_within_ttl(self):
        state = AuthState(
            email="a@b.com",
            user_id=1,
            name="A",
            validated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self.assertTrue(state.is_fresh(ttl_hours=24))

    def test_is_fresh_returns_false_when_expired(self):
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(timespec="seconds")
        state = AuthState(email="a@b.com", user_id=1, name="A", validated_at=old_ts)
        self.assertFalse(state.is_fresh(ttl_hours=24))

    def test_is_fresh_returns_false_when_timestamp_invalid(self):
        state = AuthState(email="a@b.com", user_id=1, name="A", validated_at="not-iso")
        self.assertFalse(state.is_fresh(ttl_hours=24))

    def test_round_trip_dict(self):
        state = AuthState.now(email="a@b.com", user_id=42, name="Tester")
        clone = AuthState.from_dict(state.to_dict())
        self.assertEqual(clone, state)


class AuthCacheTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "auth.json"
        self.cache = AuthCache(self.path)

    def test_load_returns_none_when_file_missing(self):
        self.assertIsNone(self.cache.load())

    def test_save_then_load(self):
        state = AuthState.now(email="a@b.com", user_id=7, name="Tester")
        self.cache.save(state)
        loaded = self.cache.load()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.email, "a@b.com")
        self.assertEqual(loaded.user_id, 7)

    def test_clear_removes_file(self):
        state = AuthState.now(email="a@b.com", user_id=1, name="A")
        self.cache.save(state)
        self.cache.clear()
        self.assertFalse(self.path.exists())

    def test_clear_silent_when_file_missing(self):
        # Tidak boleh raise.
        self.cache.clear()

    def test_load_returns_none_when_file_corrupted(self):
        self.path.write_text("not-valid-json{", encoding="utf-8")
        self.assertIsNone(self.cache.load())

    def test_load_returns_none_when_email_missing(self):
        self.path.write_text(json.dumps({"user_id": 1, "validated_at": "2025-01-01T00:00:00+00:00"}), encoding="utf-8")
        self.assertIsNone(self.cache.load())


if __name__ == "__main__":
    unittest.main()
