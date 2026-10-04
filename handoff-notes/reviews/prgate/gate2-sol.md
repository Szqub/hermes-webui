BRANCH A: BLOCK

Bloker: argument o rozłączności z dowolnym identyfikatorem z providers: jest fałszywy. Sprawdzenie członkostwa w api/config.py:3166 odbywa się po parserze, który może już skrócić identyfikator providera.

Wykonany kontrprzykład:
  providers:
    "custom:a:b":
      base_url: http://evil:1/v1
      models: [m]

  Wybór: model=m, session_provider=custom:a:b
  Encoder: @custom:a:b:m
  Wynik gałęzi: ('a:b:m', 'custom', 'http://127.0.0.1:11434/v1')

Parser w api/config.py:2706–2710 zmienia hint na custom:a. Kontrola nie znajduje go w providers:, więc nowa ścieżka przejmuje rzeczywisty, skonfigurowany named-provider pick. Baseline także źle parsuje ten token, ale fail-closed wynik ('b:m', 'custom:a', None) zostaje teraz zastąpiony cichym przekierowaniem. To nie jest dowód rozłączności wymagany przez maintainera.

Jest też kolizja odwrotna:
  custom_providers zawiera nazwę qwen3.8 z endpointem http://q:7/v1
  Wybór qwen3.8:27b z session_provider=custom
  Wynik: ('27b', 'custom:qwen3.8', 'http://q:7/v1')

Konfiguracja named providera przejmuje więc model z Custom lane. Sam token nie odróżnia tych dwóch intencji; sprawdzanie członkostwa wybiera jedną z nich, zamiast zapewniać rozłączność.

Co rzeczywiście sprawdziłem:
  • Dokładny HEAD 47f3a05a; worktree czysty.
  • Wskazany probe_matrix_7955.py na gałęzi i cdff0b8d: podstawowe layouty, oba typy konkurenta, other:9999, legacy local, named local, jawne hinty i custom-configured zachowują oczekiwane wyniki.
  • Nowe testy na gałęzi oraz wymagane sąsiednie zestawy: 445 passed.
  • Osiem dodatkowych plików custom-provider, osobno: 91 passed.
  • Łącznie w tych dwóch zestawach: 536 passed.
  • Nowe testy przeciw istniejącej kopii baseline: 12 failed, 11 passed. Porównanie cmp potwierdziło zgodność api/config.py i conftest.py z cdff0b8d oraz identyczność nowego pliku testowego. Pierwsza próba uruchomienia pliku z gałęzi „z katalogu baseline” importowała gałąź — jej 23 passed nie traktuję jako dowodu baseline.
  • #4728 przechodzi w sąsiednim zestawie; aktywny custom:lab z nieznanym slugiem nadal zwraca None.
  • Nie wykonałem pełnego iloczynu wszystkich wierszy × ollama/vllm/local × obu layoutów konkurenta. Nowe testy również go nie pokrywają.

Dokumentacja zawyża gwarancje:
  • custom-lane-endpoint-authority.md:66–68 obiecuje niezmienność każdego tokena katalogu — kontrprzykład ją obala.
  • Linie 123–126 deklarują pokrycie całej macierzy, którego plik testowy nie ma.
  • Znaleziony draft /opt/data/cache/scratch/pr-webui-body.md zawiera wymagane pola Contract Routing oraz Contract Change, ale nie wymienia nowego kontraktu w Relevant public docs i powtarza fałszywą gwarancję rozłączności.

Reinterpretacja faktycznie nieistniejącego sluga może być świadomym kompromisem. Tutaj jednak kontrola myli „nieistniejący” z „skrócony przez parser”, więc potrafi przejąć realny route. Nie proponować tej gałęzi w obecnej postaci.


BRANCH B: BLOCK

Bloker: niepokryta gałąź read-after-close została uznana za publicznie nieosiągalną na podstawie błędnego uzasadnienia; testy przerwania nie zapewniają też event-based synchronizacji momentu wysłania sygnału.

tests/agent/test_relay_blocked_generator_interrupt.py:18–23:
  Awaitowanie kolejnych odczytów wyklucza równoległe odczyty, ale nie wyklucza przerwania między submission do executora a wejściem workera pod close_guard. Worker może wystartować i zostać wstrzymany przed lockiem; consumer przejmuje close, a worker później trafia do (None, True). Nasycenie executora nie jest konieczne.

Nie wykonałem reprodukcji tego interleavingu ani stress harnessu: runtime zablokował wykonanie in-memory harnessów, a nie obchodziłem ograniczenia ani nie tworzyłem plików. Nie uznaję więc pełnego pokrycia handshake za zweryfikowane.

Sam handshake w agent/relay_llm.py:364–417 wygląda poprawnie dla serialnego managed-read path:
  • Read wygrywa lock → close zapisuje żądanie → worker zamyka po zakończeniu next().
  • Close wygrywa lock → ustawia closed przed właściwym close() → późniejszy read nie dotyka iteratora.
  • Close wygrywa między zdjęciem reading a deferred claim → worker widzi closed, bez drugiego close().
  • Żądanie pozostaje zapisane do powrotu workera. Jeśli provider nigdy nie wróci, cleanup nie nastąpi — dokumentacja uczciwie to zaznacza.

Testy mają wszystkie granice czasowe ≥2 s, lecz SIGALRM jest uzbrajany przed potwierdzeniem entered. Handler tylko sprawdza entered.is_set(); nie synchronizuje startu sygnału z wejściem providera. Na obciążonym runnerze możliwy jest fałszywy failure. Powtórzenia zielone nie dowodzą deterministyczności.

Wykonana weryfikacja:
  • Dokładny HEAD 0c6045d7; worktree czysty; diff --check czysty.
  • Nowe testy: moje cztery uruchomienia po 2 passed. Dodatkowy niezależny audyt wykonał również cztery zielone uruchomienia.
  • Niezależny audyt wszystkich 12 plików tests/agent/*relay*.py, osobnymi procesami: 135 passed, 7 failed.
  • Osobiście powtórzony zestaw relay_llm + atof_cwd + runtime_plugins + tools: 84 passed, 7 failed.
  • Istniejąca kopia pre-fix: 133 passed, 8 failed; dodatkowy failure to reprodukcja generator already executing. cmp potwierdził zgodność relay_llm.py, relay_runtime.py i trzech problematycznych sąsiednich plików testowych z parentem.
  • Siedem sąsiednich failures jest zatem odtworzonych przed zmianą, nie wprowadzonych przez handshake.

Dokładny sąsiedni failure set:
  test_relay_atof_cwd.py:
    test_run_conversation_exports_session_and_turn_cwds
  test_relay_runtime_plugins.py:
    test_real_binding_leaves_foreign_plugin_host_unchanged
    test_real_binding_hands_dynamic_records_to_relay_and_fails_open_on_rejection
    test_real_binding_discovers_user_and_ignores_project_config
    test_real_binding_explicit_config_replaces_user_and_ignores_project
    test_real_binding_keeps_two_profile_trajectories_separate_in_shared_exporters
  test_relay_tools.py:
    test_request_rewrite_reaches_authorized_callback_once

Pierwsze sześć wynika z niezgodności nemo_relay/ additional_plugins_toml; ostatni z przekazania trzech argumentów do dwuargumentowego wrap_execution.

Porównałem rzeczywiste diffy trzech konkurencyjnych PR-ów:
  • #132059: bounded drain, po timeout porzuca close.
  • #132064: deferred owner-thread close, ale nadal próbuje close z consumer thread i tłumi busy ValueError.
  • #132080: bounded retry na obu close seams, także unmanaged.

Ta gałąź ma konkretną przewagę projektową: wspólny atomowy claim zapobiega wyścigowi zamiast czekać lub tłumić jego wyjątek; deferred failure jest logowany. Jest wystarczająco odmienna technicznie, ale dotyczy tego samego managed seam co #132064 i nie obejmuje unmanaged seam z #132080. Warto zaproponować ten handshake w istniejącym review, zamiast otwierać teraz czwarty PR z niepełnym dowodem pokrycia.

Nie edytowałem, nie stage’owałem, nie commitowałem ani nie pushowałem; nie otworzyłem PR-ów.
