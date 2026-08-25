# xAI Finance Dashboard — Design Directions

## Approach 1

**Theme Name:** The Analyst’s Ledger

**Very Brief Intro:** A composed, editorial finance workspace that pairs a restrained ink-and-paper palette with fast, data-dense interactions. It conveys confidence through hierarchy, not spectacle.

**Probability:** 0.06

## Approach 2

**Theme Name:** Signal Glasshouse

**Very Brief Intro:** A luminous, translucent market observatory with low-key gradients and suspended cards. It turns real-time financial research into a calm, futuristic ritual.

**Probability:** 0.03

## Approach 3

**Theme Name:** Modern Exchange

**Very Brief Intro:** A warm institutional dashboard informed by high-end research terminals and contemporary newspaper layouts. It frames AI insight as a clear investment briefing rather than a chat toy.

**Probability:** 0.08

# Chosen Direction — The Analyst’s Ledger

## Design Movement

**Contemporary editorial data design**: the discipline of an institutional research note, softened by the material restraint of premium financial publications. It should feel analytical, focused, and distinctly human rather than like a generic SaaS console.

## Core Principles

1. **Information is the atmosphere.** Numerical change, source labels, and confidence states create the visual rhythm; ornament is deliberately spare.
2. **Editorial hierarchy over widget uniformity.** A tall hero quote, a left-rail research index, and staggered data blocks prevent the dashboard from becoming a grid of identical cards.
3. **Calm authority.** Off-black ink, soft ivory, paper-gray, and one crisp electric teal direct attention without visual noise.
4. **Tactile precision.** Hairline rules, inset data rows, measured whitespace, and subtle grain produce a considered research-desk feeling.

## Color Philosophy

The primary surface is **warm paper** rather than pure white: it reduces glare during long research sessions and makes data feel editorial. Graphite creates strong reading contrast. A single **signal teal** anchors live status, positive moves, selected controls, and key chart moments. Vermilion is reserved only for downside movement and errors, preserving semantic clarity.

## Layout Paradigm

The page behaves like a **research desk spread**. A compact top masthead controls global context. Below it, a slender, persistent research rail gives the page a directional spine; the main workspace uses two unequal columns: a broader market-and-analysis column and a narrower conversational intelligence column. On smaller screens, this sequence becomes a deliberate vertical brief rather than a squeezed desktop grid.

## Signature Elements

1. **Ledger rulework:** fine horizontal lines, small uppercase labels, and tabular numerals recur in cards, conversation labels, and metadata.
2. **Signal tabs:** compact teal line markers and circular active indicators identify the selected ticker and active data state.
3. **Editorial pull quote:** the AI analysis begins with a large serif lead sentence, lending the generated briefing the cadence of a research note.

## Interaction Philosophy

Interactions should reward intentional research behavior. Search is direct and keyboard-friendly, ticker choices are compact, and chat suggestions seed high-value questions. Tooltips and disabled states explain unavailable backend information honestly; no fabricated data is presented as live data.

## Animation

Use short, mostly transform-and-opacity transitions with the easing `cubic-bezier(0.23, 1, 0.32, 1)`. Data cards should make a restrained 10–14px rise on initial load, staggered by 45ms; button presses compress to `scale(0.97)` over 140ms. Loading states use thin sweeping lines rather than large spinners. Animations are disabled for `prefers-reduced-motion`.

## Typography System

**DM Sans** carries interface text, labels, navigation, and numeric data in 400/500/600/700 weights. **DM Serif Display** is reserved for the analysis lead, selected company name, and strategic editorial moments. Use tabular figures for all prices and percentages. Labels are 10–11px, wide-tracked, uppercase; body copy is 14–15px; headlines are compact but high contrast.

## Brand Essence

**An AI research desk for investors who want market context, source-aware analysis, and decisive financial conversation in one disciplined workspace.**

**Personality:** Exacting, composed, perceptive.

## Brand Voice

Headlines are declarative and research-led; CTAs are concise, precise verbs; microcopy speaks plainly about source or backend status.

> “Turn a ticker into a research brief.”

> “Ask the agent to pressure-test the thesis.”

## Wordmark & Logo

The mark is an **offset aperture**: two stacked, inset ledger brackets pierced by a precise teal signal stroke. It suggests a focused research window and a market quote simultaneously. The wordmark combines a compact DM Sans “xAI” with a serif “Finance” in a deliberate editorial contrast.

## Signature Brand Color

**Signal Teal — `#0E8F83`**: a sober, high-clarity blue-green that represents verified attention, live market movement, and the active research state.

## Style Decisions

- Unavailable data is presented as structured research protocol: source labels, timestamp slots, ledger bands, and explicit awaiting-source states replace large empty areas.
- Every research brief opens with a large **DM Serif Display** pull quote—live when agent text is present and a purposeful research-note prompt before the first request.
- The offset aperture becomes a repeated brand device: it appears as a bracketed source marker, active status row, and compact signal stroke across the hero, snapshot, chart, analysis, news, and AI desk.
- QuantAI remains the primary product identity because it is the current user-required brand; historical xAI references are not used as primary interface branding.
- Signal Teal is reserved for verified source markers, active research lanes, selected states, and high-attention market signals rather than general ornament.
- The conversational rail uses research-protocol language: it asks users to pressure-test a thesis, trace the source lane, or separate evidence from interpretation.

## Phase 7 Design Direction — The Research Observatory

**Design Movement:** A contemporary financial terminal interpreted through editorial publishing: dark graphite control surfaces, paper-like light research views, and data sheets that earn attention through typographic hierarchy rather than visual spectacle.

**Core Principles:** First, research state is visible but never theatrical. Second, data and provenance lead every composition; controls and decoration recede. Third, light and dark are separate intentional environments rather than inversions. Fourth, tight rules, numerical alignment, and restrained color create the sense of a considered professional instrument.

**Color Philosophy:** The dark environment is graphite and carbon with a calm indigo-blue action signal; green and red communicate price direction only. The light environment is mineral white with warm-gray rules and charcoal reading text. Signal Teal remains a provenance accent, not the default interaction color. Violet is reserved for no factual meaning and therefore omitted from market-state treatments.

**Layout Paradigm:** The product behaves as a research workstation: a slim persistent command masthead, a contextual workflow rail on wide screens, and a report canvas with deliberate section rhythm. Narrow widths collapse into a task-first sequence with no desktop tables forced into the viewport.

**Signature Elements:** A precise horizontal baseline under active workflow navigation; compact research-state capsules that disclose source/freshness rather than decoration; and a stacked A/B comparison treatment that shifts from ledger table to paired metric notes on mobile.

**Interaction Philosophy:** Every interaction should feel like operating research equipment: immediate focus, short feedback, clear unavailable states, and no fake progress. Theme choice is a visible user preference rather than a novelty control.

**Animation:** A one-time 1.2-second startup reveal combines the existing aperture mark with a single moving price-line trace. The primary app fades in only after the signal completes. All non-essential movement is removed under `prefers-reduced-motion`; regular interactions use 120–220ms opacity/transform transitions only.

**Typography System:** Keep DM Sans for navigation and precise interface text, DM Serif Display for editorial assessment moments, and DM Mono for numbers, source states, and market labels. Numeric columns must use tabular figures; labels remain compact, tracked, and quiet.

**Brand Essence:** QuantAI is a focused financial research workstation for people who need to separate sourced evidence from interpretation before making a decision.

**Personality:** Exacting, calm, discerning.

**Brand Voice:** Headlines sound like research desk headings; CTAs are direct operational verbs; microcopy explains status without technical jargon. Example: “Compare the evidence, not the narrative.” Example: “Sources are available where the record supports them.”

**Wordmark & Logo:** Preserve the existing aperture mark, now set against a quiet command-bar field. The mark opens the startup trace and remains the unique anchor of the navigation.

**Signature Brand Color:** **Research Indigo — `#6D7CFF`**, used only for primary workflow action and current workspace context; Signal Teal remains provenance-specific.

## Phase 1 Design Direction — Evidence Briefing

### Three considered approaches

| Theme Name | Very Brief Intro | Probability |
|---|---|---:|
| Terminal Ledger | A denser dark research workstation with clear data rails and compact terminal conventions. It would preserve speed, but risks retaining too much technical density. | 0.07 |
| Evidence Briefing | A warm editorial research document that sequences search, market facts, signals, and sourced reporting. Evidence is available when needed, rather than repeated inside every primary datum. | 0.04 |
| Signal Canvas | A visually expressive market canvas with a chart and event timeline as the dominant focal point. It would overemphasize visualization relative to source-backed research. | 0.08 |

### Chosen approach

**Evidence Briefing** is the Phase 1 direction. It takes the reference product’s calm, simple research-document cadence and combines it with the current product’s typed, source-backed data architecture. It does not reproduce the reference mechanically; its purpose is to make the real records easier to read.

### Core principles

1. **Search precedes interface.** The primary action is immediately clear before any secondary control competes for attention.
2. **Facts precede commentary.** Identity, price, snapshot, signal, news, and events are encountered before optional AI interpretation.
3. **Evidence earns its space.** Sources, freshness, FX records, warnings, and methodology are visible through labelled secondary disclosure, not repeated on every tile.
4. **Absence is explicit.** Unavailable data, partial coverage, and unavailable AI remain calm factual states rather than decorative blanks.

### Color philosophy

The existing mineral-paper and graphite-night environments remain, but structural borders recede so data and state carry hierarchy. Research Indigo remains the action and focus color. Signal Teal identifies verified source state. Amber and red are restricted to partiality and controlled risk messages.

### Layout paradigm

The desktop product becomes a **research document with a persistent action strip**, rather than a three-column dashboard. A search and identity masthead opens the document. The primary reading column then follows market snapshot, chart and signal, research brief, news and events, and a folded evidence appendix. Comparison and Research Desk remain secondary workspaces revealed through compact controls rather than occupying permanent competing rails.

### Signature elements

The design uses a slim **research pulse rail** under the masthead, concise **editorial metric rows** with section-level provenance, and a **folded evidence appendix** for source/freshness, FX, warnings, and methodology.

### Interaction philosophy

Search remains immediate and keyboard-friendly. Workspace switches remain explicit. Native disclosure reveals advanced evidence with accessible labels. Readers never need to open a disclosure to see live returned research, but never need to scan a wall of metadata to understand it.

### Animation

Motion remains functional and restrained. Search results enter through short opacity and translate transitions. Evidence disclosure uses concise opacity and transform changes. Skeletons appear only while live source records are pending. All non-essential motion respects `prefers-reduced-motion` and stays below 220ms.

### Typography system

**DM Serif Display** carries company identity, report headings, and high-level insight. **DM Sans** handles controls and sourced metadata. **DM Mono** is reserved for tickers, prices, rates, and timestamps. Labels are small and tracked only in secondary evidence contexts.

### Brand essence

**QuantAI is an evidence-first market research desk for people who want sourced facts before interpretation.**

Measured, lucid, disciplined.

### Brand voice

Headlines are direct and report-like. Calls to action name the research action. Microcopy states exactly what is sourced, unavailable, or optional.

> “Search a company, then follow the evidence.”

> “AI interpretation is optional; the sourced record remains available.”

### Wordmark, logo, and signature color

The existing QuantAI aperture mark remains the compact identity anchor. The masthead may pair it with a document-like **Research Desk** descriptor rather than a generic product claim. **Evidence Indigo** remains the ownable action and focus color.

## Style Decisions

- The Phase 1 primary flow is search, market snapshot, key signals, recent news, events, research brief, then sources and evidence.
- Provenance is section-level in primary reading; full source/freshness, FX, warnings, and methodology remain available through clearly named secondary disclosure.
- Comparative FX evidence remains explicit whenever normalization occurs and never appears as an implied hidden conversion.
- The Research Desk remains functional but visually secondary to the sourced research document.
