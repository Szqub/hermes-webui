1. Gramatyka i dowód rozłączności

Wybrałbym osobną rodzinę tokenów, poza przestrzenią zaczynającą się od „@”:

    configured-custom-token = "!custom-configured/v1:" + model-id

„model-id” jest całym niepustym identyfikatorem, zachowanym dosłownie. Dwukropki, ukośniki, wielkość liter i znaki procentowe nie podlegają interpretacji. Dekoder usuwa dokładnie stały prefiks; nie dzieli reszty po dwukropkach.

Przykład:

    !custom-configured/v1:qwen3.8:27b
    → model-id = qwen3.8:27b

Reguła wyłączności: rozłączne znaczniki początku rodzin tokenów.

Każdy token generyczny ma postać:

    "@" + canonical-provider-id + ":" + model-id

Zaczyna się więc od „@”. Token dedykowany zaczyna się od „!”. Równość tych ciągów wymagałaby równości ich pierwszych znaków, co jest niemożliwe.

To jest dowód konstrukcyjny, niezależny od treści i długości provider-id. Obowiązuje również dla identyfikatora zawierającego cały wybrany marker.

Nie potrzeba ani escape’owania provider-id w generycznym encoderze, ani dodatkowej walidacji kluczy providers: w celu zapewnienia rozłączności. Dotychczasowa walidacja typów pozostaje odrębnym kontraktem: nie-string powinien być obsłużony zgodnie z nim, nie przez nowe niejawne rzutowanie.

Warunek istotny dla dowodu: rozpoznawanie rodziny odbywa się na surowym ciągu, przed URL-dekodowaniem, przycinaniem prefiksów czy innymi przekształceniami.

W Pythonie i JavaScripcie obowiązuje ten sam stały prefiks oraz ta sama operacja usunięcia prefiksu. Dekoder powinien zwracać osobny rodzaj trasy, np. configured-custom, zamiast udawać, że marker jest nazwą providera.

2. Kolejność rozstrzygania i warunki działania

Encoder emituje nowy token wtedy i tylko wtedy, gdy wybór rzeczywiście należy do zwykłej sesyjnej ścieżki custom, korzystającej z model.base_url dla skonfigurowanego lokalnego endpointu. Dotyczy to opisanych wariantów ollama, vllm, lmstudio, llamacpp i legacy local.

Nie emituje go dla:

    named custom:<slug>
    jawnego wyboru @ollama:<model> lub @local:<model>
    zwykłego providera z providers:
    endpoint-derived custom:<host>:<port>

Resolver:

    A. Rozpoznaj dokładny prefiks !custom-configured/v1:.
    B. Jeśli go nie ma, przejdź do dotychczasowej ścieżki rozstrzygania.
    C. Jeśli jest, sprawdź niepusty payload i dostępność właściwej
       konfiguracji endpointu.
    D. Zwróć cały payload, provider custom oraz model.base_url,
       z uwierzytelnieniem należącym do tej samej ścieżki konfiguracji.

Krok A musi poprzedzać skany własności i parser generyczny. Po rozpoznaniu markera resolver nie konsultuje providers.ollama, providers.local, konkurencyjnych list modeli ani named custom_providers w celu wyboru endpointu lub klucza.

Ta trasa ustępuje wyłącznie wtedy, gdy prefiksu nie ma. Rozpoznany token z pustym payloadem, brakującym endpointem lub niezgodną konfiguracją kończy się jednoznacznym błędem konfiguracji — nie fallbackiem do innego właściciela. W przeciwnym razie utrata konfiguracji mogłaby przekierować żądanie i ujawnić jego treść innemu endpointowi.

Istotne rozróżnienie w macierzy akceptacyjnej:

    Custom-lane pick mistral-7b → custom, :11434
    Custom-lane pick qwen3.8:27b → custom, :11434, cały identyfikator
    Ollama-lane pick llama3 → ollama, :11434

Ostatni wiersz zależy od decyzji encodera o ścieżce wyboru. Jeśli llama3 zostanie zakodowany nowym tokenem Custom, wynik musi być custom. Resolver nie może ustępować Ollamie tylko dlatego, że identyfikator występuje wyłącznie w jej katalogu — przeczyłoby to autorytatywności nowej trasy. Jeśli wymaganie zakłada provider ollama także dla jawnego tokena Custom, jest wewnętrznie sprzeczne.

3. Kontrprzykłady

Rozważyłem następujące przypadki:

    @custom:qwen3:8b

Dziś może oznaczać model qwen3:8b na zwykłym Custom endpoint albo model 8b u named custom:qwen3. Nowa reprezentacja pierwszego znaczenia to:

    !custom-configured/v1:qwen3:8b

Drugie zachowuje dotychczasowy token. Nie ma już identycznych reprezentacji dla nowych zapisów.

    custom_providers.name = qwen3
    Custom-lane model = qwen3:8b

Nazwa qwen3 nie jest nawet sprawdzana przy obsłudze nowego tokena. Nie przejmuje endpointu, klucza ani fragmentu identyfikatora.

    providers.ollama.base_url = http://other:9999
    providers.local.base_url = http://other:9999
    custom_providers.name = local

Żaden z tych rekordów nie bierze udziału w rozstrzyganiu nowej trasy. Endpoint i klucz pozostają własnością skonfigurowanej ścieżki Custom.

Dla provider-id:

    custom
    custom:a:b
    Custom:Lab
    +x
    %2Bx
    foo bar
    foo:bar:baz
    pustego
    z początkową lub końcową spacją
    bardzo długiego
    zawierającego !custom-configured/v1:

generyczny encoder nadal dodaje początkowe „@”. Kanonikalizacja wielkości liter lub whitespace nie zmienia tego faktu. Nawet provider-id równy markerowi daje token zaczynający się od „@!”, a nie „!”.

Nie-string nie ma semantyki poprawnego provider-id bez osobnej reguły konwersji. Zarówno jego odrzucenie, jak i istniejąca konwersja do tekstu nie naruszają dowodu, o ile encoder nadal dodaje „@”.

Nie wykonywałem testów repozytorium ani nie czytałem implementacji. Próba uruchomienia izolowanego sprawdzenia ciągów została zablokowana przez politykę wykonania; powyższe są kontrprzykładami przeanalizowanymi, nie raportem z uruchomionych testów.

4. Zgodność ze starymi sesjami

Nie da się bezstratnie automatycznie zmigrować każdego starego tokena. Stary zapis nie zawiera informacji, którą teraz dodajemy.

Wybrałbym następującą politykę:

    Nowy marker:
        Zawsze nowa, autorytatywna ścieżka.

    Stary @custom:... z poprawnie rozstrzyganym znaczeniem generycznym
    lub named:
        Zachowaj to znaczenie.

    Stary @custom:... wcześniej nierozstrzygalny:
        Dopuść compatibility fallback do całego sufiksu po @custom:
        tylko przy aktywnej zwykłej konfiguracji Custom endpointu,
        gdy żaden poprawny dotychczasowy właściciel nie został znaleziony.

Sprawdzenie właściciela musi używać tej samej kanonikalizacji co encoder i pozostały resolver, nie surowego porównania kluczy providers:.

W konkretnym kolizyjnym przykładzie z named custom:qwen3:

    @custom:qwen3:8b
    → nadal named custom:qwen3, model 8b

To nie naprawia historycznie błędnego wyboru Custom. Jest jednak uczciwsze niż zmiana endpointu prawidłowo zapisanej sesji named. Ponowny świadomy wybór w pickerze zapisze nową, jednoznaczną formę.

Fallback nie może obejmować aktywnej named custom:<slug> ani omijać jej fail-closed z #4728. Nie może też naprawiać dowolnych jawnych @local:... lub @ollama:... przez przekierowanie ich do Custom.

Nie wykonywałbym automatycznego przepisywania niejednoznacznych zapisów. Brak rozstrzygającej informacji nie jest podstawą do zmiany właściciela endpointu.

5. Trzy najsłabsze punkty

1. Nowa rodzina tokenów rezerwuje prefiks w przestrzeni dotychczasowych „bare model-id”. Literalny identyfikator modelu zaczynający się od !custom-configured/v1: wymaga jawnego provider-qualified opakowania albo osobnej reprezentacji literału. Dowód rozłączności z tokenami „@” nie jest dowodem rozłączności ze wszystkimi możliwymi bare identyfikatorami.

2. Stare kolizyjne sesje pozostają nieodwracalnie niejednoznaczne. Zachowanie named znaczenia chroni kompatybilność, ale nie odzyskuje intencji historycznego wyboru Custom.

3. Token utrwala rodzaj ścieżki, nie konkretny endpoint. Po zmianie model.base_url sesja użyje nowej konfiguracji; po jej usunięciu zakończy się błędem. Dodatkowo każdy konsument Python/JS musi rozumieć nową rodzinę — pojedynczy stary dekoder może błędnie wyświetlić token lub zmienić go przy ponownym zapisie.
