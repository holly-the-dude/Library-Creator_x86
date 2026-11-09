#!/usr/bin/env bash
# NetworkManager owns both the AP and its DHCP/DNS. No wlan0 assumption.
set -euo pipefail
interface=${1:?Wi-Fi interface required}
[[ "$(LC_ALL=C nmcli -g GENERAL.TYPE device show "$interface")" == wifi ]] || {
    echo "$interface is not a NetworkManager Wi-Fi device." >&2; exit 1;
}
[[ "$(LC_ALL=C nmcli -g WIFI-PROPERTIES.AP device show "$interface")" == yes ]] || {
    echo "$interface does not support access-point mode." >&2; exit 1;
}
profile=library-hotspot
if nmcli -g connection.id connection show "$profile" >/dev/null 2>&1; then
    [[ "$(nmcli -g connection.type connection show "$profile")" == 802-11-wireless ]] || {
        echo 'library-hotspot already exists and is not a Wi-Fi profile.' >&2; exit 1;
    }
    # Remove any previous WPA/WEP configuration: library is an open network.
    nmcli connection modify "$profile" remove 802-11-wireless-security
else
    nmcli connection add type wifi ifname "$interface" con-name "$profile" ssid library
fi
nmcli connection modify "$profile" connection.interface-name "$interface" \
    connection.autoconnect yes connection.autoconnect-priority 100 \
    802-11-wireless.ssid library 802-11-wireless.mode ap \
    ipv4.method shared ipv4.addresses 10.1.1.1/24 ipv6.method disabled
nmcli connection up "$profile" ifname "$interface"
