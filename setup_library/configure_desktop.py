#!/usr/bin/env python3
"""Configure the installed Debian desktop for root Library autologin."""
from pathlib import Path
import re
import shutil
import subprocess


def write(path, content, mode=0o644):
    if path.exists() and path.read_text() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(path.name + '.before-library')
        if not backup.exists():
            shutil.copy2(path, backup)
    temporary = path.with_name(path.name + '.library-tmp')
    temporary.write_text(content)
    temporary.chmod(mode)
    temporary.replace(path)


def set_ini(path, section, values):
    """Change only the requested section/keys, retaining other settings/comments."""
    lines = path.read_text().splitlines() if path.exists() else []
    result, pending, inside, found = [], dict(values), False, False
    for line in lines:
        header = re.match(r'^\s*\[([^]]+)\]\s*$', line)
        if header:
            if inside:
                result.extend(f'{key}={value}' for key, value in pending.items())
                pending.clear()
            inside = header[1] == section
            found |= inside
        assignment = re.match(r'^\s*([^#;=\s]+)\s*=', line)
        if inside and assignment and assignment[1] in values:
            if assignment[1] in pending:
                result.append(f'{assignment[1]}={pending.pop(assignment[1])}')
            continue
        result.append(line)
    if not found:
        result.extend(['', f'[{section}]'])
    result.extend(f'{key}={value}' for key, value in pending.items())
    write(path, '\n'.join(result) + '\n')


def allow_root_autologin(path):
    # Keep PAM account/session checks. Remove only Debian's root exclusion in
    # the display manager's autologin service; password/SSH login is untouched.
    content = path.read_text()
    content = re.sub(
        r'^(\s*auth\s+(?:required|requisite)\s+pam_succeed_if\.so\s+user\s+!=\s+root(?:\s+quiet_success)?\s*)$',
        r'# Library root autologin: \1', content, flags=re.MULTILINE)
    write(path, content)


def configure(root=Path('/')):
    selector = root / 'etc/X11/default-display-manager'
    manager = Path(selector.read_text().strip()).name if selector.exists() else ''
    if not manager:
        print('[INFO] No desktop login manager installed; skipping desktop autologin.')
        return False
    if manager not in {'gdm3', 'gdm', 'lightdm', 'sddm'}:
        raise ValueError(f'Unsupported desktop login manager: {manager}')

    if manager in {'gdm3', 'gdm'}:
        pam = root / 'etc/pam.d/gdm-autologin'
        config = root / 'etc/gdm3/daemon.conf'
        settings = ('daemon', {'AutomaticLoginEnable': 'true', 'AutomaticLogin': 'root',
                               'TimedLoginEnable': 'false'})
        unit = 'gdm.service'
    elif manager == 'lightdm':
        pam = root / 'etc/pam.d/lightdm-autologin'
        config = root / 'etc/lightdm/lightdm.conf'
        settings = ('Seat:*', {'autologin-user': 'root', 'autologin-user-timeout': '0',
                               'autologin-guest': 'false'})
        unit = 'lightdm.service'
    else:
        pam = root / 'etc/pam.d/sddm-autologin'
        config = root / 'etc/sddm.conf'
        # Prefer the configured last session; otherwise select an installed one.
        import configparser
        state = configparser.ConfigParser()
        state.read(root / 'var/lib/sddm/state.conf')
        session = Path(state.get('Last', 'Session', fallback='')).name
        sessions = sorted((root / 'usr/share/wayland-sessions').glob('*.desktop'))
        sessions += sorted((root / 'usr/share/xsessions').glob('*.desktop'))
        if not sessions:
            raise ValueError('No desktop session is installed for SDDM autologin.')
        if session not in {p.name for p in sessions}:
            session = sessions[0].name
        settings = ('Autologin', {'User': 'root', 'Session': session, 'Relogin': 'false'})
        unit = 'sddm.service'

    # Validate the authentication file before changing any login settings.
    if not pam.is_file():
        raise ValueError(f'Missing desktop authentication configuration: {pam}')
    subprocess.run(['chpasswd'], input='root:library\n', text=True, check=True)
    allow_root_autologin(pam)
    set_ini(config, *settings)

    source = Path(__file__).parent / 'files'
    write(root / 'usr/local/bin/library_browser', (source / 'library_browser').read_text(), 0o755)
    write(root / 'root/.config/autostart/library-browser.desktop',
          (source / 'library-browser.desktop').read_text())
    write(root / 'root/Desktop/library-wifi.desktop',
          (source / 'library-wifi.desktop').read_text(), 0o755)
    write(root / 'usr/share/applications/library-wifi.desktop',
          (source / 'library-wifi.desktop').read_text())
    write(root / 'root/Desktop/library.desktop',
          (source / 'library.desktop').read_text(), 0o755)
    write(root / 'usr/share/applications/library.desktop',
          (source / 'library.desktop').read_text())
    write(root / 'usr/local/bin/library_desktop_icons',
          (source / 'library_desktop_icons').read_text(), 0o755)
    write(root / 'root/.config/autostart/library-desktop-icons.desktop',
          (source / 'library-desktop-icons.desktop').read_text())
    write(root / 'root/.config/gnome-initial-setup-done', 'yes\n')
    write(root / 'root/.mozilla/firefox/library/user.js', '''// Library desktop browser defaults.
user_pref("browser.startup.homepage", "http://localhost/");
user_pref("browser.startup.page", 1);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.sessionstore.resume_from_crash", false);
''')
    if not (root / 'etc/systemd/system/display-manager.service').exists():
        subprocess.run(['systemctl', 'enable', unit], check=True)
    subprocess.run(['systemctl', 'set-default', 'graphical.target'], check=True)
    print('[INFO] Root desktop autologin and Firefox Library startup configured for the next boot.')
    return True


if __name__ == '__main__':
    configure()
