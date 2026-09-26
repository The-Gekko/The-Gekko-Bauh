from unittest import TestCase
from unittest.mock import Mock, patch

from bauh.gems.flatpak import flatpak
from bauh.gems.flatpak.controller import FlatpakManager
from bauh.gems.flatpak.model import FlatpakApplication


class FlatpakManagerHiddenRefsTest(TestCase):
    """Las extensiones que 'flatpak list' esconde ('.Locale', '.Debug') se actualizan, no se instalan.

    Fallo real: 'flatpak install' contestaba «Saltando: ya está instalado», no hacía nada y la
    misma «Locale» volvía a salir como actualización después de cada recarga.
    """

    def setUp(self):
        self.manager = FlatpakManager(Mock())
        self.manager._read_ignored_updates = Mock(return_value=set())

    def _read(self, updates: set, installed_refs: set) -> dict:
        with patch.object(flatpak, 'get_version', return_value=('1', '18', '3')), \
                patch.object(flatpak, 'list_updates_as_str', return_value={'full': updates, 'partial': set()}), \
                patch.object(flatpak, 'list_required_runtime_updates', return_value=[]), \
                patch.object(flatpak, 'list_installed', return_value=[]), \
                patch.object(flatpak, 'list_installed_refs', return_value=installed_refs) as refs:
            result = self.manager.read_installed(None, internet_available=True)

        self.refs_calls = refs.call_count
        return {pkg.id: pkg for pkg in result.installed}

    def test_an_installed_locale_must_be_upgraded_and_not_installed(self):
        found = self._read({'io.missioncenter.MissionCenter.Locale/stable/user/flathub'},
                           {('io.missioncenter.MissionCenter.Locale', 'stable', 'user')})

        locale = found['io.missioncenter.MissionCenter.Locale']
        self.assertTrue(locale.update)
        self.assertFalse(locale.update_component)
        self.assertEqual('io.missioncenter.MissionCenter.Locale/x86_64/stable', locale.ref)

    def test_a_component_that_is_not_installed_is_still_installed(self):
        found = self._read({'org.freedesktop.Platform.GL.default/25.08/user/flathub'},
                           {('io.missioncenter.MissionCenter.Locale', 'stable', 'user')})

        self.assertTrue(found['org.freedesktop.Platform.GL.default'].update_component)

    def test_the_installation_must_match(self):
        # instalada en el sistema, pendiente en el usuario: en el usuario sí es nueva
        found = self._read({'org.gnome.Platform.Locale/49/user/flathub'},
                           {('org.gnome.Platform.Locale', '49', 'system')})

        self.assertTrue(found['org.gnome.Platform.Locale'].update_component)

    def test_installed_refs_are_read_once(self):
        self._read({'a.b.C.Locale/stable/user/flathub', 'd.e.F.Locale/stable/user/flathub'}, set())

        self.assertEqual(1, self.refs_calls)


class FlatpakManagerSortUpdateOrderTest(TestCase):

    def setUp(self):
        self.manager = FlatpakManager(Mock())

    def test_is_default_enabled__must_be_true_because_flatpak_is_in_scope(self):
        # Flatpak forma parte del alcance oficial del fork (Arch/AUR/Chaotic AUR, Flatpak y
        # Solus/eopkg), a diferencia de las gems heredadas que son opcionales.
        self.assertTrue(self.manager.is_default_enabled())

    def test__sort_deps__only_apps(self):
        pkgs = [
            FlatpakApplication(id="org.gnome.gedit", name='Gedit', runtime=False),
            FlatpakApplication(id="com.spotify.Client", name='com.spotify.Client', runtime=False),
        ]

        sorted_list = self.manager.sort_update_order(pkgs)
        self.assertIsInstance(sorted_list, list)
        self.assertEqual(len(pkgs), len(sorted_list))

        for pkg in sorted_list:
            self.assertIn(pkg, pkgs)

    def test__sort_deps__one_app_one_runtime(self):
        pkgs = [
            FlatpakApplication(id="org.gnome.gedit", name='Gedit', runtime=False),
            FlatpakApplication(id="org.gnome.Platform", name='org.gnome.Platform', runtime=True),
        ]

        sorted_list = self.manager.sort_update_order(pkgs)
        self.assertIsInstance(sorted_list, list)
        self.assertEqual(len(pkgs), len(sorted_list))

        self.assertEqual(pkgs[1], sorted_list[0])
        self.assertEqual(pkgs[0], sorted_list[1])

    def test__sort_deps__two_apps_one_runtime(self):
        pkgs = [
            FlatpakApplication(id="org.gnome.gedit", name='Gedit', runtime=False),
            FlatpakApplication(id="org.gnome.Platform", name='org.gnome.Platform', runtime=True),
            FlatpakApplication(id="com.spotify.Client", name='com.spotify.Client', runtime=False)
        ]

        sorted_list = self.manager.sort_update_order(pkgs)
        self.assertIsInstance(sorted_list, list)
        self.assertEqual(len(pkgs), len(sorted_list))

        self.assertEqual(pkgs[1], sorted_list[0])
        self.assertEqual(pkgs[0], sorted_list[1])
        self.assertEqual(pkgs[2], sorted_list[2])

    def test_sort_deps_two_apps_two_runtimes(self):
        pkgs = [
            FlatpakApplication(id="org.gnome.gedit", name='Gedit', runtime=False),
            FlatpakApplication(id="org.gnome.Platform", name='Platform', runtime=True),
            FlatpakApplication(id="com.spotify.Client", name='Spotify', runtime=False),
            FlatpakApplication(id="org.freedesktop.Platform.GL.default", name='default', runtime=True)
        ]

        sorted_list = self.manager.sort_update_order(pkgs)
        self.assertIsInstance(sorted_list, list)
        self.assertEqual(len(pkgs), len(sorted_list))

        self.assertEqual(pkgs[1], sorted_list[0])
        self.assertEqual(pkgs[3], sorted_list[1])
        self.assertEqual(pkgs[0], sorted_list[2])
        self.assertEqual(pkgs[2], sorted_list[3])

    def test_sort_deps_two_apps_two_runtimes_one_partial(self):
        gnome_platform = FlatpakApplication(id="org.gnome.Platform", name='Platform', runtime=True)
        gnome_locale = FlatpakApplication(id="org.gnome.Platform.Locale", name="Locale", runtime=True, partial=True)
        gnome_locale.base_id = gnome_platform.id

        pkgs = [
            FlatpakApplication(id="org.gnome.gedit", name='Gedit', runtime=False),
            gnome_platform,
            FlatpakApplication(id="com.spotify.Client", name='Spotify', runtime=False),
            FlatpakApplication(id="org.freedesktop.Platform.GL.default", name='default', runtime=True),
            gnome_locale
        ]

        sorted_list = self.manager.sort_update_order(pkgs)
        self.assertIsInstance(sorted_list, list)
        self.assertEqual(len(pkgs), len(sorted_list))

        self.assertEqual(pkgs[4], sorted_list[0])
        self.assertEqual(pkgs[1], sorted_list[1])
        self.assertEqual(pkgs[3], sorted_list[2])
        self.assertEqual(pkgs[0], sorted_list[3])
        self.assertEqual(pkgs[2], sorted_list[4])

    def test_sort_deps_two_apps_two_runtimes_two_partials(self):
        gnome_platform = FlatpakApplication(id="org.gnome.Platform", name='Platform', runtime=True)
        gnome_locale = FlatpakApplication(id="org.gnome.Platform.Locale", name="Locale", runtime=True, partial=True)
        gnome_locale.base_id = gnome_platform.id

        platform_default = FlatpakApplication(id="org.freedesktop.Platform.GL.default", name='Default', runtime=True)
        platform_locale = FlatpakApplication(id="org.freedesktop.Platform.GL.Locale", name='Locale', runtime=True, partial=True)
        platform_locale.base_id = platform_default.id

        pkgs = [
            platform_locale,
            FlatpakApplication(id="org.gnome.gedit", name='Gedit', runtime=False),
            gnome_platform,
            FlatpakApplication(id="com.spotify.Client", name='Spotify', runtime=False),
            platform_default,
            gnome_locale
        ]

        sorted_list = self.manager.sort_update_order(pkgs)
        self.assertIsInstance(sorted_list, list)
        self.assertEqual(len(pkgs), len(sorted_list))

        self.assertEqual(platform_default.id, sorted_list[0].id)
        self.assertEqual(platform_locale.id, sorted_list[1].id)
        self.assertEqual(gnome_locale.id, sorted_list[2].id)
        self.assertEqual(gnome_platform.id, sorted_list[3].id)
        self.assertEqual('org.gnome.gedit', sorted_list[4].id)
        self.assertEqual('com.spotify.Client', sorted_list[5].id)
