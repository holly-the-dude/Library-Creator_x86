"""Native amd64/arm64 installer checks; host paths and commands are sandboxed."""
import json
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tarfile
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
        source = source.replace('/Library_USB.tar', '/SEED_ARCHIVE.tar')
        for path in ['/etc/library', '/opt/library-creator', '/Library', '/run/lock']:
            source = source.replace(path, str(self.root / path.lstrip('/')))
        source = source.replace('/SEED_ARCHIVE.tar', '/Library_USB.tar')
        script = self.root / 'installer.sh'
        script.write_text(source)
        (self.root / 'run/lock').mkdir(parents=True)
        builds = self.root / 'opt/library-creator/setup_library/files/containers'
        builds.mkdir(parents=True)
        with tarfile.open(builds.parent / 'Library_USB.tar', 'w:gz') as archive:
            seed = tarfile.TarInfo('music/sample.mp3')
            seed.size = 4
            archive.addfile(seed, io.BytesIO(b'seed'))
        (self.root / 'Library/lost+found').mkdir(parents=True)
        (builds / 'build_pods.sh').write_text('echo build:$LIBRARY_OFFICE >> "$TEST_LOG"\nexit "${BUILD_STATUS:-0}"\n')
        self.fake('apt-get', 'echo apt >> "$TEST_LOG"')
        self.fake('rsync', 'echo stage >> "$TEST_LOG"')
        self.fake('ansible-playbook', 'echo services >> "$TEST_LOG"')
        self.fake('mountpoint', 'exit "${MOUNT_STATUS:-1}"')
        run = 'source "$1"; shift; preflight() { :; }; main --worker --install --yes "$@"'
        result = self.run_shell(run, str(script), '--office', 'yes')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        sample = self.root / 'Library/music/sample.mp3'
        self.assertEqual(sample.read_bytes(), b'seed')
        sample.write_bytes(b'user content')
        config = self.root / 'etc/library/config.json'
        self.assertEqual(json.loads(config.read_text()),
                         {'library_storage_mode': 'directory', 'library_office': 'yes', 'library_usb_device': '',
                          'library_storage_path': str(self.root / 'Library')})
        calls = self.log.read_text().splitlines()
        self.assertLess(calls.index('build:yes'), calls.index('services'))
        result = self.run_shell(run, str(script))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sample.read_bytes(), b'user content')
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
        shutil.rmtree(library)
        usb = self.root / 'mounted USB'
        usb.mkdir()
        library.symlink_to(usb, target_is_directory=True)
        result = self.run_shell(run, str(script), '--storage', 'mounted')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(library.is_symlink())
        self.assertEqual((usb / 'music/sample.mp3').read_bytes(), b'seed')
        self.assertEqual(json.loads(config.read_text())['library_storage_path'], str(usb))

    def mock_podman_builds(self):
        self.fake('uname', 'echo "${TEST_ARCH:-x86_64}"')
        self.fake('podman', '''printf '%s\\n' "$*" >> "$TEST_LOG"
case "$1 $2" in
    'image exists') exit "${IMAGE_EXISTS:-1}" ;;
    'image inspect') echo "${IMAGE_ARCH:-amd64}" ;;
    'build --platform') exit "${BUILD_STATUS:-0}" ;;
    'run --rm') exit "${RUN_STATUS:-0}" ;;
esac''')

    def test_native_base_builds_and_verifies_both_architectures_before_tagging(self):
        self.mock_podman_builds()
        script = str(CONTAINERS / 'rasbase/build_rasbase.sh')
        for machine, arch in [('x86_64', 'amd64'), ('aarch64', 'arm64')]:
            with self.subTest(arch=arch):
                self.env['TEST_ARCH'] = machine
                result = self.run_shell('bash "$1"', script)
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = self.log.read_text().splitlines()
                self.assertTrue(any(f'build --platform linux/{arch} --pull=always' in c for c in calls))
                verification = next(c for c in calls if c.startswith('run '))
                self.assertIn(f'--env LIBRARY_EXPECTED_ARCH={arch}', verification)
                self.assertLess(calls.index(verification), next(i for i, c in enumerate(calls) if c.startswith('tag ')))
                self.log.unlink()
        self.env['TEST_ARCH'] = 'armv7l'
        self.assertNotEqual(self.run_shell('bash "$1"', script).returncode, 0)
        self.assertFalse(self.log.exists())

    def test_cached_base_from_other_architecture_and_failed_validation_are_rejected(self):
        self.mock_podman_builds()
        script = str(CONTAINERS / 'rasbase/build_rasbase.sh')
        for machine, wrong in [('x86_64', 'arm64'), ('aarch64', 'amd64')]:
            self.env.update(TEST_ARCH=machine, IMAGE_EXISTS='0', IMAGE_ARCH=wrong)
            self.assertNotEqual(self.run_shell('bash "$1"', script).returncode, 0)
            self.assertFalse(any(c.startswith(('build ', 'run ', 'tag '))
                                 for c in self.log.read_text().splitlines()))
            self.log.unlink()
        self.env.update(TEST_ARCH='aarch64', IMAGE_EXISTS='1', RUN_STATUS='9')
        self.assertNotEqual(self.run_shell('bash "$1"', script).returncode, 0)
        self.assertFalse(any(c.startswith('tag ') for c in self.log.read_text().splitlines()))

    def test_preflight_accepts_native_64_bit_debian_and_rejects_mixed_userspace(self):
        checkout = self.root / 'checkout'
        containers = checkout / 'setup_library/files/containers'
        containers.mkdir(parents=True)
        shutil.copy(CONTAINERS / 'architecture.sh', containers)
        (containers.parent / 'start_library.yml').touch()
        release = self.root / 'os-release'
        release.write_text('ID=debian\nVERSION_CODENAME=trixie\n')
        systemd = self.root / 'systemd'
        systemd.mkdir()
        script = checkout / 'bootstrap'
        script.write_text((ROOT / 'bootstrap').read_text().replace('/etc/os-release', str(release))
                          .replace('/run/systemd/system', str(systemd)))
        self.fake('uname', 'echo "$TEST_ARCH"')
        self.fake('dpkg', 'echo "$TEST_DEB_ARCH"')
        for machine, arch, accepted in [('x86_64', 'amd64', True), ('aarch64', 'arm64', True),
                                        ('aarch64', 'armhf', False), ('x86_64', 'i386', False),
                                        ('armv7l', 'armhf', False), ('riscv64', 'riscv64', False)]:
            self.env.update(TEST_ARCH=machine, TEST_DEB_ARCH=arch)
            result = self.run_shell('source "$1"; preflight', str(script))
            self.assertEqual(result.returncode == 0, accepted, result.stderr)
        release.write_text('ID=debian\nVERSION_CODENAME=bookworm\n')
        self.env.update(TEST_ARCH='aarch64', TEST_DEB_ARCH='arm64')
        self.assertNotEqual(self.run_shell('source "$1"; preflight', str(script)).returncode, 0)

    def test_all_application_and_nested_builds_use_native_platform(self):
        self.mock_podman_builds()
        tree = self.root / 'containers'
        (tree / 'rasbase').mkdir(parents=True)
        for name in ('architecture.sh', 'build_pods.sh', 'rasbase/build_rasbase.sh'):
            shutil.copy(CONTAINERS / name, tree / name)
        for name in ('meshtastic', 'meshflash', 'library_maps', 'library_maps/graphhopper'):
            folder = tree / name
            folder.mkdir(parents=True, exist_ok=True)
            (folder / 'Containerfile').write_text('FROM scratch\n')
        for machine, arch in [('x86_64', 'amd64'), ('aarch64', 'arm64')]:
            self.env.update(TEST_ARCH=machine)
            result = self.run_shell('bash "$1"', str(tree / 'build_pods.sh'))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            builds = [c for c in self.log.read_text().splitlines() if c.startswith('build ')]
            self.assertEqual(len(builds), 5)  # base, three services, routing subimage
            self.assertTrue(all(f'--platform linux/{arch}' in c for c in builds))
            self.assertTrue(any('library_maps-graphhopper:11' in c for c in builds))
            self.log.unlink()

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
