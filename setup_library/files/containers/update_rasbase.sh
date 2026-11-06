#!/usr/bin/env bash
# Compatibility entry point: rebuild from official Debian, not Pi archives.
set -euo pipefail
exec bash "$(dirname -- "${BASH_SOURCE[0]}")/rasbase/build_rasbase.sh" --refresh
