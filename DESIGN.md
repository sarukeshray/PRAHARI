# PRAHARI — Design System

The prototype's visual direction, fixed before any component was written so that
every colour and type decision traces back to a stated reason.

## Subject

A sanction-review console for a District Collector's office. One reader, one job:
**decide which public works need a human to look at them today, and see why.**
Not an analytics product — a system of record with an opinion.

## The direction: institutional, grounded in the file

MPLADS lives in a paper world — sanction registers, Schedule of Rates books,
utilisation certificates, file notings. The prototype borrows that world's
vernacular rather than a SaaS dashboard's: ruled rows instead of floating cards,
work IDs as the structural markers, financial years as the unit of time.

**The risk taken, and its justification.** There are no donut charts, no gradient
KPI tiles, no big-number-with-small-label hero. The entire visual language is a
measurement against a line. This is a deliberate bet: the product's credibility
rests on a District Officer verifying a claim without asking a data scientist. A
wall of decorative aggregate charts quietly contradicts that promise; a page of
legible measurements enacts it.

## Colour

Six values. Colour is information, never decoration — a surface is never tinted
to look lively.

| Token | Hex | Job |
|---|---|---|
| `--paper` | `#F7F8F7` | Page ground. Cool, not cream. |
| `--surface` | `#FFFFFF` | Ledger and panel surfaces. |
| `--ink` | `#14181B` | Primary text. |
| `--ink-muted` | `#5B656E` | Labels, secondary values. |
| `--rule` | `#DCE0E2` | Hairlines. Carries all structure. |
| `--seal` | `#16457E` | Administrative blue. Navigation and interaction only — never a severity. |

Severity is the only other colour in the system, fixed by specification:

| Tier | Hex | Treatment |
|---|---|---|
| LOW | `#64748B` slate | Outline chip |
| MEDIUM | `#A9670C` amber | Outline chip |
| HIGH | `#C4460B` orange | Solid chip |
| CRITICAL | `#AE1414` red | Solid chip |

Amber, orange and red sit close together, so tier is never signalled by hue
alone: outline versus solid fill separates the advisory tiers from the urgent
ones, and every chip carries its tier as text.

## Type

**IBM Plex** across all three roles — Sans for interface, Mono for data,
Sans Devanagari for the wordmark.

This is one superfamily, chosen for a specific reason rather than neutrality:
PRAHARI (प्रहरी) is a Hindi-named system for a Government of India scheme, and
Plex is one of the few institutional-grade families that covers Latin, Devanagari
and a true monospace with a single set of proportions. A real deployment would
need exactly that coverage. Inter would have been the templated answer.

Mono is not styling — it is load-bearing. Work IDs, rupee amounts and percentages
are set in Plex Mono so digits align down a column and two costs can be compared
by eye without reading them.

Scale: 10.5px eyebrow (uppercase, 0.1em tracking) · 11px micro · 12.5px table and
data · 13px body · 19px page title. Tight, functional, no display sizes — the
data is the largest thing on the page.

## Signature element: the evidence row

Every finding renders the same way, and this is the one thing the interface
should be remembered by:

```
COST ABOVE SoR BENCHMARK                        CRITICAL

  ₹18,20,000  observed   ████████████████████▏ +41.1%
  ₹12,90,000  benchmark  ─────────────┤ flags above +25%

Estimated cost is 41% above the Rajasthan Schedule of Rates
benchmark for ROAD_CC in HILLY terrain.
```

Observed value, the threshold it crossed, the distance between them drawn to
scale, and a sentence naming both numbers. It is the specification's fourth
design rule turned into a component, and it is why the composite score never
needs to be the headline.

## Motion

Almost none. Row hover raises a 2px severity-coloured edge; that is the whole
vocabulary. `prefers-reduced-motion` removes it. A tool that reviews public
expenditure should feel steady, and heavy animation is the surest way to make a
government interface read as a mockup.

## Quality floor

Responsive to mobile, visible keyboard focus rings in `--seal`, severity never
encoded by colour alone, tabular figures throughout, and the synthetic-data
notice fixed to every screen with no dismiss control.
