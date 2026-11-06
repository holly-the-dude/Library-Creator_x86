"""PC installer regression checks; all host paths and commands are sandboxed."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
SETUP = ROOT / 'setup_library'
CONTAINERS = SETUP / 'files/containers'


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.log = self.root / 'calls'
        self.env = {**os.environ, 'PATH': str(self.bin) + ':' + os.environ['PATH'],
                    'TEST_LOG': str(self.log), 'LIBRARY_INSTALL_WORKER': '1'}

    def fake(self, name, body):
        p = self.bin / name
        p.write_text('#!/bin/bash\n' + body + '\n')
        p.chmod(0o755)

    def run_shell(self, source, *args):
        return subprocess.run(['bash', '-c', source, 'test', *args], env=self.env,
                              text=True, capture_output=True, timeout=15)

    def test_bootstrap_uses_its_own_checkout_from_another_working_directory(self):
        checkout = self.root / 'copied checkout'
        (checkout / 'setup_library').mkdir(parents=True)
        shutil.copy(ROOT / 'bootstrap', checkout / 'bootstrap')
        result = subprocess.run(['bash', '-c', 'source "$1"; printf "%s" "$SOURCE_DIR"',
                                 'test', str(checkout / 'bootstrap')],
                                cwd='/', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, str(checkout))

    def test_rejected_host_never_installs(self):
        self.fake('apt-get', 'echo mutation >> "$TEST_LOG"')
        result = self.run_shell('source "$1"; preflight() { return 42; }; main',
                                str(ROOT / 'bootstrap'))
        self.assertEqual(result.returncode, 42)
        self.assertFalse(self.log.exists())

    def test_check_is_read_only_and_options_are_validated(self):
        self.fake('apt-get', 'echo mutation >> "$TEST_LOG"')
        source = 'source "$1"; shift; preflight() { echo checked; }; main "$@"'
        for args, status in [(['--check'], 0), (['--storage', 'erase'], 2),
                             (['--office', 'maybe'], 2), (['--storage'], 2),
                             (['--hotspot-interface', 'wlp2s0'], 2)]:
            result = self.run_shell(source, str(ROOT / 'bootstrap'), *args)
            self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        self.assertFalse(self.log.exists())

    def test_fresh_install_rebuild_and_failed_build_preserve_configuration(self):
        # Run main with real shell control flow and filesystem operations, but
        # route every host path to the fixture and mock apt, rsync and Ansible.
        source = (ROOT / 'bootstrap').read_text().replace('$EUID', '0')
        for path in ['/etc/library', '/opt/library-creator', '/Library', '/run/lock']:
            source = source.replace(path, str(self.root / path.lstrip('/')))
        script = self.root / 'installer.sh'
        script.write_text(source)
        (self.root / 'run/lock').mkdir(parents=True)
        builds = self.root / 'opt/library-creator/setup_library/files/containers'
        builds.mkdir(parents=True)
        (builds / 'build_pods.sh').write_text('echo build:$LIBRARY_OFFICE >> "$TEST_LOG"\nexit "${BUILD_STATUS:-0}"\n')
        self.fake('apt-get', 'echo apt >> "$TEST_LOG"')
        self.fake('rsync', 'echo stage >> "$TEST_LOG"')
        self.fake('ansible-playbook', 'echo services >> "$TEST_LOG"')
        self.fake('mountpoint', 'exit "${MOUNT_STATUS:-1}"')
        run = 'source "$1"; shift; preflight() { :; }; main --worker --install --yes "$@"'
        result = self.run_shell(run, str(script), '--office', 'yes')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        config = self.root / 'etc/library/config.json'
        self.assertEqual(json.loads(config.read_text()),
                         {'library_storage_mode': 'directory', 'library_office': 'yes', 'library_usb_device': '',
                          'library_storage_path': str(self.root / 'Library')})
        calls = self.log.read_text().splitlines()
        self.assertLess(calls.index('build:yes'), calls.index('services'))
        result = self.run_shell(run, str(script))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log.read_text().count('build:yes'), 2)
        before = config.read_text()
        self.env['BUILD_STATUS'] = '19'
        result = self.run_shell(run, str(script), '--office', 'no')
        self.assertEqual(result.returncode, 19, result.stdout + result.stderr)
        self.assertEqual(config.read_text(), before)
        self.assertEqual(self.log.read_text().count('services'), 2)
        self.env['MOUNT_STATUS'] = '1'
        before_calls = self.log.read_text()
        result = self.run_shell(run, str(script), '--storage', 'mounted')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.log.read_text(), before_calls)
        # A desktop-mounted USB may be reached through /Library -> /media/... .
        self.env.update(BUILD_STATUS='0', MOUNT_STATUS='0')
        library = self.root / 'Library'
        library.rmdir()
        usb = self.root / 'mounted USB'
        usb.mkdir()
        library.symlink_to(usb, target_is_directory=True)
        result = self.run_shell(run, str(script), '--storage', 'mounted')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(library.is_symlink())
        self.assertEqual(json.loads(config.read_text())['library_storage_path'], str(usb))

    def test_base_rejects_arm_and_builds_before_publishing_tag(self):
        self.fake('uname', 'echo "${TEST_ARCH:-x86_64}"')
        self.fake('podman', '''printf '%s\\n' "$*" >> "$TEST_LOG"
case "$1 $2" in
    'image exists') exit "${IMAGE_EXISTS:-1}" ;;
    'image inspect') echo "${IMAGE_ARCH:-amd64}" ;;
    'build --platform') exit "${BUILD_STATUS:-0}" ;;
    'run --rm') exit "${RUN_STATUS:-0}" ;;
esac''')
        script = str(CONTAINERS / 'rasbase/build_rasbase.sh')
        result = self.run_shell('bash "$1"', script)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text().splitlines()
        self.assertTrue(any('build --platform linux/amd64 --pull=always' in c for c in calls))
        self.assertLess(next(i for i, c in enumerate(calls) if c.startswith('run ')),
                        next(i for i, c in enumerate(calls) if c.startswith('tag ')))
        self.log.unlink()
        self.env['TEST_ARCH'] = 'aarch64'
        self.assertNotEqual(self.run_shell('bash "$1"', script).returncode, 0)
        self.assertFalse(self.log.exists())
        self.env['TEST_ARCH'] = 'x86_64'
        self.env.update(IMAGE_EXISTS='0', IMAGE_ARCH='arm64')
        self.assertNotEqual(self.run_shell('bash "$1"', script).returncode, 0)
        self.assertFalse(any(c.startswith(('build ', 'run ', 'tag '))
                             for c in self.log.read_text().splitlines()))
        self.log.unlink()
        self.env.update(IMAGE_EXISTS='1', RUN_STATUS='9')
        self.assertNotEqual(self.run_shell('bash "$1"', script).returncode, 0)
        self.assertFalse(any(c.startswith('tag ') for c in self.log.read_text().splitlines()))

    def test_hotspot_uses_named_adapter_and_rejects_non_ap_devices(self):
        self.fake('nmcli', '''printf '%s\\n' "$*" >> "$TEST_LOG"
case "$*" in
    *GENERAL.TYPE*) echo wifi ;;
    *WIFI-PROPERTIES.AP*) echo "${AP_CAPABLE:-yes}" ;;
    *connection.id*) exit 10 ;;
esac''')
        script = str(SETUP / 'configure_hotspot.sh')
        result = self.run_shell('bash "$1" wlp2s0 test-password', script)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('connection up library-hotspot ifname wlp2s0', self.log.read_text())
        self.assertIn('ipv4.method shared ipv4.addresses 10.1.1.1/24', self.log.read_text())
        self.log.unlink()
        self.env['AP_CAPABLE'] = 'no'
        self.assertNotEqual(self.run_shell('bash "$1" wlp2s0 test-password', script).returncode, 0)
        self.assertNotIn('connection add', self.log.read_text())

    def test_pc_startup_has_no_pi_hardware_or_destructive_disk_actions(self):
        startup = (SETUP / 'files/start_library.yml').read_text()
        for forbidden in ['displayit', '/dev/mmcblk', 'mkfs.', 'shutdown -r',
                          'localhost/hotspot', 'podman volume rm']:
            self.assertNotIn(forbidden, startup)
        play = yaml.safe_load(startup)[0]
        mount = next(t for t in play['tasks'] if t.get('name') == 'Require mounted content storage when selected')
        self.assertEqual(mount['when'], "library_storage_mode == 'mounted'")
        services = yaml.safe_load((CONTAINERS / 'webserver/library_setup.yml').read_text())['services']
        self.assertTrue(all(s['internal_ip'].startswith('10.88.') for s in services))


if __name__ == '__main__':
    unittest.main()
