import os
import pickle
import warnings
from tempfile import TemporaryDirectory
from unittest import TestCase

from bauh.gems.arch import proc_util


class ProcUtilTest(TestCase):
    """Escritura de ficheros como otro usuario (F139)."""

    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings('ignore', category=DeprecationWarning)

    def test_the_multiprocessing_context_is_explicit(self):
        # el metodo por defecto cambia entre versiones de Python (fork hasta 3.13, forkserver
        # en 3.14): se fija para tener el mismo comportamiento en 3.8-3.14
        self.assertEqual('forkserver', proc_util._MP_START_METHOD)
        self.assertEqual('forkserver', proc_util._mp_context.get_start_method())

    def test_targets_are_picklable(self):
        # 'forkserver' serializa el objetivo con pickle: clases de modulo si, lambdas no
        target = proc_util.WriteToFile(file_path='/tmp/x', content='y')
        self.assertIsInstance(pickle.loads(pickle.dumps(target)), proc_util.WriteToFile)

        as_user = proc_util.CallAsUser(target, 'bauh-aur')
        self.assertIsInstance(pickle.loads(pickle.dumps(as_user)), proc_util.CallAsUser)

    def test_write_as_user__without_user_writes_in_the_current_process(self):
        with TemporaryDirectory() as temp_dir:
            file_path = f'{temp_dir}/PKGBUILD'

            self.assertTrue(proc_util.write_as_user(content='pkgname=test\n', file_path=file_path))

            with open(file_path) as f:
                self.assertEqual('pkgname=test\n', f.read())

    def test_write_as_user__returns_false_when_the_path_is_not_writable(self):
        with TemporaryDirectory() as temp_dir:
            file_path = f'{temp_dir}/no_existe/PKGBUILD'

            with self.assertLogs(level='ERROR'):  # el fallo se registra, no se propaga
                self.assertFalse(proc_util.write_as_user(content='x', file_path=file_path))

            self.assertFalse(os.path.exists(file_path))

    def test_exec_as_user__without_user_calls_the_target_directly(self):
        calls = []

        def target():
            calls.append(os.getpid())
            return 'hecho'

        self.assertEqual('hecho', proc_util.exec_as_user(target))
        self.assertEqual([os.getpid()], calls)
