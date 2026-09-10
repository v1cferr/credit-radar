"""Credential handling, including the properties that make it safe.

Every value here is synthetic. No test in this repository may use a real
credential, CPF or personal identifier.
"""

from __future__ import annotations

import logging
import os

import pytest

from credit_radar.credentials import (
    CREDENTIAL_SPECS,
    CredentialKey,
    CredentialOrigin,
    CredentialStore,
    MissingCredentialError,
    check_env_file_permissions,
    variable_name,
)
from credit_radar.domain.provenance import SourceId

FAKE_CPF = "00000000000"
FAKE_PASSWORD = "synthetic-password-not-real"

CPF_VAR = variable_name(SourceId.BCB_REGISTRATO, CredentialKey.CPF)
PASSWORD_VAR = variable_name(SourceId.BCB_REGISTRATO, CredentialKey.PASSWORD)


@pytest.fixture
def env_file(tmp_path):
    return tmp_path / ".env"


def write_env(path, **values: str) -> None:
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
    path.chmod(0o600)


def store_with(env_file, environ: dict[str, str] | None = None) -> CredentialStore:
    return CredentialStore(env_file=env_file, environ=environ or {})


class TestVariableNaming:
    def test_credentials_carry_their_own_prefix(self):
        # Distinct from the settings prefix, so a credential cannot be
        # mistaken for configuration when reading a `.env`, and so they group
        # together in the file.
        assert CPF_VAR == "CREDIT_RADAR_SECRET_BCB_REGISTRATO_CPF"

    def test_dots_in_a_source_id_become_underscores(self):
        assert "." not in PASSWORD_VAR


class TestDataMinimization:
    def test_no_source_asks_for_a_full_name_or_birth_date(self):
        # The point of the spec: a credential nobody requires should not be
        # provisioned at all. If a flow ever genuinely needs one, that spec
        # changes deliberately and this test changes with it.
        for spec in CREDENTIAL_SPECS.values():
            declared = spec.required | spec.optional
            assert CredentialKey.FULL_NAME not in declared
            assert CredentialKey.BIRTH_DATE not in declared

    def test_only_declared_credentials_are_loaded(self, env_file):
        write_env(
            env_file,
            **{
                CPF_VAR: FAKE_CPF,
                PASSWORD_VAR: FAKE_PASSWORD,
                # Present in the file but not declared: must be ignored.
                variable_name(SourceId.BCB_REGISTRATO, CredentialKey.FULL_NAME): "Someone",
            },
        )

        loaded = store_with(env_file).load(SourceId.BCB_REGISTRATO)

        assert set(loaded) == {CredentialKey.CPF, CredentialKey.PASSWORD}


class TestPrecedence:
    def test_the_environment_wins_over_the_file(self, env_file):
        # What lets a deployment inject a value without editing anything, and
        # a one-off override work without leaving a file behind.
        write_env(env_file, **{CPF_VAR: FAKE_CPF})
        store = store_with(env_file, {CPF_VAR: "11111111111"})

        value = store.get(SourceId.BCB_REGISTRATO, CredentialKey.CPF)

        assert value is not None
        assert value.get_secret_value() == "11111111111"

    def test_the_file_is_used_when_the_environment_has_nothing(self, env_file):
        write_env(env_file, **{CPF_VAR: FAKE_CPF})

        value = store_with(env_file).get(SourceId.BCB_REGISTRATO, CredentialKey.CPF)

        assert value is not None
        assert value.get_secret_value() == FAKE_CPF

    def test_the_origin_is_reported_accurately(self, env_file):
        write_env(env_file, **{CPF_VAR: FAKE_CPF})
        store = store_with(env_file, {PASSWORD_VAR: FAKE_PASSWORD})

        availability = store.availability(SourceId.BCB_REGISTRATO)

        assert availability == {
            CredentialKey.CPF: CredentialOrigin.ENV_FILE,
            CredentialKey.PASSWORD: CredentialOrigin.ENVIRONMENT,
        }

    def test_a_missing_file_is_not_an_error(self, tmp_path):
        store = store_with(tmp_path / "absent.env")

        assert store.get(SourceId.BCB_REGISTRATO, CredentialKey.CPF) is None


class TestRedaction:
    def test_a_loaded_value_does_not_appear_in_its_own_repr(self, env_file):
        write_env(env_file, **{CPF_VAR: FAKE_CPF, PASSWORD_VAR: FAKE_PASSWORD})

        loaded = store_with(env_file).load(SourceId.BCB_REGISTRATO)

        # A traceback or a logged object must not carry the value.
        assert FAKE_PASSWORD not in repr(loaded)
        assert FAKE_PASSWORD not in str(loaded[CredentialKey.PASSWORD])

    def test_the_value_is_still_retrievable_deliberately(self, env_file):
        write_env(env_file, **{CPF_VAR: FAKE_CPF, PASSWORD_VAR: FAKE_PASSWORD})

        loaded = store_with(env_file).load(SourceId.BCB_REGISTRATO)

        assert loaded[CredentialKey.PASSWORD].get_secret_value() == FAKE_PASSWORD

    def test_a_missing_credential_error_names_the_variable_and_no_value(self, env_file):
        write_env(env_file, **{CPF_VAR: FAKE_CPF})

        with pytest.raises(MissingCredentialError) as raised:
            store_with(env_file).load(SourceId.BCB_REGISTRATO)

        message = str(raised.value)
        assert PASSWORD_VAR in message
        # The CPF that WAS found must not be echoed while reporting the one
        # that was not.
        assert FAKE_CPF not in message

    def test_no_value_is_logged(self, env_file, caplog):
        write_env(env_file, **{CPF_VAR: FAKE_CPF, PASSWORD_VAR: FAKE_PASSWORD})

        with caplog.at_level(logging.DEBUG):
            store_with(env_file).load(SourceId.BCB_REGISTRATO)

        logged = "\n".join(record.getMessage() for record in caplog.records)
        assert FAKE_CPF not in logged
        assert FAKE_PASSWORD not in logged

    def test_reading_does_not_export_into_the_process_environment(self, env_file):
        # This application shells out to Docker and to a browser. A credential
        # that reached os.environ would be inherited by both.
        write_env(env_file, **{CPF_VAR: FAKE_CPF, PASSWORD_VAR: FAKE_PASSWORD})

        store_with(env_file).load(SourceId.BCB_REGISTRATO)

        assert CPF_VAR not in os.environ
        assert PASSWORD_VAR not in os.environ


class TestReading:
    def test_a_trailing_newline_is_stripped(self, env_file):
        # An editor adding one must not silently produce a wrong password.
        env_file.write_text(f"{PASSWORD_VAR}={FAKE_PASSWORD}   \n", encoding="utf-8")
        env_file.chmod(0o600)

        value = store_with(env_file).get(SourceId.BCB_REGISTRATO, CredentialKey.PASSWORD)

        assert value is not None
        assert value.get_secret_value() == FAKE_PASSWORD

    def test_an_empty_value_counts_as_absent(self, env_file):
        # A half-filled file should fail loudly at load time rather than
        # submit an empty password to a login form.
        write_env(env_file, **{PASSWORD_VAR: "   "})

        assert store_with(env_file).get(SourceId.BCB_REGISTRATO, CredentialKey.PASSWORD) is None

    def test_a_commented_line_is_not_read(self, env_file):
        # .env.example ships the variables commented out; uncommenting is the
        # deliberate act that provisions them.
        env_file.write_text(f"# {CPF_VAR}={FAKE_CPF}\n", encoding="utf-8")
        env_file.chmod(0o600)

        assert store_with(env_file).get(SourceId.BCB_REGISTRATO, CredentialKey.CPF) is None


class TestFilePermissions:
    def test_owner_only_passes_without_a_warning(self, env_file):
        write_env(env_file, **{CPF_VAR: FAKE_CPF})

        assert check_env_file_permissions(env_file) is None

    def test_a_group_readable_file_is_flagged(self, env_file):
        # The file holds a CPF and a password for a financial institution.
        write_env(env_file, **{CPF_VAR: FAKE_CPF})
        env_file.chmod(0o640)

        warning = check_env_file_permissions(env_file)

        assert warning is not None
        assert "chmod 600" in warning

    def test_a_world_readable_file_is_flagged(self, env_file):
        write_env(env_file, **{CPF_VAR: FAKE_CPF})
        env_file.chmod(0o644)

        assert check_env_file_permissions(env_file) is not None

    def test_the_warning_carries_no_value(self, env_file):
        write_env(env_file, **{CPF_VAR: FAKE_CPF})
        env_file.chmod(0o644)

        assert FAKE_CPF not in (check_env_file_permissions(env_file) or "")

    def test_an_absent_file_is_not_flagged(self, tmp_path):
        assert check_env_file_permissions(tmp_path / "absent.env") is None

    def test_a_permissive_file_warns_when_read(self, env_file, caplog):
        write_env(env_file, **{CPF_VAR: FAKE_CPF})
        env_file.chmod(0o644)

        with caplog.at_level(logging.WARNING):
            store_with(env_file).get(SourceId.BCB_REGISTRATO, CredentialKey.CPF)

        assert any("chmod 600" in r.getMessage() for r in caplog.records)


class TestNoStoredSecondFactor:
    def test_no_source_stores_an_mfa_seed(self):
        # Keeping a TOTP seed next to the password collapses two factors into
        # one. The second factor is completed by a person instead.
        vocabulary = {key.value for key in CredentialKey}
        for forbidden in ("totp", "totp_secret", "mfa_seed", "otp_secret"):
            assert forbidden not in vocabulary
