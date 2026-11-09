"""Exercise Wi-Fi request validation and rollback without touching host networking."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'files/library_wifi.py'
spec = importlib.util.spec_from_file_location('library_wifi', SOURCE)
wifi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wifi)


class WifiTests(unittest.TestCase):
    def setUp(self):
        self.client = wifi.app.test_client()
        wifi.state.update(busy=False, message='')
        self.adapters = patch.object(wifi, 'devices', return_value=['wlp2s0']).start()
        self.nm = patch.object(wifi, 'nm', return_value='yes').start()
        self.addCleanup(patch.stopall)

    def form(self, **changes):
        self.client.get('/wifi/')
        with self.client.session_transaction() as session:
            token = session['token']
        data = dict(token=token, interface='wlp2s0', mode='internet', ssid='Home',
                    password='secret-password', confirm='yes')
        data.update(changes)
        return data

    def test_no_adapter_explains_hardware_requirement(self):
        self.adapters.return_value = []
        page = self.client.get('/wifi/')
        self.assertIn(b'No Wi-Fi adapter detected', page.data)
        self.assertNotIn(b'Switch Wi-Fi mode</button>', page.data)

    def test_nonlocal_host_is_rejected(self):
        self.assertEqual(self.client.get('/wifi/', headers={'Host': 'external.example'}).status_code, 403)

    def test_hotspot_creation_uses_selected_adapter_and_persists_mode(self):
        with patch.object(wifi.subprocess, 'run') as run:
            wifi.lock.acquire()
            wifi.switch('wlp2s0', 'hotspot', '', 'hotspot-password')
            run.assert_called_once_with(
                ['/usr/local/bin/library_configure_hotspot', 'wlp2s0'],
                capture_output=True, check=True, timeout=60)
        self.nm.assert_any_call('connection', 'modify', 'id', 'library-hotspot',
                                'connection.autoconnect', 'yes', 'connection.autoconnect-priority', '1000')

    def test_rejects_forged_requests_unknown_interfaces_and_invalid_passwords(self):
        for changes, code in [({'token': 'forged'}, 403), ({'interface': 'eth0'}, 400),
                              ({'confirm': ''}, 400), ({'mode': 'shell'}, 400),
                              ({'password': 'one\ntwo'}, 400), ({'ssid': ''}, 400)]:
            with patch.object(wifi.threading, 'Thread') as thread:
                result = self.client.post('/wifi/', data=self.form(**changes))
                self.assertEqual(result.status_code, code)
                thread.assert_not_called()

    def test_switch_is_delayed_until_response_and_password_is_not_echoed(self):
        with patch.object(wifi.threading, 'Thread') as thread:
            result = self.client.post('/wifi/', data=self.form())
            self.assertEqual(result.status_code, 303)
            thread.return_value.start.assert_called_once()
            self.assertIn(b'Changing Wi-Fi mode', self.client.get('/wifi/').data)
            self.assertNotIn(b'secret-password', self.client.get('/wifi/').data)
        wifi.lock.release()

    def test_unsupported_ap_is_rejected(self):
        self.nm.return_value = 'no'
        self.assertEqual(self.client.post('/wifi/', data=self.form(mode='hotspot')).status_code, 400)

    def test_failure_restores_previous_connection(self):
        def nm(*args, **kwargs):
            if args[:2] == ('-g', 'GENERAL.CON-UUID'):
                return 'previous-uuid'
            if args[0] == '--ask':
                raise subprocess.CalledProcessError(10, ['nmcli'])
            return ''
        self.nm.side_effect = nm
        wifi.lock.acquire()
        wifi.switch('wlp2s0', 'internet', 'Home', 'wrong-password')
        self.nm.assert_any_call('connection', 'up', 'uuid', 'previous-uuid', 'ifname', 'wlp2s0')
        self.assertIn('previous connection was restored', wifi.state['message'])
        self.assertFalse(wifi.lock.locked())

    def test_credentials_use_stdin_and_internet_mode_disables_hotspot_autoconnect(self):
        self.nm.return_value = 'active-uuid'
        wifi.lock.acquire()
        wifi.switch('wlp2s0', 'internet', 'Home', 'password')
        self.nm.assert_any_call('--ask', 'device', 'wifi', 'connect', 'Home', 'ifname', 'wlp2s0',
                                input='password\n')
        self.nm.assert_any_call('connection', 'modify', 'id', 'library-hotspot', 'connection.autoconnect', 'no')
