## Verdict
APPROVE — fix poprawnie trafia w root cause, test failuje bez fixa (zweryfikowane), dokumentacja zgodna z kodem; dwie drobne uwagi do testów, nieblokujące.

## Verified claims
- `git show eba87b58` — diff: +18 linii w `api/config.py` (jeden guard w `model_with_provider_context`), nowy test (211 linii), nowy doc + wpis w CONTRACTS.md.
- `python -m pytest tests/test_issue7955_bare_custom_local_provider_model_id.py` (venv, `HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent`): **14 passed**.
- Proof-of-fail bez fixa: skopiowałem `api/` poza repo do `/opt/data/cache/scratch/probes/prefix/`, podmieniłem `config.py` na wersję z `3c8a533a` (`git show`) i odpaliłem ten sam plik testowy: **10 failed, 4 passed** — failing tests to dokładnie scenariusze buga (ollama/vllm/llamacpp/local + resolve round-trip), passing to kontrole negatywne. Repo nie zostało zmodyfikowane.
- Regresja sąsiednich suite'ów: 9 plików testowych używających `model_with_provider_context` (m.in. test_model_resolver, test_provider_mismatch, test_issue7333, test_issue1806, test_issue1894, test_resolve_model_provider_free_suffix): **399 passed**.
- Alias tables: `hermes_cli/auth.py:1478-1487` mapuje `local/ollama/vllm/llamacpp/llama.cpp/llama-cpp → custom`; `lmstudio/lm-studio → lmstudio` (NIE custom). WebUI `_PROVIDER_ALIASES` (config.py:1262) nie ma wpisów local-server poza `local→custom`.
- Sibling call sites: wszystkie 7 wywołań (`api/streaming.py:12170`, `api/routes.py` ×5, wewnętrzne) idą przez wspólną funkcję — fix w jednym miejscu pokrywa wszystkie ścieżki, w tym `canonical_model_provider_lane`.

## Findings
1. minor, tests/test_issue7955_bare_custom_local_provider_model_id.py:123-140 — docstring parametrized testu twierdzi "Every local-server name the picker can collapse to `custom`", ale wg obu tabel aliasów `lmstudio`, `lm-studio` i `tabby` NIGDY nie zwijają się do `custom` (alias → `lmstudio`, brak wpisu dla tabby). Dla nich session `model_provider` = `lmstudio` i trafia w preexisting equality check, więc te wiersze pinują hipotetyczny stan sesji (np. stale session po zmianie configu), nie realną ścieżkę pickera. Nieszkodliwe (guard w tamtą stronę jest poprawny), ale claim w teście jest nieudowodniony. Sugestia: doprecyzować docstring albo ograniczyć parametryzację do nazw faktycznie aliasowanych do `custom` + osobny test dla stale-session.
2. minor, tests/…:96-120 — `test_pre_fix_hint_is_the_corrupted_form` asertuje dokładny kształt ZBUGOWANEGO parsowania `("27b", "custom:qwen3.8")`. Jeśli ktoś później naprawi gramatykę `_parse_provider_qualified_model_id`, test failuje mimo że #7955 pozostaje naprawione — cechy change-detectora, którego guidelines zabraniają. Częściowo usprawiedliwione jako dokumentacja kontraktu gramatyki, ale druga połowa asercji (`!= "@custom:..."`) wystarczyłaby do celu. Sugestia: przerobić na asercję relacyjną (parsed model != wejściowy model id, provider nie w custom_providers).
3. nit, api/config.py:4877-4894 — fix replikuje warunek zwinięcia (alias==custom OR local-server) na konsumencie zamiast normalizować obie strony przez `_resolve_configured_provider_id` przed porównaniem. Root cause (raw-string equality między post-collapse session provider a raw config provider) zostaje w strukturze kodu; kolejna wariacja zwinięcia znów wymusi łatanie konsumenta. Akceptowalne jako targeted fix, ale warte odnotowania w PR.

## What is good
- Warunek jest celowany: nie rusza named `custom:<slug>` (osobny test), nie-local config provider (test kontroli negatywnej przechodzi i fail-safe), ACP/plugin/codex ścieżki są przed guardem.
- `_is_local_server_provider` jako druga klauzula pokrywa przypadek, gdy `hermes_cli` nie jest na sys.path (lokalna tabela WebUI nie ma ollama) — realna redundancja, nie dead code.
- Dokument (docs/architecture/provider-context-model-encoding.md) wiernie odzwierciedla kolejność reguł 1–9 z kodem i nie wymyśla zachowania; wpis w CONTRACTS.md zgodny z wymogiem repo.
- Jedna logiczna zmiana, brak unrelated refactors, commit message z line-level wyjaśnieniem mechanizmu.

## Residual risk
- Nie zweryfikowałem end-to-end, że picker FAKTYCZNIE zapisuje `custom` w sesji dla `model.provider: ollama` (twardo wynika z aliasów + `_resolve_configured_provider_id(resolve_alias=True)`, ale nie uruchamiałem UI); kontrakt testów zakłada to za issue.
- Nie sprawdziłem ścieżki streamingowej z prawdziwym serwerem Ollama (tylko resolve-time tuple).
- Hipoteza, że session `custom` zawsze oznacza configured endpoint (a nie inny bare custom z poprzedniego profilu/configu) — dla stale session cross-config guard zwraca bare i routuje przez AKTUALNY config, co uznałem za pożądane, ale to decyzja semantyczna warta zaznaczenia maintainerowi.
