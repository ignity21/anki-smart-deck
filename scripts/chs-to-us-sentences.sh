#!/usr/bin/env bash
WORK_DIR="$(dirname "$(readlink -f "$0")")"
ankinote sentence batch -f "$WORK_DIR/us/sentences.txt"
