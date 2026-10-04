Weryfikacja zakończona. Raport poniżej.

# Repo A — hermes-webui (d9febe20): APPROVE WITH CHANGES

Kod i testy są poprawne; dwie resztkowe nieścisłości dokumentacyjne (w tym jedna kopia zdania, które ta runda miała usunąć) do poprawienia przed upstream.

**Regresja potwierdzona usunięta.** Sonda różnicowa (skrypt /opt/data/cache/scratch/probe_7955.py, 592 przypadki: 9 konfiguracji × 13 providerów sesji × 5 id modeli + 6 repro) porównująca HEAD z parentem w worktree:

- Repro z review: `model.provider: anthropic` + `providers.custom.base_url=https://proxy.example/v1`, sesja `custom`, model `foo` → HEAD: `('foo','custom','https://proxy.example/v1')` (parent w złej rewizji dawałby bare → anthropic; obecny parent daje `@custom:foo` → ten sam wynik). Testy `test_declared_custom_endpoint_keeps_its_hint` (tests/test_issue7955_...:194) i `test_declared_local_endpoint_keeps_its_hint` (:223) pinują ten kształt i przechodzą.
- Przypadek #7955: `qwen3.8:27b` + sesja `custom` → `('qwen3.8:27b','ollama','http://127.0.0.1:11434/v1')`. Potwierdzone testem i sondą.
- **Różnica HEAD vs parent: 17/592 przypadków** — wszystkie w zamierzonej klasie (bare `custom`/`local` + skolapsowany konfig lokalny / brak providera z base_url / deklarowany lmstudio). Zero zmian poza klasą;	suite'y sąsiednie (`test_issue7333_slash_id_provider_hint.py`, `test_model_resolver.py`, `test_provider_mismatch.py`, `test_issue1894_provider_overlap.py`): 174 passed na HEAD i identycznie na parent w worktree.
- **RED potwierdzony:** nowy plik testowy skopiowany do worktree na parent (3c8a533a): `12 failed, 6 passed`; na HEAD: `18 passed` (komenda z zadania, 4.73s).

**Znaleziska:**

1. **tests/test_issue7955_bare_custom_local_provider_model_id.py:24-27** — docstring modułu wciąż zawiera zdanie z poprzedniej rundy oznaczone jako fałszywe: "A bare `custom` (and its legacy `local` alias) names an endpoint only through `model.base_url`, so `@custom:<model>` is never an actionable route: the model must stay bare whatever the configured provider is." To bezpośrednio przeczy kodowi (bramka w api/config.py:4902 warunkuje bare passthrough na `not _get_provider_base_url(provider)`), nowej dokumentacji (docs/architecture/provider-context-model-encoding.md:55-62) i własnemu testowi z tego pliku (`test_declared_custom_endpoint_keeps_its_hint` wymusza hint, gdy endpoint jest zadeklarowany). Dokumentacja testu twierdząca coś przeciwnego niż testy w tym samym pliku — dokładnie klasa finding-2. Do poprawienia przed upstream (trywialny amend).

2. **docs/architecture/provider-context-model-encoding.md:120-124** — inwariant "Round-trip integrity for colon-bearing ids" jest nadal zbyt mocny. Parenthesia obejmuje tylko stripping prefiksu, ale w kształcie zadeklarowanego endpointu round-trip nadal ucina id: sonda `declared_custom_endpoint_colon_id` (provider `custom`, `providers.custom.base_url`, model `qwen3.8:27b`) → encoded `@custom:qwen3.8:27b` → resolved `('27b','custom:qwen3.8',None)` — fail jako unconfigured custom provider. To zachowanie pre-existing (parent identyczny) i świadomie poza zakresem fixu (commit message: "Those sessions keep their explicit hint"), ale inwariant w docu twierdzi gwarancję, której kod nie spełnia w tej konfiguracji. Do zmiękczenia lub dopisania wyjątku (również amend).

Poza tymi dwoma: brak findings. Bramka, tabele aliasów (`local`→`custom`, api/config.py:1314; `_LOCAL_SERVER_PROVIDERS` :2531) i kolejność reguł zgodne z docem rules 1-9; CONTRACTS.md wpis :101 w sekcji "contributor guidance" — konwencja zachowana; authorstwo: Szymon Żołnierczyk, brak trailerów.

# Repo B — hermes-agent (7b47e3e8): APPROVE

Brak findings. Wszystkie zaakceptowane punkty zweryfikowane:

- `pytest.mark.platforms("posix")` na jedynym teście (tests/agent/test_relay_blocked_generator_interrupt.py:18, pojedynczy marker — zgodny z regułą repo o `platforms` vs `skipif`); docstring modułu opisuje zachowanie; wszystkie 4 pliki kończą się `\n`; precondition `assert stream is not None` obecny; frontmatter na stronie doc (title+description, relay-managed-stream-ownership.md:1-5) + wpis w website/sidebars.ts:857; commit message mówi tylko "a failed deferred close is logged rather than raised" — zgodne z kodem (agent/relay_llm.py:412-417 loguje wyłącznie niepowodzenia).
- **Testy (komendy z zadania):** `test_relay_blocked_generator_interrupt.py`: `1 passed in 2.47s`; `test_relay_llm.py`: `49 passed in 1.88s`.
- **Stabilność testu sygnałowego:** 5/5 kolejnych uruchomień passed (~2.5s każde) — brak flakiness.
- **RED potwierdzony:** test skopiowany do worktree na parent (bd0affe5) → fail dokładnie `AssertionError: ["ValueError('generator already executing')"]` w `assert not close_errors` — identycznie jak w claim commit message.
- **7 failure'i pre-existing:** ten sam zestaw (1× test_relay_tools, 5× test_relay_runtime_plugins, 1× test_relay_atof_cwd) na HEAD i na parent; w logu widoczny `nemo_relay` skew: `initialize() got an unexpected keyword argument 'additional_plugins_toml'` (relay_runtime.py:318/346). Nieskutkowane zmianą.
- **Przegląd handshake'u** (agent/relay_llm.py:361-450): obie decyzje (`_claim_close`, wejście w `_read_next_chunk`) pod jednym `close_guard`; zamknięcie faktyczne wykonywane poza lockiem, ale po ustawieniu `closed`, więc nowy read nie wejdzie — brak okna na overlap. Odroczone zamknięcie logowane, nie rzucane — zgodnie z docem. Twierdzenie docu o zwolnieniu `_loop`/`_runtime_lease` niezależnie od odroczenia potwierdzone w `_close()` (:626-653, `finally: self._release_runtime_lease()`). Import fixture `from tests.agent.test_relay_llm import relay_turn` — wzorzec obecny w repo.

# Przed upstream

- Repo A: dwie korekty zdania (test docstring :24-27, invariant doc :120-124). Obie czysto tekstowe, bez zmian kodu; po amend wystarczy rerun nowego pliku testowego.
- Repo B: nic — gotowy do proponowania.

Oba checkouti czyste, worktree tymczasowe usunięte; żadnych edycji/stage/commit/push. Pliki sondy: /opt/data/cache/scratch/probe_7955.py i cmp_probe.py (do ponownego użycia przy amendzie).
