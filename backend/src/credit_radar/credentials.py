"""Credentials for authenticated sources, and the rules for handling them.

Read from the environment, with a `.env` file as the local source. One
mechanism, because it is the one that travels: a `.env` while this is a
personal tool, injected variables under Docker or systemd, and whatever a
platform provides if this ever becomes a product. Nothing here is tied to
the host it currently runs on.

That also keeps sops available rather than ruling it out. sops-nix renders an
env file and systemd injects it with `EnvironmentFile=`, which is how Caddy's
secrets already reach it on this machine, so choosing environment variables
loses no option.

Three properties this module exists to guarantee.

**Nothing is stored in this repository.** `.env` is git-ignored and
`.env.example` holds placeholders only. The repository holds the NAME of a
credential and never its value, which is also why no assistant working on
this code ever needs to see one.

**Nothing is logged.** Values are wrapped in ``SecretStr``, so a traceback or
a printed object shows ``**********``. Error messages name what is missing
and never quote what was found. Values are never copied into ``os.environ``,
so a subprocess does not inherit them.

**Nothing is loaded that is not required.** Each source declares exactly
which credentials its login flow needs, and only those are read. Full name
and date of birth are declared by NO source, because no login flow needs
them, and a credential nobody requires is pure liability.
"""

from __future__ import annotations

import logging
import os
import stat
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, SecretStr

from credit_radar.domain.provenance import SourceId

logger = logging.getLogger(__name__)

ENV_PREFIX = "CREDIT_RADAR_SECRET_"
"""Distinct from the settings prefix, so a credential cannot be mistaken for
configuration when reading a `.env` file, and so they group together in it."""

DEFAULT_ENV_FILE = Path(".env")
"""Relative to the backend working directory, the same file the application's
settings read. One file to edit, one file to protect."""


class CredentialKey(StrEnum):
    """A kind of credential a login flow can require.

    The vocabulary, not the requirement: what any given source actually needs
    is declared in ``CREDENTIAL_SPECS``, and only that is ever read.
    """

    CPF = "cpf"
    """Required only where the CPF IS the username, which is the gov.br case.

    Deliberately a credential and not a domain attribute. This is a
    single-user system, so there is exactly one person the data describes and
    the CPF never needs to be a database column; the only reason the number
    exists here is that a login form asks for it.
    """

    PASSWORD = "password"
    USERNAME = "username"
    """An e-mail or account identifier, for sources that do not use the CPF."""

    FULL_NAME = "full_name"
    """Declared by no source. Kept in the vocabulary because identity
    verification forms sometimes ask for it, but nothing loads it today and
    it should not be provisioned until something does."""

    BIRTH_DATE = "birth_date"
    """Declared by no source, for the same reason as FULL_NAME."""


class CredentialOrigin(StrEnum):
    """Where a value was found. Reported so the wiring can be checked."""

    ENVIRONMENT = "environment"
    ENV_FILE = "env file"
    ABSENT = "absent"


class MissingCredentialError(RuntimeError):
    """A required credential is not available.

    Names what is missing and where it was looked for. Never includes a
    value, and never a partial one.
    """


class CredentialSpec(BaseModel):
    """What one source's login flow requires."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: SourceId
    required: frozenset[CredentialKey]
    optional: frozenset[CredentialKey] = frozenset()
    notes: str = ""


CREDENTIAL_SPECS: dict[SourceId, CredentialSpec] = {
    SourceId.BCB_REGISTRATO: CredentialSpec(
        source_id=SourceId.BCB_REGISTRATO,
        required=frozenset({CredentialKey.CPF, CredentialKey.PASSWORD}),
        notes=(
            "gov.br sign-in, where the CPF is the username. The second factor "
            "is completed by a person: no MFA seed is stored, because keeping "
            "one next to the password would collapse two factors into one."
        ),
    ),
}
"""Which credentials each authenticated source needs.

Only sources with an implemented or in-progress login flow appear here. A
spec for a source nobody has built yet would be a guess about a form nobody
has looked at, and it would ask for secrets that may turn out to be
unnecessary.

The credit bureaus are absent on purpose. Their consumer portals sign in with
an e-mail and a password rather than a CPF, but the exact requirement is
confirmed by implementing the flow, not by assuming it.
"""


def variable_name(source_id: SourceId, key: CredentialKey) -> str:
    """Return the environment variable holding one credential."""
    source = source_id.value.replace(".", "_")
    return f"{ENV_PREFIX}{source}_{key.value}".upper()


def check_env_file_permissions(path: Path) -> str | None:
    """Return a warning if the file is readable beyond its owner.

    A `.env` here holds a CPF and a password for a financial institution. It
    lives on disk rather than on a tmpfs, so unlike a decrypted secret it can
    also persist in local filesystem snapshots after deletion. Owner-only is
    the least that should be true of it.
    """
    if not path.is_file():
        return None

    mode = path.stat().st_mode
    if mode & (stat.S_IRGRP | stat.S_IROTH | stat.S_IWGRP | stat.S_IWOTH):
        return (
            f"{path} is readable or writable beyond its owner "
            f"({stat.filemode(mode)}). Run: chmod 600 {path}"
        )
    return None


class CredentialStore:
    """Reads credentials from the environment and from a `.env` file."""

    def __init__(
        self,
        *,
        env_file: Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self._env_file = env_file if env_file is not None else DEFAULT_ENV_FILE
        self._environ = environ if environ is not None else os.environ
        self._file_values: dict[str, str] | None = None

    def _from_file(self) -> dict[str, str]:
        """Parse the env file once, keeping values out of ``os.environ``.

        Deliberately not exported into the process environment: a credential
        that lives only in this object cannot be inherited by a subprocess,
        and this application shells out to Docker and to a browser.
        """
        if self._file_values is None:
            if self._env_file.is_file():
                warning = check_env_file_permissions(self._env_file)
                if warning:
                    logger.warning("%s", warning)
                self._file_values = {
                    key: value
                    for key, value in dotenv_values(self._env_file).items()
                    if value is not None
                }
            else:
                self._file_values = {}
        return self._file_values

    def locate(self, source_id: SourceId, key: CredentialKey) -> CredentialOrigin:
        """Report where a credential would be read from, without reading it."""
        name = variable_name(source_id, key)
        if (self._environ.get(name) or "").strip():
            return CredentialOrigin.ENVIRONMENT
        if (self._from_file().get(name) or "").strip():
            return CredentialOrigin.ENV_FILE
        return CredentialOrigin.ABSENT

    def get(self, source_id: SourceId, key: CredentialKey) -> SecretStr | None:
        """Return one credential, or None when it is not available.

        The process environment wins over the file, which is what lets a
        deployment inject a value without editing anything, and lets a
        one-off override work without leaving a file behind.
        """
        name = variable_name(source_id, key)

        # Trailing whitespace is stripped: an editor adding a newline must not
        # silently produce a wrong password.
        for candidate in (self._environ.get(name), self._from_file().get(name)):
            if candidate and candidate.strip():
                return SecretStr(candidate.strip())
        return None

    def load(self, source_id: SourceId) -> dict[CredentialKey, SecretStr]:
        """Load exactly the credentials a source declares, and no others.

        Raises:
            MissingCredentialError: a required credential is unavailable.
            KeyError: the source declares no credential spec.
        """
        spec = CREDENTIAL_SPECS[source_id]

        loaded: dict[CredentialKey, SecretStr] = {}
        missing: list[str] = []

        for key in sorted(spec.required, key=lambda k: k.value):
            value = self.get(source_id, key)
            if value is None:
                missing.append(variable_name(source_id, key))
            else:
                loaded[key] = value

        if missing:
            raise MissingCredentialError(
                f"{source_id.value} is missing {len(missing)} credential(s): "
                f"{', '.join(missing)}. Set them in the environment or in "
                f"{self._env_file}."
            )

        for key in sorted(spec.optional, key=lambda k: k.value):
            value = self.get(source_id, key)
            if value is not None:
                loaded[key] = value

        return loaded

    def availability(self, source_id: SourceId) -> dict[CredentialKey, CredentialOrigin]:
        """Report where each of a source's declared credentials comes from.

        Origins only. Never returns, logs or compares a value, so this is
        safe to print and is what the `credentials` command reports.
        """
        spec = CREDENTIAL_SPECS[source_id]
        keys = sorted(spec.required | spec.optional, key=lambda k: k.value)
        return {key: self.locate(source_id, key) for key in keys}
