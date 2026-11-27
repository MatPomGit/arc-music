# Lokalne symulacje Monte Carlo v1.3.0

Uruchamiaj na zaufanym komputerze (np. Andromeda/WSL), po przeglądzie kodu. Nie uruchamiaj niezaufanych PR na stałym runnerze. Bez danych uczestników, API, usług płatnych i automatycznego uruchamiania pełnych symulacji w CI.

Każdy manuskrypt ma `monte_carlo.py`. P02: NOT_APPLICABLE, refleksyjna analiza tematyczna nie wymaga symulacji mocy. P01/P03–P09 wywołują istniejące estymatory. Profile: smoke (sprawdzenie wykonania), pilot (przesiew), full (docelowa precyzja rozwojowa). Nie są to zatwierdzone metody potwierdzające.

## Uruchomienie

Z katalogu repozytorium na zaufanym, sprawdzonym HEAD. WSL/Linux: przygotowanie odrębnych środowisk (jawna instalacja zależności), następnie uruchomienie:

```bash
bash run-monte-carlo.sh all --setup
bash run-monte-carlo.sh all --profile smoke --jobs 4
bash run-monte-carlo.sh P09 --profile full --jobs 8
```

Dla każdego badania utwórz oddzielne środowisko zgodne z analysis/requirements.txt. P05 dodatkowo wymaga Rscript, lavaan oraz semTools; użyj wersji zgodnych z referencją, odnotuj rozbieżności. Nic nie instaluje się automatycznie. Jeśli systemowy Python jest niezgodny z przypiętymi pakietami, wybierz Python 3.12/3.13, np. `PYTHON_BIN=python3.12 bash run-monte-carlo.sh all --setup`. Skrypt bash używa odrębnych .venv/monte-carlo/Pxx. Bez skryptu wspólne uruchomienie runnera wymaga zgodnego środowiska; wersje NumPy/SciPy mogą się różnić.

`--list` wypisuje programy, ziarna, parametry i zależności bez obliczeń. Domyślnie jeden proces i jeden wątek BLAS; zwiększ --jobs ostrożnie względem pamięci, --threads domyślnie 1. GPU nie jest wykorzystywane przez obecne modele NumPy/SciPy/R.

## Windows (CMD i dwuklik)

W każdym katalogu manuskryptu znajduje się `monte_carlo.bat`. Pierwsza instalacja w CMD jest jawna:

```bat
monte_carlo.bat --setup
monte_carlo.bat --profile smoke --jobs 4
monte_carlo.bat --profile full --jobs 8
monte_carlo.bat --list --profile full
```

Dwuklik otwiera menu: instalacja, pilot, full, smoke, własna symulacja i wyjście. Własny profil pyta o replikacje, seed, procesy, scenariusz i parametry obsługiwane przez dany model. Konfiguracja ma osobny identyfikator skrótu; stałe siatki N i efektów pozostają bez zmian. Full pokazuje planowaną liczbę replikacji i wymaga potwierdzenia. Licznik w trakcie dotyczy zakończonych zadań, nie pojedynczych replikacji wewnątrz monolitycznych programów. Środowiska Windows są oddzielone od WSL w .venv/monte-carlo-windows/Pxx. Wymagany jest Python i Git w PATH, a dla P05 także Rscript z lavaan i semTools. Opcjonalnie ustaw PYTHON_BIN na pełną ścieżkę do zgodnego python.exe przed --setup. Po przejściu między Windows i WSL użyj odrębnego --run-id, ponieważ metadane środowisk są różne. P02 zwraca NOT_APPLICABLE. Zależności nie instalują się przy dwukliku.

Wykresy SVG i indeks wartości: `manuscripts/MSC-MUS-Pxx/results/<HEAD>/<profil>/<run-id>/`. Surowy JSON pozostaje w build/. Wykresy rozróżniają metryki i rodziny zadań; nie przedstawiają danych empirycznych.

## Zakres profilu full

Profil full: P01 20 000 replikacji na scenariusz, pozostałe badania ilościowe 2000. Dokładne konfiguracje: `--list`; liczebności: `--summary`. 

## Wyniki i wznowienie

build/monte-carlo/<HEAD>/<Pxx>/<profil>/<run-id>/ (ignorowany przez Git). Każdy JSON ma metadane SHA-256, polecenie, środowisko i zależności. Wznowienie na poziomie ukończonego zadania/partii (nie wewnątrz monolitycznej symulacji P01/P03/P04/P06/P07/P08) przez identyczne polecenie wykorzystuje wyłącznie poprawne, zgodne wyniki; nie miesza środowisk, rewizji ani ziaren. Po zmianie środowiska użyj innego --run-id. Błąd pozostawia stderr i częściowy wynik, bez znacznika sukcesu; zależności są blokowane, pozostałe zadania kontynuowane. Usuń blokadę .run.lock tylko po upewnieniu się, że nie działa proces. Testy orkiestracji: `python -m unittest -v test_monte_carlo_runner`. Sukces wykonania nie oznacza zatwierdzonej kalibracji. Nie commituj surowych wyników automatycznie.
