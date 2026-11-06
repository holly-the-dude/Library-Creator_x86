"""Installer menu, erase guards and Firefox progress output without real disks."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'setup_library' / f'{name}.py')
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


usb = module('prepare_usb')
progress = module('install_progress')


class EraseGuards(unittest.TestCase):
    def setUp(self):
        self.disks = [{'name': '/dev/sda', 'type': 'disk', 'children': [
            {'name': '/dev/sda1', 'type': 'part', 'mountpoints': ['/']} ]},
            {'name': '/dev/sdb', 'type': 'disk', 'children': [
            {'name': '/dev/sdb1', 'type': 'part', 'size': 1024**3, 'ro': False,
             'label': 'Library_USB', 'fstype': 'exfat', 'mountpoints': ['/media/pi/Library_USB']}]}]

    def test_only_selected_data_partition_is_accepted(self):
        disk, part = usb.select_partition(self.disks, '/dev/sdb1')
        self.assertEqual(disk['name'], '/dev/sdb')
        self.assertEqual(part['name'], '/dev/sdb1')
        for device in ('/dev/sda1', '/dev/sda', '/dev/sdb', '/dev/sdc1'):
            with self.subTest(device=device), self.assertRaises(ValueError):
                usb.select_partition(self.disks, device)

    def test_root_on_lvm_and_swap_on_sibling_block_formatting(self):
        for child in ({'name': '/dev/mapper/root', 'type': 'lvm', 'mountpoints': ['/']},
                      {'name': '/dev/sdb2', 'type': 'part', 'mountpoints': ['[SWAP]']}):
            disks = copy.deepcopy(self.disks)
            disks[1]['children'].append(child)
            with self.assertRaises(ValueError):
                usb.select_partition(disks, '/dev/sdb1')

    def test_noninteractive_or_cancelled_erase_never_runs_commands(self):
        part = self.disks[1]['children'][0]
        with patch.object(usb.sys.stdin, 'isatty', return_value=False), patch.object(usb.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'interactive'):
                usb.confirm_format('/dev/sdb1', part, ('original',))
            run.assert_not_called()
        with patch.object(usb.sys.stdin, 'isatty', return_value=True), patch('builtins.input', return_value='no'), \
                patch.object(usb.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'cancelled'):
                usb.confirm_format('/dev/sdb1', part, ('original',))
            run.assert_not_called()

    def test_device_swap_during_countdown_never_unmounts_or_formats(self):
        part = self.disks[1]['children'][0]
        with patch.object(usb.sys.stdin, 'isatty', return_value=True), \
                patch('builtins.input', return_value='ERASE /dev/sdb1'), \
                patch.object(usb.time, 'sleep'), patch.object(usb, 'inspect', return_value=(part, ('replacement',))), \
                patch.object(usb.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'changed'):
                usb.confirm_format('/dev/sdb1', part, ('original',))
            run.assert_not_called()

    def test_labelled_mounted_usb_is_preserved(self):
        part = {**self.disks[1]['children'][0], 'maj:min': '8:17'}
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(usb.Path, 'resolve', return_value=Path('/dev/sdb1')), \
                patch.object(usb, 'inspect', return_value=(part, ('original',))), \
                patch.object(usb.os.path, 'ismount', return_value=True), \
                patch.object(usb, 'run', return_value='8:17'), \
                patch.object(usb, 'confirm_format') as erase, patch.object(usb.subprocess, 'run') as commands:
            usb.prepare('/dev/sdb1', Path(directory), Path('unused.tar'))
            erase.assert_not_called()
            commands.assert_not_called()

    def test_symlink_to_mounted_library_is_preserved(self):
        part = {**self.disks[1]['children'][0], 'maj:min': '8:17'}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            device = root / 'device'
            device.touch()
            mounted = root / 'mounted-usb'
            mounted.mkdir()
            (mounted / 'existing-content').write_text('keep')
            link = root / 'Library'
            link.symlink_to(mounted, target_is_directory=True)
            with patch.object(usb, 'inspect', return_value=(part, ('original',))), \
                    patch.object(usb.os.path, 'ismount', side_effect=lambda p: p == mounted), \
                    patch.object(usb, 'run', return_value='8:17'), \
                    patch.object(usb, 'confirm_format') as erase, patch.object(usb.subprocess, 'run') as commands:
                usb.prepare(device, link, root / 'unused.tar')
                erase.assert_not_called()
                commands.assert_not_called()
            self.assertTrue(link.is_symlink())
            self.assertEqual((mounted / 'existing-content').read_text(), 'keep')


class ProgressTests(unittest.TestCase):
    def test_existing_private_directory_permissions_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(progress, 'launch_browser', return_value=False):
            root = Path(directory)
            root.chmod(0o700)
            self.assertEqual(progress.run([sys.executable, '-c', 'pass'], root, root / 'install.log'), 0)
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)
            self.assertTrue((root / 'progress.html').is_file())

    def exercise(self, statement, expected):
        with tempfile.TemporaryDirectory() as directory, patch.object(progress, 'launch_browser', return_value=False):
            root = Path(directory)
            code = progress.run([sys.executable, '-c', statement], root / 'state', root / 'install.log')
            self.assertEqual(code, expected)
            state = json.loads((root / 'state/library-install-state.json').read_text())
            page = (root / 'state/progress.html').read_text()
            self.assertIn('http-equiv="refresh" content="15"', page)
            self.assertEqual(state['exit_code'], expected)
            return state, page

    def test_success_reaches_final_screen(self):
        state, page = self.exercise('print("[STEP] Starting services"); print("ready")', 0)
        self.assertEqual(state['status'], 'complete')
        self.assertIn('Library is ready', page)
        self.assertIn('http://localhost', page)

    def test_failed_build_stays_failed_and_escapes_log_html(self):
        state, page = self.exercise('print("[STEP] Building wiki"); print("<script>bad()</script>"); raise SystemExit(17)', 17)
        self.assertEqual(state['status'], 'failed')
        self.assertIn('Building wiki', state['stage'])
        self.assertIn('&lt;script&gt;', page)
        self.assertNotIn('<script>bad()</script>', page)
        self.assertNotIn('Library is ready', page)

    def test_missing_worker_updates_failure_instead_of_staying_running(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(progress, 'launch_browser', return_value=False):
            root = Path(directory)
            self.assertEqual(progress.run(['/no/such/installer'], root / 'state', root / 'install.log'), 1)
            self.assertEqual(json.loads((root / 'state/library-install-state.json').read_text())['status'], 'failed')


class MenuTests(unittest.TestCase):
    def test_menu_has_the_reference_options_and_explicit_rebuild_and_format(self):
        result = subprocess.run(['bash', '-c', 'source "$1"; show_main_menu', 'test', str(ROOT / 'bootstrap')],
                                text=True, capture_output=True, check=True)
        for label in ('Fresh Install', 'Reinstall / Upgrade', 'Restart Install', 'System Status',
                      'Install / Repair Clone', 'Configure Office', 'Rebuild Containers', 'Format Library USB'):
            self.assertIn(label, result.stdout)

    def test_menu_rebuild_failure_returns_to_menu_without_running_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / 'bootstrap'
            fake.write_text('#!/bin/bash\nprintf "ACTION:%s\\n" "$*"\nexit 19\n')
            fake.chmod(0o755)
            result = subprocess.run(['bash', '-c', 'source "$1"; SOURCE_DIR=$2; menu',
                                     'test', str(ROOT / 'bootstrap'), directory],
                                    input='7\nq\n', text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0)
            self.assertIn('ACTION:--rebuild', result.stdout)
            self.assertIn('Rebuild stopped', result.stderr)
            self.assertEqual(result.stdout.count('Fresh Install'), 2)


if __name__ == '__main__':
    unittest.main()
