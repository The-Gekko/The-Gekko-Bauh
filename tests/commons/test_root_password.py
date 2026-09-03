"""Tests de validate_password (bauh.view.qt.root) con un 'sudo' simulado antepuesto al PATH."""
import importlib.util
import os
import shlex
import tempfile
import unittest
from unittest import mock

from bauh.commons import system

# 'sudo' simulado: registra argumentos, contraseña recibida por stdin y configuración regional,
# opcionalmente escribe un texto en stderr y termina con el código indicado
FAKE_SUDO_TEMPLATE = """#!/bin/sh
printf '%s\\n' "$@" > {args_file}
IFS= read -r password
printf '%s' "$password" > {password_file}
printf 'LANG=%s LC_ALL=%s LANGUAGE=%s' "$LANG" "$LC_ALL" "${{LANGUAGE-unset}}" > {env_file}
{stderr_cmd}
exit {exit_code}
"""


@unittest.skipUnless(importlib.util.find_spec('PyQt5') is not None, 'PyQt5 no disponible')
class ValidatePasswordTest(unittest.TestCase):

    def setUp(self):
        from bauh.view.qt.root import validate_password
        self.validate_password = validate_password

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bin_dir = os.path.join(self.tmp.name, 'bin')
        os.mkdir(self.bin_dir)
        self.args_file = os.path.join(self.tmp.name, 'args')
        self.password_file = os.path.join(self.tmp.name, 'password')
        self.env_file = os.path.join(self.tmp.name, 'env')

        # gen_env construye el PATH a partir de constantes del módulo, no de os.environ
        for attr in ('PATH', 'GLOBAL_INTERPRETER_PATH'):
            patcher = mock.patch.object(system, attr, f'{self.bin_dir}:{getattr(system, attr)}')
            patcher.start()
            self.addCleanup(patcher.stop)

    def _install_fake_sudo(self, exit_code: int, stderr_text: str = ''):
        script = FAKE_SUDO_TEMPLATE.format(args_file=shlex.quote(self.args_file),
                                           password_file=shlex.quote(self.password_file),
                                           env_file=shlex.quote(self.env_file),
                                           stderr_cmd=f"printf '%s' {shlex.quote(stderr_text)} >&2" if stderr_text else '',
                                           exit_code=exit_code)
        sudo_path = os.path.join(self.bin_dir, 'sudo')
        with open(sudo_path, 'w') as f:
            f.write(script)
        os.chmod(sudo_path, 0o755)

    def _read(self, path: str) -> str:
        with open(path) as f:
            return f.read()

    def test__must_accept_the_password_when_sudo_returns_zero(self):
        self._install_fake_sudo(exit_code=0)
        self.assertTrue(self.validate_password('s3cret'))

    def test__must_reject_the_password_when_sudo_fails_without_the_incorrect_password_text(self):
        self._install_fake_sudo(exit_code=1, stderr_text='sudo: user is not in the sudoers file.')

        # el motivo (distinto de una contraseña incorrecta) se registra en el log
        with self.assertLogs('bauh.view.qt.root', level='WARNING') as logs:
            self.assertFalse(self.validate_password('s3cret'))

        self.assertIn('user is not in the sudoers file', logs.output[0])

    def test__must_reject_the_password_when_sudo_reports_an_incorrect_password(self):
        self._install_fake_sudo(exit_code=1, stderr_text='sudo: 1 incorrect password attempt')
        self.assertFalse(self.validate_password('s3cret'))

    def test__must_send_the_password_through_stdin_and_never_as_an_argument(self):
        self._install_fake_sudo(exit_code=0)
        self.validate_password('s3cret pass')

        self.assertEqual('s3cret pass', self._read(self.password_file))
        self.assertEqual(['-S', '-k', '-v'], self._read(self.args_file).splitlines())

    def test__must_run_sudo_with_the_c_locale(self):
        self._install_fake_sudo(exit_code=0)

        with mock.patch.dict(os.environ, {'LANG': 'es_ES.UTF-8', 'LC_ALL': 'es_ES.UTF-8', 'LANGUAGE': 'es'}):
            self.validate_password('s3cret')

        self.assertEqual('LANG=C LC_ALL=C LANGUAGE=unset', self._read(self.env_file))

    def test__must_reject_the_password_when_sudo_is_not_available(self):
        with mock.patch.object(system, 'PATH', self.bin_dir), \
                mock.patch.object(system, 'GLOBAL_INTERPRETER_PATH', self.bin_dir), \
                self.assertLogs('bauh.view.qt.root', level='WARNING'):
            self.assertFalse(self.validate_password('s3cret'))
