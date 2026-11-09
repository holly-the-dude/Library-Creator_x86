# Audit of the initial x86 port

This records the scope and known regressions of the initial port against the
original Raspberry Pi checkout. It is not a claim that the port is complete.
The original `../Library-Creator` folder was not edited by this work.

## Native ARM64 support (November 6, 2026)

This checkout now accepts Debian Trixie on both amd64/x86_64 and arm64/aarch64.
The root bootstrap, existing filenames and menu are retained. A shared
architecture helper selects the native Podman platform; preflight also requires
matching 64-bit Debian userspace. Unsupported CPUs and 32-bit installs fail
before installation. Cached base images from the other architecture are rejected.
Both platforms build a fresh Debian Trixie base; neither loads Pi archive parts.

Kiwix selects x86_64 or aarch64 with separate pinned SHA-256 values. The ARM64
checksum matches the inherited archive and was verified against the downloaded
release during the native build. Download progress is now visible. PMTiles,
ttyd and the Office packages already had architecture selection; their ARM64
builds were exercised. Registry manifests for LMS and the Office webtop base
advertised both amd64 and arm64 at validation time.

Validation used an isolated rootless Podman store on the available RHEL ARM64
development host, not an installation onto that host:

- The native Debian base and all 12 application images compiled and their
  image metadata reports `arm64`.
- Kiwix 3.5.0 and PMTiles 1.30.2 ran natively. The Office image contains the
  ARM64 WordCraft, DeckCraft and GridCraft packages with verified checksums.
- The aggregate builder reported one failure after successfully compiling
  Office: its existing enable/disable helper requires root and correctly
  refused the rootless test. No privilege guard was removed. The installer
  runs this helper as root; Office tag transitions passed the regression suite.
- All 80 installer/startup tests passed on the ARM64 development host outside
  the sandbox, using a temporary test environment for Flask. The initial
  sandbox run could not open test sockets/Ansible RPC and lacked Flask; an
  Office fixture also needed the new architecture helper copied into it.
- Three Kiwix theme tests passed against the bundled ARM64 archive.
- On libraryd (amd64), preflight, cached native-base validation, the ten
  architecture/installer tests, twelve Office tests, and Ansible syntax checks
  passed. A separate amd64 Kiwix image built, passed its checksum verification,
  and ran `kiwix-serve --version`. Running Library services were not restarted.

Build logs: `/tmp/library-arm64-check/build.log` on the development host and
`/root/library-wiki-amd64-check.log` on libraryd. The full ARM64 host install,
reboot, desktop autologin and physical peripherals still need an ARM64 Debian
target. The successful amd64 host integration below does not establish those
ARM64 host behaviors.

## Root desktop autologin (November 6, 2026)

After successful service installation, bootstrap now configures the existing
GDM, LightDM or SDDM desktop to autologin as root, sets the requested root
password to `library`, and installs a root desktop autostart entry. Firefox
waits up to three minutes for `http://localhost/`, then opens the Library using
`/root/.mozilla/firefox/library`. The existing desktop is not interrupted by
configuration; autologin applies on the next boot. Console-only installations
remain headless. Changed login settings have `*.before-library` backups.

Verified on libraryd's GNOME/GDM desktop after an approved reboot: an active
root Wayland session started automatically, Firefox ran as root with the
Library URL, the homepage returned HTTP 200, and `start_library.service`
completed with zero failed tasks. The root password was checked against the
requested value without printing its hash. Five desktop configuration tests
passed on Debian; 24 focused desktop/installer/progress tests passed locally.
LightDM and SDDM configuration paths have fixture coverage but have not had a
live desktop login test. Existing installation progress can also open in the
new root desktop session.

## Restoration work (November 5, 2026)

The entries below remain a record of the initial port, not a description of
all current behavior. Using the supplied `bootstrap_pi` reference, the x86
installer now restores the main menu, explicit fresh/retry/rebuild/update
operations, status, targeted Office configuration, and targeted USB Clone
repair. USB selection, erase confirmation and a 30-second countdown are back;
formatting is limited to the selected non-system partition. Already-labelled
Library_USB content is preserved.

Firefox now opens a local HTML progress page on the logged-in desktop. It
refreshes every 15 seconds and retains the success, failure or cancellation
result. Progress and the complete log are saved on disk. Pi framebuffer
hardware is not required. BIOS/UEFI OS cloning remains outside the implemented
support. Desktop autologin was added on November 6, as described below.

The original targeted Clone regression suite has been restored and adapted.
Additional menu, progress-page and USB safety tests cover the new behavior.
See `bootstrap.md` for the current operational reference.

### Native VM integration results

Tested on the fresh Debian Trixie amd64 VM `libraryd` (`192.168.1.51`) on
November 5, 2026, after copying this checkout to `/root/Library-Creator_x86`.
The earlier reported container-build failure was not reproduced; no original
failure log was available. A real installation bug was corrected: the Ansible
`findmnt` output-column list must be one quoted argument, not four YAML entries.

- Built the native Debian base and all 12 application images, including Office
  and GraphHopper. The ARM archive parts are not used by the build.
- Completed `./bootstrap --install --usb-device /dev/sdb1 --office no --yes`.
  Ansible finished with zero failed tasks; `start_library.service` succeeded.
- Verified HTTP 200 from Library, Wiki, Maps, StreetZim health, Downloads health,
  eBooks, LMS, the music player and the mesh firmware setup page.
- Enabled Office through bootstrap, verified HTTPS 200 on port 3001, then disabled
  it through bootstrap. No image rebuild was required; the disabled image remains
  tagged `dontrun` and the saved preference is `no`.
- Ran the targeted Clone repair successfully. Authenticated USB discovery found
  `/dev/sdb1` and no destination disks. No clone or destructive format was run.
- Firefox opened the local progress file as desktop user `pi`. A separate Firefox
  render verified the final “Library is ready” page and its 15-second refresh.
- Rebooted through `library-restart.service`. The USB mounted automatically at
  `/Library`, the startup service succeeded and all nine runtime containers returned.
  The homepage again returned HTTP 200. Existing PMTiles, MP3 and ZIM content
  matched checksums recorded before installation, including after reboot.
- Passed 70 installer/startup regression tests and 27 downloader Clone tests on
  Debian, plus Ansible syntax checks. An additional symlink-storage regression
  now verifies `/Library -> mounted USB` preservation in the 11-test installer
  UI suite.

Remote evidence is in `/root/library-build.log`, `/root/library-install-console.log`,
`/root/library-office-test.log`, `/root/library-office-disable-test.log`,
`/root/library-clone-test.log`, `/root/library-content-before.sha256`, and
`/var/log/library-installer/install.log`. The full copied checkout includes Git
metadata for Reinstall / Upgrade; it contains the local uncommitted port changes.
No Git update, commit or push was performed during this integration test.

Physical Wi-Fi/AP mode, physical HDMI hardware, radio passthrough, large-library
startup, destructive formatting and copying to a second USB disk remain untested.
BIOS/UEFI operating-system cloning is not implemented. USB formatting guard and
countdown behavior is covered with mocked devices rather than erasing user data.

## Changes that went beyond the requested architecture port

| Area | What changed | Consequence |
| --- | --- | --- |
| `bootstrap.md` | Replaced a detailed installer reference with a short summary | Lost operating instructions, stage explanations, file descriptions and troubleshooting. Restored as a detailed reference in this audit, describing the actual current behavior. |
| `README.md` | Replaced the original with a short x86 introduction | Lost service descriptions, content/upload/deletion guidance, architecture diagram, project introduction and support information. Still requires restoration with targeted x86 edits. |
| `docs/INSTALL.md` | Replaced the original guide | Removed detailed radio setup, map/routing instructions, offline-collection examples and much troubleshooting. The replacement covers x86 host setup but is not equivalent coverage. |
| `TODO.md` | Replaced the existing list | Dropped completed feature history and the internal-documentation task. Those were unrelated to an architecture port. |
| `bootstrap` | Replaced the menu-driven workflow with immediate command-line installation | No Fresh Install/Reinstall/Restart/Status menu, confirmation flow, automatic Git update, or boot-stage resume. Running without options now installs immediately. |
| Office setup | Removed `--configure-office` and its menu action | `--office yes/no` runs the full installer. The existing manual tag helper remains, but it does not update the new saved preference. |
| HDMI | Removed kiosk/resolution/wallpaper configuration with the Pi display code | Ordinary Debian HDMI still works, but this does not preserve the original HDMI appliance experience. The request to keep HDMI was interpreted too broadly as permission to drop that behavior. |
| Clone | Removed installation of the host clone service and downloader socket | Neither boot cloning nor content-drive cloning is available through the x86 installer. The inherited implementation needs a real port; leaving it disabled is not feature parity. |
| Install paths and packages | Moved staging from `/root/install` to `/opt/library-creator`; changed pipx Ansible to Debian-packaged Ansible | Existing operating instructions and maintenance scripts may refer to old paths. This was an additional design change, not required solely by amd64. |
| Numbered playbooks | Replaced `01_install_ansible.yml` and `99_reinstall_pods.yml` with imports of `install_x86.yml` | Their previous task/tag interfaces and cleanup behavior no longer exist. |
| Installer tests | Deleted four `test_bootstrap_*` files and replaced them with a smaller x86 suite | The original menu, reinstall, source-discovery and targeted Clone behavior is no longer covered. Passing the replacement tests does not demonstrate preservation of those features. |

## Architecture and hardware changes that address the requested port

- Build a native amd64 Trixie base rather than loading ARM `rasbase_parts`.
- Use x86-64 Kiwix and PMTiles executables; verify the Kiwix archive checksum.
- Build service images for `linux/amd64`, with the shared Debian base used by
  the services that previously used it. LMS and Office retain upstream bases.
- Remove active Pi TFT/GPIO/touchscreen configuration and Pi boot-file edits.
- Accept normal Ethernet/Wi-Fi names and a VM without a Wi-Fi adapter.
- Support directory storage and the user's symlink to a mounted USB Library.
- Replace host health checks that assumed the hotspot IP with loopback or
  container addresses.

These changes still require complete integration testing; their purpose does
not establish that every implementation detail is correct.

## Additional behavior and maintenance risks

- The hotspot now uses host NetworkManager instead of the hotspot container.
  It uses open SSID `library` with no password and an explicitly selected adapter.
  Desktop-only controls switch between hotspot and internet Wi-Fi. On `library`,
  `wlp1s0` reports AP capability and Ethernet is connected. End-to-end client
  association and mode-switch recovery still require physical validation.
- Mounted-storage installation writes `/etc/fstab` and a systemd mount dependency.
  A backup is requested, but an actual reboot/missing-disk test remains necessary.
- Builds are not transactional. Successful images are retagged before the full
  build finishes, and Office's helper can stop its running container. A later
  failure does not restore the earlier state.
- Runtime startup was substantially rewritten: disk detection/formatting/cloning
  and splash tasks were removed, networking moved to the host, and selected
  containers now get replaced on service restart. The retained service blocks
  passed regression tests, but this is a larger change than a base-image swap.
- The main web readiness check now fails after roughly two minutes rather than
  using the old very long, ignored-error polling. Large-library timing needs
  validation.
- The developer guide, usage guide, and several inherited helpers still describe
  Pi paths or behaviors. They need consistency review before release.
- A separate untracked `setup_library/bootstrap` copy is present in the current
  workspace. The supported entry point is the root `bootstrap`. The duplicate
  was not changed or deleted during this audit.

## Verification evidence and limits

During the earlier VM session, the native Debian Trixie amd64 base built
successfully and 50 unit/mocked-service regression tests passed on Debian.
The x86 Kiwix archive also passed its theme-generation tests. Seven focused
installer tests subsequently passed after moving the full script into the root
`bootstrap`.

Those checks did **not** establish a successful full application build,
installation, live-content startup, reboot, or physical HDMI/Wi-Fi behavior.
The full VM install had been running when work was interrupted.

At this audit, SSH to the supplied `192.168.1.51` host succeeded, but the earlier
install/test logs were absent, `start_library.service` was inactive, and no
containers were listed. The reason for that changed VM state is not established.
No new installation or other remote mutation was performed during this audit.


## November 8, 2026 — Storage seeding, reboot, and desktop Wi-Fi

The native installer now seeds empty storage, including an ext filesystem with
only `lost+found`, from `Library_USB.tar` before startup creates files. On
`library`, missing starter content was restored without overwriting existing
files; Maps and the Library homepage returned HTTP 200, LMS returned its expected
root-path HTTP 404, and the startup unit completed successfully.

Successful installs and rebuilds now schedule a reboot within one minute. The
browser completion screen announces it. This completion behavior was checked
with mocked shutdown commands; it is not evidence of a new live reboot test.

The new local Wi-Fi UI has eight tests covering validation, CSRF/Host rejection,
hotspot setup, password handling, and failed-connection recovery. Five desktop
and ten native installer tests pass. Live Wi-Fi switching has not yet been
verified. The live machine update was staged behind bootstrap’s lock while its
reinstall was running; staging is not proof that the deferred update completed.
These changes belong to Library-Creator_x86, independently of the separate
Library-Creator Raspberry Pi project.
