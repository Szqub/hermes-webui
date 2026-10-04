BRANCH A: BLOCK

Blokujący problem: rozłączność nadal nie obejmuje wszystkich identyfikatorów emitowanych przez katalog.

W api/config.py:3163–3175 porównujesz token z surowymi kluczami providers:, case-sensitive. Tymczasem katalog kanonizuje identyfikatory (api/config.py:7255–7276), a model_with_provider_context() zamienia je na lowercase (:4927).

Odtworzyłem na obu commitach:

    providers:
      Custom:Lab:
        base_url: http://keyed:3/v1

    session provider: custom:lab
    model: llama3
    encoded: @custom:lab:llama3

    cdff0b8d: ('llama3', 'custom:lab', None)
    9ee48765: ('lab:llama3', 'custom', 'http://127.0.0.1:11434/v1')

Baseline już nie odnajduje endpointu tej konfiguracji, ale pozostaje fail-closed. Nowa gałąź przejmuje istniejącą nazwę providera i wysyła zmieniony model na aktywny endpoint. To obala deklarację „every token the generic providers namespace can emit keeps its existing resolution”.

Co rzeczywiście przeszło:
  - Nowy plik: 27 passed.
  - Ten sam aktualny plik na cdff0b8d: 14 failed, 13 passed. Podane 12 failed, 11 passed dotyczy starszego zestawu.
  - Zestaw 12 plików wymieniony w lokalnym PR-body: 449 passed.
  - probe_matrix_7955.py uruchomiony w obu worktree: podstawowe duplikaty obu typów, other:9999, legacy local, named local, custom:lab, explicit hints i custom-configured zachowują wymagane wyniki.
  - Adwersarialny custom:a:b już nie jest przejmowany; kolizje custom_providers nadal rzucają AmbiguousCustomProviderError; aktywny custom:lab z nieznanym slugiem pozostaje fail-closed.

Istotne zastrzeżenia:
  - Inny zestaw sąsiedni: na branchu 6 failed, 259 passed; odpowiadający zestaw bez nowego pliku na baseline: 238 passed. Wszystkie sześć porażek pochodzi z test_resolve_model_provider_free_suffix.py: test_custom_provider_rsplit_still_works oraz warianty free, beta, thinking, preview i slashed_model_with_free_suffix.
  - Nowy plik + free_suffix daje 6 failed, 39 passed, natomiast deklarowany zestaw 449 jest zielony. Wynik zależy od stanu konfiguracji i kolejności testów; nie można go przedstawiać jako bezwarunkowo zielonego sąsiedztwa.
  - Reinterpretacja rzeczywiście niekonfigurowanego slugu jest udokumentowanym kompromisem. Sama w sobie nie jest moim blockerem. Przejęcie slugu istniejącego pod inną wielkością liter — jest.
  - Nie uruchomiłem pełnego iloczynu wszystkich wierszy × ollama/vllm/local × obu kształtów konkurenta ani osobnego downstream-probe pożyczania klucza. Sprawdziłem routing i istniejące testy; to nie jest dowód całego toru credential lookup.

Dokumentacja i PR-body:
  - /opt/data/cache/scratch/pr-webui-body.md zawiera wymagane pola Contract Routing i sekcję Contract Change.
  - Deklaracje pełnej rozłączności są nieprawdziwe dla powyższego przypadku.
  - Twierdzenie, że providers.custom „neither grants nor removes the lane”, jest zbyt szerokie: api/config.py:3177 uzależnia nieotagowaną ścieżkę od braku tego klucza. Probe z poprawnym providers.custom zwrócił endpoint tego rekordu, nie model.base_url.
  - PR-body nie ma wymaganej przez docs/CONTRACTS.md sekcji Model Used.
  - Zweryfikowałem lokalny projekt opisu, nie opublikowany PR.

BRANCH B: BLOCK

Blokujący problem: fix zmienia zamykanie wszystkich iteratorów, nie tylko generatorów, i odbiera iteratorowi transportowemu możliwość przerwania własnego zablokowanego odczytu.

Odtworzyłem lokalnym syntetycznym iteratorem, którego close() odblokowuje next(), bez połączeń z providerem:

    baseline: provider.close() wywołane; odczyt odblokowany po 0.00 s
    b40ca5cf: provider.close() niewywołane przez 3 s;
              odczyt odblokowany dopiero po dostarczeniu syntetycznych danych

To wynika z agent/relay_llm.py:375–377 i 406–411: close czeka na powrót next(), nawet gdy to właśnie close jest mechanizmem umożliwiającym ten powrót. Dla takiego iteratora bez późniejszych danych lub timeoutu cleanup może nie nastąpić. Nie twierdzę, że sprawdziłem zachowanie każdego SDK; reprodukcja pokazuje jednak konkretną regresję obsługi wspieranego rodzaju iteratora.

Handshake:
  - Przy pojedynczym sekwencyjnym czytelniku decyzje read/close są poprawnie rozdzielone jednym lockiem.
  - Close wygrywający przed wejściem workera ustawia closed; worker zwraca (None, True).
  - Read wygrywający wcześniej ustawia reading; close zapisuje close_requested, a worker przejmuje zamknięcie po powrocie.
  - „Nie zgubi close” jest prawdziwe warunkowo: odczyt musi wrócić. Nie jest gwarancją ukończenia cleanup.
  - Gałąź read-after-close jest osiągalna w oknie executor hand-off. Aktualny komentarz to poprawnie przyznaje, ale nie ma deterministycznego testu tej gałęzi. Stress nie dowodzi jej wykonania.

Drugi problem: test nadal ma zależność od opóźnienia executora.
  - Wszystkie jawne limity mają ≥2 s, a synchronizacja używa Events.
  - Jednak Timer(8.0) startuje przed wejściem providera (:107), a alarm dopiero 2 s po wejściu (:46–59).
  - Jeśli worker wejdzie po ponad 6 s, release może wyprzedzić interrupt. Komentarz, że obciążenie nie może zmienić kolejności, jest fałszywy. Samo disarm również nie ogranicza każdego oczekiwania.

Wykonane testy:
  - Nowe testy: 2 passed; niezależny reviewer uzyskał również pięć kolejnych zielonych powtórzeń.
  - Na baseline, z wymuszonym importem źródeł baseline: 2 failed — generator already executing oraz provider close failed. Wcześniejszy pozornie zielony przebieg baseline importował kod brancha; nie traktuję go jako dowodu.
  - test_relay_llm.py + test_relay_nested_execution.py + test_auxiliary_relay.py: 60 passed.
  - Sześć dalszych sąsiednich plików: 63 passed, 6 failed.
  - Pliki zawierające te porażki na baseline: 35 passed, 6 failed. Zweryfikowałem zgodność hashów źródeł baseline z rodzicem bd0affe5.
  - Pięć porażek dotyczy additional_plugins_toml; szósta — callbacku wrap_execution przyjmującego dwa argumenty zamiast trzech. Są pre-existing skew nemo_relay, nie regresją tego patcha.
  - Stress reviewera: 100 iteracji, zero wykrytych anomalii handshake, jeden dodatkowy Relay-wrapped KeyboardInterrupt i ostrzeżenia nieodebranych wyjątków tasków. Nie jest to dowód wszystkich przeplotów.

Czwarty PR:
  - Porównanie patchy #132059, #132064 i #132080 wskazuje różnicę techniczną: tutaj jest atomowe przejęcie własności read/close, zamiast bounded drain, samego odroczenia/supresji albo retry.
  - To nadal konkurencyjne rozwiązanie tego samego defektu, nie osobna poprawka. Po usunięciu blockerów można je proponować jako wyraźnie opisaną alternatywę; obecnie nie rekomenduję czwartego PR.

Oba wskazane HEAD-y zostały potwierdzone. Worktree pozostały czyste; nie edytowałem, nie stage’owałem, nie commitowałem, nie pushowałem i nie otworzyłem PR.
