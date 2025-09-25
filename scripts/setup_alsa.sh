#!/usr/bin/env bash
set -euo pipefail

echo "Listing audio devices (arecord -l / aplay -l)"
arecord -l || true
aplay -l || true

echo "Use alsamixer to set default input/output if needed."

