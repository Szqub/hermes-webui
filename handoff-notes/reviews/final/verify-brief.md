# Final verification — two fork branches, read-only

READ-ONLY: do NOT edit, stage, commit, push, or open pull requests. Read, run
tests, report.

Two changes are committed on branches of two forks, on this machine. A previous
review round produced findings; both commits were revised. Verify the revisions
and give a final per-repo verdict.

## Repo A — /opt/data/cache/scratch/hermes-webui

Branch `fix/7955-bare-custom-local-provider-model-id`, HEAD `d9febe20`
(previously `49cc9005`). Issue: nesquena/hermes-webui#7955.

Findings from the previous round that were acted on:

1. **Routing regression.** The earlier revision returned the bare model for ANY
   session whose provider was `custom` / `local`. That was wrong: when
   `providers.custom` declares its own `base_url`, `_get_provider_base_url()`
   reads it, so `@custom:<model>` IS a route, and a bare id fell through to the
   configured default provider. Reported repro:
   `model.provider: anthropic` + `providers.custom.base_url=https://proxy.example/v1`,
   session provider `custom`, model `foo` -> parent produced
   `@custom:foo` -> `('foo','custom','https://proxy.example/v1')`, the bad
   revision produced `foo` -> `('foo','anthropic',None)`.
   Fix: the bare passthrough is now gated on
   `not _get_provider_base_url(provider)` and on the configured provider naming
   the same endpoint (alias table / local-server table / no configured provider
   plus `model.base_url`). Tests
   `test_declared_custom_endpoint_keeps_its_hint` and
   `test_declared_local_endpoint_keeps_its_hint` pin the reported repro.
2. **Documentation did not match the code.** The claim "a bare `custom` names an
   endpoint only through `model.base_url`" was false; the round-trip invariant
   was stated too strongly; the "negative control" sentence contradicted rule 9;
   and the doc claimed it changed no runtime behaviour. All four reworded.

What to verify:

- The regression is actually gone: run the repo's own repro shape on HEAD and
  confirm `('foo','custom','https://proxy.example/v1')`.
- The #7955 case still resolves: `model.provider: ollama` + `base_url` +
  `model_provider='custom'` + model `qwen3.8:27b` stays bare and resolves to
  `('qwen3.8:27b','ollama','http://127.0.0.1:11434/v1')`.
- No other routing case changed relative to the parent commit. The parent is
  `HEAD~1` on this branch (`49cc9005`'s parent, i.e. the upstream tip) — use a
  throwaway `git worktree` rather than swapping files in the checked-out tree.
- The doc now states the code as written.

Commands:

    cd /opt/data/cache/scratch/hermes-webui
    . .venv/bin/activate
    export HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent
    python -m pytest tests/test_issue7955_bare_custom_local_provider_model_id.py -q -p no:cacheprovider

## Repo B — /opt/data/cache/scratch/hermes-agent

Branch `fix/132048-relay-blocked-provider-close`, HEAD `7b47e3e8`
(previously `cd19fea3`, before that `e5dbd9f7`). Issue:
NousResearch/hermes-agent#132048.

The read/close handshake in `agent/relay_llm.py::_provider_stream` now claims
the iterator under one lock on both sides (`_claim_close`, `_read_next_chunk`).
Acted-on findings since: `pytest.mark.platforms("posix")` on the POSIX-only
test, a behaviour-describing docstring, trailing newline, an
`assert stream is not None` precondition, frontmatter on the doc page, and the
commit message no longer claims every deferral is logged.

Commands:

    cd /opt/data/cache/scratch/hermes-agent
    export HERMES_HOME=/opt/data/cache/scratch/ha-home
    /opt/data/cache/scratch/ha-venv/bin/python -m pytest tests/agent/test_relay_blocked_generator_interrupt.py -q -p no:cacheprovider
    /opt/data/cache/scratch/ha-venv/bin/python -m pytest tests/agent/test_relay_llm.py -q -p no:cacheprovider

Seven relay tests (`tests/agent/test_relay_tools.py`,
`test_relay_runtime_plugins.py`, `test_relay_atof_cwd.py`) fail in this
environment on the unmodified commit too — an installed `nemo_relay` version
skew, not a result of the change.

## Reply with

- A verdict per repo: BLOCK / APPROVE WITH CHANGES / APPROVE.
- Each finding with file:line and why it matters.
- For anything you ran, the exact command and its result.
- Anything that must be fixed before this could be proposed upstream.

Be concrete; no diff summary. If you find nothing, say so plainly.
