"""The loggers this project silences, and why it matters."""

from __future__ import annotations

import logging

from credit_radar.logging_config import NOISY_LOGGERS, configure_logging


class TestNoisyLoggers:
    def test_http_client_loggers_are_pinned_to_warning(self):
        # httpx logs the full request URL at INFO. Harmless for public Banco
        # Central series; for the authenticated providers coming later a URL
        # can carry a CPF or an account identifier, and a journal is exactly
        # where personal data ends up by accident and stays for months.
        configure_logging("INFO")

        for name in NOISY_LOGGERS:
            assert logging.getLogger(name).level == logging.WARNING

    def test_a_failing_request_is_still_reported(self):
        # Silencing must not hide errors, only routine chatter.
        configure_logging("INFO")

        assert logging.getLogger("httpx").isEnabledFor(logging.WARNING)
        assert logging.getLogger("httpx").isEnabledFor(logging.ERROR)

    def test_the_application_loggers_keep_inheriting(self):
        # Asserted as "no explicit level of its own" rather than as an
        # effective level: basicConfig is a no-op once the root logger has a
        # handler, so an effective-level assertion would really be testing
        # whatever configured logging first, which under pytest is pytest.
        configure_logging("INFO")

        for name in ("credit_radar", "credit_radar.collect"):
            assert logging.getLogger(name).level == logging.NOTSET

    def test_debug_level_still_silences_the_http_clients(self):
        # Turning the app to DEBUG to chase a parser bug must not start
        # writing request URLs to the journal as a side effect.
        configure_logging("DEBUG")

        for name in NOISY_LOGGERS:
            assert logging.getLogger(name).level == logging.WARNING
