import os
from tempfile import TemporaryDirectory
from unittest import TestCase

from bauh.gems.appimage import util
from bauh.gems.appimage.util import replace_desktop_entry_exec_command


class TestUtil(TestCase):

    def test_replace_desktop_entry_exec_command__only_one_exec_field_no_spaces_and_no_params(self):
        desktop_entry = """
        Name=MyApp
        Icon=MyApp
        Exec=myapp
        """

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='myapp',
                                                 file_path='/path/to/myapp.appimage')

        expected = """
        Name=MyApp
        Icon=MyApp
        Exec="/path/to/myapp.appimage"
        """

        self.assertEqual(expected, res)

    def test_replace_desktop_entry_exec_command__only_one_exec_field_command_with_different_cases(self):
        desktop_entry = """
        Name=MyApp
        Icon=MyApp
        Exec=MyApP
        """

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='myapp',
                                                 file_path='/path/to/myapp.appimage')

        expected = """
        Name=MyApp
        Icon=MyApp
        Exec="/path/to/myapp.appimage"
        """

        self.assertEqual(expected, res)

    def test_replace_desktop_entry_exec_command__only_one_exec_field_no_spaces_and_params(self):
        desktop_entry = """
        Name=MyApp
        Icon=MyApp
        Exec=myapp %f
        """

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='myapp',
                                                 file_path='/path/to/myapp.appimage')

        expected = """
        Name=MyApp
        Icon=MyApp
        Exec="/path/to/myapp.appimage" %f
        """

        self.assertEqual(expected, res)

    def test_replace_desktop_entry_exec_command__only_one_exec_field_no_line_jump_in_the_end(self):
        desktop_entry = """
        Name=MyApp
        Icon=MyApp
        Exec=myapp %f"""

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='myapp',
                                                 file_path='/path/to/myapp.appimage')

        expected = """
        Name=MyApp
        Icon=MyApp
        Exec="/path/to/myapp.appimage" %f"""

        self.assertEqual(expected, res)

    def test_replace_desktop_entry_exec_command__exec_as_the_first_field(self):
        desktop_entry = """
        Exec=myapp %f
        Name=MyApp
        Icon=MyApp
        """

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='myapp',
                                                 file_path='/path/to/myapp.appimage')

        expected = """
        Exec="/path/to/myapp.appimage" %f
        Name=MyApp
        Icon=MyApp
        """

        self.assertEqual(expected, res)

    def test_replace_desktop_entry_exec_command__try_exec_as_the_first_field(self):
        desktop_entry = """
        TryExec=MyApp
        Exec=myapp %f
        Name=MyApp
        Icon=MyApp
        """

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='myapp',
                                                 file_path='/path/to/myapp.appimage')

        expected = """
        Exec="/path/to/myapp.appimage" %f
        Name=MyApp
        Icon=MyApp
        """

        self.assertEqual(expected, res)

    def test_replace_desktop_entry_exec_command__only_one_exec_field_with_spaces_and_params(self):
        desktop_entry = """
        Name=MyApp
        Icon=MyApp
        Exec =  myapp %f --a
        """

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='myapp',
                                                 file_path='/path/to/myapp.appimage')

        expected = """
        Name=MyApp
        Icon=MyApp
        Exec ="/path/to/myapp.appimage" %f --a
        """

        self.assertEqual(expected, res)

    def test_replace_desktop_entry_exec_command__param_with_the_same_app_name(self):
        desktop_entry = """
        Name=MyApp
        Icon=MyApp
        Exec=myapp %f --myapp
        """

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='myapp',
                                                 file_path='/path/to/myapp.appimage')

        expected = """
        Name=MyApp
        Icon=MyApp
        Exec="/path/to/myapp.appimage" %f --myapp
        """

        self.assertEqual(expected, res)

    def test_replace_desktop_entry_exec_command__evvar_with_same_app_name(self):
        desktop_entry = """
        Name=MyApp
        Icon=MyApp
        Exec=MYAPP=123 myapp
        """

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='myapp',
                                                 file_path='/path/to/myapp.appimage')

        expected = """
        Name=MyApp
        Icon=MyApp
        Exec=MYAPP=123 "/path/to/myapp.appimage"
        """

        self.assertEqual(expected, res)

    def test_replace_desktop_entry_exec_command__must_remove_try_exec_field(self):
        desktop_entry = """
        Name=MyApp
        Icon=MyApp
        TryExec =  myapp %f --a
        """

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='myapp',
                                                 file_path='/path/to/myapp.appimage')

        expected = """
        Name=MyApp
        Icon=MyApp
        """

        self.assertEqual(expected, res)

    def test_replace_desktop_entry_exec_command__must_replace_exec_and_remove_tryexec_fields(self):
        desktop_entry = """
        Name=MyApp
        Icon=MyApp
        TryExec =  myapp %f
        Exec=myapp --a
        Terminal=false
        """

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='myapp',
                                                 file_path='/path/to/myapp.appimage')

        expected = """
        Name=MyApp
        Icon=MyApp
        Exec="/path/to/myapp.appimage" --a
        Terminal=false
        """

        self.assertEqual(expected, res)

    def test_replace_desktop_entry_exec_command__exec_field_with_envvars_and_params(self):
        desktop_entry = """
        Name=MyApp
        Icon=MyApp
        TryExec=__MY_VAR=1 myapp %f
        Exec=NEW_VAR=abc myapp --a
        Terminal=false
        """

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='myapp',
                                                 file_path='/path/to/myapp.appimage')

        expected = """
        Name=MyApp
        Icon=MyApp
        Exec=NEW_VAR=abc "/path/to/myapp.appimage" --a
        Terminal=false
        """

        self.assertEqual(expected, res)

    def test_replace_desktop_entry_exec_command__rpcs3(self):
        desktop_entry = """
        [Desktop Entry]
Type=Application
Name=RPCS3
GenericName=PlayStation 3 Emulator
Comment=An open-source PlayStation 3 emulator/debugger written in C++.
Icon=rpcs3
TryExec=rpcs3
Exec=rpcs3 %f
Terminal=false
Categories=Game;Emulator;
Keywords=PS3;Playstation;

        """

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='rpcs3',
                                                 file_path='/path/to/rpcs3.appimage')

        expected = """
        [Desktop Entry]
Type=Application
Name=RPCS3
GenericName=PlayStation 3 Emulator
Comment=An open-source PlayStation 3 emulator/debugger written in C++.
Icon=rpcs3
Exec="/path/to/rpcs3.appimage" %f
Terminal=false
Categories=Game;Emulator;
Keywords=PS3;Playstation;

        """

        self.assertEqual(expected, res)

    def test_replace_desktop_entry_exec_command__it_should_replace_the_command_by_the_file_path_if_the_appname_is_not_present(self):
        desktop_entry = """
        [Desktop Entry]
Name=GameHub
GenericName=GameHub
Comment=All your games in one place
Categories=Game;Amusement;
Keywords=Game;Hub;Steam;GOG;Humble;HumbleBundle;
Exec=com.github.tkashkin.gamehub
X-GNOME-Gettext-Domain=com.github.tkashkin.gamehub
Icon=/gamehub-0/logo.svg
Terminal=false
Type=Application
X-AppImage-Version=bionic-0.16.0-83-dev-0ca783e
        """

        res = replace_desktop_entry_exec_command(desktop_entry=desktop_entry,
                                                 appname='gamehub',
                                                 file_path='/path/to/gamehub.appimage')

        expected = """
        [Desktop Entry]
Name=GameHub
GenericName=GameHub
Comment=All your games in one place
Categories=Game;Amusement;
Keywords=Game;Hub;Steam;GOG;Humble;HumbleBundle;
Exec="/path/to/gamehub.appimage"
X-GNOME-Gettext-Domain=com.github.tkashkin.gamehub
Icon=/gamehub-0/logo.svg
Terminal=false
Type=Application
X-AppImage-Version=bionic-0.16.0-83-dev-0ca783e
        """

        self.assertEqual(expected, res)


class FindAppImageFileTest(TestCase):
    """Localización del .AppImage dentro del directorio de instalación."""

    def setUp(self):
        self.dir = TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def _touch(self, *parts) -> str:
        path = os.path.join(self.dir.name, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'w').close()
        return path

    def test_finds_the_file_in_the_root(self):
        expected = self._touch('App.AppImage')

        self.assertEqual(expected, util.find_appimage_file(self.dir.name))

    def test_the_returned_path_of_a_nested_file_exists(self):
        # antes se componía «<raíz>/<nombre>» aunque el fichero estuviera en una subcarpeta:
        # la ruta no existía y la aplicación no arrancaba
        expected = self._touch('squashfs-root', 'App.AppImage')

        found = util.find_appimage_file(self.dir.name)

        self.assertEqual(expected, found)
        self.assertTrue(os.path.exists(found))

    def test_the_root_file_wins_over_a_nested_one(self):
        self._touch('sub', 'Anidada.AppImage')
        expected = self._touch('Raiz.AppImage')

        self.assertEqual(expected, util.find_appimage_file(self.dir.name))

    def test_the_result_is_stable_when_there_are_several(self):
        self._touch('b.AppImage')
        self._touch('a.AppImage')

        # os.walk no garantiza orden: dos ejecuciones deben dar lo mismo
        first = util.find_appimage_file(self.dir.name)
        self.assertEqual(first, util.find_appimage_file(self.dir.name))
        self.assertEqual('a.AppImage', os.path.basename(first))

    def test_the_extension_is_case_insensitive(self):
        expected = self._touch('App.appimage')

        self.assertEqual(expected, util.find_appimage_file(self.dir.name))

    def test_returns_none_when_there_is_nothing(self):
        self._touch('leeme.txt')

        self.assertIsNone(util.find_appimage_file(self.dir.name))
