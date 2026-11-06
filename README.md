# Library Creator — Debian Trixie x86-64

Build an offline Library on a **64-bit Intel/AMD Debian 13 (Trixie)** laptop,
desktop, or virtual machine. This repository is the x86 fork; the original
Raspberry Pi checkout is separate and is not used by this installer.

```bash
./bootstrap --check
sudo ./bootstrap
```

Start from an installed Debian system with internet access. After installation,
open `http://localhost` on its desktop or `http://<machine-IP>` from another
machine. [Installation and configuration](docs/INSTALL.md) covers storage,
Ethernet, Wi-Fi, VMs, and the optional hotspot.

- HDMI uses Debian's existing desktop or console. Pi TFT, GPIO, touchscreen,
  framebuffer splash, and Pi boot configuration are not installed.
- Ethernet and Wi-Fi remain configured by Debian. A VM needs only a virtual NIC.
- `/Library` can be a directory on the system disk or a separately mounted disk.
  The menu restores USB formatting with explicit erase confirmation and a
  countdown; normal installs preserve an existing Library_USB partition.
- A fresh `localhost/rasbase_master:latest` is built from the official
  `debian:trixie-slim` image for `linux/amd64`. The copied ARM `rasbase_parts`
  are ignored, including by the compatibility `reconstitute.sh` entry point.
- The Debian service containers and GraphHopper use that shared base. LMS and
  the optional Office desktop use their own upstream images, built for amd64.
- Kiwix and PMTiles use x86-64 executables. Maps, GPS, Meshtastic, e-books, music,
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
