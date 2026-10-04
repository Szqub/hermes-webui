VERDICT: BLOCK

Wszystko sprawdziłem na czystym eksporcie commita ba745f59 (`git archive ba745f59`, tree a3058532), w katalogu /opt/data/cache/scratch/g6/exp. Powód: w trakcie przeglądu współdzielony worktree przestał być czysty. Ktoś inny zmienił w nim api/config.py i static/ui.js około 21:29–21:30 UTC i tych zmian nie zacommitował (dodaje m.in. `_encode_catalog_route`). Ja niczego w worktree nie edytowałem. Wyniki uzyskane na tej brudnej kopii odrzuciłem.

Bramka z briefu na ba745f59: oba pliki testów → 85 passed, `node --check` → OK, `git diff --check cdff0b8d ba745f59` → OK. Wcześniej, na jeszcze czystym worktree, z identycznym wynikiem. Bez PYTHONPATH, bo skaner go blokuje; worktree ma własny .venv.

BLOCKERS:

1. Usuwanie duplikatów wyrzuca różne modele z grupy Custom (regresja względem bazy).
   Katalog statyczny dla `model.provider: lmstudio` z base_url i nienazwanym custom_providers z kilkoma modelami emituje w grupie `custom` wartości `@custom:qwen3:8b`, `@custom:llama3.1:8b`, `@custom:qwen2.5-coder:7b`, `@custom:gemma2:9b`. To jest dokładnie ścieżka #7955. To samo dzieje się przy aktywnym anthropic lub openrouter.
   `_modelPickerOptionIdentity` używa `_parseModelRoute`, który dzieli wartość po pierwszym dwukropku jeszcze przed uwzględnieniem podpowiedzi. Dlatego `qwen3:8b` i `llama3.1:8b` dostają tę samą tożsamość `8b`. `_deduplicateModelPickerOptions` (ui.js:4026, uruchamiany przy każdym ładowaniu katalogu) usuwa wtedy jeden z nich.
     cd /opt/data/cache/scratch/g6/exp && .venv/bin/python ../e2e.py .
       ba745f59: dedupe removed: 1   (opcja '@custom:llama3.1:8b' znika z pickera)
       cdff0b8d: dedupe removed: 0
     .venv/bin/python ../mk2.py ../a2.js .
       ids => ["8b", "8b", "9b"]; removed => 1   (baza: ["qwen3:8b","llama3.1:8b","gemma2:9b"], 0)

2. Wybór wpisu Custom, który nie jest wyrenderowaną opcją, obcina identyfikator i zmienia providera (regresja).
   Chodzi o wpis z ogona overflow albo o opcję usuniętą w punkcie 1. Wybór idzie przez `selectModelFromDropdown(value, 'custom')` → `_ensureModelOptionInDropdown`. Gałąź `legacyRecordRoute` traktuje taki wybór jak zapisaną wartość legacy.
     .venv/bin/python ../mk2.py ../a5.js .
       ba745f59: state => {"model":"8b","model_provider":"custom:llama3.1"}
       cdff0b8d: state => {"model":"llama3.1:8b","model_provider":"custom"}
   W Pythonie: `model_with_provider_context('8b','custom:llama3.1')` → '@custom:llama3.1:8b' → `resolve_model_provider` → ('8b', 'custom:llama3.1', None). Czyli obcięty identyfikator na nieistniejącym nazwanym rekordzie zamiast skonfigurowanego endpointu.

3. Odtworzenie wyboru z grupy Custom nie trafia we własną opcję (regresja).
   Sesja zapisana jako ('qwen3:8b', 'custom'). `_findModelInDropdown` zwraca null, bo `routeNorm` i filtr sufiksu dzielą `@custom:qwen3:8b` na `custom:qwen3`/`8b`. W bazie zwracało '@custom:qwen3:8b'. Potem syncTopbar albo sessions.js wstrzykuje duplikat `@!:qwen3:8b` / `qwen3:8b`. Routing zostaje poprawny, ale picker pokazuje model dwa razy i nie zaznacza wiersza z katalogu.
     .venv/bin/python ../e2e.py .   → restore_lookup=None dla każdej opcji Custom (baza: własna opcja)
     .venv/bin/python ../mk2.py ../a1.js .  → find => null; ensure => "@!:qwen3:8b" (dodana druga opcja)

   Wspólna przyczyna 1–3: reguła „opcja, której autorytatywny provider to dokładnie `custom`, ma cały identyfikator” (zmiana 2) siedzi tylko w `_modelStateForSelect`. Konsumenci obok nadal stosują podział na nazwany rekord: `_modelPickerOptionIdentity`/dedupe, `routeNorm` i filtr sufiksu w `_findModelInDropdown`, `legacyRecordRoute` w `_ensureModelOptionInDropdown`. Wpisy przechodzą więc całą drogę z pickera do resolvera bez obcięcia tylko wtedy, gdy wybrana wartość jest już wyrenderowaną opcją.

4. Istniejący test zaczął padać.
     cd /opt/data/cache/scratch/g6/exp && ./scripts/test.sh tests/test_issue854_live_model_prefix.py -q
       FAILED ...::TestLiveModelPrefix::test_apply_prefix_to_any_non_at_id
       AssertionError: @provider: prefix application not found
     Ten sam test na cdff0b8d: passed.
   Przyczyna: `_addLiveModelsToSelect` buduje teraz prefiks przez `_encodeModelRoute`, a test statycznie szuka wzorca z `` mid=`@ ``. Test trzeba zaktualizować razem ze zmianą.
   Szerszy zestaw (142 pliki model/provider/custom/picker/alias): ba745f59 → 3 failed, z czego tylko ten jest nowy. `test_provider_mismatch::...known_limitation` pada też na bazie przy tej kolejności testów. `test_profile_switch_models_disk_cache[plugin-version-bumped]` jest niestabilny: na bazie pada mniej więcej 2 razy na 4 uruchomienia.

PREVIOUS FINDINGS STATUS:
- Zmiana 1 (pierwszeństwo providera z wartości w `_findModelInDropdown`): załatwiona. Sprawdziłem kombinacje `@custom:` / `@!:` / zakodowany nazwany / `@safe:` przy niezgodnej podpowiedzi i żadna nie podmienia wartości. W bazie `@!:gpt-4o` z podpowiedzią `safe` zwracało `@safe:gpt-4o`, teraz nie. Mutacja odwracająca kolejność wywala test.
- Zmiana 2 (stan opcji z grupy Custom): częściowo. `_modelStateForSelect` działa poprawnie: nazwana grupa `custom:backup` i `@safe:` zostają nietknięte, mutacja usuwająca `laneId` wywala test. Ta sama reguła nie trafiła do konsumentów obok, stąd blokery 1–3.
- Zmiana 3 (opis commita): załatwiona. Autor i committer to Szymon Żołnierczyk / Szqub, bez wzmianek o narzędziach.
- Zmiana 4 (dokumentacja): treść jest zgodna z zamierzeniem. Twierdzi jednak, że „picker identity, restore/injection” stosują spójną gramatykę, a w przypadku grupy Custom to dziś nieprawda.
- Wcześniejsze uwagi nieblokujące: blokuje tylko opisany wyżej przypadek legacy w `_ensureModelOptionInDropdown`. Reszta pozostaje nieblokująca.

NON-BLOCKING NOTES:
- `_ensureModelOptionInDropdown` nadal stawia podpowiedź przed providerem z wartości, czyli odwrotnie niż nowa reguła w lookupie. Przy niezgodnej podpowiedzi powstają podwójnie owinięte wartości:
  - `@!:a:b` + `custom:qwen3` → `@custom:qwen3:@!:a:b` (nowe zachowanie)
  - `@safe:a:b` + `custom` → `@!:@safe:a:b`

  Taki sam wzorzec dla `@custom:` i `@safe:` istniał już w bazie.
- Przy `model.provider` spoza local (np. anthropic) wybór Custom `qwen3:8b` nadal idzie jako `@custom:qwen3:8b` i rozwiązuje się do ('8b', 'custom:qwen3'). To było już w bazie i zgadza się z zawężonym opisem commita, ale warto o tym wspomnieć w PR.
- Mutacje, których nie łapią testy PR ani zmienione przez PR testy (101 testów):
  - gałąź `parsed` w `routes._catalog_group_owns_exact_model`
  - wczesny `@!:` w `_resolve_compatible_session_model_state`
  - nowa gałąź w `_strip_provider_hint_for_reasoning`
  - gałąź `@!:` / `%` w `_normalizeConfiguredModelKey`
  - regex `displayName` w `renderModelDropdown` (nie da się go wyekstrahować do testu)

  Łapane są: zmiana 1, zmiana 2, kanoniczny fallback w `_get_provider_cfg`, gałąź aux, enkoder sesji `@!:`, fail-closed resolvera, `legacyRecordRoute`, etykieta `@!:`.
- Pliki fixture opisane w PR jako `custom_providers: [{name: lab}]` i `providers: {lab: ...}` nie dają w katalogu wersji z prefiksem, więc bloker 1 nie wychodzi w obecnych testach. Brakuje testu z katalogiem statycznym, np. lmstudio z nienazwanym custom_providers i dwoma tagami o tym samym sufiksie.

Skrypty do odtworzenia wszystkiego powyżej są w /opt/data/cache/scratch/g6/ (e2e.py, mk2.py z a1–a5.js, mutate.py, subset.py). Eksport ba745f59 jest w g6/exp, a eksport bazy w g6/expbase.
