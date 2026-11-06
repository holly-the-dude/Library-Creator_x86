# Audit of the initial x86 port

This records the scope and known regressions of the initial port against the
original Raspberry Pi checkout. It is not a claim that the port is complete.
The original `../Library-Creator` folder was not edited by this work.

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
hardware is not required. BIOS/UEFI OS cloning and automatic desktop login
remain outside the implemented support.

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
  It is optional, password-protected, and uses an explicitly selected adapter.
  This changes the original appliance networking experience. Physical AP-mode
  behavior has only been mocked, not tested on a Wi-Fi adapter.
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
