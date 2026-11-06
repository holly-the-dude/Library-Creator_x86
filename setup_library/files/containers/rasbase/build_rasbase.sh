#!/usr/bin/env bash
# Build a fresh native Trixie base; never load the copied ARM rasbase_parts.
set -euo pipefail
[[ "$(uname -m)" == x86_64 ]] || { echo 'Build on an amd64 host.' >&2; exit 1; }
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
image=localhost/rasbase_master:latest
if [[ "${1:-}" != --refresh ]] && podman image exists "$image"; then
    [[ "$(podman image inspect --format '{{.Architecture}}' "$image")" == amd64 ]] || {
        echo 'Existing rasbase_master is not amd64; run build_rasbase.sh --refresh.' >&2; exit 1;
    }
    podman run --rm --network none --entrypoint /bin/sh "$image" -ec \
        '. /etc/os-release; test "$ID:$VERSION_CODENAME:$(dpkg --print-architecture)" = debian:trixie:amd64'
    exit 0
fi
candidate="localhost/library-base-build:$$"
trap 'podman rmi "$candidate" >/dev/null 2>&1 || true' EXIT
podman build --platform linux/amd64 --pull=always --format docker \
    -t "$candidate" -f "$SCRIPT_DIR/Containerfile.base" "$SCRIPT_DIR"
podman run --rm --network none --entrypoint /bin/sh "$candidate" -ec \
    '. /etc/os-release; test "$ID:$VERSION_CODENAME:$(dpkg --print-architecture)" = debian:trixie:amd64'
podman tag "$candidate" "$image"
echo "Ready: $image (Debian Trixie amd64)"
