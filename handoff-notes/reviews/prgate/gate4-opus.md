VERDICT: BLOCK dla f585b123, czyli commita wskazanego w briefie.

Uwaga: w trakcie mojego review ktoś zrobił amend tego commita. Około 21:12:02 UTC branch przeskoczył z f585b123 na 37032708 (`git reflog`: "commit (amend)"). Ja nic nie zmieniałem w gicie. Amend naprawia mój blocker, ale 37032708 nie przeszedł pełnego review, więc go nie zatwierdzam. Moje uwagi do niego są niżej.

BLOCKERS (f585b123):

1. Python i JS czytają ten sam zapisany legacy-string inaczej, a każda wersja wysyła go do innego endpointu. To przeczy claimom 4 i 5.
   W f585b123 `_parseModelRoute` sprawdza najpierw podpowiedź providera z wywołania, a dopiero potem legacy-regułę `@custom:`.
   Komenda: `git show f585b123:static/ui.js > ui_f585b123.js && node parity_hint.js ui_f585b123.js`
   Wynik:
     ["@custom:qwen3:8b","custom"] -> {"provider":"custom","model":"qwen3:8b"}
     ["@custom:localhost:11434:x","custom"] -> {"provider":"custom","model":"localhost:11434:x"}
   Python dla tych samych bajtów (`probe_session.py`, sesja `('@custom:qwen3:8b','custom')`):
     -> `('@custom:qwen3:8b', 'custom:qwen3')`, resolve `('8b', 'custom:qwen3', 'http://gpu-box:8000/v1')`
   - Co to znaczy dla sesji: przy restore przeglądarka po cichu przepisuje sesję z `@custom:qwen3:8b` na `@!:qwen3:8b`, czyli na skonfigurowany endpoint. Ścieżki tylko po stronie serwera dalej idą do rekordu nazwanego. To jest niezapowiedziana migracja, a claim 4 mówi, że jej nie ma.
   - Testy f585b123 to zapisują: `test_injecting_existing_route...` wymaga wartości `"@!:qwen3:8b"` dla wejścia `["custom","@custom:qwen3:8b"]`. Przechodzi (83 passed), więc ta rozbieżność jest wręcz zakodowana w teście.
   - W 37032708 to jest naprawione. Ta sama komenda na ui.js z 37032708 daje `custom:qwen3` / `8b` oraz `custom:localhost:11434` / `x`, zgodnie z Pythonem.

NON-BLOCKING NOTES:

1. Nowe ryzyko w 37032708, mechanizm potwierdzony, ale realnej ścieżki nie odtworzyłem.
   - Opcja w grupie Custom o wartości `@custom:qwen3:8b` i `data-provider="custom"` daje w `_modelStateForSelect` `{"model":"8b","model_provider":"custom"}`. Serwer robi z tego `@!:8b` i wysyła skrócone id na `model.base_url` (`node state_select.js ui_37032708.js`, potem `probe_dedup2.py`). Baseline i f585b123 dawały tu `qwen3:8b`.
   - Taką opcję potrafi wyprodukować sam katalog: `_deduplicate_model_ids` z pid `custom` emituje `@custom:qwen3:8b` (`probe_dedup2.py`).
   - W 4 realistycznych konfiguracjach z lokalnym fałszywym `/v1/models` grupa Custom nigdy nie dostała takiej wartości, więc to, czy ścieżka jest osiągalna, pozostaje niepotwierdzone.
   - Sugestia: dla skonfigurowanej grupy Custom dedup i prefiks powinny emitować `@!:`. Alternatywnie `_modelStateForSelect` nie powinien mieszać `route.model` z providerem wziętym z opcji.
2. `model.provider: custom` plus rekord nazwany z tym samym id: wybór Custom `qwen3:8b` dalej idzie na endpoint i klucz rekordu nazwanego (`probe_e2e.py`, `home-custom`). Tak samo jest w baseline, raport uczciwie mówi "unchanged". Commit message ("Selection now uses a reserved @!:M route for the configured endpoint") jest jednak szerszy niż faktyczny zakres: działa tylko dla aktywnego `local` i lokalnych serwerów. Warto zawęzić to sformułowanie.
3. Gdy rekord nazwany listuje `qwen3:8b`, picker w ogóle ukrywa `qwen3:8b` w grupie Custom. Z fałszywym `/v1/models` grupa Custom ma tylko `['llama3']`, w baseline tak samo. Wiersz macierzy "named competitor qwen3" da się więc osiągnąć tylko przez sesję, restore albo wpisanie id ręcznie.
4. `resolve_model_provider` wcześniej nigdy nie rzucał wyjątku, teraz rzuca `ValueError`. Wywołania w context lookup i process wakeup są w try. Wywołań w `routes.py:27224` (commit message) i `routes.py:29297` nie sprawdziłem pod kątem przestarzałej sesji `@!:` po zmianie configu.
5. Drobne rozbieżności parsera i enkodera między Pythonem a JS (`probe_parity.py`, 9 przypadków), wszystkie poza wyjściem enkodera i żadna nie trafia w `@!:`:
   - wielkość liter w `@CUSTOM:`, `@Custom:`, `@custom:LOCALHOST:`;
   - port zapisany cyframi Unicode;
   - spacja przed `@!:` oraz przed hostem;
   - błędne sekwencje procentowe;
   - różne zbiory białych znaków przy trim (`\x1c`, `\ufeff`).
6. Zmienione istniejące testy nie zostały osłabione. W #7290 regex na f-string zastąpił sprawdzanie wywołania wspólnego enkodera, a negatywny test na alias ze slashem został. W `test_model_picker_badges.py` doszło tylko wstrzyknięcie helpera do zakresu.
7. Raport jest nieaktualny: mówi "no commit" i branch `design/7955-disjoint-route`. Nie opisuje też zmian z amenda (kolejność parsowania hintu, injekcja verbatim).
8. Odstępstwa od briefu:
   - `PYTHONPATH` z briefu zablokowała polityka bezpieczeństwa, więc użyłem własnego `.venv` worktree przez `./scripts/test.sh`. Skrypt doinstalował zależności do ignorowanego `.venv`.
   - Pliki probe utworzyłem tylko poza repo, w `/opt/data/cache/scratch/review-7955-probes/`.
   - `git status` obu worktree jest czysty.

CLAIM CHECK:

- Wyniki testów z raportu odtworzone. Na baseline z testami #7955: 71 failed, 12 passed. Na f585b123: 83 passed, sąsiednie suite'y 497 passed, `node --check` OK dla ui/commands/panels. Na 37032708 łącznie 580 passed.
- Claim 1 potwierdzony dla `ollama`, `vllm` i `local`. Sprawdzenie `@!:` stoi przed jakimkolwiek skanem, wcześniej czytany jest tylko `cfg["model"]`.
  - E2E z prawdziwym resolverem runtime: `qwen3:8b` idzie na `http://127.0.0.1:11434/v1` z kluczem z `model.api_key`, nie z rekordu nazwanego.
  - Baseline z tą samą konfiguracją dawał `('8b','custom:qwen3', gpu-box)` z kluczem rekordu nazwanego.
  - Dla `qwen3.8:27b` baseline odtwarza objaw z issue (`CustomProviderRouteError: custom:qwen3.8 is not configured`), poprawka kieruje poprawnie.
  - Nie dotyczy `model.provider: custom` (uwaga 2).
- Claim 2 potwierdzony, kontrprzykładu nie znalazłem. Sprawdziłem:
  - `!`, `!:payload`, `a!b`, `%21`, `%2521`, `%25`;
  - wielkie litery, białe znaki ASCII i Unicode, zagnieżdżone dwukropki;
  - pusty provider, None, 0, False, bajty, listę, dict;
  - id o długości 20 000 znaków.
  Sprawdziłem to przez `_encode_provider_qualified_model_id`, `_apply_provider_prefix`, `_deduplicate_model_ids` i `model_with_provider_context`. Jedyne trafienie `@!:` to puste id providera przy model id, które już było `@!:y`. To przepuszczenie gotowej wartości bez zmian, nie przemyt przez providera, i raport to opisuje.
- Claim 3 potwierdzony przez testy, które uruchomiłem, oraz `probe_alias.py`. Pozostali lokalni providerzy (`lmstudio`, `tabby`, `localai`, `koboldcpp`, `llama.cpp`) zachowują się identycznie jak w baseline.
- Claim 4: w Pythonie się trzyma. W przeglądarce dla f585b123 obalony (blocker 1), dla 37032708 się trzyma.
- Claim 5: dla f585b123 obalony (blocker 1). Dla 37032708 zgodny na typowych kształtach, z drobnymi rozbieżnościami z uwagi 5 i nowym przypadkiem z uwagi 1.
- Czego nie uruchomiłem:
  - pełnej suity repo;
  - prawdziwego requestu completion;
  - przeglądarki z prawdziwym DOM;
  - pełnego review 37032708 poza testami i powyższymi probe'ami.
