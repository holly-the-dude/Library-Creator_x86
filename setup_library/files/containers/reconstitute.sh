#!/usr/bin/env bash
# ARM split archives cannot be reconstituted into an x86 image.
set -euo pipefail
exec bash "$(dirname -- "${BASH_SOURCE[0]}")/rasbase/build_rasbase.sh" "$@"
