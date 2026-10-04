Done. Summary of the work:

**Fix** (`/opt/data/cache/scratch/wt-astra-7955`, dirty, no commits): parser-side only, in `api/config.py::resolve_model_provider()`. A new endpoint-authoritative branch resolves `@custom:<payload>` to `(payload, "custom", model.base_url)` when the raw `model.provider` is the custom endpoint lane (`custom`/legacy `local`/local-server + `base_url`). Disjointness is typed, not spelling: the lane yields to exact `providers:` keys, unique named `custom_providers[]` slugs, and `custom:<host>:<port>` endpoint slugs, and never fires for non-`custom` hints — so the round-3 `@custom-configured:` collision shape resolves exactly as on master. Judging the lane from the raw provider spelling (not the named-slug-resolved id) preserves the #4728 fail-closed rule; an earlier wider version failed `test_issue1806` and was corrected.

**Verification**
- Probe matrix A–F on pristine `cdff0b8d` vs the change: every tagged row went from `('27b', 'custom:qwen3.8', None)` (the bug) to `('qwen3.8:27b', 'custom', :11434)`; untagged rows now return the configured endpoint; all E rows byte-identical. 592-case differential probe: 18 changes, all intended (6 direct repros, 12 previously-guaranteed-runtime-error unknown-slug tokens — documented as residual risk in the report).
- New tests: `tests/test_issue7955_custom_lane_endpoint_authoritative.py`, 23 tests, real config + real encode→resolve. 12 fail on master / 23 pass on the change.
- Neighbouring suites: 951 passed, 0 failed across the required 12-file set (445), the custom-provider set (91), and other consumer/lane suites (240+76+99). The one failure mode seen (combined-shard setup errors) reproduces identically on pristine master — pre-existing fixture interaction, noted in the report.
- Docs: the encoding is not a documented contract (grep of docs/); no doc edits needed, CHANGELOG untouched. Contract Routing + Contract Change wording is in the report.

Report: `/opt/data/cache/scratch/reports/astra-7955.md`. Baseline worktree left at `/opt/data/cache/scratch/wt-astra-7955-base` for re-verification.

⚠️ File-mutation verifier: 1 file edit(s) FAILED this turn despite any wording above that may suggest otherwise. Run `git status` or `read_file` to confirm what actually landed.
  • `/opt/data/cache/scratch/probe_7955.py` — [write_file] Refusing to overwrite `/opt/data/cache/scratch/probe_7955.py`: `/opt/data/cache/scratch/probe_7955.py` exists but this task has not seen its full current content (never read, only pat…
