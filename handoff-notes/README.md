# Handoff notes — #7955

Everything needed to finish, verify and publish the #7955 work lives in this
directory. It is on the `handoff/7955` branch only; the PR branch is
`fix/7955-configured-custom-disjoint-route`.

## Start here

| File | What it is |
|---|---|
| `HANDOFF-7955.md` | Full analysis: what is fixed, what is open, repro commands, evidence. Read first. |
| `DEVIN-PROMPT.md` | The work order: branch map, scope decision, constraints. |
| `pr-webui-body-v4.md` | PR body for `nesquena/hermes-webui` (#7955). |
| `pr-agent-body.md` | PR body for `NousResearch/hermes-agent` (#132048). |

## State

    Szqub/hermes-webui
      fix/7955-configured-custom-disjoint-route  843f203a  THE PR BRANCH
      handoff/7955                               (this branch)
    Szqub/hermes-agent
      fix/132048-relay-blocked-provider-close    b40ca5cf  PR #132048

- Repo A: reported issue verified fixed end to end on the issue's own
  configuration (`model.provider: ollama` + `base_url`). Targeted suite
  **101 passed**; the same tests on the base `cdff0b8d` give **79 failed /
  12 passed**. Full suite: **18007 passed, 3 failed** — all six independent of
  the change and explained in `HANDOFF-7955.md`.
- Repo B: tests **2 passed**, independent review APPROVE.

## reviews/

Independent review rounds (glm, kimi, sol, opus, astra) and their gate briefs.
`prgate/` holds the gate rounds; `final/` the last-pass reviews; `7955/` and
`132048/` the per-issue verdicts. These are the raw inputs behind the "open
blockers" list in `HANDOFF-7955.md`; keep them if you need to re-litigate a
finding.

## harness/

Small standalone probes used to produce the evidence. They are **not** part of
the product test suite and are not run by CI.

- `g7-pickers/routes.js` — executes the real picker functions from a worktree
  under node. Actions: `parse`, `inject`, `inject-existing`, `metadata`,
  `consumers`, `aliases`, `dedup`, `live`.
- `g7-pickers/dedupcheck.js` — reproduces the Custom-group dedup loss.
- `g6/cat5.py` — prints the catalog route each configuration actually emits.
- `g6/mutate.py`, `g7/mutate.py` — mutation checks (which mutants survive).
- `g7/cred.py` — credential-boundary probe.
- `g7-catalog/test_catalog_review.py` — catalog review tests (6 failed /
  16 passed, an open blocker).

### Paths

The scripts hardcode the authoring machine's layout, e.g.
`/opt/data/cache/scratch/wt-design-7955`. Replace that with your own checkout
path before running them. They take the worktree as an argument where possible:

    node harness/g7-pickers/routes.js <worktree> '{"action":"metadata","cases":[["@custom:qwen3:8b","custom","@custom:qwen3:8b","custom"]]}'
    node harness/g7-pickers/dedupcheck.js <worktree>

Python probes expect to run with the worktree as the working directory and with
`HERMES_HOME`, `HERMES_WEBUI_STATE_DIR` and `HERMES_WEBUI_AGENT_DIR` pointed at
disposable directories, e.g.:

    cd <worktree>
    HERMES_HOME=/tmp/ha-home HERMES_WEBUI_STATE_DIR=/tmp/ha-state \
      HERMES_WEBUI_AGENT_DIR=<hermes-agent checkout> \
      .venv/bin/python <path>/harness/g6/cat5.py

The real test suite is the authority, not these probes:

    ./scripts/test.sh tests/test_issue7955_disjoint_route.py tests/test_issue7955_route_js.py \
      tests/test_issue854_live_model_prefix.py tests/test_model_picker_badges.py -q