import os
from unittest import TestCase
from unittest.mock import patch, Mock

from bauh import __package_name__
from bauh.gems.flatpak import flatpak, VERSION_1_2


class LanguagesEnvTest(TestCase):
    """Idiomas del usuario para las órdenes que van con la locale C."""

    def _languages(self, **env) -> dict:
        clean = {var: '' for var in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG')}
        clean.update(env)

        with patch.dict(os.environ, clean):
            return flatpak.languages_env()

    def test_must_take_the_language_from_lang(self):
        self.assertEqual({'LANGUAGE': 'es_MX.utf8'}, self._languages(LANG='es_MX.utf8'))

    def test_must_follow_the_priority_of_gettext(self):
        self.assertEqual({'LANGUAGE': 'pt_BR:en'}, self._languages(LANGUAGE='pt_BR:en', LANG='es_MX.utf8'))
        self.assertEqual({'LANGUAGE': 'de_DE.UTF-8'}, self._languages(LC_ALL='de_DE.UTF-8', LANG='es_MX.utf8'))

    def test_must_not_invent_a_language_for_a_user_working_in_c(self):
        self.assertEqual({}, self._languages(LC_ALL='C.UTF-8', LANG='es_MX.utf8'))
        self.assertEqual({}, self._languages(LANG='POSIX'))
        self.assertEqual({}, self._languages())

    @patch(f'{__package_name__}.gems.flatpak.flatpak.subprocess.run')
    def test_run__must_add_the_languages_only_when_forcing_the_c_locale(self, run: Mock):
        run.return_value = Mock(returncode=0, stdout=b'')

        with patch.object(flatpak, 'languages_env', return_value={'LANGUAGE': 'es_MX.utf8'}):
            flatpak._run(('flatpak', 'update', '--user', '--no-deps'))
            forced = run.call_args[1]['env']
            flatpak._run(('flatpak', 'list'), lang=None)
            native = run.call_args[1]['env']

        self.assertEqual(('C', 'es_MX.utf8'), (forced['LC_ALL'], forced['LANGUAGE']))
        self.assertNotEqual('C', native.get('LC_ALL'))


class FlatpakTest(TestCase):

    @patch(f'{__package_name__}.gems.flatpak.flatpak.SimpleProcess')
    @patch(f'{__package_name__}.gems.flatpak.flatpak.ProcessHandler.handle_simple', return_value=(True, """
    Looking for updates...

    \tID\tArch\tBranch\tRemote\tDownload
    1.\t \torg.xpto.Xnote\tx86_64\tstable\tflathub\t< 4.3 MB

    """))
    def test_map_update_download_size__for_flatpak_1_2(self, SimpleProcess: Mock, handle_simple: Mock):
        download_size = flatpak.map_update_download_size(app_ids={'org.xpto.Xnote'}, installation='user', version=VERSION_1_2)
        SimpleProcess.assert_called_once()
        handle_simple.assert_called_once()

        self.assertEqual({'org.xpto.Xnote': 4300000}, download_size)
