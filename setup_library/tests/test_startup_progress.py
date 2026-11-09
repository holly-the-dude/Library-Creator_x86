"""Check boot progress, failure reporting, and immediate browser startup."""
import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

FILES = Path(__file__).resolve().parents[1] / 'files'


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


startup = load('library_startup', FILES / 'library_startup.py')
browser = load('library_browser', FILES / 'library_browser')


class StartupTests(unittest.TestCase):
    def test_running_page_shows_task_and_refreshes_without_redirect(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / 'progress.html'
            startup.publish('Start Maps <unsafe>', ['<script>bad()</script>'], page=page)
            content = page.read_text()
            self.assertIn('Ansible is starting', content)
            self.assertIn('content="2"', content)
            self.assertIn('Start Maps &lt;unsafe&gt;', content)
            self.assertNotIn('<script>bad()', content)
            self.assertNotIn('url=http://localhost/', content)

    def test_success_redirects_and_failure_retains_error(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / 'progress.html'
            self.assertEqual(startup.run([sys.executable, '-c', 'print("TASK [Start Maps]")'], page), 0)
            self.assertIn('url=http://localhost/', page.read_text())
            code = startup.run([sys.executable, '-c', 'print("TASK [Start LMS]"); raise SystemExit(2)'], page)
            self.assertEqual(code, 2)
            self.assertIn('Start LMS (exit 2)', page.read_text())
            self.assertIn('needs attention', page.read_text())
            self.assertNotIn('http-equiv="refresh"', page.read_text())

    def test_missing_ansible_is_a_visible_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / 'progress.html'
            self.assertEqual(startup.run(['/missing-ansible'], page), 1)
            self.assertIn('missing-ansible', page.read_text())

    def test_browser_opens_progress_immediately_and_preserves_existing_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def local_path(value):
                return root / str(value).lstrip('/')
            with patch.object(browser.os, 'getuid', return_value=0), \
                    patch.object(browser.shutil, 'which', return_value='/usr/bin/firefox'), \
                    patch.object(browser, 'Path', side_effect=local_path), \
                    patch.object(browser.os, 'execv') as launch:
                browser.main()
                page = root / 'run/library-startup/progress.html'
                self.assertIn('Waiting for Ansible', page.read_text())
                self.assertEqual(launch.call_args.args[1][-1], page.as_uri())
                page.write_text('Starting ebooks')
                browser.main()
                self.assertEqual(page.read_text(), 'Starting ebooks')
