# Lokalne symulacje Monte Carlo v1.1.0

Uruchamiaj na zaufanym komputerze (np. Andromeda/WSL), po przeglądzie kodu. Nie uruchamiaj niezaufanych PR na stałym runnerze. Bez danych uczestników, API, usług płatnych i automatycznego uruchamiania pełnych symulacji w CI.

Każdy manuskrypt ma `monte_carlo.py`. P02: NOT_APPLICABLE, refleksyjna analiza tematyczna nie wymaga symulacji mocy. P01/P03–P09 wywołują istniejące estymatory. Profile: smoke (sprawdzenie wykonania), pilot (przesiew), full (docelowa precyzja rozwojowa). Nie są to zatwierdzone metody potwierdzające.

## Uruchomienie

Z katalogu repozytorium na zaufanym, sprawdzonym HEAD. WSL/Linux: przygotowanie odrębnych środowisk (jawna instalacja zależności), następnie uruchomienie:

```bash
bash run-monte-carlo.sh all --setup
bash run-monte-carlo.sh all --profile smoke --jobs 4
bash run-monte-carlo.sh P09 --profile full --jobs 8
```

Alternatywnie dla pojedynczej pracy:

```bash
python3 manuscripts/MSC-MUS-P09/monte_carlo.py --profile full --list
python3 -m venv .venv/p09
source .venv/p09/bin/activate
python -m pip install -r manuscripts/MSC-MUS-P09/analysis/requirements.txt
python manuscripts/MSC-MUS-P09/monte_carlo.py --profile smoke --jobs 4
python manuscripts/MSC-MUS-P09/monte_carlo.py --profile full --jobs 8
```

Dla każdego badania utwórz oddzielne środowisko zgodne z analysis/requirements.txt. P05 dodatkowo wymaga Rscript, lavaan oraz semTools; użyj wersji zgodnych z referencją, odnotuj rozbieżności. Nic nie instaluje się automatycznie. Jeśli systemowy Python jest niezgodny z przypiętymi pakietami, wybierz Python 3.12/3.13, np. `PYTHON_BIN=python3.12 bash run-monte-carlo.sh all --setup`. Skrypt bash używa odrębnych .venv/monte-carlo/Pxx. Bez skryptu wspólne uruchomienie runnera wymaga zgodnego środowiska; wersje NumPy/SciPy mogą się różnić.

`--task 'ipw/cell-06/*'` wybiera konfigurację z zależnościami; `--list` wypisuje programy, ziarna, parametry i zależności bez obliczeń. Domyślnie jeden proces i jeden wątek BLAS; zwiększ --jobs ostrożnie względem pamięci, --threads domyślnie 1. GPU nie jest wykorzystywane przez obecne modele NumPy/SciPy/R.

## Windows (CMD i dwuklik)

W każdym katalogu manuskryptu znajduje się `monte_carlo.bat`. Pierwsza instalacja w CMD jest jawna:

```bat
monte_carlo.bat --setup
monte_carlo.bat --profile smoke --jobs 4
monte_carlo.bat --profile full --jobs 8
monte_carlo.bat --list --profile full
```

Dwuklik uruchamia profil smoke i pozostawia okno otwarte do odczytu wyniku. Pełne obliczenia wymagają jawnego wyboru full. Środowiska Windows są oddzielone od WSL w .venv/monte-carlo-windows/Pxx. Wymagany jest Python i Git w PATH, a dla P05 także Rscript z lavaan i semTools. Opcjonalnie ustaw PYTHON_BIN na pełną ścieżkę do zgodnego python.exe przed --setup. Po przejściu między Windows i WSL użyj odrębnego --run-id, ponieważ metadane środowisk są różne. P02 zwraca NOT_APPLICABLE. Zależności nie instalują się przy dwukliku.

## Zakres profilu full

P01: 96 komórek × 20 000; P03: 5 mechanizmów × 2000 na konfigurację, 50 imputacji/15 iteracji, cel 500/cap 660; P04: wspólna kalibracja PAQ-S, produkcji i PMM, 2000/50; P05: trzy struktury EFA/CFA (2000 i 500 permutacji, partie po 5) oraz 16 komórek ośmiopozycyjnej inwariancji (2000, partie po 20); P06: skupienia, ograniczone wyniki, braki, bootstrap 999, 2000; P07: H1 i rodzina H2/H3, 2000; P08: faktorialny model, brak słyszenia, bootstrap 1999, 2000; P09: 40 komórek IPW po 2000 × 999 na endpoint, partie 20 i agregacja; osobne porównania IPW/AIPW w 9 komórkach, także partie po 20. Obliczenia pełne są wymagające czasowo. Obecne programy nie obejmują wszystkich przyszłych bramek i nie dowodzą trafności empirycznej.

## Wyniki i wznowienie

build/monte-carlo/<HEAD>/<Pxx>/<profil>/<run-id>/ (ignorowany przez Git). Każdy JSON ma metadane SHA-256, polecenie, środowisko i zależności. Wznowienie na poziomie ukończonego zadania/partii (nie wewnątrz monolitycznej symulacji P01/P03/P04/P06/P07/P08) przez identyczne polecenie wykorzystuje wyłącznie poprawne, zgodne wyniki; nie miesza środowisk, rewizji ani ziaren. Po zmianie środowiska użyj innego --run-id. Błąd pozostawia stderr i częściowy wynik, bez znacznika sukcesu; zależności są blokowane, pozostałe zadania kontynuowane. Usuń blokadę .run.lock tylko po upewnieniu się, że nie działa proces. Testy orkiestracji: `python -m unittest -v test_monte_carlo_runner`. Sukces wykonania nie oznacza zatwierdzonej kalibracji. Nie commituj surowych wyników automatycznie.
