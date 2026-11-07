#!/usr/bin/env bash
# Build a fresh native Trixie base; never load the copied ARM rasbase_parts.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
. "$SCRIPT_DIR/../architecture.sh"
architecture=$(library_native_arch)
image=localhost/rasbase_master:latest
verify_base() {
    podman run --rm --network none --env "LIBRARY_EXPECTED_ARCH=$architecture" --entrypoint /bin/sh "$1" -ec \
        '. /etc/os-release; test "$ID:$VERSION_CODENAME:$(dpkg --print-architecture)" = "debian:trixie:$LIBRARY_EXPECTED_ARCH"'
}
if [[ "${1:-}" != --refresh ]] && podman image exists "$image"; then
    [[ "$(podman image inspect --format '{{.Architecture}}' "$image")" == "$architecture" ]] || {
        echo "Existing rasbase_master is not $architecture; run build_rasbase.sh --refresh." >&2; exit 1;
    }
    verify_base "$image"
    exit 0
fi
candidate="localhost/library-base-build:$$"
trap 'podman rmi "$candidate" >/dev/null 2>&1 || true' EXIT
podman build --platform "linux/$architecture" --pull=always --format docker \
    -t "$candidate" -f "$SCRIPT_DIR/Containerfile.base" "$SCRIPT_DIR"
verify_base "$candidate"
podman tag "$candidate" "$image"
echo "Ready: $image (Debian Trixie $architecture)"
