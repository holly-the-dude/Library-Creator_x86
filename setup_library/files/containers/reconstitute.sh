#!/usr/bin/env bash
# Always build a native Trixie base; copied Pi archives are not used on either architecture.
set -euo pipefail
exec bash "$(dirname -- "${BASH_SOURCE[0]}")/rasbase/build_rasbase.sh" "$@"
