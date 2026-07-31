# Synthetic Release Readiness Review

This fixture describes a fictional Thursday release. Its
purpose is to test whether a visualization separates the
decision from the supporting status detail.

## Decision rule

Ship on Thursday only when every required gate is ready by
Wednesday at 16:00 UTC. A pending required gate changes the
decision to hold.

## Required gates

| Gate              | Owner  | State   | Evidence                      |
| ----------------- | ------ | ------- | ----------------------------- |
| HTML parser       | Team A | Ready   | Offline suite passed          |
| PDF smoke test    | Team B | Pending | Backend run not recorded      |
| Clean install     | Team C | Ready   | Two clean installs passed     |
| Disclosure review | Team D | Ready   | Tree and history scans passed |

## Workstreams

### Rendering

- Curated HTML is ready.
- Formal HTML is ready.
- PDF export remains pending.

### Distribution

- The package includes the skill file and three scripts.
- The marketplace catalogue entry is drafted.
- Public publication is outside this fixture.

## Milestones

| Time                | Event                |
| ------------------- | -------------------- |
| Tuesday 12:00 UTC   | Inputs frozen        |
| Wednesday 16:00 UTC | Required-gate cutoff |
| Thursday 09:00 UTC  | Candidate release    |

## Open question

Which PDF backend will provide the recorded smoke test?

## Expected reading

The current decision is **hold** because one required gate,
the PDF smoke test, is pending.
