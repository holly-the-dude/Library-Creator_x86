# Install on Debian 13 (Trixie), amd64 or arm64

Use an existing Debian **amd64 or arm64** install on a PC, ARM64 machine or VM.
The installer detects the native CPU and requires matching 64-bit Debian userspace.
Neither i386 nor armhf/32-bit ARM is supported. Install and boot Debian first;
this does not create board-specific boot media or add Raspberry Pi display drivers.

The same checkout and root `bootstrap` entry point work on either architecture:

| Host CPU / Debian architecture | Container platform | Kiwix binary | PMTiles binary |
| --- | --- | --- | --- |
| x86_64 / amd64 | linux/amd64 | x86_64 | x86_64 |
| aarch64 / arm64 | linux/arm64 | aarch64 | arm64 |

`Library-Creator_x86` and `setup_library/install_x86.yml` retain their filenames
for compatibility; both architectures use them. Build the containers on the
destination architecture. An existing base image from the other architecture
is rejected; use Rebuild Containers to create a fresh native base. The copied
Pi `rasbase_parts` are ignored on ARM64 as well as AMD64.

Debian's installer handles UEFI/BIOS, disks, firmware, Ethernet, Wi-Fi, and HDMI.
The Library installer does not upgrade the host distribution.

Internet access is required for the initial image builds. Allow substantial
free disk space for container layers and content; the Office image and routing
imports are especially large. Routing memory depends on the chosen OSM region.

## Install

Copy this complete checkout to the target machine and run from that copy:

```bash
./bootstrap --check
sudo ./bootstrap
```

`--check` validates the host without installing packages. `sudo ./bootstrap`
opens the interactive menu. Choose Fresh Install, select the USB partition
(`/dev/sdb1` on libraryd) and Office preference, then confirm. Installation stages
this checkout under `/opt/library-creator`, builds the base and applications,
installs systemd units, and starts the Library. It requires no boot-stage cron
jobs. After successful setup, it schedules a reboot within one minute and shows
the reboot notice in the browser. Failed installs do not schedule a reboot. A failed image build stops installation before the
new host configuration and services are installed.

Open `http://localhost` on the machine, or `http://<machine-IP>` from another
computer. The existing hostname is preserved. Use `hostname -I` to see addresses.
Content can be added through Downloads at `http://<machine-IP>:4826`.

## Storage

The default is a normal `/Library` directory on the current filesystem:

```bash
sudo ./bootstrap --storage directory
```

For a separate content disk, mount it at `/Library` yourself (or symlink
`/Library` to the mounted directory), and select mounted storage:

```bash
sudo ./bootstrap --storage mounted
```

An already mounted `/Library` is detected automatically on a fresh install.
Mounted mode refuses to start without that mount. The installer preserves a
`/Library` symlink, records the resolved filesystem mount by UUID in `/etc/fstab`
(with a backup), and orders startup after that mount. Existing mount options,
including exFAT ownership, are retained. Filesystems such as ext4
and exFAT work through the host mount; no `/dev/sda1` or USB-only assumption is
made. The installer formats only an explicitly selected partition after a typed
erase confirmation and a 30-second countdown. Already-labelled Library_USB
content is preserved on normal install. It never guesses an expendable disk. USB-content cloning is available through Downloads and the Install / Repair
Clone menu. OS cloning still requires separate UEFI/BIOS support.

Empty storage, including a filesystem containing only `lost+found`, receives
`setup_library/files/Library_USB.tar` before services create folders or databases.
This applies to system directories, already mounted disks, and freshly formatted
USB storage. The archive includes sample music, a starter PMTiles map, and a
small wiki archive. Nonempty storage is preserved and is not automatically
merged with the bundled archive.

The installer and startup playbook grant read/traverse access to public files
under `/Library/library`, retaining ownership and existing write permissions.
Private application data elsewhere under `/Library` is not changed. This repairs
PDF HTTP 403 errors from older downloaded collection directories.

Existing content is retained. The familiar folders include `library`, `wiki`,
`music`, `calibre`, `maps`, and `documents`. The downloader creates its own
additional directories as needed. `/etc/library/config.json` remembers storage
and Office choices for subsequent installs.

## Ethernet, Wi-Fi and VMs

Default installation uses whichever connections Debian already has. It does
not disable NetworkManager, rewrite `/etc/network/interfaces`, rename network
interfaces, change the hostname, or require an adapter named `eth0` or `wlan0`.
A laptop can use Ethernet and Wi-Fi simultaneously as configured by Debian.

For a VM, a bridged virtual NIC lets other LAN clients connect to the VM's IP.
With NAT, configure forwarding in the hypervisor for the ports you use. No
Wi-Fi passthrough is needed unless the VM itself must broadcast a hotspot.
USB GPS and radios need hypervisor USB passthrough to be visible inside a VM.

Optional Wi-Fi hotspot (run from a console or Ethernet connection):

```bash
nmcli device status
sudo ./bootstrap --hotspot-interface wlp2s0
```

Use the actual Wi-Fi interface name. The adapter must support AP mode.
NetworkManager creates the `library-hotspot` connection with open SSID
`library` (no password) and address `10.1.1.1/24`, with shared DHCP/DNS.
Existing hotspot security is removed when hotspot mode is configured. Selecting
an adapter replaces its active client connection with the hotspot; the same
adapter is not used as an internet client at the same time. Other connections
are preserved. Ensure `10.1.1.0/24` is not already used by your LAN or VPN.

For routine switching after installation, open **Library Wi-Fi** on the root
desktop or in the applications menu. Select the adapter and hotspot or internet
mode. Internet mode accepts the network SSID and password; saved credentials can
be reused. The selected mode persists after reboot, and failed switches attempt
to restore the previous connection. Ethernet is unchanged. GNOME receives
Desktop Icons NG so the executable shortcut is visible after reboot.

The controls listen only on `127.0.0.1:4830`, not on the homepage or the LAN.
Without a Wi-Fi adapter, the local page explains that hardware is required.
Host NetworkManager provides the hotspot; the inherited hotspot container is
intentionally skipped during builds. See [Wi-Fi usage](USAGE.md#switch-wi-fi-modes-native-debian-version).

For manual recovery, stop broadcasting with:

```bash
sudo nmcli connection modify library-hotspot connection.autoconnect no
sudo nmcli connection down library-hotspot
```

Connect to your normal Wi-Fi profile through Debian afterward. Hotspot hardware
support must be checked on the actual laptop/desktop; an Ethernet-only VM
cannot validate radio behavior.

## HDMI

Use Debian's normal HDMI desktop and browser, opening `http://localhost`.
During installation Firefox opens a local HTML progress page on the logged-in
desktop. It refreshes every 15 seconds through to success or failure:
`file:///root/progress.html`. A minimal/headless Debian
install remains a console unless you install a Debian desktop yourself.
After successful installation, existing GDM/GNOME, LightDM or SDDM desktops
are configured to autologin as **root**, with password **`library`**, on the next
boot. Firefox opens a local startup page immediately, showing which services
Ansible is starting. The page refreshes every two seconds and opens
**`http://localhost/`** after startup succeeds; failures remain visible.
The **Library** desktop shortcut opens the homepage directly. The current desktop is left open through the
final installer screen, which announces the automatic reboot within one minute.
Keep power connected while the machine restarts. See [desktop autologin details](../bootstrap.md#desktop-autologin-after-installation).
Pi TFT, touchscreen, GPIO, SPI overlays and framebuffer splash services are
excluded from this installation path on both architectures.

## Images and rebuilds

`rasbase_parts` and the bundled ARM Kiwix archive are inherited files; the native
builds do not load them. Kiwix is downloaded and checksum-verified for the target
architecture. The shared base is freshly built from the official Debian Trixie
slim image and checked for Debian, Trixie, and the native amd64/arm64 architecture
before use.
To refresh it and rebuild the applications:

```bash
cd /path/to/Library-Creator_x86
sudo bash setup_library/files/containers/update_rasbase.sh
sudo ./bootstrap
```

`build_pods.sh` also prepares/verifies the base before building applications.
The local base tag stays `localhost/rasbase_master:latest` for compatibility
with the existing Containerfiles. Native amd64 or arm64 builds are required; downloaded executables and upstream images match the host.

Office is built and retained as `localhost/craft_apps:dontrun` when declined.
Use `sudo ./bootstrap --office yes` or `--office no` to change the remembered
choice. Existing images are not force-removed before rebuilding. The Reinstall / Upgrade menu explicitly runs `git pull --ff-only` before
rebuilding. Rebuild Containers uses current source without Git. Neither action
performs global Podman cleanup. Configure Office enables/disables the installed
image without rebuilding; use `--configure-office yes|no` for its CLI equivalent.

## Services and ports

| Service | Host port |
| --- | --- |
| Library | 80 |
| Downloads | 4826 |
| Kiwix | 6902 |
| Maps | 8080 |
| E-books | 8083 |
| LMS music | 9099 (also linked through Library) |
| Music player | 2001 |
| Meshtastic / firmware setup | 8086 |
| StreetZim | 8093 |
| Office, when enabled | 3001 HTTPS |
| Host shutdown/restart page | 9999 |

Services bind to host interfaces for LAN use. Content-dependent services start
when their content exists. Configure any host firewall or VM port forwarding
for the services you intend to access. The service containers retain fixed
addresses on Podman's `10.88.0.0/16` bridge; the installer refuses an incompatible
existing `podman` bridge instead of replacing another workload's network.

```bash
sudo systemctl status start_library
sudo journalctl -u start_library -b
sudo podman ps -a
sudo podman logs data_download
sudo systemctl restart start_library
```

Shutdown and restart controls affect the whole host, including a PC or VM.
Use this stack on a trusted local network.
