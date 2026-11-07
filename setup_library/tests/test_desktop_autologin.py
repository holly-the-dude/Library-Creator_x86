"""Exercise desktop configuration in temporary directories, never real accounts."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SETUP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('configure_desktop', SETUP / 'configure_desktop.py')
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = patch.object(desktop.subprocess, 'run').start()
        self.addCleanup(patch.stopall)

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_gdm_changes_only_autologin_and_preserves_backup_on_repeat(self):
        self.put('etc/X11/default-display-manager', '/usr/sbin/gdm3\n')
        original = ('# login settings\n[daemon]\nAutomaticLogin=pi\nWaylandEnable=true\n'
                    '[security]\nDisallowTCP=true\n')
        config = self.put('etc/gdm3/daemon.conf', original)
        pam_text = ('auth requisite pam_nologin.so\n'
                    'auth required pam_succeed_if.so user != root quiet_success\n'
                    '@include common-account\n@include common-session\n')
        pam = self.put('etc/pam.d/gdm-autologin', pam_text)
        manual = self.put('etc/pam.d/gdm-password', pam_text)
        self.assertTrue(desktop.configure(self.root))
        first = config.read_text()
        self.assertIn('AutomaticLogin=root\n', first)
        self.assertIn('AutomaticLoginEnable=true\n', first)
        self.assertIn('WaylandEnable=true\n', first)
        self.assertIn('[security]\nDisallowTCP=true\n', first)
        self.assertIn('# Library root autologin: auth required pam_succeed_if', pam.read_text())
        self.assertIn('@include common-account', pam.read_text())
        self.assertEqual(manual.read_text(), pam_text)
        self.run.assert_any_call(['chpasswd'], input='root:library\n', text=True, check=True)
        desktop.configure(self.root)
        self.assertEqual(config.read_text(), first)
        self.assertEqual(config.with_name('daemon.conf.before-library').read_text(), original)
        self.assertEqual(pam.with_name('gdm-autologin.before-library').read_text(), pam_text)
        launcher = self.root / 'usr/local/bin/library_browser'
        self.assertEqual(launcher.stat().st_mode & 0o777, 0o755)
        self.assertTrue((self.root / 'root/.config/autostart/library-browser.desktop').exists())

    def test_no_desktop_or_unknown_manager_never_changes_password(self):
        self.assertFalse(desktop.configure(self.root))
        self.run.assert_not_called()
        self.put('etc/X11/default-display-manager', '/usr/bin/unknown\n')
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            desktop.configure(self.root)
        self.run.assert_not_called()

    def test_missing_pam_stops_before_password_or_config_changes(self):
        self.put('etc/X11/default-display-manager', '/usr/sbin/gdm3\n')
        with self.assertRaisesRegex(ValueError, 'authentication'):
            desktop.configure(self.root)
        self.run.assert_not_called()
        self.assertFalse((self.root / 'etc/gdm3/daemon.conf').exists())

    def test_lightdm_retains_selected_desktop(self):
        self.put('etc/X11/default-display-manager', '/usr/sbin/lightdm\n')
        self.put('etc/pam.d/lightdm-autologin', '@include common-account\n')
        config = self.put('etc/lightdm/lightdm.conf', '[Seat:*]\nuser-session=xfce\nautologin-user=pi\n')
        desktop.configure(self.root)
        self.assertIn('user-session=xfce\n', config.read_text())
        self.assertIn('autologin-user=root\n', config.read_text())

    def test_sddm_uses_installed_last_session(self):
        self.put('etc/X11/default-display-manager', '/usr/bin/sddm\n')
        self.put('etc/pam.d/sddm-autologin', '@include common-account\n')
        self.put('usr/share/wayland-sessions/plasma.desktop', '[Desktop Entry]\n')
        self.put('usr/share/xsessions/xfce.desktop', '[Desktop Entry]\n')
        self.put('var/lib/sddm/state.conf', '[Last]\nSession=/usr/share/xsessions/xfce.desktop\n')
        desktop.configure(self.root)
        self.assertIn('Session=xfce.desktop\n', (self.root / 'etc/sddm.conf').read_text())


if __name__ == '__main__':
    unittest.main()
