#!/usr/bin/env bash
WORK_DIR="$(dirname "$(readlink -f "$0")")"
ankinote phrase batch -f "$WORK_DIR/us/phrases.txt"
