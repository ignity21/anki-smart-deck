#!/usr/bin/env bash
WORK_DIR="$(dirname "$(readlink -f "$0")")"
ankinote word batch -f "$WORK_DIR/us/words.txt"
