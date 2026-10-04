# Final pre-PR gate — READ ONLY. Do not edit, stage, commit, push, or create files.

Two reviewers receive this brief independently. Verify by execution, not by reading alone.

## Artifact under review

    repo:     nesquena/hermes-webui  (upstream default branch: master)
    worktree: /opt/data/cache/scratch/wt-design-7955
    branch:   fix/7955-configured-custom-disjoint-route
    commit:   f585b123   (base: upstream/master cdff0b8d)
    issue:    #7955

Changed files: api/config.py, api/routes.py, static/ui.js, static/commands.js,
static/panels.js, tests/test_issue7290_no_slash_prefixed_alias.py,
tests/test_model_picker_badges.py, docs/CONTRACTS.md
New files: tests/test_issue7955_disjoint_route.py, tests/test_issue7955_route_js.py,
docs/architecture/configured-custom-routing.md

Implementer's report (claims — treat as claims, not facts):
/opt/data/cache/scratch/reports/design-7955.md
Raw evidence (95 files): /opt/data/cache/scratch/reports/design-7955-evidence/

Read the issue text: /opt/data/cache/scratch/issues/7955*.

## How to run the tests

    cd /opt/data/cache/scratch/wt-design-7955
    export PYTHONPATH=/opt/data/cache/scratch/wt-astra-7955/.venv/lib/python3.13/site-packages \
      HERMES_HOME=/opt/data/cache/scratch/design-7955-home \
      HERMES_WEBUI_STATE_DIR=/opt/data/cache/scratch/design-7955-state \
      HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent TMPDIR=/tmp
    ./scripts/test.sh tests/test_issue7955_disjoint_route.py tests/test_issue7955_route_js.py -q --timeout=120
    node --check static/ui.js && node --check static/commands.js

Neighbour suites worth running yourself (all must stay green):
tests/test_resolve_model_provider_free_suffix.py, tests/test_model_resolver.py,
tests/test_provider_mismatch.py, tests/test_issue7290_no_slash_prefixed_alias.py,
tests/test_model_picker_badges.py, tests/test_issue1806_named_custom_provider_resolution.py,
tests/test_issue7333_slash_id_provider_hint.py, tests/test_issue1894_provider_overlap.py,
tests/test_issue1228_model_picker_duplicate_ids.py, tests/test_issue6722_provider_qualified_model_leak.py,
tests/test_issue6195_bare_id_ambiguous_no_revert.py, tests/test_model_alias_routes.py

## What the change claims

1. A selection on the configured Custom endpoint is encoded as `@!:M` (reserved,
   opaque suffix). Resolution returns `(M, "custom", model.base_url)` and runs
   BEFORE configured-provider alias resolution, before ownership scans, and
   before the generic parser.
2. Disjointness by construction: the generic encoder never emits a literal `!`
   or `%` in the provider segment (it percent-escapes them), so no provider id
   can produce `@!:`. The reserved branch is tested before any percent decoding.
3. Named custom providers, explicit `@local:` / `@ollama:`, real providers,
   `providers.custom-configured`, endpoint-derived `custom:host:port`, and the
   #4728 fail-closed behavior are unchanged.
4. Legacy `@custom:<slug>:<model>` still means the named record. Ambiguous old
   Custom picks are deliberately NOT auto-migrated.
5. Python and JavaScript share the grammar (encoder + parser), including
   lower-casing and escaping.

## Your job

Reproduce the claims; then attack them. Specifically:

- Independent disjointness attempt: construct provider ids that might smuggle a
  `!` or `%` into the provider segment and reach the reserved branch. Try
  literal `!`, `!:payload`, `a!b`, `%21`, `%2521`, uppercase, whitespace,
  embedded colons, empty, non-str, and long ids. State whether you found a
  counterexample.
- Precedence: is the `@!:` check truly before every ownership/alias/config scan
  in `resolve_model_provider`, and can a session value reach a different branch
  first (session repair, `_resolve_compatible_session_model_state`,
  `canonical_model_provider_lane`, reasoning/aux model paths, gateway payloads)?
- Regressions in the modified existing tests: were any assertions weakened
  rather than adapted (see `tests/test_issue7290_no_slash_prefixed_alias.py`
  and `tests/test_model_picker_badges.py`)?
- Cross-language parity: do the Python and JavaScript decoders agree on the
  ambiguous legacy shapes and on the reserved form? Any divergence that could
  send the same stored value to two different endpoints?
- The end-to-end user-visible claim for #7955: on the configured endpoint with a
  colon-bearing model id (e.g. `qwen3:8b`) and a colliding named record, does the
  request actually go to `model.base_url` with the full id and the configured
  credentials, and never borrow the named record's key or endpoint?
- Honesty of the report: any claim in the report that your own execution
  contradicts.

## Verdict format

    VERDICT: APPROVE  |  BLOCK
    BLOCKERS: (each with the exact command + observed output that proves it)
    NON-BLOCKING NOTES:
    CLAIM CHECK: which report claims you reproduced, which you could not, and why.

An APPROVE with no independent execution is worthless. If you cannot run
something, say so explicitly instead of assuming.

## Standing constraints

This is a contribution to an open-source project. Never mention Hermes, AI,
agents or assistants in any output you produce for it, and never sign anything.
Only the human contributor `Szqub` is an author anywhere. Your verdict goes to
the human operator, not into the repository.