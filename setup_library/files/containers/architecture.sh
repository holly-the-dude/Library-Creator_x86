#!/usr/bin/env bash
# Host architecture -> Debian/OCI name. Builds are native, never cross-emulated.
library_native_arch() {
    local machine
    machine=$(uname -m) || return
    case "$machine" in
        x86_64|amd64) printf 'amd64\n' ;;
        aarch64|arm64) printf 'arm64\n' ;;
        *) printf 'Unsupported architecture: %s. Use 64-bit amd64 or arm64.\n' "$machine" >&2; return 1 ;;
    esac
}
