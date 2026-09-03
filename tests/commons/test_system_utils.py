import os
import shlex
import tempfile
import unittest
from typing import Tuple
from unittest import mock

from bauh.commons import system
from bauh.commons.system import (
    ProcessHandler,
    SimpleProcess,
    gen_env,
    new_root_subprocess,
)

# 'sudo' simulado: registra los argumentos y la contraseña leída de stdin y ejecuta el comando restante
FAKE_SUDO_TEMPLATE = """#!/bin/sh
printf '%s\\n' "$@" > {args_file}
IFS= read -r password
printf '%s' "$password" > {password_file}
while [ "$#" -gt 0 ]; do
    case "$1" in
        -*) shift ;;
        *) break ;;
    esac
done
exec "$@"
"""

# 'notify-send' simulado: solo registra los argumentos recibidos
FAKE_NOTIFY_SEND_TEMPLATE = """#!/bin/sh
printf '%s\\n' "$@" > {args_file}
"""


def write_executable(path: str, content: str):
    with open(path, 'w') as f:
        f.write(content)

    os.chmod(path, 0o755)


def read_file(path: str) -> str:
    with open(path) as f:
        return f.read()


def handle_simple(proc: SimpleProcess) -> Tuple[bool, str]:
    """Ejecuta handle_simple sin watcher y cierra la tubería de salida para no dejar descriptores abiertos."""
    try:
        return ProcessHandler().handle_simple(proc, notify_watcher=False)
    finally:
        proc.instance.stdout.close()


class FakeSudoTestCase(unittest.TestCase):
    """Base para tests que necesitan un 'sudo' simulado localizable a través de 'extra_paths'."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bin_dir = os.path.join(self.tmp.name, 'bin')
        os.mkdir(self.bin_dir)
        self.args_file = os.path.join(self.tmp.name, 'args')
        self.password_file = os.path.join(self.tmp.name, 'password')
        write_executable(os.path.join(self.bin_dir, 'sudo'),
                         FAKE_SUDO_TEMPLATE.format(args_file=shlex.quote(self.args_file),
                                                   password_file=shlex.quote(self.password_file)))

    def sudo_args(self) -> list:
        return read_file(self.args_file).splitlines()


class TestSystemUtils(unittest.TestCase):

    def test_run_cmd(self):
        # Un test muy básico para verificar que run_cmd ejecuta y retorna salida
        res = system.run_cmd('echo test')
        self.assertEqual(res.strip(), 'test')

    def test_run_cmd_ignore_code(self):
        # Probamos el flag ignore_return_code
        res = system.run_cmd('echo test2', ignore_return_code=True)
        self.assertEqual(res.strip(), 'test2')


class GenEnvTest(unittest.TestCase):

    def test__must_force_the_c_locale_by_default_even_if_the_user_exports_lc_vars(self):
        with mock.patch.dict(os.environ, {'LANG': 'es_ES.UTF-8', 'LC_ALL': 'es_ES.UTF-8',
                                          'LC_MESSAGES': 'es_ES.UTF-8', 'LANGUAGE': 'es'}):
            env = gen_env()

        self.assertEqual('', env['LANG'])
        self.assertEqual('C', env['LC_ALL'])
        self.assertNotIn('LANGUAGE', env)

    def test__must_set_lc_all_to_the_given_lang(self):
        with mock.patch.dict(os.environ, {'LC_ALL': 'es_ES.UTF-8', 'LANGUAGE': 'es'}):
            env = gen_env(lang='en_US.UTF-8')

        self.assertEqual('en_US.UTF-8', env['LANG'])
        self.assertEqual('en_US.UTF-8', env['LC_ALL'])
        self.assertNotIn('LANGUAGE', env)

    def test__must_keep_the_user_locale_when_lang_is_none(self):
        with mock.patch.dict(os.environ, {'LANG': 'es_ES.UTF-8', 'LC_ALL': 'es_ES.UTF-8', 'LANGUAGE': 'es'}):
            env = gen_env(lang=None)

        self.assertEqual('es_ES.UTF-8', env['LANG'])
        self.assertEqual('es_ES.UTF-8', env['LC_ALL'])
        self.assertEqual('es', env['LANGUAGE'])


class SimpleProcessRootPasswordTest(FakeSudoTestCase):

    def test__must_send_the_root_password_through_stdin_and_never_as_an_argument(self):
        proc = SimpleProcess(['echo', 'hello'], root_password='s3cret pass', extra_paths={self.bin_dir})
        success, output = handle_simple(proc)

        self.assertTrue(success, output)
        self.assertEqual('hello\n', output)
        self.assertEqual('s3cret pass', read_file(self.password_file))
        self.assertEqual(['sudo', '-S', '-k', 'echo', 'hello'], proc.instance.args)
        self.assertEqual(['-S', '-k', 'echo', 'hello'], self.sudo_args())

    def test__must_send_the_root_password_through_stdin_when_using_the_shell(self):
        proc = SimpleProcess(['echo', 'hello world'], root_password='s3cret', extra_paths={self.bin_dir}, shell=True)
        success, output = handle_simple(proc)

        self.assertTrue(success, output)
        self.assertEqual('hello world\n', output)
        self.assertEqual('s3cret', read_file(self.password_file))
        # con shell=True Popen recibe la línea completa como único argumento (comportamiento heredado)
        self.assertEqual(["sudo -S -k echo 'hello world'"], proc.instance.args)
        self.assertEqual(['-S', '-k', 'echo', 'hello world'], self.sudo_args())

    def test__must_add_preserve_env_options_after_the_sudo_arguments(self):
        proc = SimpleProcess(['echo', 'x'], root_password='s3cret', extra_paths={self.bin_dir},
                             preserve_env={'DEBIAN_FRONTEND'})
        success, _ = handle_simple(proc)

        self.assertTrue(success)
        self.assertEqual(['-S', '-k', '--preserve-env=DEBIAN_FRONTEND', 'echo', 'x'], self.sudo_args())

    def test__must_not_use_sudo_nor_a_stdin_pipe_without_a_root_password(self):
        proc = SimpleProcess(['echo', 'hi'], extra_paths={self.bin_dir})
        success, output = handle_simple(proc)

        self.assertTrue(success)
        self.assertEqual('hi\n', output)
        self.assertEqual(['echo', 'hi'], proc.instance.args)
        self.assertIsNone(proc.instance.stdin)
        self.assertFalse(os.path.exists(self.args_file))


class NewRootSubprocessTest(FakeSudoTestCase):

    def test__must_send_the_root_password_through_stdin_and_never_as_an_argument(self):
        proc = new_root_subprocess(['echo', 'hello'], root_password='s3cret', extra_paths={self.bin_dir})
        out, err = proc.communicate()

        self.assertEqual(0, proc.returncode, err)
        self.assertEqual(b'hello\n', out)
        self.assertEqual('s3cret', read_file(self.password_file))
        self.assertEqual(['sudo', '-S', '-k', 'echo', 'hello'], proc.args)
        self.assertEqual(['-S', '-k', 'echo', 'hello'], self.sudo_args())

    def test__must_quote_the_arguments_when_using_the_shell(self):
        proc = new_root_subprocess(['echo', 'a b'], root_password='s3cret', extra_paths={self.bin_dir}, shell=True)
        out, err = proc.communicate()

        self.assertEqual(0, proc.returncode, err)
        self.assertEqual(b'a b\n', out)
        self.assertIsInstance(proc.args, str)
        self.assertNotIn('s3cret', proc.args)
        self.assertEqual(['-S', '-k', 'echo', 'a b'], self.sudo_args())

    def test__must_not_use_sudo_without_a_root_password(self):
        proc = new_root_subprocess(['echo', 'hi'], root_password=None, extra_paths={self.bin_dir})
        out, _ = proc.communicate()

        self.assertEqual(b'hi\n', out)
        self.assertEqual(['echo', 'hi'], proc.args)
        self.assertIsNone(proc.stdin)


class ShellQuotingTest(unittest.TestCase):

    def test__simple_process_must_quote_each_argument_when_using_the_shell(self):
        proc = SimpleProcess(['printf', '%s|%s', 'a b', '$HOME'], shell=True)
        success, output = handle_simple(proc)

        self.assertTrue(success, output)
        self.assertEqual('a b|$HOME', output)

    def test__run_cmd_must_quote_the_custom_user(self):
        with mock.patch.object(system.subprocess, 'run') as run:
            run.return_value = mock.Mock(returncode=0, stdout=b'')
            system.run_cmd('ls -l', custom_user='us er')

        self.assertEqual("runuser -u 'us er' -- ls -l", run.call_args[0][0])

    def test__execute_must_quote_the_custom_user_only_when_using_the_shell(self):
        with mock.patch.object(system.subprocess, 'run') as run:
            run.return_value = mock.Mock(returncode=0, stdout=b'')
            system.execute('ls -l', shell=True, custom_user='us er')
            self.assertEqual(["runuser -u 'us er' -- ls -l"], run.call_args[1]['args'])

            system.execute('ls -l', shell=False, custom_user='builder')
            self.assertEqual(['runuser', '-u', 'builder', '--', 'ls', '-l'], run.call_args[1]['args'])

    def test__notify_user_must_not_go_through_a_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            args_file = os.path.join(tmp, 'args')
            write_executable(os.path.join(tmp, 'notify-send'),
                             FAKE_NOTIFY_SEND_TEMPLATE.format(args_file=shlex.quote(args_file)))

            with mock.patch.dict(os.environ, {'PATH': f"{tmp}:{os.environ.get('PATH', '')}"}):
                system.notify_user("it's done; $(touch /tmp/pwned)", 'bauh', '/icon.png')

            self.assertEqual(['-a', 'bauh', '-i', '/icon.png', "it's done; $(touch /tmp/pwned)"],
                             read_file(args_file).splitlines())


if __name__ == '__main__':
    unittest.main()
