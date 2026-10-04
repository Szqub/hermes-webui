Weryfikacja zakończona. Oba drzewa robocze czyste (git status: 0 zmian), worktree'y tymczasowe usunięte.

REPO A — hermes-webui @ d9febe20: APPROVE WITH CHANGES (jedna drobna uwaga dokumentacyjna)

Co uruchomiłem i co wyszło:
- `. .venv/bin/activate && HERMES_WEBUI_AGENT_DIR=/opt/data/cache/scratch/hermes-agent python -m pytest tests/test_issue7955_bare_custom_local_provider_model_id.py -q -p no:cacheprovider` → 18 passed.
- Repro regresji na HEAD (skrypt przez `PYTHONPATH=$PWD python`, konfig `model.provider: anthropic` + `providers.custom.base_url=https://proxy.example/v1`, sesja `custom`, model `foo`): `'@custom:foo' → ('foo', 'custom', 'https://proxy.example/v1')`. Regresja usunięta — hint zostaje.
- Przypadek #7955 na HEAD (`model.provider: ollama` + base_url + `custom` + `qwen3.8:27b`): `'qwen3.8:27b' → ('qwen3.8:27b', 'ollama', 'http://127.0.0.1:11434/v1')`. Zostaje goły.
- Ten sam skrypt na worktree rodzica (3c8a533a): repro regresji daje identycznie `('foo','custom','https://proxy.example/v1')` (rodzic nie miał złej zmiany), a #7955 daje `'@custom:qwen3.8:27b' → ('27b', 'custom:qwen3.8', None)` — czyli pierwotny błąd, więc testy faktycznie pinują różnicę.
- Brak innych zmian routingu: 17 sąsiednich plików suitów kodowania (test_model_resolver, test_issue1806, 1384, 1527, 1625, 1881, 1894, 6722, 7333, 895_894, resolve_model_provider_free_suffix, 1855_fast_path, openai_api_provider_alias, provider_mismatch, plugin_model_providers, minimax, nous_portal_routing) uruchomionych plik-po-pliku na HEAD i na worktree rodzica — identyczne wyniki, wszystkie zielone (łącznie 504 testy). Diff w api/config.py jest czysto addytywny (jedna nowa gałąź dla `custom`/`local` bez zadeklarowanego `base_url`). Uwaga: przy jednolitym uruchomieniu wszystkich plików naraz w tej konfiguracji występuje konflikt fixture `test_server` — ale identyczny na obu drzewach, więc środowiskowy, nie związany ze zmianą.
- Dokument docs/architecture/provider-context-model-encoding.md: wszystkie cztery poprawione punkty są teraz zgodne z kodem — linie 56-62 poprawnie mówią o `providers.custom.base_url` jako osobnej trasie, reguła 5 (linie 96-106) opisuje dokładnie zaimplementowany guard, invariant round-trip jest złagodzony (linie 120-124), "negative control" (linie 130-132) już nie kłóci się z regułą 9, kolejność reguł 1-9 zgadza się z kolejnością w kodzie.

Finding (do poprawy przed upstreamem):
- tests/test_issue7955_bare_custom_local_provider_model_id.py:26-28 — docstring modułu nadal zawiera stare, fałszywe stwierdzenie z poprzedniej rundy: "A bare `custom` ... names an endpoint only through `model.base_url`, so `@custom:<model>` is never an actionable route: the model must stay bare whatever the configured provider is." To wprost przeczy guardom w tym samym commicie i testom `test_declared_custom_endpoint_keeps_its_hint` / `test_declared_local_endpoint_keeps_its_hint` w tym samym pliku. Dokument główny poprawiono, ten docstring został. Nie wpływa na wykonanie, ale wprowadza w błąd czytającego test.

REPO B — hermes-agent @ 7b47e3e8: APPROVE

Co uruchomiłem i co wyszło:
- `HERMES_HOME=/opt/data/cache/scratch/ha-home /opt/data/cache/scratch/ha-venv/bin/python -m pytest tests/agent/test_relay_blocked_generator_interrupt.py tests/agent/test_relay_llm.py -q -p no:cacheprovider` → 50 passed.
- tests/agent/test_relay_tools.py na HEAD i na worktree rodzica (bd0affe5): identycznie `1 failed, 3 passed` na obu — potwierdzone, że to pre-existing skew wersji `nemo_relay`, nie efekt zmiany.

Wszystkie sześć "acted-on findings" zweryfikowane w diffie:
- `pytestmark = pytest.mark.platforms("posix")` z komentarzem o SIGALRM — tests/agent/test_relay_blocked_generator_interrupt.py:17.
- Docstring opisujący zachowanie — ten sam plik, linie 1-10.
- `assert stream is not None, 'stream() did not return before the interrupt'` — linia 59.
- Frontmatter (title/description) na stronie doc — website/docs/developer-guide/relay-managed-stream-ownership.md:1-3; strona dodana do sidebars.ts.
- Końcowy newline w agent/relay_llm.py obecny (od: `) \n` na końcu pliku).
- Commit message mówi tylko "A failed deferred close is logged rather than raised" — bez twierdzenia, że każda deferral jest logowana.

Sama zmiana w agent/relay_llm.py:350-451 przejrzałem liniowo: claim na zamknięcie i claim na odczyt są pod tym samym `close_guard`, worker re-sprawdza `closed` pod lockiem przed wejściem do iteratora, odroczone zamknięcie wykonuje worker w `finally` po ustawieniu `reading=False` (jedyny wątek, który legalnie może zamknąć generator), błąd odroczonego close jest logowany zamiast rzucany, podwójne zamknięcie niemożliwe (`closed` sprawdzany pod lockiem). Ścieżka, w której fabryka rzuci przed utworzeniem iteratora, jest bezpieczna (`getattr(raw_stream, "close", None)` na None). Nie znalazłem niczego do zgłoszenia.

Podsumowanie: repo B gotowe do upstreamu; repo A gotowe po przeredagowaniu docstringa modułu testowego (linie 26-28) tak, żeby nie przeczył własnym guardom.
