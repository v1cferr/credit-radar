# Interface

How the dashboard is built and what it is not allowed to do. The
architectural boundaries are in [architecture.md](architecture.md); this is
about the layer a person actually looks at.

## The rule everything else follows

**Never put a number on screen that the system does not know.**

Not a placeholder score, not an example balance, not a greyed-out chart
waiting for data. A figure on a page about someone's credit is read as a
fact about their credit, whatever label sits beside it — and a skeleton
where data will go is indistinguishable from data that failed to load.

Ten of the thirteen sections have no backend module. Each says what it will
show and which distinction it will have to preserve, and shows no digits at
all. An end-to-end test reads the body of all ten and fails on anything
shaped like a decimal, an amount or a percentage.

## Design tokens

`frontend/src/app/globals.css`. The base palette is neutral greys; chroma is
reserved for meaning, so that a coloured element always says something.

Financial state has its own tokens — `positive`, `negative`, `warning`,
`informational`, `neutral`, each with a `-subtle` background wash. Two
reasons: one place decides what "worse" looks like, and the dark theme is not
assembled one `dark:` class at a time. Components never name a raw palette
colour.

**Colour never carries meaning alone.** Every use is paired with a sign, an
icon or a word, so a reading survives colour blindness and a greyscale print
of a page someone is using to decide about money.

Contrast is tested twice. A unit test checks thirty token-and-ground
combinations across both themes against 4.5:1, reporting the ratio; axe
checks what actually renders. The unit test exists because axe only measures
combinations that appear on a page it visits. Chart strokes are held to 3:1,
the WCAG threshold for graphical objects: forcing five hues to text contrast
would flatten them all to near-black.

The theme follows the system by default and can be pinned. It is resolved by
a small blocking script before first paint, because applying it from an
effect means the first frame is light and then flips — a white flash in a
dark room.

## Numbers

`frontend/src/lib/format.ts` owns every figure that reaches the screen, and
`format.test.ts` covers it. These are pure functions and the last step before
a number about someone's money is displayed, which makes them the cheapest
correctness in the frontend to buy.

- **Values arrive as strings and are formatted from strings.** A JSON number
  is an IEEE-754 double in the browser, and "14.00" would arrive as 14.
- **The published scale is preserved.** The trailing zero in "14,00" states
  the precision the source published.
- **A difference between two rates is in percentage points.** 15,00% a.a.
  against 14,75% a.a. is `+0,25 p.p.`, and `+0,25% a.a.` would be a
  different and much smaller claim. This shipped wrong and unreachable.
- **Figures that are compared or that change in place use tabular numerals**,
  via the `numeric` utility. Proportional digits make a value jitter
  sideways as it updates and stop a column of amounts lining up.

Direction is arithmetic; whether it is good news is not. Every indicator
collected today is a cost to a borrower, so a rise is unfavourable — but a
bureau score will not be, so `favourabilityOf` takes the indicator kind
exhaustively and the first exception cannot be added without deciding.

## Freshness

One vocabulary, in `features/data-sources/freshness.ts`: `fresh`, `stale`,
`failed`, `no_data`, `never`.

It combines the outcome of the last collection attempt with its age, because
either alone misleads. A successful read from last week is not current data;
a failed attempt this morning does not make the displayed value wrong, only
unconfirmed. Before this existed, a source collected ten days ago appeared as
"Saudável" in the sources table and carried a warning on its own card.

Every page that shows a figure also shows the collection state behind it, and
the overview and the sources page open with the same summary strip.

## Charts

Grouped by the question they answer, not one per series
(`features/market/chart-panels.ts`). The most useful comparison in this
application is between the two mortgage regimes, which differ by several
percentage points and are published separately — and that comparison only
exists if both lines share an axis.

Two constraints on what may share a panel:

- **One unit**, because an axis has one. "% a.m." beside "% a.a." puts a
  monthly figure a twelfth the size of an annual one next to it.
- **One publication frequency.** Series are merged by reference date, so a
  monthly series beside a daily one would carry a value on one date in twenty
  and render as invisible dots between gaps. This is why the Selic target is
  charted alone despite sharing its unit with the financing rates.

Curve shape follows what the series is. A policy rate is a step function —
the Selic target holds one value until the next Copom decision — so it is
drawn flat and then vertical; sloping between decisions would show the rate
passing through values it never had. Everything else is drawn straight
between measurements, not as a monotone spline, which bulges past the points
it connects and would put a rate on screen that was never published.

A date where a series published nothing stays a gap. The gap is the fact.

Charts receive a date and a value per point, never whole observations.
Provenance is mandatory on a value and is shown once per indicator, on its
card; serializing it per point cost 250 KB of a 397 KB page to draw two
lines, and hydrating that was slow enough to fail assertions under load.

## Layout

Mobile-first, and the phone layout is tested as its own Playwright project so
its assertions cannot pass at desktop width for the wrong reason.

The sidebar collapses to a drawer, which puts every destination two taps away
and then offers thirteen at once. A bottom tab bar gives one-tap access to
the three sections that hold data and leaves the full map behind "Mais".
Sections that can only report their own absence do not earn a permanent place
on a phone screen.

Breakpoints are CSS, not JavaScript. A media query is already correct in the
server-rendered HTML; a JavaScript one can only be correct after hydration,
which on a phone means the first paint is wrong.

Wide content scrolls inside its own container, and that container is
keyboard-focusable — otherwise a reader who does not use a pointer cannot
reach the columns that overflow. Tables drop columns on a phone rather than
scrolling sideways, and fold provenance under the row's name instead of off
the edge of the screen.

Navigation links do not prefetch. Every route here is server-rendered on
demand against the backend, so viewport prefetching means opening one page
asks the server to render all thirteen others.

## Metadata

Everything on these surfaces is a constant.

A title, a description, an Open Graph tag and a manifest are quoted verbatim
by whatever renders a link — a chat app unfurling a URL, a crawler, an
operating system building a home-screen shortcut. None of them may contain a
score, a balance, a limit, a CPF or a collection time, and none may hint at
one either: "3 dívidas em aberto" is a fact about someone's credit.

The preview image is generated from nothing but the strings in its own file,
so it cannot leak an observation: it has no access to one. A test asserts it
is byte-identical between two requests, and reads every meta tag and link
href on five routes for anything shaped like a rate, an amount, a CPF or a
bare eleven-digit number. A companion test asserts the figures *do* appear in
the body, so the suite cannot pass by the dashboard having nothing to say.

The application is `noindex, nofollow, nocache`.

## Information architecture

`components/app-shell/navigation.ts` is the single source of truth for the
sections, and page titles, the overview's list of what is missing and each
planned page all derive from it. A page that restated its own name would
eventually disagree with the menu linking to it, and the browser tab is
exactly where nobody notices.

`NavItem` is a discriminated union: a section that is not implemented cannot
be declared without saying what it is waiting on. "Coming soon" is not
information, and a placeholder that has forgotten its own blocker is how one
becomes permanent.

## Quality gate

```bash
cd frontend
pnpm lint
pnpm exec tsc --noEmit
pnpm test:unit    # pure functions, tokens, content invariants
pnpm build
pnpm test:e2e     # builds first, then browser -> Next -> FastAPI -> PostgreSQL
```

`test:e2e` builds before Playwright starts, and that ordering is load-bearing.
Playwright launches `webServer` entries *before* global setup, so building
inside global setup replaces `.next` underneath three running `next start`
processes, which go on serving chunk names from the previous build. The
browser then receives pages whose stylesheet and scripts 404, and it reads as
a scatter of product bugs — a phone tab bar on a desktop screen, a chart with
no line, a drawer that will not open, a table overflowing its card. None of
it reproduces when a single spec is run, because then nothing was rebuilt.
