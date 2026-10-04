VERDICT: BLOCK

BLOCKERS:

1. Przeglądarka może reinterpretować stary zapis jako configured Custom, mimo deklaracji „NOT auto-migrated”.

   Komenda wykonana w podanym worktree:

     HERMES_HOME=/opt/data/cache/scratch/design-7955-home HERMES_WEBUI_STATE_DIR=/opt/data/cache/scratch/design-7955-state HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent HERMES_WEBUI_PYTHON=/opt/data/cache/scratch/wt-astra-7955/.venv/bin/python HERMES_WEBUI_TEST_STATE_ROOT=/opt/data/cache/scratch PYTHONDONTWRITEBYTECODE=1 /opt/data/cache/scratch/wt-astra-7955/.venv/bin/python -B -m pytest tests/test_issue7955_route_js.py::test_generic_decoding_is_single_pass_and_does_not_decode_model tests/test_issue7955_route_js.py::test_injecting_existing_route_never_double_wraps_or_decodes_suffix tests/test_issue7955_disjoint_route.py::test_legacy_ambiguity_retains_named_route -v --timeout=120 -p no:cacheprovider --tb=short

   Obserwowany wynik: wszystkie trzy testy PASSED.

   Te testy wykonują i potwierdzają sprzeczne interpretacje:
     Python: @custom:qwen3:8b → model 8b, provider custom:qwen3, named endpoint.
     JavaScript z hintem custom: ten sam zapis → model qwen3:8b, provider custom.
     Browser injection: ten sam zapis z hintem custom → @!:qwen3:8b.

   Dowody: tests/test_issue7955_route_js.py:181–190 oraz 215–223; tests/test_issue7955_disjoint_route.py:117–121.

   To nie jest wyłącznie zmiana etykiety: nowy token wybiera inny endpoint. Injection jest także wywoływane podczas odtwarzania sesji, nie tylko przy świadomym ponownym wyborze: static/boot.js:3770–3791 i static/ui.js:11723–11745.

   Potrzebne jest zachowanie starego qualified value podczas restore albo jednoznaczne ograniczenie konwersji do świadomego wyboru. Obecne testy wręcz wymagają tej konwersji.

NON-BLOCKING NOTES:

- Wszystkie nowe testy i wszystkie wskazane sąsiednie suites przeszły razem: 580 passed in 26.79s.
- Dodatkowe suites dotyczące session repair, auxiliary models, reasoning, runtime observation, #4728 i cron: 80 passed in 10.55s.
- node --check dla static/ui.js, static/commands.js i static/panels.js: exit 0.
- Nie znalazłem osłabienia assertions w dwóch zmodyfikowanych istniejących plikach. Dodano helper do harnessów; structural assertion #7290 dostosowano do wspólnego encodera.
- W resolve_model_provider reserved check rzeczywiście poprzedza alias resolution, ownership scans i generic parser.
- Nie jest jednak pierwszą gałęzią wszędzie: _resolve_compatible_session_model_state obsługuje moa przed @!:; streaming wykonuje alias resolution przed głównym resolverem. Nie potwierdziłem wykonaniem konfliktowych kombinacji tych ścieżek.
- Raport deklaruje czysty whitespace check. Dla ocenianego commitu:

     git diff --check cdff0b8d..f585b123

   Wynik: exit 2, „tests/test_issue7955_disjoint_route.py:162: new blank line at EOF.”

- HEAD potwierdzony jako f585b1234e94b9aca3d92fb0d4a5068d003eda75; końcowy git status --short był pusty. Nie edytowałem, nie stage’owałem ani nie wykonywałem operacji publikujących. Uruchomione testy tworzą własne tymczasowe fixtures/logi — nie były dosłownie bezplikowe.

CLAIM CHECK:

1. Reserved resolution — odtworzone.
   Ponownie wykonany istniejący probe zwrócił pełne qwen3:8b, provider custom i configured base_url przy kolizjach. Wszystkie jego overlap rows miały ok: true.

2. Disjointness — brak znalezionego kontrprzykładu w wykonanych testach.
   Pokrycie obejmowało !, !:payload, a!b, percent-bearing ids, uppercase, whitespace, colons, empty, 123, None i identyfikator długości 10 000. Testy encoder parity przeszły.
   Nie ukończyłem niezależnego rozszerzenia o własne %2521/non-str cases: środowisko odmówiło uruchomienia inline Python/Node i execute_code. Nie przedstawiam istniejącego zestawu jako niezależnego fuzzingu.

3. Zachowanie neighboring routes — odtworzone dla wykonanych suites i probe controls, w tym named custom, @local:, @ollama:, custom-configured, host:port i fail-closed.

4. Brak automatycznej reinterpretacji legacy picks — niepotwierdzone; browser restore/injection przeczy tej deklaracji, jak wyżej.

5. Wspólna gramatyka Python/JavaScript — częściowo.
   Encodery oraz reserved/escaped cases przeszły. Legacy decoding z browser provider hintem może wybrać inną interpretację niż Python.

6. End-to-end request i configured credentials — niezweryfikowane.
   Probe odtworzył runtime_base zgodny z configured endpoint oraz borrowed_named_key: false, ale używa synthetic config, wyłącza credential pools i nie wysyła completion. Nie dowodzi configured credential selection ani faktycznego HTTP requestu z pełnym modelem przy colliding named record.

Runner z podanym PYTHONPATH został zablokowany przez środowisko. Alternatywny interpreter wymagał jawnego HERMES_WEBUI_PYTHON dla test-server subprocess; po tym testy przeszły. Początkowych błędów brakujących zależności nie traktuję jako regresji zmiany.
