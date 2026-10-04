VERDICT: BLOCK

Sprawdzony HEAD: ba745f59909b2090e371d90bbfd88560af52f7e5.
Właściwa gałąź, czysty worktree. Bez edycji, commitów ani pushów.

BLOCKERS:

1. Restore nadal reinterpretowuje zapisaną trasę named-custom, jeśli identyczna wartość istnieje w grupie Custom.

Polecenie wykonane w podanym worktree:

    node /opt/data/cache/scratch/pytest-of-hermes/pytest-126/test_legacy_value_is_not_subst0/routes.js /opt/data/cache/scratch/wt-design-7955 '{"action":"inject-existing","cases":[["custom","@custom:backup:model-a",["@custom:backup:model-a"]],["custom","@safe:model-a",["@!:model-a"]],["safe","@safe:model-a",["@!:model-a"]]]}'

Obserwowany pierwszy wynik:

    {"applied":"@custom:backup:model-a","selected":"@custom:backup:model-a","options":["@custom:backup:model-a"],"state":{"model":"backup:model-a","model_provider":"custom"}}

Zapisane @custom:backup:model-a powinno zachować provider custom:backup i identyfikator model-a. Zamiast tego otrzymuje configured Custom z identyfikatorem backup:model-a.

Przyczyna: exact-match w static/ui.js:3650–3654 wraca przed nową regułą pierwszeństwa. Następnie _modelStateForSelect stosuje nowe laneId, a _ensureModelOptionInDropdown akceptuje wynik. Przy lokalnym configured providerze encoder może już zapisać @!:backup:model-a.

2. Brakująca qualified wartość nadal może zostać opakowana w @!: przy sprzecznym caller hint.

Polecenie:

    node /opt/data/cache/scratch/pytest-of-hermes/pytest-126/test_legacy_value_is_not_subst0/routes.js /opt/data/cache/scratch/wt-design-7955 '{"action":"inject","cases":[["custom","@safe:model-a"],["custom","@custom%3Aeast%3Awest:model-a"],["custom:backup","@!:model-a"]]}'

Obserwowany output:

    [{"value":"@!:@safe:model-a","state":{"model":"@safe:model-a","model_provider":"custom"},"label":"@safe:model-a"},{"value":"@!:@custom%3Aeast%3Awest:model-a","state":{"model":"@custom%3Aeast%3Awest:model-a","model_provider":"custom"},"label":"@custom%3Aeast%3Awest:model-a"},{"value":"@custom:backup:@!:model-a","state":{"model":"@!:model-a","model_provider":"custom:backup"},"label":"@!:model-a"}]

_ensureModelOptionInDropdown nadal wybiera hint przed providerem wartości (3826). Wyjątek zachowania verbatim obejmuje tylko legacy @custom: (3840). Escaped named route, @safe: i reserved route nie są chronione.

3. Lookup non-custom nadal podstawia opcję innego providera.

Drugi wynik pierwszego polecenia:

    {"applied":"@!:model-a","selected":"@!:model-a","options":["@!:model-a"],"state":{"model":"model-a","model_provider":"custom"}}

Wejście @safe:model-a zostało zastąpione configured-lane @!:model-a. Po nieudanym provider-aware lookup funkcja przechodzi do nieograniczonego normalized match (3712–3726). Ta luka istniała wcześniej, ale blokuje żądany invariant wszystkich qualified restore paths.

PREVIOUS FINDINGS STATUS: addressed / still blocking

    addressed:
    - Konkretny przypadek @custom:qwen3:8b kontra @!:8b.
    - Zachowanie pełnego colon-bearing identyfikatora przez _modelStateForSelect dla opcji Custom.
    - Sprawdzone przypadki custom:backup oraz @safe: nie są psute przez samą nową regułę state.
    - Zawężony commit message i dokumentacja.

    still blocking:
    - Ochrona restore/injection jest niepełna: reprodukcje powyżej.
    - Zwykły wybór Custom zachowuje pełne qwen3:8b; testy encodera/resolvera potwierdzają @!:qwen3:8b i configured endpoint. Pełnego łańcucha z configured credentials nie uznaję za zweryfikowany: nowe testy sprawdzają brak pożyczania named credentials, nie końcowy runtime credential bundle.

NON-BLOCKING NOTES:

    - Nowe testy: 85 passed in 6.98s.
    - Sąsiednie testy pickerów, aliases, cron, profile/session i provider identity: 161 passed in 13.51s.
    - node --check static/ui.js oraz git diff --check cdff0b8d: exit 0.
    - Uruchomienie bez PYTHONPATH, którego ustawienie zablokowała polityka wykonania; użyto istniejącego środowiska runnera i izolowanych katalogów stanu.
    - Udokumentowane ograniczenia migracji historycznych !/% oraz model.provider: custom pozostają nieblokujące w zadeklarowanym zakresie.
    - Brakuje regresji dla exact-value collision, sprzecznego hint przy escaped/reserved routes oraz non-custom fallback. Zielony zestaw ich nie wykrył.
    - Nie wykonałem mutation testing; nie potwierdzam, że usunięcie każdej zmienionej gałęzi zostałoby wykryte przez testy.
