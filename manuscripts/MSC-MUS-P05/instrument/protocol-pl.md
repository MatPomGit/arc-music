# AI-MRFS: pula kandydacka v0.1.0 (26.11.2026)

Status: projekt prospektywny, bez walidacji. Pula 35 autorskich pozycji nie jest gotowym kwestionariuszem ani narzędziem klinicznym. Wymaga analizy P02, oceny treści, wywiadów poznawczych oraz zatwierdzenia zespołu.

## Instrukcja robocza

Przypomnij sobie ostatnią sesję z ostatnich 30 dni, w której aktywnie kierowałeś lub kierowałaś tworzeniem muzyki z użyciem generatora AI. Może to być sesja przerwana lub bez ukończonego utworu. Oceń, w jakim stopniu podczas tej sesji tworzenie służyło każdej z wymienionych funkcji, niezależnie od tego, czy udało się osiągnąć zamierzony efekt.

0: wcale; 1: w niewielkim stopniu; 2: umiarkowanie; 3: w dużym stopniu; 4: w bardzo dużym stopniu. Odrębnie: nie potrafię ocenić / wolę nie odpowiadać (brak danych). Nie wymagamy ujawniania treści utworu.

## Procedura

Dla każdej pozycji zapisz źródło koncepcyjne, przyszły identyfikator tematu P02, ocenę ekspertów i uwagi uczestników. Nie wpisuj fikcyjnych danych. Weryfikuj synonimiczność oraz rozróżnienia między funkcją, motywem i wynikiem. Przeprowadź dwa cykle wywiadów poznawczych. Po pilotażu ustal kolejność losową pozycji oraz reguły wyświetlania. Nie zmieniaj brzmienia w toku EFA. Zamroź model i zestaw pozycji przed oddzielną CFA. Każda późniejsza zmiana wymaga nowej próby potwierdzającej. Nie obliczaj sumy ogólnej, norm, progów klinicznych ani wyniku osoby przed walidacją.

P02 dostarcza materiału jakościowego, P03 rozróżnia motyw i konsekwencję, P04 dotyczy eksperymentu oraz PAQ-S-PL, P06 bada ruminację i unikanie. PAQ-S-PL to ewentualny odrębny korelat, nie składnik AI-MRFS. Żadna pozycja porównawczych skal nie została tu skopiowana.

Nie rozpoczynać rekrutacji bez zgody etycznej, zatwierdzenia materiałów, weryfikacji praw do narzędzi porównawczych, kalibracji liczebności i prerejestracji.

## Rejestr decyzji dotyczących treści

Przed pierwszą oceną zamroź identyfikatory pozycji i numer puli. Dla każdej pozycji prowadź w zatwierdzonym rejestrze badawczym rekord o polach: identyfikator i wersja pozycji, domena, uzasadnienie teoretyczne, identyfikator wyniku P02, rodzaj powiązania, komentarz o pokryciu domeny, rozkłady ocen ekspertów, kod trudności z wywiadu poznawczego, decyzja, uzasadnienie i wersja następna. Dopuszczalne powiązania to potwierdzenie, rozszerzenie, sprzeczność i brak powiązania po analizie. Do pozyskania rzeczywistych wyników P02 zapisz status `oczekuje_na_P02` i pozostaw identyfikator pusty. Jedna pozycja może mieć kilka powiązań. Temat P02 może wskazywać lukę nawet przy braku pasującej pozycji. Cytaty, klucze do materiału źródłowego i oceny indywidualne pozostają w zatwierdzonym rejestrze poza Git.

Eksperci oceniają niezależnie trafność domenową i jasność w skali 1–4. Dodatkowo wskazują domeny niepokryte przez pulę oraz przypadki interpretacji jako motyw początkowy lub osiągnięty skutek. Próg .78 odsetka ocen 3–4 sygnalizuje potrzebę dyskusji. Udokumentuj mianowniki, brakujące oceny i decyzję zespołu także przy dużej zgodności. Nie aprobuj pozycji pokrywającej niezamierzoną domenę na podstawie samego wyniku liczbowego.

W każdej rundzie wywiadów poznawczych stosuj tę samą kolejność zadań: wskazanie epizodu, samodzielna odpowiedź, parafraza, opis procesu przypominania i uzasadnienie wyboru kategorii. Koduj problemy jako rozumienie, przypominanie, przypisanie do domeny lub mapowanie odpowiedzi. Celowo uwzględniaj przerwane i rozczarowujące epizody. Zmienione pozycje poddaj ponownej obserwacji. Na końcu uzasadnij zachowanie, zmianę, dodanie albo usunięcie pozycji. Przed pilotażem sprawdź prawa do wybranych komparatorów i wersji językowych oraz uzyskaj wymaganą zgodę etyczną.

## Alternatywna pula kandydacka v0.2.0 (27.11.2026)

Plik `item-pool-v0.2.0-pl.csv` zawiera 35 pozycji z niezmienionymi identyfikatorami, w tym 12 propozycji zmian. Pierwotna pula `item-pool-pl.csv` pozostaje zachowana jako v0.1.0. Plik `item-revision-v0.2.0.csv` dokumentuje dla wszystkich pozycji brzmienie przed i po, uzasadnienie oraz puste pola wyników P02 i ocen. Nie jest to zatwierdzona pula.

Rozróżnienia domen: EXP dotyczy nadawania uczuciom formy wyrazu (również złożoności i intensywności przekazu); REF interpretowania znaczenia lub rozważania nowych perspektyw; MOD postrzeganej funkcji regulowania jakości, intensywności, pobudzenia, podtrzymywania lub przywracania stanu, a nie początkowej deklaracji motywu ani osiągniętej zmiany. PER obejmuje powroty uwagi, pamięci i treści myślowej do tego samego tematu. Nie jest miarą klinicznej ruminacji, negatywności, niekontrolowalności czy szkody. AVO dotyczy odkładania konkretnego działania podczas wskazanej sesji; DIV krótkiej zmiany uwagi bez koniecznego odkładania działania.

W obu rundach wywiadów należy oddzielnie sprawdzić, czy respondenci rozpoznają funkcję (a nie motyw lub skutek), czy EXP03/04 są rozróżnialne, czy MOD03/05 nie wymuszają nieadekwatnej odpowiedzi przy braku odpowiedniego stanu oraz czy PER02/03/05 odróżniają powracanie od refleksji i nie wymagają wielu sesji. Zbadać rozróżnienie AVO04/DIV03 przy faktycznym odłożeniu działania oraz jego braku. Nie sugerować, że niska lub wysoka ocena jest lepsza. Jeżeli pozycja systematycznie nie dotyczy znacznej części epizodów, zmodyfikować treść lub regułę odpowiedzi przed EFA zamiast imputować brak jako zero. Dopuszczalne zmiany zależą od danych P02, decyzji zespołu i rzeczywistej oceny ekspertów/uczestników. Żadne dane jakościowe ani oceny nie zostały uzupełnione.
