"""Provider failure taxonomy.

The distinctions here are not cosmetic. A historical dataset needs to tell
apart "the source says there is nothing for this period" from "we could not
reach the source", because the first is a fact worth recording and the
second is a gap to retry.
"""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for any failure while collecting from an external source."""


class ProviderUnavailableError(ProviderError):
    """The source could not be reached, timed out, or returned a server error.

    Transient by assumption: the request may succeed later.
    """


class ProviderNoDataError(ProviderError):
    """The source answered authoritatively that it holds no data for the request.

    Despite the name required by convention, this is a successful interaction
    with an empty result. Callers are expected to translate it into an empty
    collection plus a ``NO_DATA`` run status, not to treat it as a fault.
    """


class ProviderResponseInvalidError(ProviderError):
    """The source answered, but the payload did not match the expected contract.

    Usually means the upstream format changed and the parser needs updating.
    """
