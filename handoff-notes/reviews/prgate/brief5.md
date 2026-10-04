# Gate 5 — re-verification after the blocker fix. READ ONLY (no edits, commits, pushes).

You reviewed commit `f585b123` and issued a BLOCK. The blocker was:

> The browser can reinterpret an old `@custom:qwen3:8b` as the configured Custom
> lane (injection produced `@!:qwen3:8b`), while Python reads the same bytes as
> named provider `custom:qwen3` with identifier `8b`. That contradicts the
> "not auto-migrated" claim and can move a restored session to another endpoint.

## Artifact now under review

    worktree: /opt/data/cache/scratch/wt-design-7955
    branch:   fix/7955-configured-custom-disjoint-route
    commit:   37032708     (base cdff0b8d)
    previous: f585b123

## What changed in response

The stricter of the two options you named was taken: a legacy value is never
rewritten by parsing.

1. `static/ui.js` `_parseModelRoute`: the legacy `@custom:` split (one slug
   segment, or `host:port`) is now evaluated BEFORE any caller hint. A hint can
   no longer re-read a colon-bearing suffix as the configured lane.
2. `static/ui.js` `_ensureModelOptionInDropdown`: a colon-bearing legacy
   `@custom:` value is injected verbatim (`legacyRecordRoute`), never rewritten
   into `@!:`; its option metadata is taken from the parsed route.
3. `tests/test_issue7955_route_js.py` expectations updated to the new contract:
   `_parseModelRoute("@custom:qwen3:8b","custom")` now returns
   `{provider:"custom:qwen3", model:"8b"}` — identical to Python — and injection
   preserves `@custom:qwen3:8b` with state model `8b`, provider `custom:qwen3`.
4. `docs/architecture/configured-custom-routing.md`: the legacy section now
   states that a caller hint never overrides the legacy split and that reaching
   the configured endpoint for a stored colon-bearing id requires re-selection.
5. Trailing blank line at EOF removed (`git diff --check cdff0b8d` now exits 0).

No Python behaviour changed in this round: Python already read the value as the
named record, so parity was achieved by moving JavaScript to Python's rule.

## Verify (run it yourself)

    cd /opt/data/cache/scratch/wt-design-7955
    export PYTHONPATH=/opt/data/cache/scratch/wt-astra-7955/.venv/lib/python3.13/site-packages \
      HERMES_HOME=/opt/data/cache/scratch/design-7955-home \
      HERMES_WEBUI_STATE_DIR=/opt/data/cache/scratch/design-7955-state \
      HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent TMPDIR=/tmp
    ./scripts/test.sh tests/test_issue7955_route_js.py tests/test_issue7955_disjoint_route.py -q --timeout=180
    node --check static/ui.js
    git diff --check cdff0b8d

Required checks for this round:

- Your original blocker: does any browser path still convert a legacy
  `@custom:<slug>:<model>` into `@!:` on restore/injection? Find one if you can
  (boot.js, ui.js session restore, profile injection, cron persistence,
  `_applySessionModelFallback`, `_modelStateForSelect`, `_findModelInDropdown`).
- Parity: for every legacy shape (`@custom:X`, `@custom:X:Y`,
  `@custom:host:port:model`, `${}%`-bearing, `@!:`), does Python
  `_parse_provider_qualified_model_id` agree with JavaScript `_parseModelRoute`
  about provider and model? Show any disagreement.
- Does the "restore preserves the value" contract hold end to end, i.e. can a
  restored session still reach the runtime with a stored legacy string, and does
  the runtime then route where Python's parser says (named record), not to the
  configured lane?
- Regressions: any of the neighbour suites you ran previously now failing?
- Did removing the hint shortcut break a legitimate case where the hint was the
  only way to identify an option (picker identity, dedup, badge, alias lookup)?
- Is the documentation now accurate for every behaviour you observed?

Also re-state any finding from your previous review that this round does NOT
address, and say whether you still consider it blocking.

## Verdict format

    VERDICT: APPROVE | BLOCK
    BLOCKERS: (exact command + observed output for each)
    PREVIOUS FINDINGS STATUS: addressed / not addressed / still blocking
    NON-BLOCKING NOTES:

## Standing constraints

Never mention Hermes, AI, agents or assistants in output intended for the
project; never sign anything; only the human contributor `Szqub` is an author.
Your verdict goes to the human operator only.