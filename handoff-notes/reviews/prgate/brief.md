# Pre-PR gate — final verdict on two fork branches (read-only)

READ-ONLY: do NOT edit, stage, commit, push, or open pull requests. This is the
gate before the branches are proposed upstream: two reviewers are being asked
independently, and the PRs go out only if both agree.

Answer in this shape, at the very top of your reply:

    VERDICT: APPROVE
    or
    VERDICT: BLOCK — <one-line reason>

Then the evidence. If you find nothing, say so plainly and keep it short.

## Repo A — /opt/data/cache/scratch/hermes-webui

Branch `fix/7955-bare-custom-local-provider-model-id`, HEAD `15b59cb2`, three
commits behind upstream tip `3c8a533a`… actually one commit on top of it.
Upstream: `nesquena/hermes-webui`, default branch `main`. Issue: #7955.

The commit fixes: with `model.provider: ollama` (any local OpenAI-compatible
server) plus a `base_url`, the model picker collapses the active provider to the
generic `custom` slug, and `model_with_provider_context()` compared the RAW
strings, so a model id without a slash was minted into a synthetic
`@custom:<model>` hint. For a colon-bearing id that hint comes back corrupted
(`@custom:qwen3.8:27b` → provider `custom:qwen3.8` / model `27b`), surfacing as
`custom:<tag-prefix> not configured`.

Files: `api/config.py`, new `tests/test_issue7955_bare_custom_local_provider_model_id.py`,
new `docs/architecture/provider-context-model-encoding.md`, `docs/CONTRACTS.md`.

    cd /opt/data/cache/scratch/hermes-webui
    . .venv/bin/activate
    export HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent
    python -m pytest tests/test_issue7955_bare_custom_local_provider_model_id.py -q -p no:cacheprovider

## Repo B — /opt/data/cache/scratch/hermes-agent

Branch `fix/132048-relay-blocked-provider-close`, HEAD `d3eb1a03`, one commit on
top of upstream tip `bd0affe5`. Upstream: `NousResearch/hermes-agent`, default
branch `main`. Issue: #132048.

Interrupting a Relay-managed provider read closed the provider generator while a
worker thread was still executing it → `ValueError: generator already executing`,
and the generator's own `finally` never ran. The fix makes the read and the close
claim the iterator under one lock (`_claim_close` / `_read_next_chunk`), so
exactly one of the two can win.

Files: `agent/relay_llm.py`, new `tests/agent/test_relay_blocked_generator_interrupt.py`,
new `website/docs/developer-guide/relay-managed-stream-ownership.md`,
`website/sidebars.ts`.

    cd /opt/data/cache/scratch/hermes-agent
    export HERMES_HOME=/opt/data/cache/scratch/ha-home
    /opt/data/cache/scratch/ha-venv/bin/python -m pytest tests/agent/test_relay_blocked_generator_interrupt.py -q -p no:cacheprovider
    /opt/data/cache/scratch/ha-venv/bin/python -m pytest tests/agent/test_relay_llm.py -q -p no:cacheprovider

Seven relay tests (`tests/agent/test_relay_tools.py`,
`test_relay_runtime_plugins.py`, `test_relay_atof_cwd.py`) fail in this
environment on the unmodified commit too — an installed `nemo_relay` version
skew, not a result of the change.

## Rounds already done (all findings actioned)

Three review rounds by glm-5.3-flash, glm-5.3, kimi-k3 and opus-5.5. Notable:
opus-5.5 caught a routing regression in repo A (the bare passthrough must not
apply when `providers.custom`/`providers.local` declares its own `base_url`),
and glm-5.3 caught that the earlier handshake in repo B decided under the lock
but closed after releasing it; both were fixed and re-verified. The last round
(kimi-k3 and glm-5.3-flash, on these two SHAs) returned PASS on both.

## What to judge

1. Would you merge this as-is into `main`? If not, what exactly blocks it?
2. Does the change satisfy the repo's own contribution rules (each repo's
   `AGENTS.md` / `CONTRIBUTING.md`): one logical change, bug-class coverage,
   evidence that the test fails before and passes after, docs updated.
3. Anything a maintainer would ask for that is missing from the commit itself.