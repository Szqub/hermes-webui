  🔀 [set 1] delegating 2 tasks
  ✓ [set 1 · 1/2] READ ONLY review catalog rule at commit   (163.07s)
  ✓ [set 1 · 2/2] READ ONLY review picker end-to-end reser  (217.66s)
VERDICT: BLOCK

Sprawdzony commit: f4b039b927dc4d4369c7006d3e1090727944f491.
Gałąź zgodna, worktree czysty. Bez zmian w plikach projektu, commitów ani publikacji.

BLOCKERS:

1. Qualified restore nadal może podstawić opcję innego providera.

Polecenie:

    node /opt/data/cache/scratch/g7-pickers/routes.js /opt/data/cache/scratch/wt-design-7955 '{"action":"metadata","cases":[["@custom:qwen3:8b","custom","@!:8b","custom"],["@other:8b","custom","@!:8b","custom"]]}'

Obserwowany output:

    [{"matched":"@custom:qwen3:8b","state":{"model":"8b","model_provider":"custom:qwen3"}},{"matched":"@other:8b","state":{"model":"@other:8b","model_provider":"other"}}]

Żądane @!:8b zostaje zastąpione trasą named-custom albo @other:8b. Filtr w static/ui.js:3694–3696 sprawdza provider metadanych opcji, nie provider jej qualified wartości. Nowa ochrona normalized fallback nie obejmuje wcześniejszego provider-aware return.

Dedup również scala te odrębne trasy:

    node /opt/data/cache/scratch/g7-pickers/routes.js /opt/data/cache/scratch/wt-design-7955 '{"action":"dedup"}'

    {"removed":1,"values":["@!:8b"]}

2. Injection nadal zmienia znaczenie non-custom namespace.

Polecenia:

    node /opt/data/cache/scratch/g7-pickers/routes.js /opt/data/cache/scratch/wt-design-7955 '{"action":"inject","cases":[["custom","@safe:model-a"]]}'
    node /opt/data/cache/scratch/g7-pickers/routes.js /opt/data/cache/scratch/wt-design-7955 '{"action":"consumers","cases":[["@safe:model-a","safe","model-a"]]}'

Istotne wyniki:

    injection: {"value":"@safe:model-a","state":{"model":"model-a","model_provider":"safe"}}
    catalog:   {"state":{"model":"@safe:model-a","model_provider":"safe"}}

Wrapper wartości jest zachowany, ale injected data-model powoduje usunięcie namespace w _modelStateForSelect. Ta sama qualified wartość daje inny zapis zależnie od sposobu utworzenia opcji. Powód: routedModel ma pierwszeństwo także dla non-custom route, static/ui.js:3379.

3. Catalog dedup przekierowuje providers.custom do configured endpoint.

Polecenie, wykonane z worktree i izolowanym stanem:

    HERMES_HOME=/opt/data/cache/scratch/design-7955-home HERMES_WEBUI_STATE_DIR=/opt/data/cache/scratch/design-7955-state TMPDIR=/opt/data/cache/scratch ./scripts/test.sh /opt/data/cache/scratch/g7-catalog/test_catalog_review.py -q -s --timeout=60 -p no:cacheprovider

Konfiguracja próby: model.provider=ollama, model.base_url=http://127.0.0.1:11434/v1; providers.custom.base_url=http://record.invalid:9999/v1; custom i aaa oferują vendor/qwen3:8b.

Wynik rzeczywistego static catalog:

    ('custom', '@!:vendor/qwen3:8b',
     ('vendor/qwen3:8b', 'custom', 'http://127.0.0.1:11434/v1'))

Opcja rekordu custom trafia do model.base_url zamiast endpointu rekordu. _encode_catalog_route rozróżnia jedynie provider_id, bez pochodzenia grupy.

Bez model.base_url ta sama próba daje:

    ('custom', '@custom:vendor/qwen3:8b',
     ('8b', 'custom:vendor/qwen3', None))

Czyli traci również identyfikator modelu. Cały zestaw katalogowych kontrprób: 6 failed, 16 passed.

4. Profile persistence pozwala hintowi przejąć qualified route.

Polecenie:

    HERMES_HOME=/opt/data/cache/scratch/design-7955-home HERMES_WEBUI_STATE_DIR=/opt/data/cache/scratch/design-7955-state TMPDIR=/opt/data/cache/scratch ./scripts/test.sh /opt/data/cache/scratch/g7-pickers/probe.py -q -s --timeout=60 -p no:cacheprovider

Obserwowany output:

    profile conflicting hint: ('qwen3:8b', 'custom:backup')
    profile persisted config: "model:\n  default: qwen3:8b\n  provider: custom:backup\n"

Wejście: default_model=@!:qwen3:8b, model_provider=custom:backup. Zapis usuwa reserved route i wybiera named provider. api/profiles.py:2543 używa provider or parsed_provider — odwrotnie niż deklarowana reguła.

5. Testy nie wykrywają usunięcia całego JS hardeningu tej rundy.

Polecenie:

    HERMES_HOME=/opt/data/cache/scratch/design-7955-home HERMES_WEBUI_STATE_DIR=/opt/data/cache/scratch/design-7955-state TMPDIR=/opt/data/cache/scratch ./scripts/test.sh /opt/data/cache/scratch/g7-mutation/test_round3_coverage.py -q -s --timeout=60 -p no:cacheprovider

Próba uruchamia wszystkie obecne funkcje testowe test_issue7955_route_js.py z static/ui.js pobranym przez git show ba745f59:static/ui.js, wyłącznie w scratch.

Wynik:

    DETECTED: 0 OF 11

Wszystkie 11 testów przechodzi ze starym JS. Nie ma więc wymaganej regresji wykrywającej cofnięcie generalizacji injection, lookup i state tej rundy.

PREVIOUS FINDINGS STATUS: addressed / still blocking

    addressed:
    Trzy wcześniejsze kontrprzykłady odtworzone z identycznymi payloadami.
    Named-custom zachowuje własny provider; conflicting hint nie tworzy
    dodatkowego wrappera; @safe:model-a nie jest już zastępowane @!:model-a
    w poprzednim non-custom lookup.

    still blocking:
    Uogólniony invariant nadal łamią lookup przy sprzecznych metadanych,
    injected non-custom state, catalog record collision i profile persistence.

NON-BLOCKING NOTES:

    Weryfikacja podstawowa: 91 passed.
    Sąsiednie suite pickerów, badges, aliases, cron, profiles, session restore,
    seeding i provider identity: 361 passed.
    node --check static/ui.js i git diff --check cdff0b8d: exit 0.

    PYTHONPATH z instrukcji został zablokowany przez politykę wykonania.
    Użyto istniejącego środowiska scripts/test.sh; TMPDIR wskazywał scratch.

    Macierz katalogu:
    - model.provider=custom z base_url: predicate=False, ale resolver przyjmuje
      @!:qwen3:8b. Encoder i resolver nie mają równoważnych warunków.
    - Bez base_url i przy aktywnym custom:lab reserved resolver odmawia.
    - custom_providers z name=custom prawidłowo daje custom:custom.
    - Przy custom:ollama session encoder emituje @!:, które resolver odrzuca.
      Sam catalog predicate w tym przypadku nie emituje reserved route.

    Dodatkowe luki: alias-object może podwójnie opakować qualified model;
    fallback badge przypisuje configured Custom do named opcji;
    Python i JS inaczej parsują port zapisany cyframi Unicode.
    Nie traktuję tych prób jako dowodu zwykłego, pełnego przepływu UI.

    Dokumentacja przeczy wykonaniu:
    configured-custom-routing.md:70–71 — generic record custom może dostać @!:;
    :113–118 — restore nadal podstawia obcego providera;
    :140–142 — catalog używa już odrębnego producenta, nie wspólnego generic.
    Docstring _configured_custom_lane_is_reserved także błędnie deklaruje
    zgodność warunków z resolverem.

    Pełny runtime credential bundle i wizualny przepływ przeglądarki nie były
    w tej rundzie zweryfikowane. Zielone suite nie zamykają powyższych luk.
