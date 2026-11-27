"""Forward Windows launcher arguments without CMD SHIFT truncation."""
import runpy
import sys
from pathlib import Path

from monte_carlo_runner import STUDIES, directory

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in STUDIES:
        raise SystemExit("Expected study P01 through P09")
    study = sys.argv.pop(1)
    launcher = directory(study) / "monte_carlo.py"
    sys.argv[0] = str(launcher)
    runpy.run_path(str(launcher), run_name="__main__")

if __name__ == "__main__":
    main()
