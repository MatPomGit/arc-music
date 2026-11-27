#!/usr/bin/env bash
# Explicitly prepare isolated per-study venvs or run reviewed local simulations.
set -uo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$root" || exit 1
study="${1:-all}"
if [[ $# -gt 0 ]]; then shift; fi
case "$study" in
  all) studies=(P01 P02 P03 P04 P05 P06 P07 P08 P09);;
  P0[1-9]) studies=("$study");;
  *) echo "Usage: bash run-monte-carlo.sh {all|P01..P09} [--setup | runner options]" >&2; exit 2;;
esac
setup=false
list=false
for arg in "$@"; do
  [[ "$arg" == --setup ]] && setup=true
  [[ "$arg" == --list ]] && list=true
done
if "$setup" && [[ $# -ne 1 ]]; then
  echo "--setup prepares environments only; run separately" >&2; exit 2
fi
status=0
for id in "${studies[@]}"; do
  launcher="manuscripts/MSC-MUS-$id/monte_carlo.py"
  if [[ "$id" == P02 ]]; then
    if "$setup"; then echo "P02: NOT_APPLICABLE"; else python3 "$launcher" "$@" || status=1; fi
    continue
  fi
  venv=".venv/monte-carlo/$id"
  if "$setup"; then
    python3 -m venv "$venv" &&
      "$venv/bin/python" -m pip install -r "manuscripts/MSC-MUS-$id/analysis/requirements.txt" || status=1
    continue
  fi
  if "$list"; then python3 "$launcher" "$@" || status=1; continue; fi
  if [[ ! -x "$venv/bin/python" ]]; then
    echo "$id: prepare with bash run-monte-carlo.sh $id --setup" >&2
    status=1; continue
  fi
  "$venv/bin/python" "$launcher" "$@" || status=1
done
exit "$status"
