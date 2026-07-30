- **Mode:** Curated
- **Source:** `examples/curated/release-readiness.gpt.md`
- **Output:** `examples/curated/index.html`

Checks and repairs:

- Source facts remain intact: decision rule, hold status, gates/evidence, workstreams, milestones, and unresolved backend question.
- Narrow-overflow containment remains intact: grid children can shrink while the 670px table scrolls inside `.table-scroll`.
- Uppercased `<!DOCTYPE html>`.
- Removed redundant `aria-label` attributes from `.decision-evidence` and `.workstreams`.
- Changed `.table-scroll` from `div` to native `section`, removed `role="region"`, and retained `tabindex="0"` and its accessible label.
- Static validation passed for balanced HTML structure, matching tags, unique IDs, resolved `aria-labelledby` targets, and requested semantics.
- No browser tools were used.