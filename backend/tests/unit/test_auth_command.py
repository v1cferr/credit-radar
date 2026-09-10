"""The sign-in handoff, at the level that does not need a browser."""

from __future__ import annotations

import pytest

from credit_radar.cli import AUTHENTICATED_SOURCES, authenticate, wait_for_sign_in
from credit_radar.providers.bcb import registrato


class FakeContext:
    """Stands in for a Playwright context, recording what was asked of it."""

    def __init__(self) -> None:
        self.waited_for: list[str] = []

    def wait_for_event(self, event: str, timeout: int = 0) -> None:
        self.waited_for.append(event)


class TestWaitingForTheHuman:
    def test_an_interactive_terminal_waits_for_enter(self, monkeypatch):
        prompts: list[str] = []
        monkeypatch.setattr("builtins.input", lambda prompt="": prompts.append(prompt))
        context = FakeContext()

        wait_for_sign_in(context)

        assert prompts and "signing in" in prompts[0]
        assert context.waited_for == []

    def test_without_a_terminal_it_waits_for_the_window_to_close(self, monkeypatch):
        # The branch that matters: returning immediately would save a profile
        # nobody signed into, and then report a session that does not exist.
        def raise_eof(prompt: str = "") -> str:
            raise EOFError

        monkeypatch.setattr("builtins.input", raise_eof)
        context = FakeContext()

        wait_for_sign_in(context)

        assert context.waited_for == ["close"]

    def test_it_does_not_fail_on_a_context_that_cannot_wait(self, monkeypatch):
        def raise_eof(prompt: str = "") -> str:
            raise EOFError

        monkeypatch.setattr("builtins.input", raise_eof)

        wait_for_sign_in(object())  # must not raise


class TestSourceSelection:
    def test_an_unknown_source_is_refused_without_opening_a_browser(self, capsys):
        exit_code = authenticate("serasa")

        assert exit_code == 1
        assert "No sign-in flow is implemented" in capsys.readouterr().out

    def test_registrato_is_the_implemented_source(self):
        assert set(AUTHENTICATED_SOURCES) == {registrato.SOURCE_ID.value}


class TestRegistratoEntryPoint:
    def test_it_opens_the_application_and_not_the_help_page(self):
        # The published Registrato page is an FAQ: opening it left a person
        # hunting for one small "Fazer login" link among help articles.
        assert registrato.ENTRY_URL == "https://meubc.bcb.gov.br/meubc/"

    def test_it_knows_how_to_confirm_the_form_rendered(self):
        # gov.br renders client-side, so a loaded page can still be blank.
        assert "accountId" in registrato.LOGIN_FORM_SELECTOR

    def test_it_states_that_a_person_completes_the_challenge(self):
        notes = registrato.SIGN_IN_NOTES.lower()
        assert "bypass" in notes or "completed by you" in notes


@pytest.mark.parametrize("source", sorted(AUTHENTICATED_SOURCES))
def test_every_declared_source_has_an_entry_url_and_notes(source):
    module = AUTHENTICATED_SOURCES[source]

    assert module.ENTRY_URL.startswith("https://")
    assert module.SIGN_IN_NOTES


class TestProfileDetection:
    def test_it_reports_a_profile_and_not_a_session(self, tmp_path):
        # The distinction the name now carries. A browser creates hundreds of
        # files the moment it starts, so a non-empty directory says one has
        # run here, never that anyone signed in.
        from credit_radar.domain.provenance import SourceId
        from credit_radar.providers.browser import has_profile, profile_dir

        root = tmp_path / "profiles"
        root.mkdir()

        assert has_profile(SourceId.BCB_REGISTRATO, root) is False

        directory = profile_dir(SourceId.BCB_REGISTRATO, root)
        (directory / "SingletonLock").write_text("", encoding="utf-8")

        assert has_profile(SourceId.BCB_REGISTRATO, root) is True

    def test_a_profile_directory_is_owner_only(self, tmp_path):
        # It holds a session, which is a credential stronger than the
        # password that produced it.
        import stat

        from credit_radar.domain.provenance import SourceId
        from credit_radar.providers.browser import profile_dir

        root = tmp_path / "profiles"
        root.mkdir()

        directory = profile_dir(SourceId.BCB_REGISTRATO, root)

        assert stat.S_IMODE(directory.stat().st_mode) == 0o700
        assert stat.S_IMODE(root.stat().st_mode) == 0o700

    def test_each_source_gets_its_own_directory(self, tmp_path):
        # A shared profile would let a script that went wrong on one source
        # act with the session of another.
        from credit_radar.domain.provenance import SourceId
        from credit_radar.providers.browser import profile_dir

        root = tmp_path / "profiles"
        root.mkdir()

        first = profile_dir(SourceId.BCB_REGISTRATO, root)
        second = profile_dir(SourceId.BCB_SGS, root)

        assert first != second
