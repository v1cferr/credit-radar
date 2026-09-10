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

ENTRY_URL: Final = "https://meubc.bcb.gov.br/meubc/"
"""The application's own entry, which redirects to the gov.br sign-in.

Not guessed: it is the target of the "Fazer login" link on Banco Central's
published Registrato page, and it was verified to redirect to
`sso.acesso.gov.br/login?client_id=p-meubc.bcb.gov.br` with the CPF field
present.

An earlier version opened that published page instead, on the reasoning that
a documented door beats a deep link. In practice it is an FAQ: the way in is
one small link among accessibility notices and help articles, so the command
dropped a person onto documentation and left them to hunt for it. Preferring
the documented page was right in principle and wrong in effect.
"""

LOGIN_FORM_SELECTOR: Final = "#accountId, input[name='accountId']"
"""The gov.br CPF field, used only to confirm the form actually rendered.

gov.br is a client-side application, so a page that has finished loading can
still be blank. Handing over a blank window and saying "sign in there" is
indistinguishable, to the person looking at it, from the thing being broken.
"""

SIGN_IN_NOTES: Final = (
    "Registrato signs in through gov.br, where the CPF is the username. "
    "The second factor, and any device confirmation, are completed by you: "
    "nothing here attempts to solve or bypass a challenge."
)
