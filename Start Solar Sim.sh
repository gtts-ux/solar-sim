#!/bin/sh
# Run from anywhere, including paths containing spaces.
solar_app_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
export PYTHONDONTWRITEBYTECODE=1
for solar_python in python3 python; do
    if command -v "$solar_python" >/dev/null 2>&1 &&
       "$solar_python" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
        "$solar_python" -B "$solar_app_dir/solar_sim.py" "$@"
        exit "$?"
    fi
done
printf '%s\n' 'Solar Sim requires Python 3.10 or newer.' 'Install Python from https://www.python.org/downloads/ and try again.'
exit 1
