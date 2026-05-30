"""Unit test untuk aturan Free version."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from funcs.free_limits import (
    DISABLED_TABS,
    MAX_TELEGRAM_ACCOUNTS,
    block_if_account_limit_reached,
    is_account_limit_reached,
    is_tab_disabled,
    upgrade_required_message,
)


class FreeLimitsConstantsTest(unittest.TestCase):
    def test_max_one_account(self):
        self.assertEqual(MAX_TELEGRAM_ACCOUNTS, 1)

    def test_disabled_tabs(self):
        self.assertEqual(set(DISABLED_TABS), {"Members Adder", "Grup Scrapper"})

    def test_upgrade_message_has_keywords(self):
        msg = upgrade_required_message()
        self.assertIn("Free", msg)
        self.assertIn("Pro", msg)
        self.assertIn("satu akun", msg.lower())


class IsAccountLimitReachedTest(unittest.TestCase):
    def test_zero_sessions_not_at_limit(self):
        self.assertFalse(is_account_limit_reached(0))

    def test_one_session_at_limit(self):
        self.assertTrue(is_account_limit_reached(1))

    def test_two_sessions_over_limit(self):
        self.assertTrue(is_account_limit_reached(2))


class BlockIfAccountLimitReachedTest(unittest.TestCase):
    def test_no_popup_when_under_limit(self):
        with mock.patch("funcs.free_limits.messagebox") as mb:
            blocked = block_if_account_limit_reached(0)
        self.assertFalse(blocked)
        mb.showinfo.assert_not_called()

    def test_shows_popup_and_blocks_when_at_limit(self):
        with mock.patch("funcs.free_limits.messagebox") as mb:
            blocked = block_if_account_limit_reached(1)
        self.assertTrue(blocked)
        mb.showinfo.assert_called_once()
        title_arg = mb.showinfo.call_args.args[0]
        self.assertIn("Free", title_arg)


class IsTabDisabledTest(unittest.TestCase):
    def test_members_adder_disabled(self):
        self.assertTrue(is_tab_disabled("Members Adder"))

    def test_grup_scrapper_disabled(self):
        self.assertTrue(is_tab_disabled("Grup Scrapper"))

    def test_members_scraper_not_disabled(self):
        self.assertFalse(is_tab_disabled("Members Scraper"))

    def test_login_not_disabled(self):
        self.assertFalse(is_tab_disabled("Login"))


if __name__ == "__main__":
    unittest.main()
