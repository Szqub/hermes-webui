BRANCH A: BLOCK

Gałąź zmieniła się w trakcie review. O 19:45 UTC ktoś zrobił amend i push: fork wskazuje teraz 9ee48765, a nie 47f3a05a z briefu. Większość sprawdzeń powtórzyłem na 9ee48765. Amend naprawia jedną kolizję, którą znalazłem na 47f3a05a: klucz `providers: custom:a:b` z modelem `m` trafiał do :11434 jako `a:b:m`. Najpoważniejszy problem nie zmienia się w żadnym z tych commitów.

Blocker: lane nie jest rozdzielny od nazwanych slugów. Rozstrzyga pisownia, czyli dokładnie to, co maintainer odrzucił w rundzie 3.

`@custom:<model>` z lane'u Custom i `@custom:<slug>:<model>` z nazwanego providera to ten sam ciąg znaków. Jeśli prefiks tagu modelu Ollama równa się nazwie wpisu w `custom_providers[]`, wybór z lane'u Custom trafia do obcego endpointu i używa jego klucza. Ten sam wynik daje 47f3a05a i 9ee48765:

    model.provider: ollama, base_url :11434
    custom_providers: [{name: qwen3, base_url: http://gpu-box:8000/v1, api_key: sk-gpu}]
    wybór z lane'u custom: qwen3:8b
      -> ('8b', 'custom:qwen3', 'http://gpu-box:8000/v1')   (zły endpoint, cudzy klucz, ucięte id)
    analogicznie llama3:70b przy providerze "llama3" -> ('70b', 'custom:llama3', gpu-box)

To jest regresja z rundy 1 („inny provider przejmuje model wybrany z lane'u Ollama”), tylko w innym kształcie. Nowy test `test_named_custom_provider_slug_owning_the_token_is_not_stolen` utrwala to zachowanie jako zamierzone. Tymczasem dokument mówi, że payload jest „taken whole”, a sekcja „Known ambiguity” opisuje tylko stronę nieskonfigurowanego sluga. Bez zmiany kodowania na wire parser nie odróżni tych dwóch znaczeń.

Pozostałe ustalenia:
- Macierz z briefu przechodzi w całości na 47f3a05a i na 9ee48765, dla ollama, vllm, local, lmstudio i llamacpp, w obu kształtach konkurenta. `other:9999` nigdy nie jest używany, klucz `local` nie jest pożyczany. Kontrolki bez zmian (`custom:lab`, `@local:`, `@ollama:`, `@custom-configured:`, wpis malformed) też są OK.
- Przy `model.provider: custom` (dosłowny plain custom) koder wysyła goły `mistral-7b`, który trafia do `custom:lab` na 10.0.0.8. To problem istniejący już przed zmianą i dokument to przyznaje. Mimo to „endpoint authority” nie obejmuje surowego `custom`, choć opis kontraktu je wymienia.
- Reguła fail-closed z #4728:
  - Przy aktywnym nazwanym `custom:<slug>` działa: `@custom:ghost:m` daje base None.
  - Zduplikowane slugi dalej rzucają `AmbiguousCustomProviderError`.
  - Pod lane'em Custom nieskonfigurowany slug dostaje teraz aktywny `base_url`: `@custom:ghost:llama3` daje `('ghost:llama3', 'custom', :11434)`. Docstring testu #4728 nazywa ten fallback wprost regresją. Klucz nie wycieka, bo to ten sam właściciel, ale błąd „not configured” zamienia się w ciche „model not found” na innym endpoincie.
  - Klucz `providers: Custom:Lab` (wielkie litery) przy sesji `custom:lab` daje `lab:llama3` na :11434. Wcześniej wynik był `custom:lab` z None.
- Testy:
  - 47f3a05a: nowy plik na bazie cdff0b8d dał 12 failed / 11 passed, czyli zgodnie z oczekiwaniem.
  - 9ee48765: 27 passed na gałęzi, na bazie 14 failed / 13 passed (nie 12/11).
  - 25 sąsiednich plików (m.in. 1806, 1384, 1625, 4728, pr1947, free_suffix): baza 415 passed, gałąź 442 passed (415 + 27), zero porażek.
  - Trzeba ustawić `TMPDIR=/tmp`, inaczej fixture serwera z conftest pada przez ścieżkę scratch. Nie uruchamiałem `./scripts/test.sh`, tylko .venv bezpośrednio.
- Dokumentacja i body PR:
  - Wersja robocza w `reports/astra-7955.md` jest nieaktualna. „Touched areas” pomija `docs/architecture/custom-lane-endpoint-authority.md` i `docs/CONTRACTS.md`. Contract Change twierdzi, że kontrakt żyje tylko w komentarzach `api/config.py`. Liczba testów to 23, a jest 27.
  - Do decyzji: CONTRIBUTING wymaga sekcji „Model Used” z ujawnieniem użytych narzędzi, a Twoja reguła zabrania wzmianek o AI. Wpisanie „None -- human-authored” byłoby nieprawdą, więc to musisz rozstrzygnąć Ty.

BRANCH B: BLOCK

Sam handshake jest poprawny. Blokuję z czterech powodów.

1. Ta sama klasa błędu zostaje w bliźniaczej ścieżce. Unmanaged stream (`_close_provider_resources`): wątek konsumenta jest w `next()`, inny wątek woła `close()`. Wynik na 0c6045d7: `ValueError('generator already executing')`, a `finally` providera się nie wykonał. AGENTS.md wymaga naprawy całej klasy, a #132080 tę ścieżkę obejmuje. Skrypt: `scratch/unmanaged_seam_132048.py`.

2. Close odłożony dla każdego iteratora, nie tylko generatorów. Zrobiłem iterator „HTTP-like”, w którym `close()` przerywa zablokowany odczyt.
   - Baza: przerwanie plus `close()` wywołuje `provider.close()` od razu, odczyt zwolniony po 0.00 s.
   - Gałąź: `provider.close()` nie wywołany w ciągu 3 s, odczyt wisi, dopóki „serwer” nie przyśle danych.
   - Ścieżka MoA zamyka zarządzany stream jako jedyny abort (komentarz w kodzie: „Relay alone closes the provider stream”). Ta zmiana może więc wydłużyć reakcję na interrupt do read timeout.
   - Nie sprawdzałem tego na prawdziwym `openai.Stream`/httpx, to symulacja. Dokument PR przyznaje „bounded by the provider, not by the interrupt”, ale uzasadnia to tylko dla generatorów.

3. Duplikat. #132064 to ten sam projekt: zamknięcie przekazane wątkowi, który kończy odczyt. B jest jego staranniejszą wersją z jednym lockiem i wykonaniem dokładnie raz, ale czwarty draft na tym samym issue powiela #132064 i ma węższy zakres niż #132080. Sensowniejszy będzie komentarz lub review pod #132064.

4. Fałszywe twierdzenie w teście. Gałąź `(None, True)` jest osiągalna z publicznego API bez podmiany `asyncio.to_thread` i bez saturacji executora. Wystarczy wywłaszczenie wątku workera między startem zadania a wzięciem `close_guard`. Odtworzyłem to opóźnieniem pierwszego `acquire`: close przejmuje iterator na wątku `relay-llm-stream-aclose`, worker potem wychodzi bez wejścia w generator (0 wywołań `_next_provider_chunk`). Zachowanie jest poprawne, ale ta gałąź nie ma testu, a docstring jest błędny. Skrypt: `scratch/reach_none_true_132048.py`.

Co sprawdziłem:
- Handshake jest poprawny z konstrukcji. Wejście w odczyt, przejęcie close i zakończenie odczytu (`reading=False` plus odczyt `close_requested`) dzieją się pod jednym lockiem. Nie znalazłem przeplotu, w którym odczyt i close nachodzą na siebie albo zamknięcie wykonuje się dwa razy.
  - Close może przepaść, jeśli odczyt nigdy nie wróci. To konsekwencja punktu 2.
  - Losowy SIGALRM, 300 iteracji na gałęzi: ani jednego „generator already executing”. W 3 przebiegach generator nie został sfinalizowany w 3 s, przy błędach asyncio typu „Event loop stopped before Future completed” i „aclose(): asynchronous generator is already running”. Wygląda to na KeyboardInterrupt trafiający w środek pętli asyncio, ale nie udowodniłem, że handshake jest tu bez winy.
  - Ten sam stres na bazie się zawiesił (timeout), więc nie mam liczb do porównania.
- Nowe testy:
  - Na bazie 2 failed: `ValueError` oraz `RuntimeError` w close.
  - Na gałęzi 2 passed, 3 przebiegi z rzędu, ~7 s każdy.
  - Limity ≥ 2 s są zachowane. Test 1 opiera kolejność na zegarze (alarm 2 s, release 4 s), więc wymóg synchronizacji zdarzeniami jest spełniony tylko częściowo.
  - Test 2 deterministycznie trafia w ścieżkę odroczonego close.
- Sąsiednie suity relay (12 plików `tests/agent/*relay*`):
  - Gałąź: 7 failed / 135 passed. Baza z dołożonymi nowymi testami: 9 failed / 133 passed.
  - Różnica to wyłącznie 2 nowe testy.
  - Tych samych 7 porażek występuje na obu: 5 w `test_relay_runtime_plugins`, po 1 w `test_relay_atof_cwd` i `test_relay_tools::test_request_rewrite...`.
  - To istniejąca wcześniej niezgodność wersji `nemo_relay`: `initialize() got an unexpected keyword argument 'additional_plugins_toml'`. Zmiana jej nie powoduje.

Niczego nie edytowałem, nie commitowałem ani nie pushowałem w żadnej z gałęzi. Bazy do porównań to rozpakowane kopie w `/opt/data/cache/scratch/rv-base7955` i `/opt/data/cache/scratch/ha-base132048`. Sondy i harnessy są w `/opt/data/cache/scratch/`.
