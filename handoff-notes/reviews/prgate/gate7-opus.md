VERDICT: BLOCK

Sprawdziłem `f4b039b9` na czystym worktree. Niczego w nim nie zmieniałem. Wszystkie próby i mutanty są w `/opt/data/cache/scratch/g7/`.

Komendy z briefu:
- 91 passed.
- `node --check static/ui.js` i `git diff --check cdff0b8d` kończą się kodem 0.
- `export PYTHONPATH` zablokowała polityka wykonania, więc uruchomiłem testy bez niego, na `.venv` z worktree.

BLOCKERS:

1. Pole Custom wysyła klucz jednego endpointu do innego hosta (granica poświadczeń).

Konfiguracja testowa w osobnym `HERMES_HOME`:
- `model: {provider: ollama, base_url: http://127.0.0.1:11434/v1}`
- `providers.custom: {base_url: http://gpu-box:8000/v1, api_key: <syntetyczny>, models: [mistral]}`

    cd /opt/data/cache/scratch/wt-design-7955 && HERMES_HOME=/opt/data/cache/scratch/g7/home-head-ollama_providers_custom HERMES_WEBUI_STATE_DIR=/opt/data/cache/scratch/g7/state-head-ollama_providers_custom HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent .venv/bin/python /opt/data/cache/scratch/g7/cred.py ollama_providers_custom

    "wire": "@!:mistral"
    "resolved": ["mistral","custom","http://127.0.0.1:11434/v1"]
    "runtime": {"base_url":"http://gpu-box:8000/v1","api_key_is_OTHER_key":true}
    "bundle": {"provider":"custom","base_url":"http://127.0.0.1:11434/v1","api_key":"OTHER-KEY"}

- Na `cdff0b8d` ten sam przypadek daje spójny bundle: `gpu-box` z kluczem `gpu-box`.
- Na PR URL pochodzi z `model.base_url`, a klucz z `providers.custom`. Ten sam wynik daje wariant z `lmstudio`.
- `cred.py` sam składa wywołania z `api/streaming.py:12170–12230`. To nie jest pełne przejście przez stream.
- Model `mistral` jest zadeklarowany tylko pod `gpu-box`, a trafia do lokalnego endpointu.
- Problem istnieje od `f585b123` (session encoder). W tej rundzie katalog dla `lmstudio` i `llamacpp` dodatkowo ogłasza to jako `@!:mistral`.
- To jest punkt „pełny łańcuch credentials niezweryfikowany” z poprzedniej rundy. Teraz jest zweryfikowany i nie przechodzi.

2. Istniejący test repo pada deterministycznie.

    ./scripts/test.sh tests/test_issue854_live_model_prefix.py -q --timeout=180
    FAILED tests/test_issue854_live_model_prefix.py::TestLiveModelPrefix::test_apply_prefix_to_any_non_at_id
    AssertionError: @provider: prefix application not found

- Przechodzi na `cdff0b8d`.
- Pada na `f585b123`, `37032708`, `ba745f59` i `f4b039b9`.
- Przyczyna: `_addLiveModelsToSelect` używa teraz `_encodeModelRoute`, a test sprawdza tekst źródła. Trzeba go dostosować, tak jak `test_issue7290` i `test_model_picker_badges`.

3. Dwie z trzech poprawek tej rundy nie są przypięte testami.

    cd /opt/data/cache/scratch/g7 && /opt/data/cache/scratch/wt-design-7955/.venv/bin/python mutate.py M2_find_exact_ignores_provider M3_state_group_wins

    M2_find_exact_ignores_provider: rc=0 91 passed
    M3_state_group_wins: rc=0 91 passed

Na tych mutantach wracają counterexample'e z Gate 6:

    node routes.js mut/M3_state_group_wins '{"action":"inject-existing","cases":[["custom","@custom:backup:model-a",["@custom:backup:model-a"]]]}'
    → "state":{"model":"model-a","model_provider":"custom"}

    M2: _findModelInDropdown("@safe:model-a", sel[@!:model-a], "safe") → "@!:model-a"

- Testy wywołują `_ensureModelOptionInDropdown`, który maskuje błąd w `_findModelInDropdown`.
- Przeżywają też mutanty predykatu katalogu:
  - M5: bez guardu `custom:` katalog emituje `@!:`, które resolver odrzuca.
  - M6: brak `base_url`.
  - M7: przyjmowanie `model.provider: custom`.
- Przeżywają też wszystkie cztery wywołania `_encode_catalog_route` (M8–M11). Testy katalogu wołają funkcję bezpośrednio, nigdy przez `_apply_provider_prefix`, dedup ani backstop.

PREVIOUS FINDINGS STATUS:

- `inject-existing`: addressed. Wynik: `{"model":"model-a","model_provider":"custom:backup"}`, `@safe` nie jest podmieniany przez `@!:`.
- `inject`: addressed. Wartości trafiają dosłownie (`@safe:model-a`, `@custom%3Aeast%3Awest:model-a`, `@!:model-a`), bez zawijania.
- Lookup non-custom: addressed. `find("@safe:model-a")` daje `null`.
- Credential chain: still blocking (blocker 1).

NON-BLOCKING NOTES:

- Kierunki reguły katalogu:
  - Katalog nigdy nie emituje `@!:` tam, gdzie resolver je odrzuca: przy aktywnym `custom:<slug>`, bez `base_url` i przy wpisie `custom_providers` o nazwie `custom` (to `custom:custom`, zostaje generyczny).
  - Pomija `@!:` dla `model.provider: custom` z `base_url`, choć resolver by je przyjął. Commit message opisuje to jako zamierzone.
  - Przy takiej konfiguracji dedup nadal może dać `@custom:vendor/x:tag` w grupie Custom. HEAD czyta to teraz jako `custom:vendor/x` + `tag` (fail-closed). Base czytał to jako Custom, ale routował do innego providera. Oba wyniki są złe, to przypadek brzegowy.
- Konfiguracje bez zarezerwowanego pola (np. `openai` + Custom): opcja `@custom:qwen3:8b` daje teraz stan `custom:qwen3`/`8b`, wcześniej `custom`/`qwen3:8b`. Runtime jest identyczny w obu przypadkach (`8b`, `custom:qwen3`, `None`). Klasa #7955 zostaje poza local-server.
- Hint nadal interpretuje wartości kwalifikowane w starej, nieescapowanej pisowni non-custom: `@a:b:c` z hintem `a:b` daje (`a:b`, `c`), z innym hintem (`a`, `b:c`). Routing tego nie zmienia, bo model zachowuje pełną wartość. Sformułowanie „never interprets” jest jednak za mocne.
- Duplikaty opcji: gdy hint różni się od providera wartości, a dokładna opcja już istnieje, ensure wstrzykuje drugą identyczną (np. `@safe:model-a` dwa razy). Dedup jej nie usuwa. To kwestia kosmetyczna.
- Alias stringiem `custom/qwen3:8b`, gdy modelu nie ma w katalogu: fallback daje `@custom:qwen3:8b`, czyli rekord `qwen3`. Test to wymusza.
- Seeding z `_encode_catalog_route` nic nie robi dla Custom, bo w `_PROVIDER_MODELS` nie ma klucza `custom`.
- Pisownia `@!:` przechodzi przez dedup, badge, aliasy, cron (nazwa gołego modelu) i restore. W macierzy 5 wartości × 7 hintów nie ma podwójnego zawijania.
- Sąsiednie suity (236 plików): poza testem 854 wszystkie porażki HEAD padają też na base. Są to `3691`, `managed_profile_startup` (środowiskowy), `provider_mismatch` i flaky `profile_switch`. `3691` i `provider_mismatch` przechodzą w izolacji na HEAD.
- Dokumentacja jest sprzeczna z wykonaniem:
  - Linie 140–141 mówią „prefixing, dedup, seeding … share the generic producer”, a te ścieżki używają teraz `_encode_catalog_route`.
  - Linie 70–71 mówią, że rekordy generyczne używają tylko generycznego encodera, a modele z `providers.custom` dostają `@!:`.
  - Linie 57–61, wiersz macierzy „named credential not borrowed” i commit message twierdzą, że nic nie odbiera endpointu ani poświadczeń. Klucz z `providers.custom` jest jednak pożyczany (blocker 1).
