# Authenticated providers

How CreditRadar reaches data that sits behind a login, and the division of
labour that keeps identifiers out of this repository.

## Who does what

| | |
| --- | --- |
| **This repository** | the *name* of a secret, the code that reads it, the login flow, the parser |
| **The password manager** | the *value*, entered by the person it belongs to |
| **sops / `/run/secrets`** | delivery to the running process, at runtime |
| **A person, once per session** | the second factor, and the gov.br confirmation |

The consequence worth stating: **nobody working on this code needs to see a
credential, and no assistant should ever be given one.** An agent
conversation is a transcript; a value pasted into one has left its owner's
control regardless of what happens next. A task that appears to require a
real identifier is a task that is wrong: use a synthetic fixture.

## Only what a login form actually asks for

`credit_radar.credentials` declares, per source, exactly which credentials
its flow needs, and loads only those. Running the check reports what is
present without printing anything:

```bash
credit-radar credentials
```

Today the declared requirement is:

| Source | Needs | Why |
| --- | --- | --- |
| `bcb.registrato` | CPF, password | gov.br sign-in, where the **CPF is the username** |

**Full name and date of birth are declared by nothing, and should not be
provisioned.** They are in the credential vocabulary because identity
verification forms sometimes ask for them, but no login flow here does. A
credential nobody requires is pure liability.

The credit bureaus are deliberately absent from that table. Their consumer
portals sign in with an e-mail and a password rather than a CPF, but the
exact requirement gets confirmed by implementing the flow, not by guessing at
a form nobody has opened yet.

### The CPF is a credential, not domain data

It appears here only because a login form asks for it. It is **not** a
database column and must not become one: this is a single-user system, so
there is exactly one person the data describes, and every debt, score and
exposure record belongs to that person by construction.

## Provisioning a secret

Following the host's existing chain, which already carries Caddy's ACME and
Cloudflare secrets:

1. Create the entry in Bitwarden, value in the *password* field.
2. Add its name to `secrets/bitwarden-secrets.json` in the dotfiles repo.
3. `sync-secrets`, then rebuild, so `/run/secrets` updates.
4. `credit-radar credentials` to confirm presence.

Secrets are read at runtime and never at build time, because `/nix/store` is
world-readable and a value interpolated into a derivation would leak.

## The second factor is never stored

No MFA seed, TOTP secret or recovery code is kept anywhere. Storing a TOTP
seed next to the password collapses two factors into one and turns a single
compromised secret store into a full account takeover.

CAPTCHA, MFA, gov.br confirmation and device approval are **never bypassed**.
The intended flow is human-assisted:

```text
credit-radar auth bcb.registrato
  -> opens a visible browser
  -> fills what it is allowed to fill
  -> STOPS and waits for the person to complete the second factor
  -> saves the authenticated session
```

Later collections reuse that session. When it expires the system **asks
again** rather than attempting to work around the challenge.

## An authenticated session is a credential

A saved browser profile is equivalent to the password it was obtained with,
and often better than it, since it is already past the second factor. So:

- one isolated profile per source, never shared;
- git-ignored, and encrypted at rest where practical;
- treated as a secret in logs, backups and error reports;
- screenshots off by default, because a screenshot of a bureau page *is* a
  credit report.

## The open decision: where the browser runs

Not settled, and worth settling before the first flow is written.

The first sign-in needs a **visible** browser, which is naturally a host
concern: a headed browser inside a container needs display forwarding, and
the point of the step is that a person interacts with it. Later collection
could run headless, either on the host or in the container with the session
shared through a mount.

The trade is between one runtime with awkward display handling, and two
runtimes with a session file crossing between them. It is written down here
rather than decided by whichever one gets built first.

## Parsers need a sanitized sample, and that is a real constraint

A parser cannot be written without knowing the format, and the format is
visible only in a real report, which contains a CPF, a name and a complete
credit history. That report must not be shared with an assistant, pasted into
a conversation, or committed.

The way through is a **redaction tool run by the person who owns the data**:
it takes the real report, replaces identifiers and values with synthetic
ones, keeps the *structure*, and produces a fixture that is safe to commit
and to review. The parser is then written and tested against that fixture,
exactly as the Banco Central SGS parsers are today.

That ordering is not a formality. A parser written against a real document
that nobody may look at is a parser nobody can review.

## Legal and terms of service

Automating one's own authenticated account, for personal use, reading one's
own data. No security mechanism is bypassed, no other person's data is
accessed, no access is resold or redistributed, and nothing is automated that
creates a financial obligation. Where a source offers an official export or
API, that is used in preference to automation, which is why Registrato comes
before the bureaus: it produces a downloadable report rather than a page to
scrape.
