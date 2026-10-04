VERDICT: BLOCK — Repo A brings back the exact regression the maintainer already rejected on PR #7966 ("the bare return drops the session's endpoint ownership"). A Custom-lane model whose id another provider also lists now goes to that other machine.

Repo B has no blocker. The verdict comes from Repo A alone. I didn't edit, commit or push anything in either repo. My scratch copies and probes are only under /opt/data/cache/scratch/rv-*.

Repo A — hermes-webui 15b59cb2

1. Blocker: requests silently go to a different endpoint. On 2026-10-02 the maintainer (nesquena-hermes) marked PR #7966 `gate-fail` for exactly this production change ("One CORE regression: the bare return drops the session's endpoint ownership"). Our commit has the same shape. I reproduced it with the layout from that review: `model.provider: ollama` on :11434, plus a `lab` provider at 10.0.0.8:8000 that lists the same models, session provider `custom`.

       model          before the commit (HEAD~1)          our HEAD
       mistral-7b     ('mistral-7b','custom',None) → :11434   ('mistral-7b','custom:lab','http://10.0.0.8:8000/v1')
       qwen3.8:27b    ('27b','custom:qwen3.8') (the #7955 bug)  ('qwen3.8:27b','custom:lab','http://10.0.0.8:8000/v1')
       via providers: map → 'lab', 10.0.0.8:8000 for both ids

   - Untagged models used to reach the Ollama server the user picked. Now they reach another machine.
   - The tagged case swaps one wrong endpoint for another.
   - The maintainer named the fix: keep the configured endpoint in charge in `resolve_model_provider()` before the model-ownership scan, or use a hint form that doesn't split on the model's own colon. They also asked for tests of this layout with untagged and tagged ids, through both `custom_providers[]` and `providers:`. None of the three earlier review rounds checked the upstream PR thread.

2. Smaller regression: a new crash for any provider. The line `(providers_cfg_for_custom.get(slug) or {}).get("base_url")` runs on every call, before the `provider in ("custom","local")` check. If `providers.custom` or `providers.local` isn't a dict (e.g. `providers: {custom: "http://x"}`), the call raises `AttributeError: 'str' object has no attribute 'get'`. In my probe an `openrouter` session crashed on HEAD; before the commit it gave `'@openrouter:claude-x'`. The file already has a safe helper, `_get_provider_cfg()`.

3. The bug class is only partly fixed. With `providers.custom.base_url` declared, `qwen3.8:27b` still comes back as `('27b', 'custom:qwen3.8')`. The doc lists this as a known limit. But `docs/GUIDELINES.md` rule 1 asks for the fix at the shared chokepoint, here the parser or a lossless hint. #7966 already went that way with a `@custom-configured:` hint.

4. A maintainer would also ask about:
   - Duplication: #7966 (ybai08) is open as the lead PR for this issue and is being reworked. #7967 was closed. The maintainer already said which approach they expect.
   - The doc says it "was added because the #7955 review flagged the encoding rules as undocumented". No public review said that. The maintainer's review flagged the regression above.
   - The upstream default branch is `master`, not `main`.

5. What does hold:
   - The test fails before and passes after: on HEAD~1, 12 fail and 7 pass; on HEAD, 19/19 pass.
   - `api/config.py` on master (cdff0b8d) is byte-identical to our base, so there's no conflict.
   - The docs are linked from `docs/CONTRACTS.md`.

Repo B — hermes-agent d3eb1a03

1. No blocker in the logic. Read and close claim the iterator under the same lock, and the deferred close runs on the worker after it leaves `next()`. I found no ordering where `close()` reaches a generator that is still executing.

2. Tests:
   - New test plus `test_relay_llm.py`: 50 passed.
   - Before the fix: 3/3 runs fail with `ValueError('generator already executing')`.
   - After the fix: 8/8 pass on an idle machine, and 8/8 pass with 16 busy processes on 8 CPUs.
   - `agent/relay_llm.py` on upstream main (c8301ea6) is byte-identical to our base.

3. What a maintainer would ask for:
   - The test uses a 0.5 s itimer, and the signal handler asserts the provider has already started. The release timer is 1.5 s. Root `AGENTS.md` asks for "wall-clock bounds ≥ 2s, event-based sync". It isn't flaky in practice, but it doesn't meet that rule as written.
   - Two branches of the handshake have no test: the close claiming first so the read becomes a no-op, and a deferred close that fails and only gets logged.
   - Three open PRs already target this issue: #132059, #132064 and #132080, all opened today. Ours would be the fourth. The PR body needs to say why this approach is better.

Bottom line: Repo A shouldn't go out until it keeps the configured endpoint in charge instead of returning a bare id, and has tests for the duplicate-id layout. Better still, coordinate with #7966. Repo B is fine to merge, but expect to defend it against the three existing PRs.
