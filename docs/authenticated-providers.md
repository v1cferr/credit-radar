# Authenticated providers

How CreditRadar reaches data that sits behind a login, and the division of
labour that keeps identifiers out of this repository.

## The model: you export, the application ingests

Consumer financial portals protect their sign-in against automation. That was
measured rather than assumed, on the source that mattered most: gov.br gates
every Registrato login path behind invisible hCaptcha, and a driven browser is
refused. See [registrato.md](providers/registrato.md) for the evidence.

So authenticated sources are reached the way the acquisition strategy already
preferred, and the browser detour was abandoned:

```text
you, in your ordinary browser  ->  the source  ->  download the export
                                                       |
                                                       v
                                    credit-radar imports the file
```

| | |
| --- | --- |
| **You** | sign in normally, in your own browser, and download the report |
| **This repository** | the parser, the domain model, the provenance |
| **The application** | holds no credential, no session and no CPF |

**CreditRadar stores no credentials at all.** Not in a file, not in a secret
manager, not in a browser profile. There is nothing to leak, rotate, or keep
out of a backup. The credential layer and the browser-session layer were both
built and then removed, because once the login is not automated nothing needs
them.

That also removes the failure mode that was going to hurt most: gov.br
sessions are short, so an automated collector would have required a person to
re-authenticate every few hours. The collection cadence for an authenticated
source is "whenever you export", and it always was.

## What a person still does, and what is never done

CAPTCHA, MFA, gov.br confirmation and device approval are **completed by
you, in your own browser**. Nothing in this repository attempts to solve,
score around or circumvent any of them, and no code path exists that could.
That is permanent, not pending a better idea.

## Getting a report in

The parser is written against a redacted fixture, never against a real
report. A real report is a CPF plus a full credit history, and must not be
shared with an assistant, pasted into a conversation, or committed.

```bash
cd backend
uv run python scripts/redact_capture.py ~/Downloads/report.pdf \
  --out tests/fixtures/registrato/report.json
```

It replaces identifiers and amounts with synthetic values while keeping the
structure, prints what it changed, and over-redacts where a field is
ambiguous. **Review the output before committing it**: it is a first pass by
a machine over a document only you have seen.

## If this ever becomes a product

Worth writing down, because the answer changes and the current design should
not be mistaken for the eventual one.

Today there is no application login, and the substitute is reach: the service
binds to loopback and the reverse proxy answers 403 to anything that is not
the home network. Adequate for one trusted user on one machine, and adequate
for nothing else.

A multi-user version needs an application login with sessions, a subject
entity so observations belong to someone rather than being implicitly the only
person's, per-subject authorization on every query, and encrypted per-subject
storage for anything uploaded. The data model is the piece that changes most:
it assumes exactly one subject, which is why a CPF is not a column anywhere.

**Open Finance Brasil** is the interface that would replace manual exports
entirely, and it requires being an authorized, certified participant. That is
a regulatory step rather than a technical one, and it is the legitimate path
if the product question becomes real.

## Legal and terms of service

Reading your own data, from your own account, that you exported yourself. No
security mechanism is bypassed, no other person's data is touched, no access
is resold, and nothing that creates a financial obligation is automated.
Where a source offers an export, that is used in preference to automation,
which after this investigation means every authenticated source.
