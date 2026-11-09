# Bootstrap installer reference

[`bootstrap`](bootstrap) contains the complete Debian Trixie amd64/arm64 installer.
For hardware, storage, networking and content preparation, follow the
[installation guide](docs/INSTALL.md). The [developer guide](docs/DEVELOPERS.md)
and individual container READMEs explain the services, but some inherited
instructions still describe the Raspberry Pi deployment paths.

This reference describes the current native Debian implementation. The menu and USB
workflow follow [`bootstrap_pi`](bootstrap_pi), the supplied Raspberry Pi
reference. Pi boot/display operations are replaced with Debian services and a
Firefox progress page; the existing content layout is retained.

## Start the installer

Use an installed **Debian 13 (Trixie), amd64 or arm64** system on a laptop, desktop or VM.
The installer checks the distribution, release, CPU architecture, systemd, and
presence of the source files before making installation changes. It does not
upgrade an older Debian installation to Trixie.

Run from this checkout on either supported architecture:

```bash
cd /path/to/Library-Creator_x86
./bootstrap --check
sudo ./bootstrap
```

The checkout can have another name and need not contain `.git`. Keep the root
`bootstrap` file and the complete `setup_library` directory together. The
script finds its source relative to its own location, not the current working
directory. Copying `bootstrap` alone does not provide the installation files.

You can also launch it by absolute path:

```bash
sudo /path/to/Library-Creator_x86/bootstrap --storage mounted
```

Installation needs internet access for Debian packages, image builds, application
packages and firmware downloads. Completed containers retain their downloaded
assets for offline use. Build on native AMD64 or ARM64 hardware with matching 64-bit Debian userspace;
32-bit ARM/i386 and cross-architecture emulation are not supported.

## Commands and options

Run `sudo ./bootstrap` for the interactive menu:

| Option | Action |
| --- | --- |
| 1) Fresh Install | Select USB/mounted/directory storage and Office preference, confirm, then install |
| 2) Reinstall / Upgrade | Confirm, run `git pull --ff-only` in this checkout, then rebuild with the updated installer |
| 3) Restart Install | Retry installation from this checkout; successful build layers may be reused |
| 4) System Status | Show progress, storage, systemd status and containers |
| 5) Install / Repair Clone | Install the host USB-content clone service and reconnect Downloads to its socket |
| 6) Configure Office | Enable or disable the installed Office image without a full rebuild |
| 7) Rebuild Containers | Refresh the native base, rebuild application images without cache, and refresh services |
| 8) Format Library USB | Select a partition, confirm erasure, and run the 30-second countdown |
| q) Quit | Leave the installer |

Command-line equivalents are available for scripted use:

```bash
sudo ./bootstrap --install --usb-device /dev/sdb1 --office no
sudo ./bootstrap --rebuild
sudo ./bootstrap --reinstall
sudo ./bootstrap --configure-office yes
sudo ./bootstrap --configure-office no
sudo ./bootstrap --install-clone
sudo ./bootstrap --format-usb --usb-device /dev/sdb1
sudo ./bootstrap --status
./bootstrap --check
```

`--storage directory|mounted` and the hotspot options remain supported.
`--yes` bypasses the operation-summary confirmation, **never USB erase
confirmation**. With no arguments, a terminal is required and the menu opens;
installation does not start simply by opening bootstrap.

Storage and Office choices are saved in `/etc/library/config.json` and reused
when omitted on later runs. On a fresh install, an already mounted `/Library`
selects mounted mode; otherwise directory mode is selected. Office defaults to
No. Hotspot settings are stored in NetworkManager's connection profile.

`--check` is a host preflight, not a complete installation test. It does not
build containers, check upstream download availability, check free disk space,
validate the USB mount configuration, or exercise Wi-Fi hardware.

## Content storage and the `/Library` symlink

Existing content remains under `/Library`. A selected partition already using
exFAT with the `Library_USB` label is preserved. Unprepared storage opens the
formatting confirmation flow; menu option 8 explicitly requests that flow
even for a prepared partition. A normal directory can be used for a
VM or a PC with content on its system disk:

```bash
sudo ./bootstrap --storage directory
```

For an attached content drive, mount it first and use mounted mode:

```bash
readlink -f /Library
findmnt -T /Library
mountpoint /Library
sudo ./bootstrap --storage mounted
```

A layout such as `/Library -> /media/pi/Library_USB` is supported. The installer
keeps the symlink and records its resolved destination. The service installer
reads the mounted filesystem's UUID, type and options, writes a persistent
entry in `/etc/fstab` with a backup, and adds `nofail`. It writes a systemd
override so Library startup depends on the resolved mount. It does not remount
the filesystem during this step.

Mounted mode checks the mount before installation and at normal service
startup. Missing storage stops startup instead of creating content on the root
filesystem. Directory mode does not require a separate mount. If you change
the symlink destination after installation, rerun bootstrap with the correct
storage mode so the saved path and systemd mount dependency are updated.

### Formatting confirmation and countdown

The USB selector shows `lsblk` output and suggests `/dev/sdb1`. Verify the
selected partition on your machine. The formatting screen shows its path,
size, filesystem and label. To proceed, type the complete phrase, for example
`ERASE /dev/sdb1`. You then have **30 seconds to cancel with Ctrl+C**.

The installer rechecks device identity after the countdown, refuses disks
containing system/home/boot/swap filesystems, and formats only the selected
partition as exFAT with label `Library_USB`. It does not erase the partition
table or guess a whole disk from `fdisk` output. A new filesystem receives the
bundled `Library_USB.tar` seed content. Bootstrap also seeds an empty system
directory or already mounted disk, ignoring `lost+found` when checking emptiness,
before building and starting services. Existing content is not overwritten by
that archive during a normal install. Formatting cannot be approved through
`--yes` or noninteractive input.

The standard content directories are `library`, `web`, `wiki`, `music`,
`calibre`, `maps`, and `documents`. Existing databases and content are retained;
the runtime playbook can initialize missing music and Calibre databases from
the bundled defaults. See the [usage guide](docs/USAGE.md) and
[downloader guide](setup_library/files/containers/data_download/README.md) for
adding content. The usage guide's `library` hostname assumes you configured
that hostname; this installer preserves the host's existing name.

## Ethernet, Wi-Fi and HDMI

Normal installation uses Debian's existing network connections. Ethernet and
Wi-Fi interface names do not have to be `eth0` and `wlan0`. A VM can operate
with a virtual Ethernet NIC and no Wi-Fi hardware. A bridged NIC provides LAN
access to the VM; NAT may require hypervisor port forwarding.

The optional hotspot uses an explicitly selected AP-capable Wi-Fi adapter:

```bash
nmcli device status
sudo ./bootstrap --hotspot-interface wlp2s0
```

This creates or updates the `library-hotspot` NetworkManager profile with SSID
`library` with no password, address `10.1.1.1/24`, and shared DHCP/DNS.
After installation, use **Library Wi-Fi** on the root desktop or in the
applications menu for routine switching between hotspot and internet Wi-Fi.
The executable `/usr/local/bin/library_wifi` opens local-only controls at
`http://127.0.0.1:4830/wifi/`. There is no homepage control. GNOME installs
Desktop Icons NG to display the shortcut. Ethernet remains connected. It replaces the selected
adapter's client connection with AP mode. Use a console or Ethernet session for
that change. The inherited hotspot container is not built or started by this
native Debian path. See [network configuration](docs/INSTALL.md#ethernet-wi-fi-and-vms).

HDMI uses Debian's existing desktop. Bootstrap opens Firefox in the active
graphical session on a local progress file. No framebuffer or
`displayit` is needed. Monitor resolution remains controlled by Debian.

## Firefox installation progress

The page is `file:///root/progress.html`. It reloads every
**15 seconds**, showing the current stage and recent output throughout package
installation, USB preparation, each container build and service startup. The
output panel shows only the latest **30 lines** and scrolls to its bottom on
each reload while the page stays at the top with the stage heading visible.
The terminal and saved log retain the full output. The
final success screen links to `http://localhost`; a failure or cancellation
stays on a failure screen with the stage and error output instead of claiming
success. The same page reports Office, Clone and formatting operations.

Firefox runs as the logged-in desktop user, including root after autologin is configured. Installation over SSH
can open the page on the machine's existing graphical session. If there is no
single active graphical session, installation continues in the terminal and
prints the file URL for opening after login. A minimal/headless install does
not automatically acquire a desktop. Firefox is installed if needed.
For a non-root desktop, the installer grants that user traversal permission on `/root` using
an ACL, so Firefox can read `progress.html` without listing the directory.
Firefox launch errors are saved in `/var/log/library-installer/firefox.log`.

Formatting and other confirmations are answered in the installer terminal;
the HTML page is a progress display. Full output is saved in
`/var/log/library-installer/install.log`; the machine-readable status is
`/root/library-install-state.json`.

## Desktop autologin after installation

After the Library services start successfully, a full install or rebuild sets
the **root password to `library`** and configures the existing desktop login
manager to log in as **root** on the next boot. GDM (GNOME), LightDM and SDDM
are supported. A console-only installation stays headless; it needs an installed
desktop/login manager for this feature.

Root's desktop startup entry opens Firefox immediately on
`file:///run/library-startup/progress.html`. This page shows the current Ansible
task while the USB mount and services start, refreshes every two seconds, and
redirects to **`http://localhost/`** after startup succeeds. Errors remain visible
instead of redirecting. The page works before nginx starts. The browser uses
the dedicated Firefox profile
`/root/.mozilla/firefox/library`. The installer keeps the current desktop session
open so you can see its final progress screen. Successful installs and rebuilds
schedule a reboot within one minute; the browser announces it. Keep power
connected. Failed installations do not schedule a reboot.

The helper `setup_library/configure_desktop.py` backs up changed login settings
as `*.before-library`. It changes the display manager's autologin settings and
its root exclusion in the autologin PAM file, keeping the other account/session
checks. Firefox starts through `/root/.config/autostart/library-browser.desktop`
and `/usr/local/bin/library_browser`.

To apply this feature to an existing installation without rebuilding images:

```bash
sudo ansible-playbook -i localhost, -c local setup_library/install_x86.yml --tags desktop_config
```

Configuration references: [GNOME automatic login](https://help.gnome.org/system-admin-guide/login-automatic.html),
[LightDM configuration](https://wiki.freedesktop.org/www/Software/LightDM/CommonConfiguration/),
and [Debian SDDM settings](https://manpages.debian.org/trixie/sddm/sddm.conf.5.en.html).

## Optional Office add-on

WordCraft, DeckCraft and GridCraft share a browser desktop and require a
**keyboard and a pointing device** on the client. When enabled, open
`https://<machine-IP>:3001`; it uses a self-signed certificate. Documents are
stored in `/documents` inside the container, backed by `/Library/documents`.

| Choice / tags | Startup behavior |
| --- | --- |
| Yes: `localhost/craft_apps:latest` | Start the Office desktop |
| No: `localhost/craft_apps:dontrun` | Stop any existing Office container and skip startup |
| Both tags | `:dontrun` wins; Office remains disabled |
| Neither tag | Skip Office |

The image is built even when Office is declined so it remains available for
later offline use. Choose **6) Configure Office**, or run:

```bash
sudo ./bootstrap --configure-office yes
sudo ./bootstrap --configure-office no
```

Save open Office documents first. This retags the installed image, saves the
choice, runs only the Office startup tasks, and refreshes the web frontend.
It does not rebuild images or remove documents/settings. The full installer
still accepts `--office yes|no` to choose the state during installation.
See the [Office guide](setup_library/files/containers/craft_apps/README.md).

## Installation stages

The current native Debian implementation runs these stages in one invocation. There are
no First/Second/Third Boot flags or intermediate installer reboots. A successful
run schedules one reboot within one minute after all setup steps finish.

### 1. Preflight and host packages

Validate Debian Trixie, matching amd64/arm64 hardware and userspace, and the checkout, require root for installation,
and acquire `/run/lock/library-install.lock`. Read saved choices and check the
selected mounted-storage mode. Install Podman, Ansible, Python dependencies,
rsync, curl, jq, Firefox, Git, certificates and filesystem utilities using Debian packages.

### 2. Prepare USB storage, stage the checkout and build containers

Prepare the selected USB partition as described above, or verify the selected
existing mount/directory. Copy the selected checkout to `/opt/library-creator`, excluding `.git`, Python
cache directories and `rasbase_parts`. Seed empty selected storage from
`Library_USB.tar`, then run `build_pods.sh` from the staged copy.

The builder first prepares `localhost/rasbase_master:latest` from the official
`docker.io/library/debian:trixie-slim` image for the detected `linux/amd64` or `linux/arm64` platform. It verifies the
image's architecture and Debian release. An existing compatible base is reused;
an incompatible base is rejected with instructions to refresh it. ARM archive
parts are never reconstituted into either native base.

Application Containerfiles use that base except LMS and Office, which use their
own upstream images. Kiwix selects the pinned x86-64 or aarch64 archive with its own SHA-256 check;
PMTiles selects the matching x86-64 or arm64 release asset. The nested GraphHopper image is built
as `localhost/library_maps-graphhopper:11`. Podman uses Docker image format to
preserve health checks; installing Docker is unnecessary.

Both `meshtastic` and `meshflash` build contexts are required. Meshflash captures
firmware during the image build; installing Library does not flash a connected
radio. StreetZim, the music player and downloader are also built. See the
[Meshtastic](setup_library/files/containers/meshtastic/README.md),
[meshflash](setup_library/files/containers/meshflash/README.md), and
[maps](setup_library/files/containers/library_maps/README.md) guides.

### 3. Save settings and configure host services

After the image builder succeeds, write `/etc/library/config.json`. If requested,
install/configure the NetworkManager hotspot. Run `setup_library/install_x86.yml`
to persist mounted storage, install host helpers and systemd units, copy the
runtime playbook to `/root/start_library.yml`, and start the services. Install
`library-wifi.service` and the local desktop launcher, configure desktop startup,
then schedule the completion reboot. The Wi-Fi service runs on the host and does
not require a hotspot container.

The numbered `01_install_ansible.yml` and `99_reinstall_pods.yml` now forward to
this native Debian service installer. They are not equivalents of their original Pi
workflows and require the configuration and images prepared by bootstrap.

### 4. Normal service startup

`start_library.service` runs `/root/start_library.yml` through the Debian
`/usr/bin/ansible-playbook`. It checks storage, prepares content directories,
checks the Podman bridge, and starts the content services. The fixed service
addresses require Podman's `10.88.0.0/16` network.

The radio check selects Meshtastic or firmware setup on port 8086. GPS and USB
radio use in a VM require USB passthrough. Open `http://localhost` locally or
`http://<machine-IP>` over the network. Links use the browser's hostname rather
than assuming a hotspot address.

## Reinstalling, retrying and refreshing the base

Rerun bootstrap from the intended checkout after fixing a failed step. Choose **Restart Install** to retry the current source. Choose **Rebuild
Containers** for a fresh image rebuild, or **Reinstall / Upgrade** to update
a Git checkout first with `git pull --ff-only`. A missing Git checkout or failed
pull stops before rebuilding. There are no numbered Pi boot stages to resume.

To refresh the native base and rebuild applications:

```bash
cd /path/to/Library-Creator_x86
sudo bash setup_library/files/containers/update_rasbase.sh
sudo ./bootstrap
```

`update_rasbase.sh` and `reconstitute.sh` are compatibility entry points for the
native base builder. They no longer perform Pi archive reconstruction or
release-by-release upgrades. Existing application images are not force-removed
before rebuilding, but successful builds replace their tags as they finish.
The workflow is not transactional: an eventual failure does not roll back
earlier image changes, and the Office build helper can already have changed
its tag or stopped its container.

## Clone support

Fresh installs include the host USB-content cloning service. On an existing
Library, choose **5) Install / Repair Clone** or `sudo ./bootstrap --install-clone`.
The targeted repair checks that transfers and clones are idle, installs the
helper/socket, recreates only the downloader with its socket, and verifies that
the socket is visible inside the container. Existing USB clone confirmation,
capacity, device-identity and destination-removal checks remain in place.

On both architectures, the service permits **Library USB content cloning only**. It protects
mounted Debian boot/EFI filesystems without requiring `/boot/firmware`.
BIOS/UEFI operating-system cloning is not implemented; selecting OS cloning
returns an explicit unsupported-layout error. See the
[Clone guide](setup_library/files/containers/data_download/docs/CLONE.md).

## Installed files and logs

| Path | Purpose |
| --- | --- |
| Your `Library-Creator_x86` checkout | Source used for this installation |
| `/opt/library-creator/` | Staged source and container build contexts |
| `/etc/library/config.json` | Storage mode, resolved content path and Office preference |
| `/etc/fstab` | Persistent content mount entry in mounted mode; backed up before modification |
| `/etc/systemd/system/start_library.service.d/storage.conf` | Dependency on the resolved content mount |
| `/root/start_library.yml` | Deployed runtime startup playbook |
| `/usr/local/bin/library_control.py` | Host restart socket handler |
| `/usr/local/bin/library_restart` | Graceful host restart helper |
| `/usr/local/bin/library_shutdown` and `library_shutdown.py` | Host shutdown helper and confirmation page |
| `/run/library-control/control.sock` | Downloader's host restart socket |
| `/Library/` | Content directory, mounted storage, or symlink to mounted storage |

Bootstrap writes progress to both the terminal and
`/var/log/library-installer/install.log`. The HTML progress page and JSON state
remain available after the operation finishes. Use **4) System Status** or
`sudo ./bootstrap --status` to inspect them alongside the running services.

Runtime checks:

```bash
sudo systemctl status start_library shutdown_library library-control.socket
sudo journalctl -u start_library -b
sudo podman ps -a
sudo podman logs data_download
```

## Troubleshooting

- **Wrong OS or architecture:** use Debian Trixie amd64 or arm64 with matching 64-bit userspace. This path does not
  upgrade the host or configure cross-architecture emulation.
- **Content disk missing:** inspect `readlink -f /Library`, `findmnt -T /Library`
  and `/etc/fstab`. Restore the expected mount before restarting Library.
- **Base image has the wrong architecture:** refresh it with
  `update_rasbase.sh`, then rerun bootstrap. Loading the copied ARM tar parts
  cannot solve an architecture mismatch.
- **Container build failed:** inspect the build summary and the first error
  for that image. Confirm available disk space and access to package/release
  servers. Later reruns may reuse successful build layers.
- **Ansible or service startup failed:** inspect the task failure and
  `journalctl -u start_library -b`; successful package/image builds alone do
  not establish that installation completed.
- **Frontend unavailable from another computer:** use the machine's actual IP,
  check its firewall and VM NIC mode, and inspect the webserver container.
- **Radio setup appears instead of messaging:** the radio must answer the
  Meshtastic protocol; a USB serial device alone is insufficient. Check
  firmware and passthrough with the service guides linked above.
- **Firefox did not open:** log into the Debian graphical desktop and open
  `file:///root/progress.html`. The terminal and saved log
  remain available without a desktop; check whether multiple sessions are active.
