#!/usr/bin/env bash
WORK_DIR="$(dirname "$(readlink -f "$0")")"
ankinote phrase batch --target Japanese --native "Chinese(Simplified)" -f "$WORK_DIR/jp/phrases.txt"
