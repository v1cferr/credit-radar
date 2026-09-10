"""Credentials for authenticated sources, and the rules for handling them.

Three properties this module exists to guarantee.

**Nothing is stored in this repository.** A credential is read at runtime
from the host's secret directory, delivered there by sops from Bitwarden.
The repository holds the NAME of a secret and never its value, which is also
why no assistant working on this code ever needs to see one.

**Nothing is logged.** Values are wrapped in ``SecretStr``, so a traceback or
a printed object shows ``**********``. Error messages name the missing secret
and never quote what was found.

**Nothing is loaded that is not required.** Each source declares exactly
which credentials its login flow needs, and only those are read. This is
the point worth stating plainly: full name and date of birth are declared by
NO source here, because no login flow needs them. A credential nobody
requires should not be provisioned at all.
"""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, SecretStr

from credit_radar.domain.provenance import SourceId

DEFAULT_SECRET_DIR = Path("/run/secrets")
"""Where sops-nix places decrypted secrets on the host.

Read at runtime and never at build time: /nix/store is world-readable, so a
secret interpolated into a derivation would leak.
"""

ENV_PREFIX = "CREDIT_RADAR_SECRET_"
"""Environment fallback, for development against a throwaway account.

Checked after the secret directory, so a real deployment cannot be
accidentally overridden by a stray variable.
"""


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


class MissingCredentialError(RuntimeError):
    """A required credential is not available.

    Names the secret that is missing and where it was looked for. Never
    includes a value, and never a partial one.
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


def secret_name(source_id: SourceId, key: CredentialKey) -> str:
    """Return the host-wide name of a secret.

    Follows the naming already used on this host (``caddy_acme_email``,
    ``caddy_cloudflare_dns_token``): the service, then the context, then the
    thing. Prefixed so it cannot collide with another service's secret.
    """
    source = source_id.value.replace(".", "_")
    return f"credit_radar_{source}_{key.value}"


class CredentialStore:
    """Reads credentials from the host's secret directory."""

    def __init__(self, secret_dir: Path | None = None) -> None:
        self._secret_dir = secret_dir if secret_dir is not None else DEFAULT_SECRET_DIR

    def _read(self, name: str) -> SecretStr | None:
        path = self._secret_dir / name
        try:
            # Trailing newlines are stripped: an editor adding one must not
            # silently produce a wrong password.
            content = path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError):
            content = ""

        if content:
            return SecretStr(content)

        from_env = os.environ.get(f"{ENV_PREFIX}{name.removeprefix('credit_radar_').upper()}")
        return SecretStr(from_env.strip()) if from_env and from_env.strip() else None

    def get(self, source_id: SourceId, key: CredentialKey) -> SecretStr | None:
        """Return one credential, or None when it is not available."""
        return self._read(secret_name(source_id, key))

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
                missing.append(secret_name(source_id, key))
            else:
                loaded[key] = value

        if missing:
            raise MissingCredentialError(
                f"{source_id.value} is missing {len(missing)} credential(s): "
                f"{', '.join(missing)}. Expected under {self._secret_dir} "
                f"or as {ENV_PREFIX}* in the environment."
            )

        for key in sorted(spec.optional, key=lambda k: k.value):
            value = self.get(source_id, key)
            if value is not None:
                loaded[key] = value

        return loaded

    def availability(self, source_id: SourceId) -> dict[CredentialKey, bool]:
        """Report which of a source's declared credentials are present.

        Presence only. Never returns, logs or compares a value, so this is
        safe to print and is what the `credentials` command reports.
        """
        spec = CREDENTIAL_SPECS[source_id]
        keys = sorted(spec.required | spec.optional, key=lambda k: k.value)
        return {key: self.get(source_id, key) is not None for key in keys}
