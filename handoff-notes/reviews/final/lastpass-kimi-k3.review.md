Both repos verified. Final report:

Repo A — hermes-webui @ 15b59cb2: PASS

- Diff scope: `git diff HEAD^ HEAD --stat` touches only api/config.py, docs/CONTRACTS.md, docs/architecture/provider-context-model-encoding.md, and the new test file. A worktree of HEAD^ (created at /opt/data/cache/scratch/wt-verify-7955-parent) diffed recursively against the checkout shows no other content differences (only untracked .venv). The new code block in `model_with_provider_context` (api/config.py:4879-4918) is gated on `provider in ("custom","local") and not declared_custom_endpoint`, so no other routing case can reach it.
- Revision 1 confirmed: `declared_custom_endpoint` iterates both slugs from `_get_providers_cfg()` and deliberately avoids `_get_provider_base_url` (api/config.py:4909-4913), matching the commit message's rationale.
- anthropic + providers.custom.base_url + session custom/local: pinned by `test_declared_custom_endpoint_keeps_its_hint` (line 199) and `test_endpoint_declared_under_either_slug_keeps_its_hint` (line 239, both slug directions); the first asserts `resolve_model_provider` returns `("foo","custom","https://proxy.example/v1")`.
- ollama + base_url + session custom + qwen3.8:27b: `test_reported_colon_model_resolves_to_configured_endpoint` (line 78) asserts the exact triple model `qwen3.8:27b`, provider `ollama`, base_url `http://127.0.0.1:11434/v1`.
- No-provider + model.base_url: `test_empty_config_provider_with_base_url_stays_bare` (line 137), matching the new branch at api/config.py:4916-4918.
- Test/doc consistency: module docstring (lines 1-29), the parametrized test docstring (lines 176-184, correctly describes both alias-table and WebUI-table paths), and the architecture doc (rule 5, invariants incl. the qualified round-trip invariant at line 120-127) all match the code. No stale "whenever the active provider is a local server" claim remains.
- Commands run:
  - `python -m pytest tests/test_issue7955_bare_custom_local_provider_model_id.py -q -p no:cacheprovider` → 19 passed
  - `python -m pytest tests/test_issue7333_slash_id_provider_hint.py tests/test_model_resolver.py tests/test_provider_mismatch.py tests/test_issue1894_provider_overlap.py -q -p no:cacheprovider` → 174 passed

Repo B — hermes-agent @ d3eb1a03: PASS

- Own fixture: `relay_turn` is defined locally at tests/agent/test_relay_blocked_generator_interrupt.py:27-48; the file's only imports are signal/threading/time/pytest and `agent.relay_llm`/`agent.relay_runtime` (lines 12-22) — no import from test_relay_llm.
- Dead guard: the only `if stream is not None:` (line 91) is the legitimate guard inside `finally` (stream may be None if `stream()` raised before returning). After the precondition assert at line 96, `stream` is used unguarded — the dead guard is gone.
- Doc wording: website/docs/developer-guide/relay-managed-stream-ownership.md:37-38 says "a platform stop"; grep finds no `/stop` or platform-command name anywhere in the doc, relay_llm.py, or the test.
- Commands run (HERMES_HOME=/opt/data/cache/scratch/ha-home, ha-venv python):
  - `python -m pytest tests/agent/test_relay_blocked_generator_interrupt.py tests/agent/test_relay_llm.py -q -p no:cacheprovider` → 50 passed
- The seven unrelated relay failures you flagged (nemo_relay version skew) were not re-checked; they're out of scope for this commit, which touches only relay_llm.py, its new test, the doc, and sidebars.ts.

Both commits are clean and ready.
