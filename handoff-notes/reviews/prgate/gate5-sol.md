VERDICT: BLOCK

BLOCKERS:

1. Ochronę legacy można ominąć przez dopasowanie istniejącej opcji, przed wejściem do legacyRecordRoute.

   Scenariusz:
     zapis sesji: @custom:qwen3:8b
     hint: custom
     istniejąca opcja: @!:8b, data-provider="custom"

   _findModelInDropdown filtruje opcje według hintu custom, ale porównuje tylko sparsowane modele. Oba wartości mają model 8b, mimo różnych providerów:
     @custom:qwen3:8b → custom:qwen3 / 8b
     @!:8b → custom / 8b

   W konsekwencji matcher wybiera @!:8b. _ensureModelOptionInDropdown akceptuje ten wynik i wraca przed ochroną legacyRecordRoute.

   Wykonane komendy w ocenianym worktree:
     git blame -L 3667,3685 HEAD -- static/ui.js
     git blame -L 3813,3839 HEAD -- static/ui.js

   Obserwowany fragment wyjścia:
     3683: const providerOptions=options.filter(o=>_getOptionProviderId(o).toLowerCase()===preferred);
     3684: const providerMatch=providerOptions.find(o=>routeNorm(o.value)===routeNorm(rawModel));
     3685: if(providerMatch) return providerMatch.value;

     3817: const applied=_applyModelToDropdown(modelId,sel,requestedProvider||null);
     3822: if(!requestedProvider||String(appliedState&&appliedState.model_provider||'').toLowerCase()===requestedProvider.toLowerCase()) return applied;

   Ochrona legacy zaczyna się dopiero w linii 3830. Restore w boot.js:3782–3791 i ui.js:11735 również najpierw wywołuje _applyModelToDropdown.

   To jest wniosek z prześledzenia kodu, nie wynik wykonanego własnego probe. Próby uruchomienia probe zostały zablokowane przez środowisko:
     „BLOCKED: Command flagged as dangerous (script execution via -e/-c flag)”
     „BLOCKED: Command flagged as dangerous (script execution via heredoc)”

   Nie przedstawiam przewidywanego wyniku jako zaobserwowanego stdout. Niemniej ścieżka w kodzie pozostaje: restore może pokazać configured lane zamiast named record. Dokumentacja „restored value is injected verbatim” nie obejmuje tego wcześniejszego dopasowania. Nowy test injection używa pustego selecta, więc go nie wykrywa.

   Potrzebne jest respektowanie providera jawnie zapisanego w qualified value także podczas lookup/apply, nie tylko podczas tworzenia brakującej opcji.

PREVIOUS FINDINGS STATUS:

- addressed: _parseModelRoute("@custom:qwen3:8b","custom") stosuje teraz legacy split. Injection do pustego selecta zachowuje string oraz stan 8b / custom:qwen3. Nowe testy przeszły.
- still blocking: pierwotny problem nie jest zamknięty dla selecta zawierającego pasującą opcję configured lane — opisany bypass.
- addressed: trailing blank line. git diff --check cdff0b8d kończy się exit 0.
- not addressed, nadal non-blocking: moa poprzedza reserved branch w _resolve_compatible_session_model_state; wcześniejsza uwaga o alias resolution przed głównym resolverem nie została zmieniona w tej rundzie. Nie potwierdziłem konfliktowych kombinacji wykonaniem.
- not addressed, nadal granica weryfikacji: brak rzeczywistego upstream completion i dowodu doboru configured credentials. Nie traktuję tego samoistnie jako blokera tej poprawki.

NON-BLOCKING NOTES:

- Weryfikacja wykonana:
    nowe suites: 83 passed in 6.96s
    wskazane sąsiednie suites oraz provider-aware/session-switch coverage: 511 passed in 25.05s
    dodatkowe repair/auxiliary/reasoning/runtime/cron/boot/profile/dedup/badge/alias suites: 197 passed in 14.96s

  Grupy częściowo się pokrywają; nie sumuję ich jako unikalnych testów. Nie zaobserwowałem regresji w uruchomionych suites.

- node --check dla static/ui.js, static/commands.js i static/panels.js: exit 0.

- Literalna parity nie jest pełna, niezależnie od naprawionego hintu:
    @custom:Qwen3:8b
      Python zwraca provider custom:Qwen3.
      JavaScript zwraca provider custom:qwen3.

  Wynika to bezpośrednio z api/config.py:2727 i static/ui.js:3203. Downstream canonicalization może zniwelować różnicę; sama różnica case nie dowodzi zmiany endpointu.

- Obsługa malformed percent również różni się w kodzie: Python używa permissive unquote, JavaScript decodeURIComponent z zachowaniem całego tokenu po wyjątku. Przykłady wymagające dodatkowego executable coverage:
    @foo%20bar%ZZ:model
    @bad%FF:model

  Nie wykonałem tych przypadków. Nie deklaruję pełnej parity dla wszystkich ${}%‑bearing wartości na podstawie obecnego zestawu.

- Usunięcie hint shortcut nie spowodowało zaobserwowanych awarii picker identity, dedup, badge ani alias lookup. To nie eliminuje opisanego problemu: matcher nadal pozwala hintowi wybrać lane sprzeczny z qualified input.

- Restore może nadal wysłać oryginalny legacy string: static/messages.js:108–124 preferuje S.session.model nad dropdownem. Samo dopasowanie opcji podczas restore nie przepisuje automatycznie S.session.model. Pythonowy test potwierdza, że @custom:qwen3:8b rozwiązuje się do named endpointu. Nie twierdzę więc, że znaleziony bypass sam w sobie natychmiast przekierowuje następny request; dowodzi rozjazdu picker/runtime i naruszenia kontraktu zachowania wyboru.

- HEAD: 37032708802425e505f7b6b9de61dcc5b84e4001. Końcowy git status --short pusty. Bez edycji, commitów i pushów; testy korzystały z tymczasowych fixtures.
