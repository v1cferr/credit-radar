"""Credential handling, including the properties that make it safe.

Every value here is synthetic. No test in this repository may use a real
credential, CPF or personal identifier.
"""

from __future__ import annotations

import logging

import pytest

from credit_radar.credentials import (
    CREDENTIAL_SPECS,
    CredentialKey,
    CredentialStore,
    MissingCredentialError,
    secret_name,
)
from credit_radar.domain.provenance import SourceId

FAKE_CPF = "00000000000"
FAKE_PASSWORD = "synthetic-password-not-real"


@pytest.fixture
def secret_dir(tmp_path):
    return tmp_path


@pytest.fixture
def store(secret_dir):
    return CredentialStore(secret_dir=secret_dir)


def write_secret(secret_dir, source_id: SourceId, key: CredentialKey, value: str) -> None:
    (secret_dir / secret_name(source_id, key)).write_text(value, encoding="utf-8")


class TestSecretNaming:
    def test_follows_the_host_naming_convention(self):
        # Matches the existing `caddy_acme_email` shape: service, context,
        # thing. Prefixed so it cannot collide with another service's secret.
        assert (
            secret_name(SourceId.BCB_REGISTRATO, CredentialKey.CPF)
            == "credit_radar_bcb_registrato_cpf"
        )

    def test_dots_in_a_source_id_become_underscores(self):
        # A filename with a dot would still work, but the host's other
        # secrets are all snake_case and consistency is what makes a missing
        # entry obvious.
        assert "." not in secret_name(SourceId.BCB_REGISTRATO, CredentialKey.PASSWORD)


class TestDataMinimization:
    def test_no_source_asks_for_a_full_name_or_birth_date(self):
        # The point of the spec: a credential nobody requires should not be
        # provisioned at all. If a flow ever genuinely needs one, that spec
        # changes deliberately and this test changes with it.
        for spec in CREDENTIAL_SPECS.values():
            declared = spec.required | spec.optional
            assert CredentialKey.FULL_NAME not in declared
            assert CredentialKey.BIRTH_DATE not in declared

    def test_only_declared_credentials_are_loaded(self, store, secret_dir):
        write_secret(secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.CPF, FAKE_CPF)
        write_secret(secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.PASSWORD, FAKE_PASSWORD)
        # Present on disk but not declared: must be ignored, not picked up.
        write_secret(secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.FULL_NAME, "Someone")

        loaded = store.load(SourceId.BCB_REGISTRATO)

        assert set(loaded) == {CredentialKey.CPF, CredentialKey.PASSWORD}


class TestRedaction:
    def test_a_loaded_value_does_not_appear_in_its_own_repr(self, store, secret_dir):
        write_secret(secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.CPF, FAKE_CPF)
        write_secret(secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.PASSWORD, FAKE_PASSWORD)

        loaded = store.load(SourceId.BCB_REGISTRATO)

        # A traceback or a logged object must not carry the value.
        assert FAKE_PASSWORD not in repr(loaded)
        assert FAKE_CPF not in repr(loaded)
        assert FAKE_PASSWORD not in str(loaded[CredentialKey.PASSWORD])

    def test_the_value_is_still_retrievable_deliberately(self, store, secret_dir):
        write_secret(secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.CPF, FAKE_CPF)
        write_secret(secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.PASSWORD, FAKE_PASSWORD)

        loaded = store.load(SourceId.BCB_REGISTRATO)

        assert loaded[CredentialKey.PASSWORD].get_secret_value() == FAKE_PASSWORD

    def test_a_missing_credential_error_names_the_secret_and_no_value(self, store, secret_dir):
        write_secret(secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.CPF, FAKE_CPF)

        with pytest.raises(MissingCredentialError) as raised:
            store.load(SourceId.BCB_REGISTRATO)

        message = str(raised.value)
        assert "credit_radar_bcb_registrato_password" in message
        # The CPF that WAS found must not be echoed while reporting the one
        # that was not.
        assert FAKE_CPF not in message


class TestReading:
    def test_a_trailing_newline_is_stripped(self, store, secret_dir):
        # An editor adding one must not silently produce a wrong password.
        write_secret(
            secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.PASSWORD, FAKE_PASSWORD + "\n"
        )

        value = store.get(SourceId.BCB_REGISTRATO, CredentialKey.PASSWORD)

        assert value is not None
        assert value.get_secret_value() == FAKE_PASSWORD

    def test_an_empty_file_counts_as_absent(self, store, secret_dir):
        # A half-provisioned secret should fail loudly at load time rather
        # than submit an empty password to a login form.
        write_secret(secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.PASSWORD, "   ")

        assert store.get(SourceId.BCB_REGISTRATO, CredentialKey.PASSWORD) is None

    def test_a_missing_file_is_absent_and_not_an_error(self, store):
        assert store.get(SourceId.BCB_REGISTRATO, CredentialKey.CPF) is None

    def test_the_environment_is_only_a_fallback(self, store, secret_dir, monkeypatch):
        # The file wins, so a stray variable cannot override a real
        # deployment's secret.
        write_secret(secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.CPF, FAKE_CPF)
        monkeypatch.setenv("CREDIT_RADAR_SECRET_BCB_REGISTRATO_CPF", "11111111111")

        value = store.get(SourceId.BCB_REGISTRATO, CredentialKey.CPF)

        assert value is not None
        assert value.get_secret_value() == FAKE_CPF

    def test_the_environment_is_used_when_no_file_exists(self, store, monkeypatch):
        monkeypatch.setenv("CREDIT_RADAR_SECRET_BCB_REGISTRATO_CPF", FAKE_CPF)

        value = store.get(SourceId.BCB_REGISTRATO, CredentialKey.CPF)

        assert value is not None
        assert value.get_secret_value() == FAKE_CPF


class TestAvailability:
    def test_reports_presence_without_returning_values(self, store, secret_dir):
        write_secret(secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.CPF, FAKE_CPF)

        availability = store.availability(SourceId.BCB_REGISTRATO)

        assert availability == {
            CredentialKey.CPF: True,
            CredentialKey.PASSWORD: False,
        }
        assert FAKE_CPF not in repr(availability)

    def test_no_credential_value_is_ever_logged(self, store, secret_dir, caplog):
        write_secret(secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.CPF, FAKE_CPF)
        write_secret(secret_dir, SourceId.BCB_REGISTRATO, CredentialKey.PASSWORD, FAKE_PASSWORD)

        with caplog.at_level(logging.DEBUG):
            store.load(SourceId.BCB_REGISTRATO)

        logged = "\n".join(record.getMessage() for record in caplog.records)
        assert FAKE_CPF not in logged
        assert FAKE_PASSWORD not in logged


class TestNoStoredSecondFactor:
    def test_no_source_stores_an_mfa_seed(self):
        # Keeping a TOTP seed next to the password collapses two factors into
        # one. The second factor is completed by a person instead.
        vocabulary = {key.value for key in CredentialKey}
        for forbidden in ("totp", "totp_secret", "mfa_seed", "otp_secret"):
            assert forbidden not in vocabulary
