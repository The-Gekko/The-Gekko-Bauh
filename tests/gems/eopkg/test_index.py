"""Estado de sincronización del índice de repositorios y su efecto en el arranque.

Todo esto existe por un fallo concreto: ``eopkg list-upgrades`` responde a partir del índice
local, así que sin un ``eopkg ur`` previo bauh daba el sistema por actualizado aunque Solus
hubiese publicado paquetes ese mismo día.
"""

import os
import tempfile
import time
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from bauh.api.abstract.controller import SoftwareAction
from bauh.gems.eopkg import controller, index
from bauh.gems.eopkg.controller import EopkgManager
from bauh.gems.eopkg.worker import SyncRepositories


class _Dirs:
    """Directorio temporal con una marca de sincronización y un índice falsos."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sync_file = os.path.join(self.tmp.name, 'cache', 'repo_sync')
        self.index_dir = os.path.join(self.tmp.name, 'index')

    def write_sync_file(self, moment: datetime):
        os.makedirs(os.path.dirname(self.sync_file), exist_ok=True)

        with open(self.sync_file, 'w') as handle:
            handle.write(str(int(moment.timestamp())))

    def write_index(self, moment: datetime, name: str = 'eopkg-index.xml.xz'):
        repo_dir = os.path.join(self.index_dir, 'Solus')
        os.makedirs(repo_dir, exist_ok=True)
        index_file = os.path.join(repo_dir, name)

        with open(index_file, 'w') as handle:
            handle.write('x')

        os.utime(index_file, (moment.timestamp(), moment.timestamp()))
        return index_file

    def cleanup(self):
        self.tmp.cleanup()


class IndexSyncStateTest(unittest.TestCase):

    def setUp(self):
        self.dirs = _Dirs()
        self.addCleanup(self.dirs.cleanup)
        patcher = patch.multiple(index, SYNC_FILE=self.dirs.sync_file,
                                 INDEX_DIR=self.dirs.index_dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_should_sync__when_it_was_never_synchronized(self):
        self.assertTrue(index.should_sync())

    def test_should_not_sync__when_bauh_already_synced_today(self):
        self.dirs.write_sync_file(datetime.now())

        self.assertFalse(index.should_sync())

    def test_should_sync__when_the_last_sync_was_yesterday(self):
        self.dirs.write_sync_file(datetime.now() - timedelta(days=1))

        self.assertTrue(index.should_sync())

    def test_should_not_sync__when_the_index_itself_is_from_today(self):
        # 'sudo eopkg ur' desde una terminal o el Centro de Software no deja marca de bauh:
        # pedir la contraseña de root otra vez sería molestar sin motivo
        self.dirs.write_index(datetime.now())

        self.assertFalse(index.should_sync())

    def test_should_sync__when_both_sources_are_old(self):
        old = datetime.now() - timedelta(days=3)
        self.dirs.write_sync_file(old)
        self.dirs.write_index(old)

        self.assertTrue(index.should_sync())

    def test_last_sync__must_take_the_most_recent_source(self):
        old = datetime.now() - timedelta(days=5)
        recent = datetime.now() - timedelta(hours=1)
        self.dirs.write_sync_file(old)
        self.dirs.write_index(recent)

        self.assertAlmostEqual(recent.timestamp(), index.last_sync().timestamp(), delta=2)

    def test_a_corrupt_sync_file_must_not_break_the_check(self):
        os.makedirs(os.path.dirname(self.dirs.sync_file), exist_ok=True)

        with open(self.dirs.sync_file, 'w') as handle:
            handle.write('no es una marca de tiempo')

        self.assertIsNone(index.last_sync())
        self.assertTrue(index.should_sync())

    def test_a_missing_index_directory_must_not_break_the_check(self):
        self.assertIsNone(index._index_date())
        self.assertTrue(index.should_sync())

    def test_register_sync__writes_a_readable_timestamp(self):
        index.register_sync()

        self.assertFalse(index.should_sync())
        self.assertAlmostEqual(time.time(), index.last_sync().timestamp(), delta=5)

    def test_a_clock_in_the_future_must_force_a_sync(self):
        # un arranque con la hora aún sin sincronizar no puede dejar a bauh sin ver
        # actualizaciones durante días
        self.dirs.write_sync_file(datetime.now() + timedelta(days=2))

        self.assertTrue(index.should_sync(reference=date.today()))

    def test_the_uri_file_must_not_pass_for_a_finished_download(self):
        # eopkg reescribe 'uri' ANTES de intentar la descarga (pisi/index.py,
        # read_uri_of_repo): si contase, un 'eopkg ur' caído por falta de red pasaría por
        # sincronización buena, no se avisaría y no se reintentaría hasta el día siguiente
        old = datetime.now() - timedelta(days=3)
        self.dirs.write_index(old)
        self.dirs.write_index(old, name='eopkg-index.xml.xz.sha1sum')
        self.dirs.write_index(datetime.now(), name='uri')

        self.assertEqual(old.date(), index._index_date().date())
        self.assertTrue(index.should_sync())

    def test_a_partial_download_must_not_pass_for_a_finished_one(self):
        # '.part' / '.tmp' son justo la señal de que la descarga NO terminó
        self.dirs.write_index(datetime.now(), name='eopkg-index.xml.xz.part')
        self.dirs.write_index(datetime.now(), name='eopkg-index.xml.tmp')

        self.assertIsNone(index._index_date())
        self.assertTrue(index.should_sync())

    def test_the_sha1sum_of_a_finished_download_does_count(self):
        self.dirs.write_index(datetime.now(), name='eopkg-index.xml.xz.sha1sum')

        self.assertFalse(index.should_sync())

    def test_an_absurd_sync_mark_must_not_break_the_startup(self):
        # datetime.fromtimestamp lanza OverflowError, no ValueError: sin capturarlo la
        # excepción sube hasta requires_root(PREPARE) y tumba el arranque
        os.makedirs(os.path.dirname(self.dirs.sync_file), exist_ok=True)

        with open(self.dirs.sync_file, 'w') as handle:
            handle.write('99999999999999999999')

        self.assertIsNone(index._sync_file_date())
        self.assertTrue(index.should_sync())

    def test_an_absurd_index_date_must_not_break_the_startup(self):
        self.dirs.write_index(datetime.now())

        with patch.object(index.os.path, 'getmtime', return_value=1e19):
            self.assertIsNone(index._index_date())

    def test_an_index_dated_in_the_future_must_be_ignored(self):
        # un arranque anterior con el reloj mal puesto no puede obligar a pedir la contraseña
        # y sincronizar en cada arranque, ni anunciar un índice «desfasado» con fecha futura
        recent = datetime.now() - timedelta(hours=2)
        self.dirs.write_index(recent)
        self.dirs.write_index(datetime.now() + timedelta(days=5), name='eopkg-index.xml')

        self.assertAlmostEqual(recent.timestamp(), index._index_date().timestamp(), delta=2)
        self.assertFalse(index.should_sync())

    def test_an_index_dated_only_a_bit_ahead_still_counts(self):
        # un desfase pequeño (husos horarios, reloj con unos minutos de más) no invalida nada
        self.dirs.write_index(datetime.now() + timedelta(hours=2))

        self.assertIsNotNone(index._index_date())
        self.assertFalse(index.should_sync())


class SyncRepositoriesDecisionTest(unittest.TestCase):

    def test_is_enabled__defaults_to_true(self):
        self.assertTrue(SyncRepositories.is_enabled({}))
        self.assertTrue(SyncRepositories.is_enabled(None))

    def test_is_enabled__respects_the_setting(self):
        self.assertFalse(SyncRepositories.is_enabled({'sync_repos_startup': False}))

    def test_should_sync__is_false_when_disabled_even_if_the_index_is_old(self):
        with patch.object(index, 'should_sync', return_value=True):
            self.assertFalse(SyncRepositories.should_sync({'sync_repos_startup': False}))

    def test_should_sync__is_true_when_enabled_and_the_index_is_old(self):
        with patch.object(index, 'should_sync', return_value=True):
            self.assertTrue(SyncRepositories.should_sync({'sync_repos_startup': True}))


class _ExplodingStdout:
    """Salida que se cae a media lectura (descriptor cerrado, proceso matado desde fuera)."""

    def __iter__(self):
        return self

    def __next__(self):
        raise OSError('descriptor de salida caído')


class _BlockingStdout:
    """Salida de un 'eopkg ur' colgado contra un mirror que no responde."""

    def __iter__(self):
        return self

    def __next__(self):
        time.sleep(3600)


class SyncRepositoriesRunTest(unittest.TestCase):
    """El cuerpo de la tarea: es quien de verdad ejecuta 'eopkg ur' al arrancar."""

    def _new_task(self, config: dict) -> SyncRepositories:
        create_config = Mock()
        create_config.config = config
        create_config.task_name = 'config'
        # el I18n real devuelve la propia clave cuando falta; un dict pelado lanzaría KeyError
        i18n = {'task.waiting_task': '{}',
                'eopkg.action.update_repos.status': 'Actualizando los repositorios',
                'eopkg.task.disabled': 'off', 'eopkg.task.synchronized': 'ok',
                'eopkg.task.error': 'err'}
        return SyncRepositories(taskman=Mock(), root_password='secret', i18n=i18n,
                                logger=Mock(), create_config=create_config)

    @patch('bauh.gems.eopkg.worker.SimpleProcess')
    def test_run__must_execute_eopkg_ur_and_register_the_sync(self, simple_process: Mock):
        simple_process.return_value.instance.stdout = [b'Updating repository: Solus\n']
        simple_process.return_value.instance.returncode = 0
        task = self._new_task({'sync_repos_startup': True})
        invalidated = Mock()
        task.on_synchronized = invalidated

        with patch.object(index, 'should_sync', return_value=True), \
                patch.object(index, 'register_sync') as register:
            task.run()

        self.assertEqual(['eopkg', 'ur', '--no-color'], simple_process.call_args[0][0])
        self.assertTrue(task.synchronized)
        register.assert_called_once()
        # la caché de la sesión debe invalidarse: si no, se seguiría leyendo el índice viejo
        invalidated.assert_called_once()

    @patch('bauh.gems.eopkg.worker.SimpleProcess')
    def test_run__must_not_register_a_failed_sync(self, simple_process: Mock):
        # contraseña cancelada o 'eopkg ur' caído: registrar la marca dejaría a bauh creyendo
        # que el índice está al día y volvería a esconder las actualizaciones todo el día
        simple_process.return_value.instance.stdout = [b'permission denied\n']
        simple_process.return_value.instance.returncode = 1
        task = self._new_task({'sync_repos_startup': True})

        with patch.object(index, 'should_sync', return_value=True), \
                patch.object(index, 'register_sync') as register:
            task.run()

        self.assertFalse(task.synchronized)
        register.assert_not_called()

    @patch('bauh.gems.eopkg.worker.SimpleProcess')
    def test_run__must_do_nothing_when_disabled(self, simple_process: Mock):
        task = self._new_task({'sync_repos_startup': False})

        task.run()

        simple_process.assert_not_called()

    @patch('bauh.gems.eopkg.worker.SimpleProcess')
    def test_run__must_skip_when_the_index_is_already_fresh(self, simple_process: Mock):
        task = self._new_task({'sync_repos_startup': True})

        with patch.object(index, 'should_sync', return_value=False):
            task.run()

        simple_process.assert_not_called()
        self.assertTrue(task.synchronized)

    @patch('bauh.gems.eopkg.worker.SimpleProcess')
    def test_run__must_finish_the_task_when_reading_the_output_fails(self, simple_process: Mock):
        # si el hilo muere sin llamar a 'finish_task', el panel de arranque se queda esperando
        # una tarea que ya no existe y no aparece ningún botón con el que seguir
        simple_process.return_value.instance.stdout = _ExplodingStdout()
        task = self._new_task({'sync_repos_startup': True})

        with patch.object(index, 'should_sync', return_value=True), \
                patch.object(index, 'register_sync') as register:
            task.run()

        self.assertFalse(task.synchronized)
        register.assert_not_called()
        task.taskman.finish_task.assert_called_once_with(task.task_id)

    @patch('bauh.gems.eopkg.worker.SimpleProcess')
    def test_run__must_finish_the_task_when_waiting_fails(self, simple_process: Mock):
        simple_process.return_value.instance.stdout = []
        simple_process.return_value.instance.wait.side_effect = OSError('proceso perdido')
        task = self._new_task({'sync_repos_startup': True})

        with patch.object(index, 'should_sync', return_value=True):
            task.run()

        self.assertFalse(task.synchronized)
        task.taskman.finish_task.assert_called_once_with(task.task_id)

    @patch('bauh.gems.eopkg.worker.SimpleProcess')
    def test_run__must_strip_the_sudo_password_prompt(self, simple_process: Mock):
        simple_process.return_value.instance.stdout = [b'[sudo] password for gekko: Updating '
                                                       b'repository: Solus\n']
        simple_process.return_value.instance.returncode = 0
        task = self._new_task({'sync_repos_startup': True})

        with patch.object(index, 'should_sync', return_value=True), \
                patch.object(index, 'register_sync'):
            task.run()

        task.taskman.update_output.assert_called_once_with(task.task_id,
                                                           'Updating repository: Solus')


class PrepareTest(unittest.TestCase):
    """El arranque de la gem: sin esta sincronización no se ve ninguna actualización."""

    def setUp(self):
        self.manager = EopkgManager(Mock())
        self.manager.i18n = {}
        self.manager.logger = Mock()
        self.manager.configman = Mock()
        self.manager.configman.get_config.return_value = {'sync_repos_startup': True}

    @patch('bauh.gems.eopkg.controller.SyncRepositories')
    @patch('bauh.gems.eopkg.controller.CreateConfigFile')
    def test_prepare__must_synchronize_the_repositories(self, create_config: Mock, sync: Mock):
        self.manager.prepare(Mock(), 'secret', True)

        sync.return_value.start.assert_called_once()
        # se espera a que termine: 'read_installed' y 'list_updates' corren justo después y
        # deben ver el índice ya refrescado
        sync.return_value.join.assert_called_once()

    @patch('bauh.gems.eopkg.controller.SyncRepositories')
    @patch('bauh.gems.eopkg.controller.CreateConfigFile')
    def test_prepare__must_skip_without_root_privileges(self, create_config: Mock, sync: Mock):
        # la recarga de ajustes llama a prepare() sin contraseña ni gestor de tareas
        with patch('bauh.gems.eopkg.controller.user.is_root', return_value=False):
            self.manager.prepare(None, None, None)

        sync.assert_not_called()

    @patch('bauh.gems.eopkg.controller.SyncRepositories')
    @patch('bauh.gems.eopkg.controller.CreateConfigFile')
    def test_prepare__must_skip_without_a_task_manager_even_as_root(self, create_config: Mock,
                                                                    sync: Mock):
        # la recarga de ajustes llama a prepare(None, None, None) ('bauh/view/qt/settings.py'):
        # con bauh lanzado como root la guarda de privilegios no corta, y el guardado de
        # ajustes se quedaría bloqueado en un 'eopkg ur' sin barra de progreso
        with patch('bauh.gems.eopkg.controller.user.is_root', return_value=True):
            self.manager.prepare(None, None, None)

        sync.assert_not_called()
        create_config.assert_not_called()

    def test_prepare__must_return_even_if_the_sync_never_ends(self):
        # la vista Qt no emite 'signal_started' hasta que prepare() vuelve: un 'eopkg ur'
        # colgado dejaría el panel de arranque sin botón de Saltar ni de Cerrar
        process = Mock()
        process.instance.stdout = _BlockingStdout()
        taskman = Mock()
        self.manager.i18n = {'task.waiting_task': '{}', 'task.checking_config': 'c',
                             'task.checking_config.saving': 'c',
                             'eopkg.action.update_repos.status': 's',
                             'eopkg.task.disabled': 'off', 'eopkg.task.synchronized': 'ok',
                             'eopkg.task.error': 'err'}

        with patch('bauh.gems.eopkg.worker.SimpleProcess', return_value=process), \
                patch.object(index, 'should_sync', return_value=True), \
                patch.object(controller, 'SYNC_TIMEOUT', 0.2):
            started = time.monotonic()
            self.manager.prepare(taskman, 'secret', True)
            elapsed = time.monotonic() - started

        self.assertLess(elapsed, 30)
        self.manager.logger.warning.assert_called()

    def test_the_sync_timeout_must_stay_generous(self):
        # acotar la espera no puede cortar una sincronización que iba a terminar
        self.assertGreaterEqual(controller.SYNC_TIMEOUT, 300)

    @patch('bauh.gems.eopkg.controller.SyncRepositories')
    @patch('bauh.gems.eopkg.controller.CreateConfigFile')
    def test_prepare__must_run_as_root_without_a_password(self, create_config: Mock, sync: Mock):
        with patch('bauh.gems.eopkg.controller.user.is_root', return_value=True):
            self.manager.prepare(Mock(), None, True)

        sync.return_value.start.assert_called_once()

    @patch('bauh.gems.eopkg.controller.SyncRepositories')
    @patch('bauh.gems.eopkg.controller.CreateConfigFile')
    def test_prepare__must_skip_without_internet(self, create_config: Mock, sync: Mock):
        self.manager.prepare(Mock(), 'secret', False)

        sync.assert_not_called()

    def test_requires_root__must_ask_for_the_password_only_when_a_sync_is_due(self):
        with patch.object(SyncRepositories, 'should_sync', return_value=True):
            self.assertTrue(self.manager.requires_root(SoftwareAction.PREPARE))

        with patch.object(SyncRepositories, 'should_sync', return_value=False):
            self.assertFalse(self.manager.requires_root(SoftwareAction.PREPARE))


class WarningsTest(unittest.TestCase):
    """Un índice desfasado no puede confundirse con un sistema al día."""

    def setUp(self):
        self.manager = EopkgManager(Mock())
        self.manager.i18n = {'eopkg.warning.repos_outdated': 'desfasado: {}',
                             'eopkg.warning.repos_never_synced': 'nunca sincronizado'}
        self.manager.configman = Mock()

    def test_no_warning_when_the_index_is_fresh(self):
        with patch.object(index, 'should_sync', return_value=False):
            self.assertIsNone(self.manager.list_warnings(internet_available=True))

    def test_warning_when_the_index_is_outdated(self):
        moment = datetime.now() - timedelta(days=3)

        with patch.object(index, 'should_sync', return_value=True), \
                patch.object(index, 'last_sync', return_value=moment):
            warnings = self.manager.list_warnings(internet_available=True)

        self.assertEqual(1, len(warnings))
        # fecha en ISO: el aviso se traduce a diez idiomas y '04/09/2026' se lee como el 9 de
        # abril en inglés
        self.assertIn(moment.strftime('%Y-%m-%d %H:%M'), warnings[0])
        self.assertNotIn(moment.strftime('%d/%m/%Y'), warnings[0])

    def test_warning_when_it_was_never_synchronized(self):
        with patch.object(index, 'should_sync', return_value=True), \
                patch.object(index, 'last_sync', return_value=None):
            self.assertEqual(['nunca sincronizado'],
                             self.manager.list_warnings(internet_available=True))

    def test_no_warning_without_internet(self):
        with patch.object(index, 'should_sync', return_value=True):
            self.assertIsNone(self.manager.list_warnings(internet_available=False))


if __name__ == '__main__':
    unittest.main()
