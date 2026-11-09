#!/usr/bin/python3
"""NetworkManager controls for the local Library desktop, bound to loopback."""
from pathlib import Path
import secrets
import subprocess
import threading
import time

from flask import Flask, abort, redirect, render_template_string, request, session

app = Flask(__name__)
app.secret_key = secrets.token_bytes(32)
app.config.update(SESSION_COOKIE_NAME='library_wifi', SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE='Strict', MAX_CONTENT_LENGTH=8192)
lock = threading.Lock()
state = {'busy': False, 'message': ''}


@app.before_request
def local_host_only():
    # Reject DNS rebinding to the loopback listener.
    if request.host.split(':', 1)[0] not in {'127.0.0.1', 'localhost'}:
        abort(403)


def nm(*args, input=None):
    return subprocess.run(['nmcli', '--wait', '35', *args], input=input, text=True,
                          capture_output=True, check=True, timeout=45).stdout.strip()


def devices():
    # sysfs names cannot contain newlines; use one property per query to avoid
    # parsing nmcli's escaped SSIDs and profile names as delimiters.
    return [p.name for p in sorted(Path('/sys/class/net').glob('*'))
            if (p / 'wireless').exists()]


def device_status(interface):
    return nm('-g', 'GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS', 'device', 'show', interface)


def switch(interface, mode, ssid, password):
    previous = ''
    try:
        previous = nm('-g', 'GENERAL.CON-UUID', 'device', 'show', interface)
        nm('radio', 'wifi', 'on')
        if mode == 'hotspot':
            subprocess.run(['/usr/local/bin/library_configure_hotspot', interface],
                           capture_output=True, check=True, timeout=60)
            nm('connection', 'modify', 'id', 'library-hotspot', 'connection.autoconnect', 'yes',
               'connection.autoconnect-priority', '1000')
        else:
            # --ask reads credentials from stdin, keeping passwords out of argv
            # and the service log. Saved NetworkManager credentials are reused.
            nm('--ask', 'device', 'wifi', 'connect', ssid, 'ifname', interface,
               input=password + '\n')
            active = nm('-g', 'GENERAL.CON-UUID', 'device', 'show', interface)
            nm('connection', 'modify', 'uuid', active, 'connection.autoconnect', 'yes')
            # Keep the selected internet mode after reboot as well.
            try:
                nm('connection', 'modify', 'id', 'library-hotspot', 'connection.autoconnect', 'no')
            except subprocess.CalledProcessError:
                pass
        state['message'] = 'Wi-Fi mode changed successfully.'
    except (OSError, subprocess.SubprocessError):
        state['message'] = 'Could not connect. Check the password, Wi-Fi radio, and adapter support.'
        if previous and previous != '--':
            try:
                nm('connection', 'up', 'uuid', previous, 'ifname', interface)
                state['message'] += ' The previous connection was restored.'
            except (OSError, subprocess.SubprocessError):
                state['message'] += ' Use the desktop shortcut to reconnect.'
    finally:
        state['busy'] = False
        lock.release()


def delayed_switch(*args):
    # Return the explanation before changing the connection carrying the page.
    time.sleep(3)
    switch(*args)


PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Library Wi-Fi</title>
{% if busy %}<meta http-equiv="refresh" content="8">{% endif %}
<style>body{font:18px system-ui;background:#101a29;color:#ecf1fa;max-width:750px;margin:3em auto;padding:20px}fieldset{margin:20px 0;padding:20px}label{display:block;margin:12px 0}input,select,button{font:inherit;padding:10px;max-width:100%;box-sizing:border-box}button,a{color:#12634a}pre{white-space:pre-wrap}small{display:block}</style>
<a href="http://localhost/">Library home</a><h1>Wi-Fi</h1>
<p>A single Wi-Fi adapter uses either hotspot mode or internet Wi-Fi mode. Switching disconnects devices using the hotspot. Ethernet stays available.</p>
{% if message %}<p role="status">{{ message }}</p>{% endif %}
{% if busy %}<p>Changing Wi-Fi mode. This page will refresh. If disconnected, reconnect to the selected network or open this page from the Library desktop.</p>{% endif %}
{% if not adapters %}<p>No Wi-Fi adapter detected. Connect a supported Wi-Fi adapter, then refresh this page.</p>{% endif %}
{% for adapter, status in adapters %}<h2>{{ adapter }}</h2><pre>{{ status }}</pre>{% endfor %}
{% if adapters and not busy %}
<form method="post" action="/wifi/">
<input type="hidden" name="token" value="{{ token }}">
<label>Wi-Fi adapter <select name="interface">{% for adapter, status in adapters %}<option>{{ adapter }}</option>{% endfor %}</select></label>
<fieldset><legend>Choose mode</legend>
<label><input type="radio" name="mode" value="internet" checked> Connect to internet Wi-Fi</label>
<label>Network name (SSID)<input name="ssid" maxlength="32" autocomplete="off"></label>
<label><input type="radio" name="mode" value="hotspot"> Library hotspot (network name: library)</label>
<small>The library hotspot is open and requires no password. Hotspot mode requires an adapter with access-point support. Its address is http://10.1.1.1/.</small>
<label>Internet Wi-Fi password <input type="password" name="password" maxlength="63" autocomplete="new-password"></label>
<small>For internet Wi-Fi, enter the network password or leave blank to reuse saved credentials. The library hotspot never uses a password.</small>
</fieldset><label><input type="checkbox" name="confirm" value="yes" required> I understand Wi-Fi clients may disconnect.</label>
<button>Switch Wi-Fi mode</button></form>{% endif %}</html>'''


@app.route('/wifi/', methods=['GET', 'POST'])
def wifi():
    session.setdefault('token', secrets.token_urlsafe(32))
    if request.method == 'POST':
        if not secrets.compare_digest(request.form.get('token', ''), session['token']):
            abort(403)
        interface = request.form.get('interface', '')
        mode = request.form.get('mode', '')
        ssid = request.form.get('ssid', '')
        password = request.form.get('password', '') if mode == 'internet' else ''
        if (interface not in devices() or mode not in {'hotspot', 'internet'}
                or request.form.get('confirm') != 'yes' or '\n' in password or '\r' in password
                or len(password) > 63
                or (mode == 'internet' and not 1 <= len(ssid.encode()) <= 32)):
            abort(400)
        if mode == 'hotspot':
            try:
                if nm('-g', 'WIFI-PROPERTIES.AP', 'device', 'show', interface) != 'yes':
                    return 'This adapter does not support hotspot mode. Return to Wi-Fi settings.', 400
            except (OSError, subprocess.SubprocessError):
                return 'Could not check hotspot support. Check NetworkManager.', 400
        if not lock.acquire(blocking=False):
            abort(409)
        state.update(busy=True, message='Wi-Fi change scheduled.')
        threading.Thread(target=delayed_switch, args=(interface, mode, ssid, password), daemon=True).start()
        return redirect('/wifi/', code=303)
    adapters = []
    for interface in devices():
        try:
            status = device_status(interface)
        except (OSError, subprocess.SubprocessError):
            status = 'NetworkManager is unavailable or this adapter is unmanaged.'
        adapters.append((interface, status))
    response = app.make_response(render_template_string(PAGE, adapters=adapters, token=session['token'], **state))
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Frame-Options'] = 'DENY'
    return response
