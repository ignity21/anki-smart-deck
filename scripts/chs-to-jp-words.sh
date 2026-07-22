#!/usr/bin/env bash
WORK_DIR="$(dirname "$(readlink -f "$0")")"
ankinote word batch --target Japanese --native "Chinese(Simplified)" -f "$WORK_DIR/jp/words.txt"
