import unittest

from bauh.gems.eopkg import parsers

# --- fixtures tomadas de la especificación aportada por el dueño del fork ---------------

SEARCH_OUTPUT = """vlc - The cross-platform open-source multimedia framework and player
vlc-devel - Development files for vlc
"""

LIST_INSTALLED_CLASSIC = """a2ps - Any to PostScript filter
vlc - The cross-platform open-source multimedia framework and player
"""

LIST_INSTALLED_TABLE = """Package Name          |St|        Version|  Rel.|  Distro|             Date
a2ps                  | i|          4.14|     1|   Solus| 2016-01-01
vlc                   | i|        3.0.20|    78|   Solus| 2024-05-02
"""

LIST_INSTALLED_SPACED = """vlc 3.0.20 78 The cross-platform open-source multimedia framework
discord 1.0.155 176 All-in-one voice and text chat
"""

NO_UPGRADES_OUTPUT = "No packages to upgrade.\n"

NO_UPGRADES_OUTPUT_ES = "No hay paquetes para actualizar.\n"

UPGRADES_OUTPUT = """vlc - The cross-platform open-source multimedia framework and player
discord - All-in-one voice and text chat
"""

INFO_OUTPUT = """Installed package:
Name            : vlc, version: 3.0.20, release: 78
Summary         : The cross-platform open-source multimedia framework
Description     : VLC is a free and open source cross-platform multimedia player...
Licenses        : GPL-2.0-or-later, LGPL-2.1-or-later
Component       : multimedia.video
Dependencies    : ffmpeg, qt5-base
Distribution    : Solus, Distro Release: 1
Installed Size  : 45.20 MB

Package found in Solus repository:
Name            : vlc, version: 3.0.21, release: 79
Summary         : The cross-platform open-source multimedia framework
"""

INSTALL_OUTPUT_ES = """The following packages will be installed:
discord  libayatana-appindicator  libayatana-ido  libayatana-indicator
Tamaño total de paquete(s): 1.91 MB
Hay paquetes adicionales por motivo de dependencias.
Desea continuar ? (yes/no)yes
Downloading 4 package resources (0 cached)
Downloaded libayatana-ido-0.10.4-5-1-x86_64.eopkg
Finished downloading packages.
Disabling keyboard interrupts for file operations.
Instalado 1 / 4
Instalando libayatana-ido, versión 0.10.4, release 5
Extracting the files of libayatana-ido (100%) [complete]
Instalado libayatana-ido
Instalado 4 / 4
Instalando discord, versión 1.0.155, release 176
Extracting the files of discord (100%) [complete]
Instalado discord
 [✓] Syncing filesystems                                                success
Failed to record path /lib32
 [✓] Updating desktop database                                          success
"""

INSTALL_OUTPUT_EN = """The following packages will be installed:
discord  libayatana-appindicator
Do you want to continue ? (yes/no)yes
Installed 1 / 2
Installing libayatana-appindicator, version 0.5.93, release 3
Installed libayatana-appindicator
Installed 2 / 2
Installing discord, version 1.0.155, release 176
Installed discord
"""

REMOVE_OUTPUT_ES = """La siguiente lista de paquetes será removida
en el orden indicado, para satisfacer las dependencias:
discord libayatana-appindicator libayatana-ido libayatana-indicator
Desea continuar ? (yes/no)yes
Disabling keyboard interrupts for file operations.
Eliminando paquete discord
Removido discord
Eliminando paquete libayatana-appindicator
Removido libayatana-appindicator
Removido libayatana-ido
Removido libayatana-indicator
 [✓] Syncing filesystems                                                success
Failed to record path /lib32
"""

REMOVE_OUTPUT_EN = """The following list of packages will be removed
in the order they are listed:
discord libayatana-appindicator
Do you want to continue ? (yes/no)yes
Removing package discord
Removed discord
Removing package libayatana-appindicator
Removed libayatana-appindicator
"""


class SearchParsingTest(unittest.TestCase):

    def test_parse_search__must_split_by_dash_and_keep_the_summary(self):
        result = parsers.parse_search(SEARCH_OUTPUT)

        self.assertEqual(['vlc', 'vlc-devel'], [p['name'] for p in result])
        self.assertEqual('The cross-platform open-source multimedia framework and player',
                         result[0]['summary'])

    def test_parse_search__must_keep_a_summary_containing_a_colon(self):
        result = parsers.parse_search('foo - Tool: does things\n')

        self.assertEqual(1, len(result))
        self.assertEqual('foo', result[0]['name'])
        self.assertEqual('Tool: does things', result[0]['summary'])

    def test_parse_search__must_return_nothing_for_an_empty_output(self):
        self.assertEqual([], parsers.parse_search(''))
        self.assertEqual([], parsers.parse_search(None))


class InstalledParsingTest(unittest.TestCase):

    def test_parse_package_list__classic_format(self):
        result = parsers.parse_package_list(LIST_INSTALLED_CLASSIC)

        self.assertEqual(['a2ps', 'vlc'], [p['name'] for p in result])
        self.assertIsNone(result[0]['version'])

    def test_parse_package_list__install_info_table(self):
        result = parsers.parse_package_list(LIST_INSTALLED_TABLE)

        self.assertEqual(['a2ps', 'vlc'], [p['name'] for p in result])
        self.assertEqual('4.14', result[0]['version'])
        self.assertEqual('1', result[0]['release'])
        self.assertEqual('3.0.20', result[1]['version'])
        self.assertEqual('78', result[1]['release'])

    def test_parse_package_list__must_ignore_the_table_header(self):
        names = [p['name'] for p in parsers.parse_package_list(LIST_INSTALLED_TABLE)]

        self.assertNotIn('Package Name', names)
        self.assertNotIn('Package', names)

    def test_parse_package_list__space_separated_columns(self):
        result = parsers.parse_package_list(LIST_INSTALLED_SPACED)

        self.assertEqual('vlc', result[0]['name'])
        self.assertEqual('3.0.20', result[0]['version'])
        self.assertEqual('78', result[0]['release'])
        self.assertEqual('The cross-platform open-source multimedia framework',
                         result[0]['summary'])

    def test_parse_package_list__must_ignore_headers_and_noise(self):
        output = ('Installed packages:\n'
                  'Failed to record path /lib32\n'
                  ' [OK] Syncing filesystems                    success\n'
                  'vlc - player\n')

        self.assertEqual(['vlc'], [p['name'] for p in parsers.parse_package_list(output)])


class UpgradeParsingTest(unittest.TestCase):

    def test_parse_upgradable__must_ignore_no_packages_to_upgrade(self):
        self.assertEqual([], parsers.parse_upgradable(NO_UPGRADES_OUTPUT))

    def test_parse_upgradable__must_ignore_the_translated_no_packages_message(self):
        self.assertEqual([], parsers.parse_upgradable(NO_UPGRADES_OUTPUT_ES))

    def test_parse_upgradable__must_not_invent_a_package_called_no(self):
        names = parsers.parse_upgradable(NO_UPGRADES_OUTPUT)

        self.assertNotIn('No', names)
        self.assertNotIn('no', names)

    def test_parse_upgradable__must_return_the_package_names(self):
        self.assertEqual(['vlc', 'discord'], parsers.parse_upgradable(UPGRADES_OUTPUT))

    def test_parse_upgradable__must_not_use_the_dash_as_a_version(self):
        entries = parsers.parse_upgradable_entries(UPGRADES_OUTPUT)

        for entry in entries:
            self.assertNotEqual('-', entry['version'])

    def test_parse_upgradable__must_ignore_any_informative_sentence(self):
        self.assertEqual([], parsers.parse_upgradable('Nothing to do here really.\n'))


class InfoParsingTest(unittest.TestCase):

    def setUp(self):
        self.blocks = parsers.parse_info_blocks(INFO_OUTPUT)
        self.index = parsers.index_info_blocks(self.blocks)

    def test_parse_info_blocks__must_split_installed_and_repository(self):
        self.assertEqual(2, len(self.blocks))
        self.assertEqual('installed', self.blocks[0]['section'])
        self.assertEqual('repository', self.blocks[1]['section'])

    def test_parse_info_blocks__must_read_name_version_and_release(self):
        block = self.blocks[0]

        self.assertEqual('vlc', block['name'])
        self.assertEqual('3.0.20', block['version'])
        self.assertEqual('78', block['release'])

    def test_parse_info_blocks__must_read_the_remaining_fields(self):
        block = self.blocks[0]

        self.assertEqual('The cross-platform open-source multimedia framework',
                         block['summary'])
        self.assertEqual('GPL-2.0-or-later, LGPL-2.1-or-later', block['licenses'])
        self.assertEqual('multimedia.video', block['component'])
        self.assertEqual('ffmpeg, qt5-base', block['dependencies'])
        self.assertEqual('45.20 MB', block['installed_size'])
        self.assertEqual('Solus, Distro Release: 1', block['distribution'])

    def test_index_info_blocks__must_expose_the_available_version(self):
        sections = self.index['vlc']

        self.assertEqual('3.0.20-78', parsers.format_version(sections['installed']['version'],
                                                             sections['installed']['release']))
        self.assertEqual('3.0.21-79', parsers.format_version(sections['repository']['version'],
                                                             sections['repository']['release']))

    def test_parse_info_blocks__spanish_output(self):
        output = ('Paquete instalado:\n'
                  'Nombre          : vlc, versión: 3.0.20, release: 78\n'
                  'Resumen         : Reproductor multimedia\n')
        blocks = parsers.parse_info_blocks(output)

        self.assertEqual(1, len(blocks))
        self.assertEqual('vlc', blocks[0]['name'])
        self.assertEqual('3.0.20', blocks[0]['version'])
        self.assertEqual('Reproductor multimedia', blocks[0]['summary'])

    def test_format_version(self):
        self.assertEqual('3.0.20-78', parsers.format_version('3.0.20', '78'))
        self.assertEqual('3.0.20', parsers.format_version('3.0.20', None))
        self.assertIsNone(parsers.format_version(None, '78'))


class InstallOutputParsingTest(unittest.TestCase):

    def test_parse_install_progress__spanish_and_english(self):
        self.assertEqual((1, 4), parsers.parse_install_progress('Instalado 1 / 4'))
        self.assertEqual((2, 4), parsers.parse_install_progress('Installed 2 / 4'))

    def test_parse_install_progress__must_ignore_other_lines(self):
        self.assertIsNone(parsers.parse_install_progress('Installed discord'))
        self.assertIsNone(parsers.parse_install_progress('Failed to record path /lib32'))

    def test_parse_installing_package(self):
        parsed = parsers.parse_installing_package(
            'Instalando libayatana-ido, versión 0.10.4, release 5')

        self.assertEqual({'name': 'libayatana-ido', 'version': '0.10.4', 'release': '5'},
                         parsed)

    def test_parse_installing_package__english(self):
        parsed = parsers.parse_installing_package(
            'Installing discord, version 1.0.155, release 176')

        self.assertEqual('discord', parsed['name'])
        self.assertEqual('1.0.155', parsed['version'])

    def test_parse_install_targets__must_list_the_dependencies(self):
        self.assertEqual(['discord', 'libayatana-appindicator', 'libayatana-ido',
                          'libayatana-indicator'],
                         parsers.parse_install_targets(INSTALL_OUTPUT_ES))

    def test_parse_installed_packages__spanish_output(self):
        self.assertEqual(['libayatana-ido', 'discord'],
                         parsers.parse_installed_packages(INSTALL_OUTPUT_ES))

    def test_parse_installed_packages__english_output(self):
        self.assertEqual(['libayatana-appindicator', 'discord'],
                         parsers.parse_installed_packages(INSTALL_OUTPUT_EN))

    def test_parse_installed_packages__must_not_take_the_progress_counter(self):
        self.assertNotIn('1', parsers.parse_installed_packages(INSTALL_OUTPUT_EN))


class RemovalOutputParsingTest(unittest.TestCase):

    def test_parse_removal_targets__spanish_output(self):
        self.assertEqual(['discord', 'libayatana-appindicator', 'libayatana-ido',
                          'libayatana-indicator'],
                         parsers.parse_removal_targets(REMOVE_OUTPUT_ES))

    def test_parse_removal_targets__english_output(self):
        self.assertEqual(['discord', 'libayatana-appindicator'],
                         parsers.parse_removal_targets(REMOVE_OUTPUT_EN))

    def test_parse_removed_packages__spanish_output(self):
        self.assertEqual(['discord', 'libayatana-appindicator', 'libayatana-ido',
                          'libayatana-indicator'],
                         parsers.parse_removed_packages(REMOVE_OUTPUT_ES))

    def test_parse_removed_packages__must_not_match_removing_lines(self):
        self.assertEqual(['discord', 'libayatana-appindicator'],
                         parsers.parse_removed_packages(REMOVE_OUTPUT_EN))

    def test_collector__must_report_the_list_once_it_is_complete(self):
        collector = parsers.TransactionTargetsCollector()
        completed = [collector.feed(line) for line in REMOVE_OUTPUT_ES.splitlines()]

        self.assertEqual(1, sum(1 for c in completed if c))
        self.assertEqual(['discord', 'libayatana-appindicator', 'libayatana-ido',
                          'libayatana-indicator'], collector.targets)


class NoiseTest(unittest.TestCase):

    def test_is_noise_line__failed_to_record_path_is_not_an_error(self):
        self.assertTrue(parsers.is_noise_line('Failed to record path /lib32'))

    def test_is_noise_line__progress_marks(self):
        self.assertTrue(parsers.is_noise_line(' [OK] Syncing filesystems      success'))

    def test_is_noise_line__a_package_line_is_not_noise(self):
        self.assertFalse(parsers.is_noise_line('vlc - a player'))

    def test_strip_ansi(self):
        self.assertEqual('vlc', parsers.strip_ansi('\x1b[32mvlc\x1b[0m'))


class SummaryWithSeparatorsTest(unittest.TestCase):
    """Resúmenes que contienen los propios separadores del formato."""

    def test_a_summary_with_a_dash_does_not_hide_the_package(self):
        # el formato de cuatro columnas de «eopkg li» deja el resumen al final: si contiene
        # « - », la estrategia de corte por guion producía un nombre inválido y se descartaba
        # la línea entera, con lo que el paquete desaparecía de la lista de instalados
        entry = parsers.parse_package_line('gnome-shell 45.4 5 GNOME Shell - the core user interface')

        self.assertIsNotNone(entry)
        self.assertEqual('gnome-shell', entry['name'])
        self.assertEqual('45.4', entry['version'])
        self.assertEqual('5', entry['release'])
        self.assertEqual('GNOME Shell - the core user interface', entry['summary'])

    def test_a_summary_with_a_pipe_does_not_hide_the_package(self):
        entry = parsers.parse_package_line('ranger - Console file manager | vim-like')

        self.assertIsNotNone(entry)
        self.assertEqual('ranger', entry['name'])
        self.assertEqual('Console file manager | vim-like', entry['summary'])

    def test_informative_lines_are_still_discarded(self):
        # «Installed N / M» no entra aquí: es una línea de progreso de «eopkg it», que
        # analiza parse_install_progress, no el listado de paquetes
        for line in ('No packages to upgrade.', 'Total download size:', 'Reinstalling:'):
            with self.subTest(line=line):
                self.assertIsNone(parsers.parse_package_line(line))

    def test_the_package_list_keeps_them(self):
        output = ('gnome-shell 45.4 5 GNOME Shell - the core user interface\n'
                  'vlc 3.0.20 1 VLC media player\n')

        self.assertEqual(['gnome-shell', 'vlc'], [p['name'] for p in parsers.parse_package_list(output)])


class WrappedInfoNameLineTest(unittest.TestCase):
    """Salida real de Solus 4.9 (eopkg 5.0.0) para un paquete de nombre largo.

    eopkg parte 'Name : x, version: v, release: n' cuando no cabe en el ancho de línea.
    Antes de rejuntarla, el bloque se identificaba por el texto entero y se quedaba sin
    versión: la lista de actualizaciones enseñaba esos paquetes con la versión en blanco.
    """

    OUTPUT = """Installed package:
Name                : nvidia-580-glx-driver-common, version: 580.178.04,
                      release: 13
Summary             : Shared assets for the NVIDIA 580.xx Binary Driver
Component           : xorg.driver

Package found in Solus repository:
Name                : nvidia-580-glx-driver-common, version: 580.178.04,
                      release: 14
Summary             : Shared assets for the NVIDIA 580.xx Binary Driver
Component           : xorg.driver
"""

    def test_the_wrapped_name_line_must_yield_name_version_and_release(self):
        blocks = parsers.parse_info_blocks(self.OUTPUT)

        self.assertEqual(2, len(blocks))

        for block in blocks:
            self.assertEqual('nvidia-580-glx-driver-common', block['name'])
            self.assertEqual('580.178.04', block['version'])

        self.assertEqual('13', blocks[0]['release'])
        self.assertEqual('14', blocks[1]['release'])

    def test_the_package_must_be_indexed_by_its_real_name(self):
        sections = parsers.index_info_blocks(parsers.parse_info_blocks(self.OUTPUT))

        self.assertEqual(['nvidia-580-glx-driver-common'], list(sections))
        entry = sections['nvidia-580-glx-driver-common']
        self.assertEqual('580.178.04-13', parsers.format_version(entry['installed']['version'],
                                                                entry['installed']['release']))
        self.assertEqual('580.178.04-14', parsers.format_version(entry['repository']['version'],
                                                                entry['repository']['release']))

    def test_the_fields_after_the_wrap_must_still_be_read(self):
        # la continuación no puede tragarse los campos siguientes, que van sin indentar
        blocks = parsers.parse_info_blocks(self.OUTPUT)

        self.assertEqual('xorg.driver', blocks[0]['component'])
        self.assertEqual('Shared assets for the NVIDIA 580.xx Binary Driver', blocks[0]['summary'])

    def test_a_name_line_that_does_not_wrap_must_keep_working(self):
        output = "Name                : vlc, version: 3.0.23, release: 203\n"

        block = parsers.parse_info_blocks(output)[0]

        self.assertEqual(('vlc', '3.0.23', '203'),
                         (block['name'], block['version'], block['release']))


class WrappedInfoNameLineCutPointsTest(unittest.TestCase):
    """Los tres puntos por donde eopkg puede partir la línea compuesta.

    ``align()`` (``pisi/cli/__init__.py``) retrocede hasta el último espacio anterior a la
    columna ``ancho - 22`` (58 con las 80 columnas de reserva de ``shutil.get_terminal_size``),
    y en esta línea sólo hay espacios detrás de una coma y detrás de ``version:`` /
    ``release:``.  Las salidas de abajo están renderizadas con ese algoritmo a partir de los
    nombres, versiones y releases del índice real de Solus (``shannon``): de los 11660
    paquetes, 325 envuelven la línea (167 cortan tras la coma, 153 tras ``release:`` y 5 tras
    ``version:``).
    """

    # anoise-media-community-extension1 0.0.17-10 (índice de Solus): corte tras la coma
    CUT_AFTER_COMMA = ("Name                : anoise-media-community-extension1, version: 0.0.17,\n"
                       "                      release: 10\n")

    # gnome-shell-extension-native-window-placement 48.3-58: corte tras 'version:'
    CUT_AFTER_VERSION = ("Name                : gnome-shell-extension-native-window-placement, "
                         "version:\n                      48.3, release: 58\n")

    # gstreamer-1.0-plugins-bad-libs 1.26.7-120: corte tras 'release:', el caso que dejaba
    # 'release' valiendo ':' y el número pegado al final del nombre
    CUT_AFTER_RELEASE = ("Name                : gstreamer-1.0-plugins-bad-libs, version: 1.26.7, "
                         "release:\n                      120\n")

    # vlc 3.0.21-190: cabe entera, control sin envoltura
    NO_CUT = "Name                : vlc, version: 3.0.21, release: 190\n"

    def _parse(self, output: str):
        block = parsers.parse_info_blocks(output)[0]
        return block['name'], block['version'], block['release']

    def test_a_cut_after_the_comma(self):
        self.assertEqual(('anoise-media-community-extension1', '0.0.17', '10'),
                         self._parse(self.CUT_AFTER_COMMA))

    def test_a_cut_after_the_version_key(self):
        self.assertEqual(('gnome-shell-extension-native-window-placement', '48.3', '58'),
                         self._parse(self.CUT_AFTER_VERSION))

    def test_a_cut_after_the_release_key(self):
        # antes se leía ('gstreamer-1.0-plugins-bad-libs 120', '1.26.7', ':')
        self.assertEqual(('gstreamer-1.0-plugins-bad-libs', '1.26.7', '120'),
                         self._parse(self.CUT_AFTER_RELEASE))

    def test_a_line_that_does_not_wrap(self):
        self.assertEqual(('vlc', '3.0.21', '190'), self._parse(self.NO_CUT))

    def test_the_release_must_never_be_a_stray_colon(self):
        # la mitad de línea suelta no puede casar por sí sola: sin esto, ':' pasaba por release
        half = "Name                : gstreamer-1.0-plugins-bad-libs, version: 1.26.7, release:"

        self.assertIsNone(parsers.RE_INFO_NAME_LINE.match(half))

    def test_the_fields_after_a_release_cut_must_still_be_read(self):
        output = (self.CUT_AFTER_RELEASE
                  + "Summary             : GStreamer bad plugins libraries\n"
                    "Component           : multimedia.library\n")

        block = parsers.parse_info_blocks(output)[0]

        self.assertEqual('gstreamer-1.0-plugins-bad-libs', block['name'])
        self.assertEqual('GStreamer bad plugins libraries', block['summary'])
        self.assertEqual('multimedia.library', block['component'])
