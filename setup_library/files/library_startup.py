#!/usr/bin/python3
"""Show Ansible startup progress in the desktop browser without needing nginx."""
from collections import deque
import html
from pathlib import Path
import re
import subprocess
import sys

PAGE = Path('/run/library-startup/progress.html')
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')


def publish(stage, lines=(), status='running', page=PAGE):
    page.parent.mkdir(parents=True, exist_ok=True)
    refresh = ('<meta http-equiv="refresh" content="2">' if status == 'running' else
               '<meta http-equiv="refresh" content="2;url=http://localhost/">' if status == 'complete' else '')
    title = {'running': 'Starting your Library', 'complete': 'Your Library is ready',
             'failed': 'Library startup needs attention'}[status]
    message = {'running': 'Ansible is starting the Library services. This page updates automatically.',
               'complete': 'Opening the Library homepage…',
               'failed': 'Startup stopped. Check the details below or ask the operator for help.'}[status]
    content = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">{refresh}
<title>{title}</title><style>body{{font:20px system-ui;background:#101a29;color:#ecf1fa;margin:6vh auto;padding:24px;max-width:1000px}}h1{{font-size:2.4rem}}.stage{{padding:20px;background:#21334d;border-left:5px solid #55b9ef}}pre{{font:14px monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#09121e;padding:20px}}a{{color:#91e3bd}}</style></head>
<body><h1>{title}</h1><p>{message}</p><p class="stage">{html.escape(stage)}</p>
<details><summary>Startup details</summary><pre>{html.escape(chr(10).join(lines))}</pre></details>
<p><a href="http://localhost/">Open Library</a></p></body></html>'''
    temporary = page.with_suffix('.tmp')
    temporary.write_text(content)
    temporary.chmod(0o644)
    temporary.replace(page)


def run(command, page=PAGE):
    stage = 'Preparing Library services'
    lines = deque(maxlen=30)
    publish(stage, page=page)
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, bufsize=1)
        for line in process.stdout:
            print(line, end='', flush=True)
            clean = ANSI.sub('', line).rstrip()
            lines.append(clean)
            task = re.search(r'TASK \[(.+)\]', clean)
            if task:
                stage = task[1]
            publish(stage, lines, page=page)
        process.stdout.close()
        code = process.wait()
    except OSError as error:
        lines.append(str(error))
        code = 1
    publish('Services started' if code == 0 else f'{stage} (exit {code})', lines,
            status='complete' if code == 0 else 'failed', page=page)
    return code


if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
