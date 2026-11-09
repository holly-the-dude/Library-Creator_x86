#!/usr/bin/env python3
"""Capture installer output and publish an atomically updated local Firefox page."""
import argparse
import codecs
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time

STATE_DIR = Path('/root')
STATE_FILE = 'library-install-state.json'
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')


def atomic(path, text):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(text)
    temporary.chmod(0o644)
    temporary.replace(path)


def publish(directory, status, stage, output, code=None, operation='installation'):
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    title = {'running': f'Library {operation} in progress',
             'complete': 'Library is ready' if operation == 'installation' else f'Library {operation} complete',
             'failed': f'Library {operation} stopped'}[status]
    safe = html.escape('\n'.join(ANSI.sub('', output).splitlines()[-30:]))
    final = ('<p><a href="http://localhost">Open your Library</a></p>' if status == 'complete' and operation != 'USB formatting'
             else '<p>The USB partition is ready. Return to the terminal menu to install Library.</p>' if status == 'complete'
             else '<p>Read the error below, correct it, and choose Restart Install.</p>' if status == 'failed'
             else '<p>Keep this machine powered on. Terminal prompts must be answered in the installer terminal.</p>')
    if status == 'complete' and operation == 'installation':
        title = 'Installation complete — reboot scheduled'
        stage = 'This machine will reboot automatically within one minute.'
        final = ('<p>Keep this machine powered on while it restarts. '
                 'The browser will close during the reboot. On supported desktops, '
                 'Firefox will open your Library automatically after startup.</p>')
    atomic(directory / STATE_FILE, json.dumps({'status': status, 'operation': operation, 'stage': stage,
           'updated': now, 'exit_code': code}, indent=2) + '\n')
    atomic(directory / 'progress.html', f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="15">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>body{{font:18px system-ui,sans-serif;background:#101a29;color:#ecf1fa;margin:0}}
main{{max-width:1100px;margin:4vh auto;padding:24px}}h1{{font-size:2.4rem}}
.stage{{padding:18px;background:#21334d;border-left:5px solid #55b9ef}}
pre{{font:14px monospace;white-space:pre-wrap;overflow-wrap:anywhere;padding:20px;
max-height:45vh;overflow:auto;
background:#09121e;border-radius:8px}}a{{display:inline-block;padding:12px 22px;
background:#91e3bd;color:#08291b;border-radius:6px}}small{{color:#adbed5}}</style></head>
<body><main><h1>{html.escape(title)}</h1><p class="stage">{html.escape(stage)}</p>{final}
<small>Last 30 lines · Refreshes every 15 seconds · Updated {now}<br>
Full output: installer terminal and /var/log/library-installer/install.log</small>
<pre>{safe}</pre></main>
<script>
window.addEventListener('pageshow', () => requestAnimationFrame(() => {{
    window.scrollTo(0, 0);
    const output = document.querySelector('pre');
    output.scrollTop = output.scrollHeight;
}}));
</script></body></html>''')


def launch_browser(page):
    """Join the logged-in desktop session, including the root Library desktop."""
    browser = shutil.which('firefox') or shutil.which('firefox-esr')
    if not browser:
        print('[INFO] Firefox is not installed yet; the progress page is available at ' + str(page), flush=True)
        return False
    sessions = subprocess.run(['loginctl', 'list-sessions', '--no-legend'],
                              text=True, capture_output=True, check=True)
    candidates = []
    for line in sessions.stdout.splitlines():
        session = line.split()[0]
        result = subprocess.run(['loginctl', 'show-session', session,
            '-p', 'Active', '-p', 'Remote', '-p', 'Type', '-p', 'Name', '-p', 'User', '-p', 'Display'],
            text=True, capture_output=True, check=True)
        info = dict(x.split('=', 1) for x in result.stdout.splitlines() if '=' in x)
        if (info.get('Active') == 'yes' and info.get('Remote') == 'no'
                and info.get('Type') in {'wayland', 'x11'}):
            candidates.append(info)
    if len(candidates) != 1:
        print(f'[INFO] No single active desktop session. Open {page.as_uri()} in Firefox after logging in.', flush=True)
        return False
    info = candidates[0]
    runtime = Path('/run/user') / info['User']
    env = [f'XDG_RUNTIME_DIR={runtime}', f'DBUS_SESSION_BUS_ADDRESS=unix:path={runtime}/bus']
    if info['Type'] == 'wayland':
        sockets = [p for p in runtime.glob('wayland-*') if stat.S_ISSOCK(p.stat().st_mode)]
        if len(sockets) != 1:
            print('[INFO] Cannot select a unique Wayland display; open the progress file manually.', flush=True)
            return False
        env += [f'WAYLAND_DISPLAY={sockets[0].name}', 'MOZ_ENABLE_WAYLAND=1']
    else:
        if not info.get('Display'):
            return False
        env += [f'DISPLAY={info["Display"]}']
    if page.resolve().is_relative_to('/root') and info['User'] != '0':
        # Firefox runs as the desktop user. Permit traversal to this readable
        # page without granting directory listing or access to private files.
        subprocess.run(['setfacl', '-m', f'u:{info["User"]}:--x', '/root'], check=True)
    browser_log = Path('/var/log/library-installer/firefox.log')
    browser_log.parent.mkdir(parents=True, exist_ok=True)
    with browser_log.open('a') as output:
        browser_log.chmod(0o600)
        process = subprocess.Popen(['runuser', '-u', info['Name'], '--', 'env', *env,
                          browser, '--new-window', page.as_uri()],
                         stdin=subprocess.DEVNULL, stdout=output,
                         stderr=output, start_new_session=True)
    try:
        code = process.wait(timeout=3)
        if code != 0:
            print(f'[WARN] Firefox failed to open; see {browser_log}.', flush=True)
            return False
    except subprocess.TimeoutExpired:
        pass
    print(f'[INFO] Firefox opened {page.as_uri()} for {info["Name"]}.', flush=True)
    return True


def run(command, directory=STATE_DIR, log=Path('/var/log/library-installer/install.log'), operation='installation'):
    directory.mkdir(mode=0o755, parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    stage = 'Starting installer'
    output = ''
    publish(directory, 'running', stage, output, operation=operation)
    opened = False
    try:
        opened = launch_browser(directory / 'progress.html')
    except (OSError, subprocess.SubprocessError) as exc:
        print(f'[INFO] Browser launch unavailable: {exc}', flush=True)
    decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
    code = 1
    with log.open('a') as stream:
        log.chmod(0o600)
        stream.write('\n=== Library install ' + datetime.now(timezone.utc).isoformat() + ' ===\n')
        stream.flush()
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       start_new_session=True,
                                       env={**os.environ, 'LIBRARY_PROGRESS_BROWSER_OPENED': '1' if opened else '0'})
        except OSError as exc:
            publish(directory, 'failed', 'Could not start the installer', str(exc), 1, operation)
            return 1
        poller = selectors.DefaultSelector()
        poller.register(process.stdout, selectors.EVENT_READ)
        last = 0
        try:
            while poller.get_map():
                for key, _ in poller.select(timeout=1):
                    data = os.read(key.fileobj.fileno(), 16384)
                    if not data:
                        poller.unregister(key.fileobj)
                        continue
                    text = decoder.decode(data)
                    sys.stdout.write(text)
                    sys.stdout.flush()
                    stream.write(text)
                    stream.flush()
                    output = (output + text)[-24000:]
                    stages = re.findall(r'\[STEP\] ([^\r\n]+)', ANSI.sub('', output))
                    if stages:
                        stage = stages[-1]
                if time.monotonic() - last >= 1:
                    publish(directory, 'running', stage, output, operation=operation)
                    last = time.monotonic()
            code = process.wait()
        except KeyboardInterrupt:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
            output += '\nInstallation cancelled from the terminal.\n'
            code = 130
        finally:
            poller.close()
            process.stdout.close()
            publish(directory, 'complete' if code == 0 else 'failed',
                    f'{operation.capitalize()} complete' if code == 0 else f'{stage} (exit {code})', output, code, operation)
    return code


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--operation', default='installation')
    parser.add_argument('--directory', type=Path, default=STATE_DIR)
    parser.add_argument('--log', type=Path, default=Path('/var/log/library-installer/install.log'))
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.open:
        sys.exit(0 if launch_browser(args.directory / 'progress.html') else 1)
    else:
        command = args.command[1:] if args.command[:1] == ['--'] else args.command
        if not command:
            parser.error('An installer command is required')
        sys.exit(run(command, args.directory, args.log, args.operation))
