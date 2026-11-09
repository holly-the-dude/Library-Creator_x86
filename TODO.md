# TODO

- [ ] Validate a complete Debian Trixie ARM64 host installation and desktop autologin.
- [ ] Verify a client can join the open `library` hotspot on the physical amd64
  machine and load `http://10.1.1.1/`; verify internet Wi-Fi switching, rollback,
  persisted mode after reboot, and uninterrupted Ethernet.
- [ ] Verify the GNOME Library Wi-Fi desktop shortcut is visible and trusted after login.
- [ ] Verify a successful live install displays the browser notice and reboots;
  verify failed installs do not schedule a reboot.
- [ ] Validate HDMI in the target Debian desktop session.
- [ ] Validate USB GPS and Meshtastic passthrough on the selected hypervisor.
- [ ] Implement x86 boot-disk cloning with explicit BIOS/UEFI support if needed; Pi cloning is disabled.
- [ ] GUI file and folder deletion.
