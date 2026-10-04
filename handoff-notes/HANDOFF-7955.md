# Handoff — issue #7955 (nesquena/hermes-webui)

## What this is

Fix for issue **#7955** — *"model.provider: ollama makes every Custom-group
model fail with `custom:<tag-prefix>` not configured"*.

The picker collapses the active local provider to the generic `custom` slug and
the wire form for a configured-endpoint pick (`@custom:<model>`) is
indistinguishable from a named custom record (`@custom:<slug>:<model>`) whenever
the model id itself contains a colon (Ollama tags, vLLM/llama.cpp revisions).
The pick then leaves the configured endpoint, adopts an unrelated record's
`base_url` and credentials, and truncates the model id at the first colon.

## Where the work lives

- **Upstream repo:** `nesquena/hermes-webui`
- **Issue:** https://github.com/nesquena/hermes-webui/issues/7955
- **Fork:** `Szqub/hermes-webui`
- **Branch:** `fix/7955-configured-custom-disjoint-route`
- **Current head:** `c8d9f41c`
- **Base:** `cdff0b8d` (upstream `master` at fork time)
- **PR:** not opened yet — the available token has read-only access to the
  upstream repo, so the PR must be opened from the fork. Compare URL:
  https://github.com/nesquena/hermes-webui/compare/master...Szqub:fix/7955-configured-custom-disjoint-route?expand=1
  The gate did not pass either — see "Open blockers".

Local worktree: `/opt/data/cache/scratch/wt-design-7955`
(other exploratory branches from this session: `fix/7955-bare-custom-local-provider-model-id`
@ `e55a7d36`, `fix/7955-custom-lane-endpoint-authoritative` @ `9ee48765`)

## What the branch changes

Selection on the configured endpoint now uses a reserved route:

- `@!:M` — configured-endpoint lane; everything after the prefix is the opaque
  identifier (colons and slashes included).
- `@E(P):M` — generic provider route, unchanged in shape, but the provider
  segment is escaped when not legacy-safe (`!` and `%` always percent-encoded),
  so no provider id can ever emit the reserved prefix.

Resolution consumes `@!:` before configured-provider alias resolution,
ownership scans and the generic parser, so no catalog entry, no `providers.*`
override and no named slug can take the endpoint away from the active
`model.base_url`.

Files: `api/config.py`, `api/routes.py`, `static/ui.js`, `static/commands.js`,
`static/panels.js`, `docs/architecture/configured-custom-routing.md`,
`docs/CONTRACTS.md`, plus tests
(`tests/test_issue7955_disjoint_route.py`, `tests/test_issue7955_route_js.py`).

## How to run the gate

```sh
cd /opt/data/cache/scratch/wt-design-7955
export HERMES_HOME=/opt/data/cache/scratch/design-7955-home \
       HERMES_WEBUI_STATE_DIR=/opt/data/cache/scratch/design-7955-state \
       HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent TMPDIR=/tmp
./scripts/test.sh tests/test_issue7955_disjoint_route.py tests/test_issue7955_route_js.py -q --timeout=180
node --check static/ui.js && git diff --check cdff0b8d
```

Current state: **91 passed** (the two #7955 files) and **95 passed** once
`tests/test_issue854_live_model_prefix.py` is included.

Regression evidence (the new tests pin the change, they are not vacuous):
copied onto a worktree at the base `cdff0b8d` they give
**79 failed, 12 passed**; the base source contains zero occurrences of `@!:`.

Full-suite baseline (`./scripts/test.sh tests -q --timeout=240`): **18007 passed,
3 failed, 236 skipped, 2 xfailed, 2 xpassed, 399 subtests passed** in 966s on the
fix branch. The three failures are environment-dependent and fail identically on
the base `cdff0b8d`:

- `tests/test_managed_profile_startup.py::test_real_managed_bootstrap_preserves_named_profile_concurrency`,
  `tests/test_tls_aware_probe.py::test_helper_self_signed_warns_and_succeeds`,
  `tests/test_tls_aware_probe.py::test_helper_insecure_optin_is_silent`
  — the health probe needs a live server.

A full run on the pre-fix state of this branch reported six; the extra three
(`test_minimax_provider` x2 and
`test_profile_switch_models_disk_cache[plugin-version-bumped]`) pass in isolation
on both the base and this branch — flaky under the full parallel run, not
regressions.

## Open blockers (independent review, gate 7 — both reviewers BLOCK)

Reviewer artefacts: `/opt/data/cache/scratch/reviews/prgate/gate7-opus.md`
(opus) and `gate7-sol.md` (sol). Reproductions live under
`/opt/data/cache/scratch/g7/` and `/opt/data/cache/scratch/g7-pickers/`.

**Fixed this round (verified):**
- Foreign-credential pairing on the plain custom lane (opus blocker 1).
  `g7/cred.py <variant>` now yields `api_key: false` when the runtime
  credential belongs to a different endpoint origin; same-endpoint keeps its key.
- `tests/test_issue854_live_model_prefix.py` no longer fails (opus blocker 2).
- Gate 6's three counterexamples, re-run verbatim against the current head
  (`g7-pickers/routes.js`): `inject-existing` now keeps
  `custom:backup`/`model-a` and preserves `@safe:model-a`; `inject` writes the
  qualified values verbatim with no re-wrapping; the non-custom lookup no
  longer substitutes `@!:model-a` for `@safe:model-a`. Do not re-investigate
  these three.
  Caveat: gate7-sol blocker 2 (below) is the surviving half of the `inject`
  case — the wrapper is preserved but the state still drops the namespace.

**VERIFIED REGRESSION — highest priority, fix before anything else:**

`_parseModelRoute` (new this round) splits a legacy `@custom:` value at its
first colon before consulting the caller's hint. The code it replaced checked
the exact provider prefix first. The catalog sets an option's `data-provider` to
the group it listed the model under, so a plain Custom-lane option is
`@custom:<model>` in group `custom` — and the split then reads a colon-bearing
model id as a record name:

    # picker state of option '@custom:qwen3:8b' with data-provider 'custom'
    BASE cdff0b8d -> {"model":"qwen3:8b","model_provider":"custom"}
    HEAD c8d9f41c -> {"model":"8b","model_provider":"custom:qwen3"}

    # namespaced id, the common Ollama/LM Studio `vendor/model:tag` form
    BASE -> {"model":"vendor/qwen3:8b","model_provider":"custom"}
    HEAD -> {"model":"8b","model_provider":"custom:vendor/qwen3"}

    # ensure/inject '@custom:llama3.1:8b' with hint 'custom'
    BASE -> {"model":"llama3.1:8b","model_provider":"custom"}
    HEAD -> {"model":"8b","model_provider":"custom:llama3.1"}

Same defect in `_deduplicateModelPickerOptions`, because identities go through
the same parser:

    HEAD  identities ['8b','8b','7b','9b'] -> removes '@custom:llama3.1:8b'
    BASE  identities ['qwen3:8b','llama3.1:8b','qwen2.5.coder:7b','gemma2:9b'] -> removes 0

Scope, stated precisely (measured, do not overstate): HEAD destroys the model id
in the picker state. The **end-to-end route is unresolvable in the base too** —
`model_with_provider_context('qwen3:8b','custom')` returns `@custom:qwen3:8b`,
which `resolve_model_provider` reads as the named record `custom:qwen3` with
model `8b` and no matching endpoint. So this branch does not fix #7955 for a
configuration whose active provider is not a local server, and it degrades the
state further. gate7-opus called the base result "also wrong" — that is correct
about the resolution outcome; the id truncation is still a regression.

Root cause of the deeper defect: `_configured_custom_lane_is_reserved()` is
false whenever the active provider is not a local server, so `_encode_catalog_route`
falls back to `@custom:<model>` even though that spelling cannot express a
colon-bearing model id on the plain lane. Either the plain lane needs the same
reserved route (and the resolver must accept it in that configuration), or the
catalog must not advertise a plain lane that the resolver cannot read back.

Reachability (the ambiguous spelling is emitted for `anthropic`, `openrouter`,
and `lmstudio` without `model.base_url`):

    lmstudio+nobase+unnamed_cp  group custom | ['@custom:qwen3:8b', '@custom:llama3.1:8b']
    anthropic+base+unnamed_cp   group custom | ['@custom:qwen3:8b', '@custom:llama3.1:8b']
    openrouter+base+unnamed_cp  group custom | ['@custom:qwen3:8b', '@custom:llama3.1:8b']

Reproduce (node harness, no browser):

    cd /opt/data/cache/scratch/g7-pickers
    node routes.js <worktree> '{"action":"metadata","cases":[["@custom:qwen3:8b","custom","@custom:qwen3:8b","custom"]]}'
    node routes.js <worktree> '{"action":"inject","cases":[["custom","@custom:llama3.1:8b"]]}'
    # base copy of static/*.js at /tmp/baseui/ for the comparison

Catalog reachability (run from the worktree):

    HERMES_HOME=... HERMES_WEBUI_STATE_DIR=... .venv/bin/python /opt/data/cache/scratch/g6/cat5.py

Root cause: `_parseModelRoute('@custom:qwen3:8b', 'custom')` splits at the first
colon of `custom:` and yields provider `custom:qwen3` / model `8b`; the caller
hint that says the option belongs to the plain `custom` lane is not allowed to
disambiguate. The "a hint never interprets a qualified value" rule is too broad
for an option whose authoritative `data-provider` is exactly `custom` and whose
value came from this catalog.

Related, same cause — dedup then drops distinct models from the group:

    HEAD  identities ['8b','8b','7b','9b'] -> _deduplicateModelPickerOptions removes '@custom:llama3.1:8b'
    BASE  identities ['qwen3:8b','llama3.1:8b','qwen2.5.coder:7b','gemma2:9b'] -> removes 0

    node g7-pickers/dedupcheck.js <worktree>

**Candidate fix — now merged into this branch.** Commit `73589862` fixes the
regression by honouring an exact hint prefix before the legacy `@custom:` split
in `_parseModelRoute` (one file, 15 insertions / 9 deletions); `8fea33fd`
corrects the three tests that pinned the truncated result; `843f203a` aligns the
docs. `fix/7955-configured-custom-disjoint-route` is now the single PR branch and
carries all of it.

**Blocker 1 is fixed** on this branch. `@custom:qwen3:8b` in group `custom` now
reads as `{"model":"qwen3:8b","model_provider":"custom"}`, and dedup removes 0
instead of 1.

**Scope decision (measured, do not re-litigate):** the reported issue is
`model.provider: ollama` *with* `base_url` — the case where the reserved
predicate is true. Verified end to end on that configuration:

    reserved lane: True
    session ('qwen3.8:27b', 'custom') -> wire '@!:qwen3.8:27b'
                                      -> ('qwen3.8:27b', 'custom', 'http://127.0.0.1:11434/v1')

The unresolvable `@custom:<model>` route for a *cloud* active provider plus an
*unnamed* `custom_providers` entry is a separate, pre-existing gap (the reserved
predicate requires `model.base_url`; the endpoint lives in that entry). Closing
it needs the resolver guard to accept that entry, which is out of scope here and
belongs in its own issue. This PR neither causes nor worsens it.

**Still open** (item 1 is now partly fixed — see below; items 2–3 re-verified by
hand at `c8d9f41c`, 2026-10-04 and still reproducing unchanged):
1. *Qualified restore can still substitute another provider's option* (sol 1) —
   **partly fixed.** The dedup half is gone (`{"removed":0}`, both routes kept).
   What remains: `_findModelInDropdown`'s provider-aware return still does not
   cover the metadata filter at `static/ui.js:3694–3696`, so requesting `@!:8b`
   against an option set containing `@other:8b` matches `@other:8b` and yields
   `{"model":"@other:8b","model_provider":"other"}`. Repro:
   `node g7-pickers/routes.js <wt> '{"action":"metadata","cases":[["@other:8b","custom","@!:8b","custom"]]}'`.
2. *Injection still changes the meaning of a non-custom namespace* (sol 2).
   Injected `data-model` drops the namespace in `_modelStateForSelect`;
   `routedModel` wins for non-custom routes too (`static/ui.js:3379`).
   Re-verified at HEAD: `inject ["custom","@safe:model-a"]` →
   `{"model":"model-a","model_provider":"safe"}` while the catalog renders the
   same qualified value as `{"model":"@safe:model-a","model_provider":"safe"}`.
3. *Catalog dedup redirects `providers.custom` to the configured endpoint*
   (sol 3). `_encode_catalog_route` distinguishes only `provider_id`, not group
   origin. Repro: `g7-catalog/test_catalog_review.py` (6 failed / 16 passed).
4. *Profile persistence lets a hint take over a qualified route* (sol 4).
   `api/profiles.py:2543` uses `provider or parsed_provider`, the inverse of the
   declared rule. Repro: `g7-pickers/probe.py`.
5. *Tests do not detect removal of this round's JS hardening* (sol 5). Old JS
   from `ba745f59` passes all 11 route-JS tests (`DETECTED: 0 OF 11`).
6. *Two of three JS fixes are not pinned by tests* (opus blocker 3).
   Mutants `M2_find_exact_ignores_provider`, `M3_state_group_wins` (and catalog
   mutants `M5–M11`) survive; `g7/mutate.py`.
7. Docs contradict execution in three places
   (`docs/architecture/configured-custom-routing.md` lines ~57–61, ~70–71,
   ~113–118, ~140–142; and the `_configured_custom_lane_is_reserved` docstring).
8. `resolve_model_provider` now raises `ValueError` where it previously never
   raised (when a stored model is literally `@!:M` and the configured endpoint
   is gone). Verified call sites in `api/routes.py`:
   - `29297` (`_handle_session_compress`) — inside `try/except Exception`, caught.
   - `27224` (`_llm_git_commit_message`) — both callers (27310, 27343) are in
     `try/except ValueError` → returns 400 with the message, not a crash.
   - `26518` (`_handle_chat_sync`) — the enclosing `try` has only `finally`, so
     the error escapes to `_handle_write`'s `except Exception` → **500
     "Internal server error"** instead of a useful message.
   - `15778` (`_llm_update_summary`) — no enclosing try → 500.
   Reachability: this branch's UI never persists a raw `@!:M` — `_modelStateForSelect`
   strips it to a bare model + `custom` provider, and `model_with_provider_context`
   only re-mints `@!:` while the endpoint is configured. So a raw `@!:` in a
   session requires an external writer (hand-edited state, import). Low
   reachability, but the 500 path is worth a guard.
   (Source: gate4-opus, refined by execution.)

## Constraints (do not violate)

- Author/signatory is **`Szqub` only** — no mention of any tool, agent or AI in
  commits, PR body, issues or comments.
- The PR body must satisfy the repo's **AI Usage Disclosure / `Model Used`**
  checklist in `docs/CONTRACTS.md` — this conflicts with the rule above and is
  **unresolved**; do not guess a value.
- Documentation stays in the repo, not only in the PR body.
- Gate briefs are READ-ONLY for the reviewer.