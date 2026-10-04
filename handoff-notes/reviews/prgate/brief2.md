# Pre-PR gate — final verdict on two fork branches (READ-ONLY)

READ-ONLY: do NOT edit, stage, commit, push, or open pull requests. Two branches are
about to be proposed upstream; your job is to decide whether they may be.

You have a terminal. Verify independently — do not take the authors' summaries on trust.

## Branch A — `nesquena/hermes-webui`, issue #7955

    fork:   https://github.com/Szqub/hermes-webui.git
    branch: fix/7955-custom-lane-endpoint-authoritative   @ 47f3a05a
    base:   upstream master cdff0b8d
    local:  /opt/data/cache/scratch/wt-astra-7955   (clean worktree, this exact commit)
    venv:   /opt/data/cache/scratch/wt-astra-7955/.venv
    run:    . .venv/bin/activate && export HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent
    baseline worktree at cdff0b8d: /opt/data/cache/scratch/wt-astra-7955-base

Changed: `api/config.py` (+67/-1, in `resolve_model_provider`), new
`tests/test_issue7955_custom_lane_endpoint_authoritative.py`, new
`docs/architecture/custom-lane-endpoint-authority.md`, `docs/CONTRACTS.md` link.

The change makes the plain `custom` lane endpoint-authoritative in the *parser*
(`resolve_model_provider`) instead of changing the wire encoding: when the configured
lane is the custom endpoint (`model.base_url` set, raw `model.provider` empty / `custom`
/ legacy `local` / a local-server provider), the whole payload after `@custom:` is the
model id, returned as provider `custom` + `model.base_url`, bypassing the
`custom_providers[]` ownership scan and `_get_provider_base_url()`.

### The maintainer's acceptance bar (three review rounds on two competing PRs)

He rejected, in order (verbatim, from PR #7966):

1. **"return the model bare"** — "One CORE regression: the bare return drops the session's
   endpoint ownership. Once the model is bare, `resolve_model_provider()` runs its
   model-ownership scan over `custom_providers[]` and `providers:` before falling back to
   the configured endpoint. If another configured provider also lists the same model id,
   the request goes to *that* endpoint even though the user picked the model from the
   Ollama/local lane."
2. **emitting the configured provider as the hint (`@ollama:<model>`)** — "it fixes the
   duplicate-id scan, but `_get_provider_base_url()` / `resolve_model_provider()` now
   consult same-named records that the Custom lane never used" (e.g.
   `providers.ollama.base_url: other:9999` hijacks the route).
3. **a new internal token `@custom-configured:`** — "The new internal `@custom-configured:`
   route collides with an ordinary provider name the existing catalog can emit."
   The lesson he drew: the route must be **provably disjoint from every token the generic
   `providers:` namespace can emit**, enforced by construction or a check in code, not by
   an unlikely spelling.

He also named the bar for whoever lands it first: *"Whichever branch first keeps the
configured endpoint authoritative … is the one I'll take."*

### Required matrix — verify all of it, in both competitor shapes

Layout: `model.provider: ollama` (also `vllm`, and the legacy `local` spelling) with
`model.base_url: http://127.0.0.1:11434/v1`, session provider `custom`, competitor
listing the same ids (`custom_providers: [{name: lab, base_url: http://10.0.0.8:8000/v1,
models: [mistral-7b, qwen3.8:27b]}]`, and the same under `providers:`).

- untagged `mistral-7b` (both offer it) → provider `custom`, base `:11434`
- tagged `qwen3.8:27b` (both offer it) → provider `custom`, base `:11434`, whole id kept
- `llama3` (only on the Ollama lane) → `ollama`, `:11434`
- with `providers.ollama.base_url: http://other:9999` present → still `custom` → `:11434`;
  `other:9999` must never be consulted
- legacy `provider: local` with `providers.local.base_url: other:9999` → `custom` → `:11434`
- `custom_providers: [{name: local, base_url: http://named:7777/v1, api_key: sk-…}]` with
  legacy `provider: local` → `custom` → `:11434`, and that record's key must not be borrowed
- unchanged: named `custom:lab` passthrough (incl. tagged id), explicit `@local:`,
  `@ollama:`, real provider ids, a valid `providers.custom-configured` entry
  (`@custom-configured:<model>` → that named provider + its endpoint), malformed
  non-mapping `providers.<slug>` does not raise

A probe you can start from: `/opt/data/cache/scratch/probe_matrix_7955.py` (run it in both
worktrees; `HERMES_WEBUI_AGENT_DIR` as above).

### Questions that matter

- Does the disjointness argument actually hold for **every** token the `providers:`
  namespace can emit, including adversarial provider ids? Try to construct a collision.
- Does the lane misfire for a legitimate named-provider pick, or break the #4728
  fail-closed rule (`tests/test_issue1806_named_custom_provider_resolution.py`)?
- Is the previously-erroring `@custom:<unconfigured-slug>:<model>` reinterpretation
  acceptable, or does it silently steal a real named-provider route?
- Do the new tests fail on `cdff0b8d` and pass here (`12 failed, 11 passed` expected on
  the baseline)? Run the neighbouring suites and report real counts.
- Is the documentation accurate, and does the PR-body `Contract Routing` section match
  `docs/CONTRACTS.md` requirements?

## Branch B — `NousResearch/hermes-agent`, issue #132048

    fork:   https://github.com/Szqub/hermes-agent.git
    branch: fix/132048-relay-blocked-provider-close   @ 0c6045d7
    base:   upstream main
    local:  /opt/data/cache/scratch/hermes-agent
    python: /opt/data/cache/scratch/ha-venv/bin/python   (needs HERMES_HOME set)
    run:    HERMES_HOME=/opt/data/cache/scratch/ha-home \
            /opt/data/cache/scratch/ha-venv/bin/python -m pytest <paths> -q -p no:cacheprovider

Changed: `agent/relay_llm.py` (read/close ownership handshake:
`close_guard`/`close_state`/`_claim_close`/`_read_next_chunk`),
`tests/agent/test_relay_blocked_generator_interrupt.py` (2 tests),
`website/docs/developer-guide/relay-managed-stream-ownership.md`, `website/sidebars.ts`.

Interrupting a Relay-managed provider read used to close a generator the worker thread was
still executing (`ValueError: generator already executing`) and skipped the provider's own
`finally`. The fix reserves the iterator under one lock for both read and close, so the two
decisions cannot overlap; a close requested while a worker is reading is deferred to that
worker, which runs it after its read returns and logs (never raises) a failure.

Context you should know: **three other draft PRs are already open on this issue**
(#132059, #132064, #132080, all from 2026-10-03). Assess whether this branch is
distinct enough to be worth proposing as a fourth, or duplicates them.

### Questions that matter

- Prove the handshake: can read and close ever interleave, or a close be lost, under any
  interleaving you can construct? A stress harness is welcome.
- Are all three branches of the guard covered by tests? A read that arrives after the close
  claimed the iterator (`(None, True)`) is documented as unreachable from the public API —
  check that claim rather than accepting it.
- `AGENTS.md` requires wall-clock bounds ≥ 2s and event-based sync in tests. Verify the new
  tests comply and are deterministic (run them several times).
- Report the real failure set of the neighbouring relay suites, and whether it is
  pre-existing skew (`nemo_relay`/`additional_plugins_toml`) or caused by the change.

## Output

For EACH branch, start your answer with a single line:

    BRANCH A: APPROVE   |  BRANCH A: BLOCK
    BRANCH B: APPROVE   |  BRANCH B: BLOCK

(then, if BLOCK, the specific blocking finding, and for APPROVE, the evidence you actually
ran). Be blunt about anything you could not verify. Synthetic endpoints only, no real
credentials, no network calls beyond the repositories above.