#!/bin/sh
# Double-click in Finder, or run this file from any terminal directory.
cd -- "$(dirname -- "$0")" || exit 1
exec sh './Start Solar Sim.sh' "$@"
