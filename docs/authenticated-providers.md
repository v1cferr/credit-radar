# Authenticated providers

How CreditRadar reaches data that sits behind a login, and the division of
labour that keeps identifiers out of this repository.

## Who does what

| | |
| --- | --- |
| **This repository** | the *name* of a variable, the code that reads it, the login flow, the parser |
| **`backend/.env`** | the *value*, written by the person it belongs to. Git-ignored |
| **The environment** | the same variables, when a deployment injects them instead |
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

## Provisioning a credential

```bash
cd backend
cp .env.example .env      # if you have not already
chmod 600 .env
$EDITOR .env              # uncomment and fill only what a source declares
uv run credit-radar credentials
```

`credentials` reports where each declared value comes from, and never prints,
compares or validates one, so its output is safe to share.

### Why environment variables and not a host secret manager

One mechanism, because it is the one that travels. A `.env` while this is a
personal tool; injected variables under Docker or systemd; whatever a
platform provides if this ever becomes a product. Nothing about credential
handling is tied to the machine it currently runs on, which would not be true
of a host-specific secret store.

It also keeps sops available rather than ruling it out: sops-nix renders an
env file and systemd injects it with `EnvironmentFile=`, which is already how
Caddy's secrets reach it on this host. Choosing environment variables loses
no option.

The environment wins over the file, so a deployment can inject a value
without editing anything, and a one-off override needs no file at all.

### What the file costs

A filled-in `.env` holds a CPF and a password for a financial institution,
and unlike a decrypted secret on a tmpfs it is a real file on a real disk.
Two consequences:

- **It can outlive its deletion.** Local filesystem snapshots (btrfs, Time
  Machine, anything hourly) keep a copy until they rotate. An encrypted
  off-site backup is a smaller concern, since the copy is encrypted, but a
  plain local snapshot is not.
- **Permissions matter.** The application warns, once, when the file is
  readable beyond its owner, with the `chmod` to fix it.

Values are never copied into `os.environ`, because this application shells
out to Docker and to a browser and a subprocess would inherit them.

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

## Authenticated providers run on the host, not in the container

Settled. The sign-in step is interactive and needs a visible browser, which
is inherently host-bound: a headed browser inside a container needs display
forwarding, and the whole point of the step is that a person interacts with
it.

Splitting sign-in from collection would mean a session file crossing that
boundary and half a gigabyte of browser added to an image that never runs it.
So the entire authenticated path stays on the host, and the session never
leaves it. The container keeps serving the API and collecting public market
data, which needs no browser at all.

Playwright is therefore an optional extra rather than a dependency:

```bash
cd backend && uv sync --extra rpa
```

The consequence to remember: when scheduled collection from an authenticated
source arrives, its timer runs against the host installation, not through
`docker compose exec` the way the market collector does.

### Signing in

```bash
credit-radar auth bcb.registrato
```

Opens Registrato's own entry page in a visible browser and stops. It types
nothing, reads nothing while you sign in, and has no code path that could
answer a challenge. When you are done it keeps the session.

It will also tell you that the session is stored but **not verified**,
because collection from that source is not implemented yet. Reporting success
for a collection that did not happen is the kind of false confidence this
project exists to avoid.

Sessions live under `~/.local/state/credit-radar/browser-profiles/<source>`,
one directory per source, owner-only. A single profile shared between bureaus
would let a script that went wrong on one act with the session of another.

Chromium comes from the development shell through
`CREDIT_RADAR_CHROMIUM_PATH`, the same variable the E2E suite uses, because
the binaries Playwright downloads are linked against paths that do not exist
on NixOS.

## Parsers need a sanitized sample, and that is a real constraint

A parser cannot be written without knowing the format, and the format is
visible only in a real report, which contains a CPF, a name and a complete
credit history. That report must not be shared with an assistant, pasted into
a conversation, or committed.

The way through is a redaction tool that **you** run, on your machine, over
your file:

```bash
cd backend
uv run python scripts/redact_capture.py report.json --out fixture.json
```

It replaces CPFs, CNPJs, e-mails, phone numbers, names, birth dates and
amounts with synthetic values while keeping the structure a parser is written
against. Replacements match the original length, so a fixed-width or
column-aligned format still parses. Numbers that carry no identity, like an
instalment count or a rate, are left alone, because changing everything would
destroy the shape the parser needs.

It prints what it changed, and **it over-redacts where a field is
ambiguous**. A `nome` can hold the account holder or an institution, and only
you can tell which, so both are replaced with a marker that reads as redacted
rather than as somebody's name. Restoring a value that was never personal is
safe; the reverse is not.

**Review the output before committing it.** The tool is a first pass by a
machine over a document only you have seen, so it cannot be the last word on
whether the file is safe.

That ordering is not a formality. A parser written against a real document
that nobody may look at is a parser nobody can review.

## If this ever becomes a product

Worth writing down now, because the answer changes and the current design
should not be mistaken for the eventual one.

Today there is **no application login**, and the substitute is reach: the
service binds to loopback and the reverse proxy answers 403 to anything that
is not the home network. That is adequate for one trusted user on one machine
and adequate for nothing else.

A multi-user version needs, in roughly this order: an application login with
sessions, a subject entity so observations belong to someone rather than
being implicitly the only person's, per-subject authorization on every query,
and encrypted per-subject credential storage instead of one shared file.
The credential layer is the piece that changes least, since it already reads
from an injected environment rather than from anything host-specific.

The piece that changes most is the data model. It currently assumes exactly
one subject, which is why the CPF is a credential and not a column: that
assumption is documented and cheap to hold now, and it is the thing to revisit
first, not last, if the product question ever becomes real.

## Legal and terms of service

Automating one's own authenticated account, for personal use, reading one's
own data. No security mechanism is bypassed, no other person's data is
accessed, no access is resold or redistributed, and nothing is automated that
creates a financial obligation. Where a source offers an official export or
API, that is used in preference to automation, which is why Registrato comes
before the bureaus: it produces a downloadable report rather than a page to
scrape.
