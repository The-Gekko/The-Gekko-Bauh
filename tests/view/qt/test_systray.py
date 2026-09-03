import importlib.util
import json
import logging
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

PYQT5_AVAILABLE = importlib.util.find_spec('PyQt5') is not None

if PYQT5_AVAILABLE:
    from bauh.view.core import tray_client
    from bauh.view.qt import systray


def new_completed_process(stdout: bytes = b'', stderr: bytes = b'', returncode: int = 0):
    return subprocess.CompletedProcess(args=['bauh-cli'], returncode=returncode, stdout=stdout, stderr=stderr)


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class TestGetCliCommand(unittest.TestCase):

    def setUp(self):
        self.logger = MagicMock(spec=logging.Logger)

    def test_returns_the_virtualenv_binary_as_a_list_of_arguments(self):
        with tempfile.TemporaryDirectory(prefix='bauh venv ') as venv:  # ruta con espacios a proposito
            bin_dir = os.path.join(venv, 'bin')
            os.makedirs(bin_dir)
            cli_path = os.path.join(bin_dir, systray.CLI_NAME)

            with open(cli_path, 'w') as f:
                f.write('')

            os.chmod(cli_path, 0o755)

            with patch.dict(os.environ, {'VIRTUAL_ENV': venv}, clear=False):
                os.environ.pop('APPIMAGE', None)
                cmd = systray.get_cli_command(self.logger)

            self.assertEqual([cli_path], cmd)

    def test_falls_back_to_the_cli_module_and_logs_the_reason(self):
        with patch.dict(os.environ, {}, clear=False), \
                patch.object(systray.os.path, 'isfile', return_value=False), \
                patch.object(systray.shutil, 'which', return_value=None):
            os.environ.pop('APPIMAGE', None)
            os.environ.pop('VIRTUAL_ENV', None)
            cmd = systray.get_cli_command(self.logger)

        self.assertEqual([sys.executable, '-m', 'bauh.cli.app'], cmd)
        self.logger.warning.assert_called()


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class TestListUpdates(unittest.TestCase):

    def setUp(self):
        self.logger = MagicMock(spec=logging.Logger)

    def test_parses_the_json_output(self):
        payload = json.dumps([{'id': '1', 'name': 'vim', 'version': '9.0', 'type': 'arch'}]).encode()

        with patch.object(systray, 'get_cli_command', return_value=['bauh-cli']), \
                patch.object(systray.subprocess, 'run', return_value=new_completed_process(stdout=payload)):
            updates = systray.list_updates(self.logger)

        self.assertEqual(1, len(updates))
        self.assertEqual('vim', updates[0].name)

    def test_returns_no_updates_when_the_output_is_not_valid_json(self):
        with patch.object(systray, 'get_cli_command', return_value=['bauh-cli']), \
                patch.object(systray.subprocess, 'run', return_value=new_completed_process(stdout=b'not json')):
            updates = systray.list_updates(self.logger)

        self.assertEqual([], updates)
        self.logger.warning.assert_called()

    def test_returns_no_updates_when_the_command_times_out(self):
        error = subprocess.TimeoutExpired(cmd='bauh-cli', timeout=1)

        with patch.object(systray, 'get_cli_command', return_value=['bauh-cli']), \
                patch.object(systray.subprocess, 'run', side_effect=error):
            updates = systray.list_updates(self.logger, timeout=1)

        self.assertEqual([], updates)
        self.logger.warning.assert_called()

    def test_passes_a_timeout_to_the_subprocess(self):
        with patch.object(systray, 'get_cli_command', return_value=['bauh-cli']), \
                patch.object(systray.subprocess, 'run', return_value=new_completed_process()) as run:
            systray.list_updates(self.logger, timeout=30)

        self.assertEqual(30, run.call_args.kwargs['timeout'])


@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class TestTrayClient(unittest.TestCase):

    def test_the_tray_check_file_is_specific_to_the_fork(self):
        self.assertTrue(tray_client.TRAY_CHECK_FILE.endswith('notify_tray_gekko'))

    def test_manage_window_pid_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = os.path.join(tmp, 'manage_window.pid')

            with patch.object(tray_client, 'MANAGE_WINDOW_PID_FILE', pid_file), \
                    patch.object(tray_client, 'TEMP_DIR', tmp):
                tray_client.register_manage_window()
                self.assertEqual(os.getpid(), tray_client.read_manage_window_pid())
                self.assertTrue(tray_client.is_manage_window_running())

    def test_a_dead_pid_is_not_reported_as_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = os.path.join(tmp, 'manage_window.pid')

            with open(pid_file, 'w') as f:
                f.write('0')

            with patch.object(tray_client, 'MANAGE_WINDOW_PID_FILE', pid_file):
                self.assertFalse(tray_client.is_manage_window_running())

    def test_a_missing_pid_file_is_not_reported_as_running(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(tray_client, 'MANAGE_WINDOW_PID_FILE', os.path.join(tmp, 'absent.pid')):
            self.assertIsNone(tray_client.read_manage_window_pid())
            self.assertFalse(tray_client.is_manage_window_running())


if __name__ == '__main__':
    unittest.main()
