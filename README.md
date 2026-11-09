# Library-Creator_x86 — Debian Trixie AMD64 / ARM64

**Your personal, portable digital library — on your own Debian machine.**

[![Donate](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal)](https://www.paypal.com/ncp/payment/T8MGW39TXCR4J)

> **Prefer a ready-made Library device?** Explore the pre-configured kits at
> **[librarydepository.com](https://librarydepository.com)**.
> Those kits are an alternative to installing this Debian version on your own hardware.

Build an offline Library using **Debian 13 (Trixie), amd64 or arm64**, on a
laptop, desktop, ARM64 machine, or virtual machine. This checkout retains its
`Library-Creator_x86` name but builds natively for either architecture. The original
Raspberry Pi checkout is separate and is not used by this installer.

Library-Creator_x86 brings Wikipedia, music and audiobooks, e-books, offline
maps, optional office apps, and your own files together in a browser. Add a USB
Meshtastic radio for mesh messaging. Stored content works without internet access:
keep your Library to yourself or share it with people nearby.

Use Ethernet, your existing network, or an AP-capable Wi-Fi adapter broadcasting
the open **`library`** network. Hotspot visitors connect without a password and
open **`http://10.1.1.1/`**. The **Library Wi-Fi** desktop shortcut switches between
hotspot and internet Wi-Fi modes.

Inspired by accessible information where internet access is limited, including
projects such as [Survivor Library](https://www.survivorlibrary.com).

## Perfect for

- <img src="docs/icons/png/camping.png" alt="" height="20"> **Camping trips** — bring books, maps, music, and practical information.
- <img src="docs/icons/png/roadtrip.png" alt="" height="20"> **Road trips** — share offline entertainment and maps with fellow travelers.
- <img src="docs/icons/png/class.png" alt="" height="20"> **Classes and presentations** — share resources with a room without relying on internet access.
- <img src="docs/icons/png/rural.png" alt="" height="20"> **Remote areas** — keep useful information available where connectivity is limited.
- <img src="docs/icons/png/emergency.png" alt="" height="20"> **Emergencies** — access saved reference material during outages.
- <img src="docs/icons/png/private.png" alt="" height="20"> **Personal collections** — keep your files on hardware you control.
- <img src="docs/icons/png/tech.png" alt="" height="20"> **Tech projects** — give a spare laptop, desktop, or ARM64 machine a useful job.

## What’s included

Open services from the Library homepage. On the host, use `http://localhost/`;
on your LAN, use `http://<machine-IP>/`. The addresses below apply in hotspot mode.

| Service | What it provides | Hotspot address |
| --- | --- | --- |
| <img src="docs/icons/png/web.png" alt="" height="20"> Web hub | Service menus and your saved files | `http://10.1.1.1/` |
| <img src="docs/icons/png/wiki.png" alt="" height="20"> Wikipedia | Offline Kiwix ZIM collections | `http://10.1.1.1:6902/` |
| <img src="docs/icons/png/music.png" alt="" height="20"> Music library | LMS music and audiobooks | `http://10.1.1.1/music` |
| <img src="docs/icons/svg/music_player.svg" alt="" height="20"> iPod-style player | Click-wheel music player with Purple and Classic skins | `http://10.1.1.1:2001/` |
| <img src="docs/icons/png/ebooks.png" alt="" height="20"> E-books | Calibre-Web reader and library | `http://10.1.1.1:8083/` |
| <img src="docs/icons/png/maps.png" alt="" height="20"> OpenStreetMap | PMTiles maps and optional GraphHopper directions | `http://10.1.1.1:8080/` |
| <img src="docs/icons/svg/street_zim.svg" alt="" height="20"> StreetZim | Regional ZIM map archives and shared USB GPS feed | `http://10.1.1.1:8093/` |
| <img src="docs/icons/svg/meshtastic.svg" alt="" height="20"> Meshtastic | USB radio messaging or offline firmware setup | `http://10.1.1.1:8086/` |
| <img src="docs/icons/svg/data_download.svg" alt="" height="20"> Downloads | Download maps and collections; upload music, files, and ebooks | `http://10.1.1.1:4826/` |
| <img src="docs/icons/png/hotspot.png" alt="" height="20"> Wi-Fi hotspot | Host NetworkManager; open SSID `library` | `http://10.1.1.1/` |
| Optional Office | WordCraft, DeckCraft, and GridCraft; keyboard and pointing device required | `https://10.1.1.1:3001/` |

The homepage groups both players under **Music** and both map viewers under
**Maps**. Unavailable choices show **Not running**. Both music players read
`/Library/music`. A USB radio connects to the Library host, not the browser device.

## Documentation

| Guide | Start here to… |
| --- | --- |
| <img src="docs/icons/png/usage.png" alt="" height="18"> **[Usage Guide](docs/USAGE.md)** | Connect, browse, listen, read, download content, and use the desktop Wi-Fi controls. |
| <img src="docs/icons/png/install.png" alt="" height="18"> **[Installation Guide](docs/INSTALL.md)** | Set up this native Debian version on amd64 or arm64 hardware or a VM. |
| <img src="docs/icons/png/developer.png" alt="" height="18"> **[Developer Guide](docs/DEVELOPERS.md)** | Understand the host services, native container builds, and service integration. |

Also see the [bootstrap reference](bootstrap.md), [change log](ChangeLog.md),
[remaining validation](TODO.md), and individual
[service READMEs](setup_library/files/containers/).

## Install this Debian version

```bash
./bootstrap --check
sudo ./bootstrap
```

Start from an installed Debian system with internet access. Successful installs
and rebuilds schedule a reboot within one minute; Firefox displays the reboot
notice. Failed installations do not schedule a reboot. After startup,
open `http://localhost` on its desktop or `http://<machine-IP>` from another
machine. [Installation and configuration](docs/INSTALL.md) covers storage,
Ethernet, Wi-Fi, VMs, and the optional hotspot.

- HDMI uses Debian's existing desktop or console. Pi TFT, GPIO, touchscreen,
  framebuffer splash, and Pi boot configuration are not installed.
- After installation, supported desktops autologin as root (password `library`)
  on the next boot. Firefox immediately shows Ansible startup progress, then
  opens `http://localhost/` when services are ready. The **Library** desktop
  shortcut opens the homepage directly.
- Ethernet stays configured by Debian. Use **Library Wi-Fi** on the root desktop
  or in the applications menu to switch an adapter between internet Wi-Fi and
  an open **`library`** hotspot, with no password. Hotspot clients open
  **`http://10.1.1.1/`**. The controls are local to the desktop; there is no
  homepage Wi-Fi control. A VM needs only a virtual NIC.
- `/Library` can be a directory on the system disk or a separately mounted disk.
  The menu restores USB formatting with explicit erase confirmation and a
  countdown; normal installs preserve an existing Library_USB partition. Empty
  storage is seeded from `setup_library/files/Library_USB.tar` before services
  start, including storage containing only `lost+found`.
- A fresh `localhost/rasbase_master:latest` is built from the official
  `debian:trixie-slim` image for the detected `linux/amd64` or `linux/arm64` platform. The copied ARM `rasbase_parts`
  are ignored, including by the compatibility `reconstitute.sh` entry point.
- The Debian service containers and GraphHopper use that shared base. LMS and
  the optional Office desktop use their own upstream images, selected for the native architecture.
- Kiwix and PMTiles select matching AMD64 or ARM64 executables. Maps, GPS, Meshtastic, e-books, music,
  the downloader, and the Library web front end retain the existing content layout.

The initial install downloads packages, images, and offline assets. Office is
built but disabled by default; use `sudo ./bootstrap --office yes` to enable it.
Office requires a keyboard and pointing device in the client browser. Use
**Configure Office** or `sudo ./bootstrap --configure-office yes|no` to change
its state without rebuilding. The menu also provides reinstall, retry, rebuild,
status and USB Clone repair. Firefox shows installation progress in a local
HTML page that refreshes every 15 seconds through to the final result.

Useful commands:

```bash
sudo systemctl restart start_library
sudo journalctl -u start_library -b
sudo podman ps -a
```

See [bootstrap details](bootstrap.md) and [remaining validation](TODO.md).

## Adding your own content

Open **Downloads** on the homepage to download PMTiles maps, StreetZim archives,
Kiwix collections, routing extracts, and Survivor Library collections. Upload
music to `/Library/music`, files to `/Library/library`, and ebooks to
`/Library/calibre/put_new_books_here`. Downloads need internet access; local
uploads and browsing saved content work offline.

Empty storage receives starter content during installation. Add regions and
collections that suit your needs; offline directions need a separate routing
extract. See the [downloader guide](setup_library/files/containers/data_download/README.md)
and [routing guide](setup_library/files/containers/data_download/docs/ROUTING.md).

Thanks to the content and software projects that make offline libraries possible,
including Kiwix, OpenStreetMap contributors, Protomaps, Project N.O.M.A.D.,
Pendia, and Survivor Library. See the
[source acknowledgments and availability notes](setup_library/files/containers/data_download/README.md#source-acknowledgments-and-availability)
for licensing, source availability, and the discretionary donation policy.

## Support the project

If this project is useful to you, consider
[**supporting development through PayPal**](https://www.paypal.com/ncp/payment/T8MGW39TXCR4J).

Prefer a ready-made Library device? Visit
[**librarydepository.com**](https://librarydepository.com) for pre-configured kits.
**Library-Creator**, the Raspberry Pi project, is separate from
**Library-Creator_x86**, this native Debian amd64/arm64 project.
