# Final pass — verify two revised commits (read-only)

READ-ONLY: do not edit, stage, commit, push, or open pull requests.

Two earlier review rounds produced findings; both commits were revised again.
Verify only the revisions and give a final per-repo verdict. Both repos are on
this machine. Be concrete and short: for each repo, a verdict, findings with
`file:line`, and the exact command + result for anything you ran.

## Repo A — /opt/data/cache/scratch/hermes-webui

Branch `fix/7955-bare-custom-local-provider-model-id`, HEAD **`15b59cb2`**
(previous revisions `05eecf61`, `d9febe20`, `49cc9005`). Issue:
nesquena/hermes-webui#7955.

Revisions since the last round:

1. The bare-passthrough gate now checks BOTH slugs for a declared endpoint
   (`api/config.py`): `declared_custom_endpoint = any(providers[slug].base_url
   for slug in ("custom", "local"))`, computed from `_get_providers_cfg()`
   rather than `_get_provider_base_url()`, because that helper's
   `model.base_url` fallback fires whenever `model.provider` equals the slug —
   which is the same-endpoint case the rule is about, not a declared route.
2. Stale statements in the test module were corrected: the section header, the
   parametrized test docstring (`test_bare_custom_stays_bare_for_local_config_names`),
   and the module docstring. New test
   `test_endpoint_declared_under_either_slug_keeps_its_hint` covers revision 1.
3. The architecture doc softened two over-claims ("whenever the active provider
   is a local server", the round-trip invariant).
4. The commit message no longer claims the rule is independent of the agent tree.

What to verify:

- `model.provider: anthropic` + `providers.custom.base_url` + session `custom`
  (or `local`) keeps its hint and resolves to the proxy endpoint.
- `model.provider: ollama` + `base_url` + session `custom` + `qwen3.8:27b` stays
  bare and resolves to `('qwen3.8:27b','ollama','http://127.0.0.1:11434/v1')`.
- Config naming no provider but setting `model.base_url` stays bare.
- No routing case outside bare `custom`/`local` changed relative to the parent
  (use a throwaway `git worktree`; do not swap files in the checked-out tree).
- Every statement in the test module and in the architecture doc now matches the
  code and the tests in the same commit.

    cd /opt/data/cache/scratch/hermes-webui
    . .venv/bin/activate
    export HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent
    python -m pytest tests/test_issue7955_bare_custom_local_provider_model_id.py -q -p no:cacheprovider

## Repo B — /opt/data/cache/scratch/hermes-agent

Branch `fix/132048-relay-blocked-provider-close`, HEAD **`d3eb1a03`**
(previous `7b47e3e8`, `cd19fea3`, `e5dbd9f7`). Issue:
NousResearch/hermes-agent#132048.

Revisions since the last round: the test now defines its own `relay_turn`
fixture instead of importing it from `tests/agent/test_relay_llm.py`, the dead
`if stream is not None:` guard after the precondition assert is gone, and the doc
says "a platform stop" instead of naming a specific platform command.

    cd /opt/data/cache/scratch/hermes-agent
    export HERMES_HOME=/opt/data/cache/scratch/ha-home
    /opt/data/cache/scratch/ha-venv/bin/python -m pytest tests/agent/test_relay_blocked_generator_interrupt.py -q -p no:cacheprovider
    /opt/data/cache/scratch/ha-venv/bin/python -m pytest tests/agent/test_relay_llm.py -q -p no:cacheprovider

Seven relay tests (`tests/agent/test_relay_tools.py`,
`test_relay_runtime_plugins.py`, `test_relay_atof_cwd.py`) fail in this
environment on the unmodified commit too — an installed `nemo_relay` version
skew.
