# Devin prompt — finish and publish the two PRs

Open Devin in this repository (the fork, not the upstream):

    https://github.com/Szqub/hermes-webui

Everything below is already pushed to that fork. Work on the branches named
here; do not re-derive the analysis.

---

## Task

Finish the #7955 fix in `nesquena/hermes-webui` and open the pull request
against upstream `master`. Then open the second PR for
`NousResearch/hermes-agent` issue #132048 from the other fork.

Both PRs must be mergeable-quality: the maintainer has already rejected two
previous attempts, so read `HANDOFF-7955.md` before touching anything.

## Branch map

    Szqub/hermes-webui
      handoff/7955                               c12850a2  <- read HANDOFF-7955.md first
      fix/7955-configured-custom-disjoint-route  843f203a  <- THE PR BRANCH, complete
      fix/7955-authoritative-provider-prefix     5aae99e3  <- same two commits, kept for reference

    Szqub/hermes-agent
      fix/132048-relay-blocked-provider-close    b40ca5cf  <- PR #132048, ready to open

PR body for repo A: `/opt/data/cache/scratch/pr-webui-body-v4.md`.
PR body for repo B: `/opt/data/cache/scratch/pr-agent-body.md`.

## Priority 1 — DONE on this branch; scope decision recorded

Both parts of Priority 1 are now resolved on `fix/7955-configured-custom-disjoint-route`
@ `843f203a`:

- **1a fixed** by `73589862` (honour an exact hint prefix before the legacy
  `@custom:` split in `_parseModelRoute`, one file, 15/9). `8fea33fd` corrects
  the three tests that pinned the truncated result; `843f203a` aligns the docs.
  `@custom:qwen3:8b` in group `custom` now reads as
  `{"model":"qwen3:8b","model_provider":"custom"}`, and dedup removes 0 instead
  of 1.
- **1b is out of scope and stays open.** The reported issue is
  `model.provider: ollama` *with* `base_url` — the case where the reserved
  predicate is true — and that configuration is verified working end to end:

      reserved lane: True
      session ('qwen3.8:27b', 'custom') -> wire '@!:qwen3.8:27b'
                                        -> ('qwen3.8:27b', 'custom', 'http://127.0.0.1:11434/v1')

  The unresolvable `@custom:<model>` route for a *cloud* active provider plus an
  *unnamed* `custom_providers` entry is pre-existing (the predicate requires
  `model.base_url`; the endpoint lives in that entry). It needs the resolver
  guard to accept that entry, which is a design change — file it as its own
  issue, do not fold it into this PR. The PR body already states this.

Everything below is the evidence trail. Re-run it only if you change the code.

### 1a. The picker truncates the model id (regression, this branch)

`static/ui.js` `_parseModelRoute` (new this round) splits a legacy `@custom:`
value at its first colon before consulting the caller's hint. The code it
replaced checked the exact provider prefix first. The catalog sets an option's
`data-provider` to the group it listed the model under, so a plain Custom-lane
option is `@custom:<model>` in group `custom`, and the split reads a
colon-bearing model id as a record name:

    @custom:qwen3:8b        BASE cdff0b8d -> {"model":"qwen3:8b","model_provider":"custom"}
                            HEAD c8d9f41c -> {"model":"8b","model_provider":"custom:qwen3"}

    @custom:vendor/qwen3:8b BASE -> {"model":"vendor/qwen3:8b","model_provider":"custom"}
                            HEAD -> {"model":"8b","model_provider":"custom:vendor/qwen3"}

`_deduplicateModelPickerOptions` shares the parser, so it also drops distinct
models (identities `['8b','8b','7b','9b']` -> removes one option; correct is
`['qwen3:8b','llama3.1:8b','qwen2.5.coder:7b','gemma2:9b']` -> removes none).

`fix/7955-authoritative-provider-prefix` (@ `5aae99e3`) carries the same two
commits and is kept only for reference — do not build on it. The three tests
that pinned the truncated result were corrected in `8fea33fd`, not weakened.

    tests/test_issue7955_route_js.py
      test_generic_decoding_is_single_pass_and_does_not_decode_model
      test_injecting_existing_route_never_double_wraps_or_decodes_suffix
      test_legacy_value_is_not_substituted_by_a_configured_lane_option

They assert `'8b'` and justify it as "the runtime's own reading". That reading
is what breaks the feature: `resolve_model_provider` cannot resolve it.

### 1b. The route is unresolvable in the base too — OUT OF SCOPE, file separately

    model_with_provider_context('qwen3:8b','custom') -> '@custom:qwen3:8b'
    resolve_model_provider('@custom:qwen3:8b')       -> ('8b','custom:qwen3', None)

No endpoint. So for any configuration whose active provider is not a local
server, the Custom group advertises a route the resolver cannot read back:

    lmstudio+nobase+unnamed_cp  group custom | ['@custom:qwen3:8b', '@custom:llama3.1:8b']
    anthropic+base+unnamed_cp   group custom | ['@custom:qwen3:8b', '@custom:llama3.1:8b']
    openrouter+base+unnamed_cp  group custom | ['@custom:qwen3:8b', '@custom:llama3.1:8b']

`_configured_custom_lane_is_reserved()` is false there, so `_encode_catalog_route`
falls back to the ambiguous `@custom:<model>` spelling. Extending only that
predicate is not enough — the resolver's guard also requires `model.base_url`,
while the endpoint lives in the `custom_providers` entry:

    catalog with predicate forced true -> ['@!:qwen3:8b', ...]
    resolve_model_provider('@!:qwen3:8b') -> RAISED ValueError: Configured Custom endpoint is not available

So a real fix has to make the plain custom endpoint the reserved lane on both
sides: the catalog predicate and the resolver's guard must agree that an
unnamed `custom_providers` entry (or `model.base_url`) is the configured Custom
endpoint, and `@!:` must route to it. That is a design change touching the
resolver — get maintainer agreement on it before writing the PR. The maintainer
already rejected the literal `@custom-configured:` in the PR #7966 thread, so
do not invent another spelling; extend the route that is already accepted.

Decide nothing here: the scope is already settled. 1b is out of scope and gets
its own issue. Do not describe the branch as fixing #7955 while claiming 1b is
also closed — the PR body is explicit that 1b remains open.

Verification (no browser needed):

    cd <worktree>
    node --check static/ui.js
    node /opt/data/cache/scratch/g7-pickers/routes.js <worktree> \
      '{"action":"metadata","cases":[["@custom:qwen3:8b","custom","@custom:qwen3:8b","custom"]]}'
    node /opt/data/cache/scratch/g7-pickers/dedupcheck.js <worktree>
    HERMES_HOME=... HERMES_WEBUI_STATE_DIR=... .venv/bin/python /opt/data/cache/scratch/g6/cat5.py

## Priority 2 — the remaining blockers

`HANDOFF-7955.md` (branch `handoff/7955`) lists all eight with reproduction
commands and marks which are already fixed. The open ones in short:

1. Qualified restore can still substitute another provider's option
   (`_findModelInDropdown` provider-aware return does not cover the metadata
   filter at `static/ui.js:3694-3696`). Same root cause as Priority 1.
2. Injection still drops a non-custom namespace in `_modelStateForSelect`
   (`static/ui.js:3379`) — the same qualified value gets a different state
   depending on how the option was created.
3. Catalog dedup redirects `providers.custom` to the configured endpoint
   (`_encode_catalog_route` looks only at `provider_id`, not group origin);
   `g7-catalog/test_catalog_review.py` is 6 failed / 16 passed.
4. `api/profiles.py:2543` uses `provider or parsed_provider` — the inverse of
   the declared rule, so a hint can take over a qualified route.
5. Tests do not detect removal of this round's JS hardening (old JS from
   `ba745f59` passes all 11 route-JS tests) and the mutants
   `M2_find_exact_ignores_provider`, `M3_state_group_wins` and catalog
   `M5-M11` survive (`g7/mutate.py`).
6. Docs contradict execution in three places
   (`docs/architecture/configured-custom-routing.md` ~57-61, ~70-71, ~113-118,
   ~140-142, and the `_configured_custom_lane_is_reserved` docstring).
7. `resolve_model_provider` now raises `ValueError` where it never did before.
   `api/routes.py:29297` is caught; `27224` returns 400; `26518`
   (`_handle_chat_sync`) escapes to a **500**. Needs a guarded call site.

## Non-negotiable constraints

- Maintainer requirement: keep the configured endpoint authoritative, on a
  dedicated route disjoint from every `@provider:` token. The literal
  `@custom-configured:` was rejected — do not reintroduce it.
- The PR body must not claim the work is finished while any blocker above is
  open. State what is verified and what is not.
- Author and signatory on every commit, PR, issue and comment is **Szqub** only.
  No mention of AI, agents or assistants anywhere.
- **Open decision, do not guess:** `docs/CONTRACTS.md` asks the PR body for a
  `Model Used` disclosure, and `pr-webui-body-v4.md` carries the section header
  with a bracketed note instead of a value. The standing rule is that only Szqub
  is the author and signatory, so this is Szqub's call alone. Leave the note in
  place and raise it; do not fill it in and do not remove the section.

## Second PR

    https://github.com/Szqub/hermes-agent
    branch fix/132048-relay-blocked-provider-close @ b40ca5cf
    -> open PR against NousResearch/hermes-agent main for issue #132048

Body draft is at `/opt/data/cache/scratch/pr-agent-body.md`. Tests:
`scripts/run_tests.sh -j 1 --file-timeout 90 tests/agent/test_relay_blocked_generator_interrupt.py`
-> 2 passed. This repo's PR template has no AI-disclosure section.

## Opening the PRs

Both upstreams are read-only for the token currently on this machine, so the PRs
must be opened with write access:

    https://github.com/nesquena/hermes-webui/compare/master...Szqub:fix/7955-configured-custom-disjoint-route?expand=1
    https://github.com/NousResearch/hermes-agent/compare/main...Szqub:fix/132048-relay-blocked-provider-close?expand=1