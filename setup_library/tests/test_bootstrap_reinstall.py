"""Reinstall must update the selected checkout before executing a rebuild."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

BOOTSTRAP = Path(__file__).resolve().parents[2] / 'bootstrap'


class ReinstallTests(unittest.TestCase):
    def exercise(self, checkout=0, pull=0):
        with tempfile.TemporaryDirectory(prefix='library reinstall ') as directory:
            root = Path(directory)
            script = root / 'installer'
            script.write_text(BOOTSTRAP.read_text().replace('$EUID', '0').replace(
                '/run/lock/library-install.lock', str(root / 'install.lock')))
            trace = root / 'trace'
            (root / 'git').write_text('''#!/bin/bash
printf 'git:%s\\n' "$*" >> "$TRACE"
if [[ "$3" == rev-parse ]]; then exit "$CHECKOUT_STATUS"; fi
if [[ "$3" == pull ]]; then exit "$PULL_STATUS"; fi
exit 99
''')
            (root / 'bootstrap').write_text('#!/bin/bash\nprintf "bootstrap:%s\\n" "$*" >> "$TRACE"\n')
            for file in ('git', 'bootstrap'):
                (root / file).chmod(0o755)
            result = subprocess.run(['bash', '-c', 'source "$1"; preflight() { :; }; main --reinstall --yes',
                                     'test', str(script)], text=True, capture_output=True, timeout=5,
                                    env={**os.environ, 'PATH': directory + ':' + os.environ['PATH'],
                                         'TRACE': str(trace), 'CHECKOUT_STATUS': str(checkout),
                                         'PULL_STATUS': str(pull)})
            return result, trace.read_text().splitlines()

    def test_success_reexecutes_updated_checkout_after_fast_forward_pull(self):
        result, trace = self.exercise()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('pull --ff-only', trace[1])
        self.assertEqual(trace[2], 'bootstrap:--rebuild --yes')
        self.assertIn('library reinstall ', trace[0])

    def test_failed_pull_never_starts_rebuild(self):
        result, trace = self.exercise(pull=17)
        self.assertEqual(result.returncode, 17)
        self.assertEqual(len(trace), 2)
        self.assertFalse(any(t.startswith('bootstrap:') for t in trace))

    def test_missing_git_checkout_never_pulls_or_rebuilds(self):
        result, trace = self.exercise(checkout=1)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(trace), 1)


if __name__ == '__main__':
    unittest.main()
