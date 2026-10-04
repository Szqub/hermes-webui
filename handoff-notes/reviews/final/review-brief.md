# Final independent review — two fork branches, read-only

You are the final reviewer. Two independent changes are staged as commits on
branches of two forks of the repo checkouts below. You are READ-ONLY: do NOT
edit, stage, commit, push, or open pull requests. Read, run tests, and report.

Everything runs on this machine; there is no network requirement.

## Repo A — /opt/data/cache/scratch/hermes-webui

Branch `fix/7955-bare-custom-local-provider-model-id`, commit HEAD (`49cc9005`).

Upstream issue: nesquena/hermes-webui#7955 — with `model.provider: ollama` plus a
`base_url`, every Custom-group model fails with
`custom:<tag-prefix> not configured`.

Files touched: `api/config.py` (the guard in `model_with_provider_context`),
`tests/test_issue7955_bare_custom_local_provider_model_id.py` (new),
`docs/architecture/provider-context-model-encoding.md` (new contract doc),
`docs/CONTRACTS.md` (link).

Run the tests with:

    cd /opt/data/cache/scratch/hermes-webui
    . .venv/bin/activate
    export HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent
    python -m pytest tests/test_issue7955_bare_custom_local_provider_model_id.py -q -p no:cacheprovider

and the neighbouring encoding suites:
`test_issue7333_slash_id_provider_hint.py`, `test_provider_mismatch.py`,
`test_model_resolver.py`, `test_issue1894_provider_overlap.py`,
`test_resolve_model_provider_free_suffix.py`, `test_openai_api_provider_alias.py`,
`test_plugin_model_providers.py`, `test_issue1228_model_picker_duplicate_ids.py`,
`test_issue1806_named_custom_provider_resolution.py`, `test_issue1384_local_provider.py`
(reported: 17 passed new file, 412 passed neighbours).

## Repo B — /opt/data/cache/scratch/hermes-agent

Branch `fix/132048-relay-blocked-provider-close`, commit HEAD (`e5dbd9f7`).

Upstream issue: NousResearch/hermes-agent#132048 — interrupting a Relay-managed
provider read closes the provider generator while a worker thread is still
executing it, raising `ValueError: generator already executing` and skipping the
provider's own cleanup.

Files touched: `agent/relay_llm.py` (`ManagedLlmStream._provider_stream` read /
close ownership handshake), `tests/agent/test_relay_blocked_generator_interrupt.py`
(new), `website/docs/developer-guide/relay-managed-stream-ownership.md` (new),
`website/sidebars.ts` (entry).

Run the tests with:

    cd /opt/data/cache/scratch/hermes-agent
    export HERMES_HOME=/opt/data/cache/scratch/ha-home
    /opt/data/cache/scratch/ha-venv/bin/python -m pytest tests/agent/test_relay_blocked_generator_interrupt.py -q -p no:cacheprovider
    /opt/data/cache/scratch/ha-venv/bin/python -m pytest tests/agent/test_relay_llm.py -q -p no:cacheprovider

The venv borrows the installed Hermes site-packages through a `.pth` file, so
seven relay tests (`tests/agent/test_relay_tools.py`,
`test_relay_runtime_plugins.py`, `test_relay_atof_cwd.py`) fail in this
environment on the unmodified commit too — that is a version skew of the
installed `nemo_relay`, not a result of the commit.

## What to judge

1. Is the fix in each repo correct and complete for the issue it claims to
   close, and does it avoid regressing the behaviour the surrounding tests pin?
2. Is the new evidence (tests) real — does it actually fail before and pass
   after? Verify at least one by checking out the parent of HEAD in a
   throwaway worktree or by reading the pre-fix code path, then restore.
3. Does the new documentation state the code as written?
4. Anything that must be fixed before this could be proposed upstream.

## Intermediate reviews already received (see /opt/data/cache/scratch/reviews/)

Repo A: `7955/glm-5.3-flash.review.md`, `7955/kimi-k3.review.md`,
`7955/glm-5.3.review.md`.
Repo B: `132048/glm-5.3-flash.review.md`, `132048/kimi-k3.review.md`.

Findings already actioned in the current commits:

- A: the guard was widened from a per-config-name check to "any bare `custom`
  (or legacy `local`) session provider stays bare", closing the empty-provider
  and stale-session variants; the test docstring no longer over-claims; the
  pre-fix assertion is relational rather than shape-pinned.
- B: the new test carries `pytest.mark.platforms("posix")`; the
  queued-worker window is documented in `_read_next_chunk`; the new test file
  has a behaviour-describing docstring and a trailing newline; the doc's
  ownership rule now says "the consumer lane may close it only while no worker
  is executing it".

Deliberately NOT changed (say so if you disagree, with the reason):

- A: the guard lists `custom` and `local` literally rather than routing through
  `_resolve_provider_alias`, because that alias table lives in the agent tree
  and maps unrelated names (`ollama`) to `custom` when importable, which would
  widen the passthrough to sessions that legitimately route to a configured
  `ollama` provider.
- B: the close stays deferred rather than joining the worker, because joining
  would reintroduce the hang the deferral exists to avoid.

Reply with: a verdict per repo (BLOCK / APPROVE WITH CHANGES / APPROVE), the
findings that matter with file:line, and — if you ran anything — the exact
command and its result. Be concrete; no summary of the diff.
