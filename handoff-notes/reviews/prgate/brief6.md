# Gate 6 — final verification of the exact PR commit. READ ONLY (no edits/commits/pushes).

    worktree: /opt/data/cache/scratch/wt-design-7955
    branch:   fix/7955-configured-custom-disjoint-route
    commit:   ba745f59        (base cdff0b8d)
    history:  f585b123 -> 37032708 -> ba745f59

Both of you already verified the reserved-route design and found the browser
reinterpretation blocker; 37032708 addressed it and you confirmed that part.
Two further findings from your last round are addressed here. Verify them and
re-attack everything.

## Changes since 37032708

1. Option lookup precedence (reviewer finding: a stored value could be
   substituted by a differently-providenced option).
   `static/ui.js` `_findModelInDropdown`: the provider carried by a qualified
   value now outranks the caller hint — `preferred = explicitProvider ||
   preferredProviderId`. Previously a dropdown holding the configured-lane
   option `@!:8b` replaced the stored `@custom:qwen3:8b` on restore. Locked by
   `test_legacy_value_is_not_substituted_by_a_configured_lane_option`.
2. Custom-group option state (reviewer finding: catalog-emitted `@custom:<id>`
   in the Custom group lost the whole identifier).
   `static/ui.js` `_modelStateForSelect`: for an option whose authoritative
   provider is exactly `custom`, the legacy `@custom:` prefix is stripped and
   the entire remainder is the identifier, so a colon-bearing id is not read as
   a named record. Locked by `test_custom_group_option_keeps_the_whole_identifier`.
3. Commit message narrowed: the reserved form is written for a lane backed by a
   local server or legacy `local` with a base URL; `model.provider: custom`
   keeps its previous routing.
4. Docs updated for both behaviours in
   `docs/architecture/configured-custom-routing.md`.

## Run

    cd /opt/data/cache/scratch/wt-design-7955
    export PYTHONPATH=/opt/data/cache/scratch/wt-astra-7955/.venv/lib/python3.13/site-packages \
      HERMES_HOME=/opt/data/cache/scratch/design-7955-home \
      HERMES_WEBUI_STATE_DIR=/opt/data/cache/scratch/design-7955-state \
      HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent TMPDIR=/tmp
    ./scripts/test.sh tests/test_issue7955_disjoint_route.py tests/test_issue7955_route_js.py -q --timeout=180
    node --check static/ui.js && git diff --check cdff0b8d

## Attack these specifically

- Can any restore/injection/lookup path still substitute a stored qualified
  value with an option of another provider, or rewrite it into `@!:`?
- Does the Custom-group state rule break a named group (`custom:backup`) or a
  non-custom namespace (`@safe:...`) case you can construct?
- Is the picker → session encoder → resolver chain now consistent for a
  colon-bearing id picked from the Custom group (no truncation, configured
  endpoint, configured credentials)?
- Re-check your earlier non-blocking notes: are any of them now blocking?
- Anything in the diff that is not covered by a test that would catch its
  removal?

## Verdict format

    VERDICT: APPROVE | BLOCK
    BLOCKERS: (exact command + observed output)
    PREVIOUS FINDINGS STATUS: addressed / not addressed / still blocking
    NON-BLOCKING NOTES:

## Standing constraints

Never mention Hermes, AI, agents or assistants in output for the project; never
sign anything; only the human contributor `Szqub` is an author. Verdict goes to
the human operator only.