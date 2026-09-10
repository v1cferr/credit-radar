"""Banco Central Registrato: the credit exposure held under a CPF.

Registrato is the highest-preference AUTHENTICATED source in this project's
acquisition strategy, and the reason is the integration tier rather than the
institution: it produces a downloadable report, which is tier three, while
every bureau portal is a page to scrape, which is tier five. A report has a
format that can be parsed and versioned; a page has a DOM that changes
without notice.

What this module owns today is the sign-in handoff. It deliberately does NOT
contain post-login navigation, because that would mean selectors written
against a page nobody has opened, which is a guess that looks like code. The
navigation is written after a first sign-in, against a redacted capture that
the account holder produces themselves.
"""

from __future__ import annotations

from typing import Final

from credit_radar.domain.provenance import SourceId

SOURCE_ID: Final = SourceId.BCB_REGISTRATO

ENTRY_URL: Final = "https://www.bcb.gov.br/meubc/registrato"
"""The documented entry page, not a deep link into the application.

Deliberate. The application URL has moved before and answers 503 to a plain
client, while this page is Banco Central's own published starting point and
carries the current link. Opening the documented door is also the honest
shape for a flow a person completes.
"""

SIGN_IN_NOTES: Final = (
    "Registrato signs in through gov.br, where the CPF is the username. "
    "The second factor, and any device confirmation, are completed by you: "
    "nothing here attempts to solve or bypass a challenge."
)
