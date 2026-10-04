# Gate 7 — verification of the PR commit after the third hardening round. READ ONLY.

    worktree: /opt/data/cache/scratch/wt-design-7955
    branch:   fix/7955-configured-custom-disjoint-route
    commit:   f4b039b9      (base cdff0b8d)
    history:  f585b123 -> 37032708 -> ba745f59 -> f4b039b9

Your last round produced three executable counterexamples against `ba745f59`.
All three reproduce as fixed now, and the underlying rule was generalised.

## What changed in this round

Rule: a qualified value carries its own provider, and a caller hint never
interprets it.

1. `_ensureModelOptionInDropdown`: any already-qualified value is injected
   verbatim; the hint only encodes models that arrive bare. Wrapping a
   qualified value under the hint produced `@!:@safe:model-a` and
   `@custom:backup:@!:model-a`.
2. `_findModelInDropdown`: the normalized-match fallback now refuses to
   substitute an option whose provider differs from the provider named by the
   requested value, and the exact-match path is included in that precedence.
3. `_modelStateForSelect`: the value's own provider wins over the option group;
   only a custom namespace is stripped to its identifier (a non-custom qualified
   id stays a provider namespace, #1771).
4. `api/config.py`: new `_encode_catalog_route` / `_configured_custom_lane_is_reserved`.
   The catalog now advertises the configured lane as `@!:M`, so the Custom group
   no longer contains the ambiguous `@custom:M` spelling; every other provider,
   and any configuration without that endpoint, keeps the generic escaped
   spelling.
5. Tests: `test_legacy_value_is_not_substituted_by_a_configured_lane_option`,
   `test_configured_lane_option_carries_the_reserved_route`,
   `test_catalog_advertises_the_reserved_lane`,
   `test_catalog_keeps_generic_spelling_without_an_endpoint`.

## Run

    cd /opt/data/cache/scratch/wt-design-7955
    export PYTHONPATH=/opt/data/cache/scratch/wt-astra-7955/.venv/lib/python3.13/site-packages \
      HERMES_HOME=/opt/data/cache/scratch/design-7955-home \
      HERMES_WEBUI_STATE_DIR=/opt/data/cache/scratch/design-7955-state \
      HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent TMPDIR=/tmp
    ./scripts/test.sh tests/test_issue7955_disjoint_route.py tests/test_issue7955_route_js.py -q --timeout=180
    node --check static/ui.js && git diff --check cdff0b8d

## Required checks

- Re-run your three counterexamples verbatim (`inject-existing`, `inject`, and
  the non-custom lookup). Then try to break the new rule: construct a path where
  a hint still changes the interpretation of a qualified value, or where one
  provider's option substitutes another's.
- Catalog rule: can `_encode_catalog_route` ever emit `@!:` for a configuration
  where the resolver would refuse it, or skip it where the configured lane is
  active? Check both directions, including `model.provider: custom`,
  `providers: {custom: ...}`, no `base_url`, an active `custom:<slug>`, and a
  custom_providers entry literally named `custom`.
- Pickers: does the reserved catalog spelling survive dedup, seeding, badge
  matching, alias resolution, cron/profile persistence and restore without
  double-wrapping?
- Any regression in the neighbour suites you ran previously?
- Is every new behaviour covered by a test that would fail if the branch were
  removed?
- Anything in the docs that your execution contradicts?

## Verdict format

    VERDICT: APPROVE | BLOCK
    BLOCKERS: (exact command + observed output)
    PREVIOUS FINDINGS STATUS: addressed / not addressed / still blocking
    NON-BLOCKING NOTES:

## Standing constraints

Never mention Hermes, AI, agents or assistants in output for the project; never
sign anything; only the human contributor `Szqub` is an author. Verdict goes to
the human operator only.