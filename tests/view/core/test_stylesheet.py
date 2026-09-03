import importlib.util
import logging
import os
import tempfile
import unittest
from unittest import TestCase
from unittest.mock import patch

from bauh import stylesheet

PYQT5_AVAILABLE = importlib.util.find_spec('PyQt5') is not None


class StylesheetTest(TestCase):

    def test__process_var_of_vars__it_should_remove_vars_pointing_to_themselves(self):
        var_map = {
            'abc': 'aaa',
            'xxx': '@xxx'
        }

        stylesheet.process_var_of_vars(var_map)

        self.assertEqual(1, len(var_map))
        self.assertIn('abc', var_map)
        self.assertEqual('aaa', var_map['abc'])

    def test__process_var_of_vars__it_should_remove_vars_pointing_to_unknown_vars(self):
        var_map = {
            'abc': 'aaa',
            'xxx': '@def'
        }

        stylesheet.process_var_of_vars(var_map)

        self.assertEqual(1, len(var_map))
        self.assertIn('abc', var_map)
        self.assertEqual('aaa', var_map['abc'])

    def test__process_var_of_vars__it_should_not_replace_invalid_expressions(self):
        var_map = {
            'abc': 'aaa',
            'bcd': '@ xpto'  # has a space between @ and 'xpto'
        }

        self.assertEqual(2, len(var_map))
        self.assertIn('abc', var_map)
        self.assertEqual('aaa', var_map['abc'])
        self.assertIn('bcd', var_map)
        self.assertEqual('@ xpto', var_map['bcd'])

    def test__process_var_of_vars__it_should_replace_value_at_first_iteration(self):
        var_map = {
            'abc': 'aaa',
            'xxx': '@abc'
        }

        stylesheet.process_var_of_vars(var_map)

        self.assertEqual(2, len(var_map))
        self.assertIn('abc', var_map)
        self.assertEqual('aaa', var_map['abc'])
        self.assertIn('xxx', var_map)
        self.assertEqual('aaa', var_map['xxx'])

    def test__process_var_of_vars__it_should_replace_value_at_second_iteration(self):
        var_map = {
            'abc': 'aaa',
            'def': '@abc',
            'xxx': '@def'
        }

        stylesheet.process_var_of_vars(var_map)

        self.assertEqual(3, len(var_map))
        self.assertIn('abc', var_map)
        self.assertEqual('aaa', var_map['abc'])
        self.assertIn('def', var_map)
        self.assertEqual('aaa', var_map['def'])
        self.assertIn('xxx', var_map)
        self.assertEqual('aaa', var_map['xxx'])

    def test__process_var_of_vars__it_should_replace_value_at_third_iteration(self):
        var_map = {
            'abc': 'aaa',
            'def': '@abc',
            'fgh': '@def',
            'xxx': '@fgh'
        }

        stylesheet.process_var_of_vars(var_map)

        self.assertEqual(4, len(var_map))
        self.assertIn('abc', var_map)
        self.assertEqual('aaa', var_map['abc'])
        self.assertIn('def', var_map)
        self.assertEqual('aaa', var_map['def'])
        self.assertIn('fgh', var_map)
        self.assertEqual('aaa', var_map['fgh'])
        self.assertIn('xxx', var_map)
        self.assertEqual('aaa', var_map['xxx'])

    def test__process_var_of_vars__it_should_replace_multiple_vars(self):
        var_map = {
            'abc': 'aaa',
            'def': '@abc',
            'fgh': 'bbb',
            'ijk': '@fgh',
            'lmn': '@ijk'
        }

        stylesheet.process_var_of_vars(var_map)

        self.assertEqual(5, len(var_map))
        self.assertIn('abc', var_map)
        self.assertEqual('aaa', var_map['abc'])
        self.assertIn('def', var_map)
        self.assertEqual('aaa', var_map['def'])
        self.assertIn('fgh', var_map)
        self.assertEqual('bbb', var_map['fgh'])
        self.assertIn('ijk', var_map)
        self.assertEqual('bbb', var_map['ijk'])
        self.assertIn('lmn', var_map)
        self.assertEqual('bbb', var_map['lmn'])

    def test__process_var_of_vars__it_should_not_hang_on_cycles(self):
        var_map = {
            'a': '@b',
            'b': '@a',
            'c': '#fff'
        }

        stylesheet.process_var_of_vars(var_map)

        self.assertEqual({'c': '#fff'}, var_map)

    def test__process_var_of_vars__it_should_not_hang_on_long_cycles(self):
        var_map = {
            'a': '@b',
            'b': '@c',
            'c': '@a',
            'ok': '#000'
        }

        stylesheet.process_var_of_vars(var_map)

        self.assertEqual({'ok': '#000'}, var_map)


class ThemeDiscoveryTest(TestCase):

    def test__read_default_themes__it_should_map_matugen_and_gtk_to_their_own_files(self):
        themes = stylesheet.read_default_themes()

        for key in ('aurora', 'matugen', 'gtk'):
            self.assertIn(key, themes)

        self.assertNotEqual(themes['aurora'], themes['matugen'])
        self.assertNotEqual(themes['aurora'], themes['gtk'])
        self.assertNotEqual(themes['matugen'], themes['gtk'])
        self.assertTrue(themes['matugen'].endswith('/matugen/matugen.qss'))
        self.assertTrue(themes['gtk'].endswith('/gtk/gtk.qss'))

    def test__read_all_themes_metadata__it_should_contain_matugen_and_gtk_with_different_paths(self):
        metadata = {m.key: m for m in stylesheet.read_all_themes_metadata()}

        for key in ('aurora', 'matugen', 'gtk'):
            self.assertIn(key, metadata)

        paths = {metadata[key].file_path for key in ('aurora', 'matugen', 'gtk')}
        self.assertEqual(3, len(paths))

    def test__read_all_themes_metadata__it_should_read_the_matugen_own_metadata(self):
        metadata = {m.key: m for m in stylesheet.read_all_themes_metadata()}

        self.assertEqual('aurora', metadata['matugen'].root_theme)
        self.assertNotEqual(metadata['aurora'].default_name, metadata['matugen'].default_name)
        self.assertNotEqual(metadata['aurora'].default_name, metadata['gtk'].default_name)

    def test__read_theme_chain__it_should_return_the_inheritance_chain(self):
        themes = stylesheet.read_default_themes()

        self.assertEqual(('matugen', 'aurora', 'default'), stylesheet.read_theme_chain('matugen', themes))
        self.assertEqual(('gtk', 'aurora', 'default'), stylesheet.read_theme_chain('gtk', themes))

    def test__read_theme_chain__it_should_not_hang_on_cyclic_inheritance(self):
        with tempfile.TemporaryDirectory() as tmp:
            for key, root in (('a', 'b'), ('b', 'a')):
                with open(f'{tmp}/{key}.qss', 'w') as f:
                    f.write('/* x */')
                with open(f'{tmp}/{key}.meta', 'w') as f:
                    f.write(f'root_theme={root}')

            themes = {'a': f'{tmp}/a.qss', 'b': f'{tmp}/b.qss'}
            self.assertEqual(('a', 'b'), stylesheet.read_theme_chain('a', themes))

    def test__dynamic_theme_kind__it_should_be_based_on_the_key_and_its_inheritance_chain(self):
        themes = stylesheet.read_default_themes()

        self.assertEqual('matugen', stylesheet.dynamic_theme_kind('matugen', themes))
        self.assertEqual('gtk', stylesheet.dynamic_theme_kind('gtk', themes))
        self.assertIsNone(stylesheet.dynamic_theme_kind('aurora', themes))
        self.assertIsNone(stylesheet.dynamic_theme_kind('light', themes))
        self.assertIsNone(stylesheet.dynamic_theme_kind(None, themes))

    def test__dynamic_theme_kind__it_should_detect_a_user_theme_inheriting_from_matugen(self):
        with tempfile.TemporaryDirectory() as tmp:
            user_qss = f'{tmp}/mine.qss'

            with open(user_qss, 'w') as f:
                f.write('/* mine */')

            with open(f'{tmp}/mine.meta', 'w') as f:
                f.write('root_theme=matugen')

            themes = dict(stylesheet.read_default_themes())
            themes[user_qss] = user_qss

            self.assertEqual('matugen', stylesheet.dynamic_theme_kind(user_qss, themes))

    def test__dynamic_color_sources__it_should_split_matugen_and_gtk_files(self):
        matugen = stylesheet.dynamic_color_sources('matugen')
        gtk = stylesheet.dynamic_color_sources('gtk')

        self.assertEqual(1, len(matugen))
        self.assertTrue(matugen[0].endswith('/.cache/matugen/colors-gtk.css'))
        self.assertTrue(all('matugen' not in path for path in gtk))
        self.assertTrue(any(path.startswith('/etc/gtk-3.0/') for path in gtk))
        self.assertTrue(any('/.config/gtk-4.0/' in path for path in gtk))

    def test__dynamic_color_sources__system_files_must_come_before_the_user_ones(self):
        gtk = stylesheet.dynamic_color_sources('gtk')
        system_idx = [i for i, path in enumerate(gtk) if path.startswith('/etc/')]
        user_idx = [i for i, path in enumerate(gtk) if '/.config/' in path]

        self.assertTrue(max(system_idx) < min(user_idx))


class GtkColorParsingTest(TestCase):

    def _write(self, directory: str, name: str, content: str) -> str:
        path = os.path.join(directory, name)

        with open(path, 'w') as f:
            f.write(content)

        return path

    def test__parse_gtk_matugen_colors__it_should_follow_a_relative_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, 'colors.css', '@define-color window_bg_color #123456;\n')
            main = self._write(tmp, 'gtk.css', '@import "colors.css";\n'
                                               '@define-color window_fg_color #abcdef;\n')

            colors = stylesheet.parse_gtk_matugen_colors(sources=(main,))

        self.assertEqual('#123456', colors.get('window_bg_color'))
        self.assertEqual('#abcdef', colors.get('window_fg_color'))

    def test__parse_gtk_matugen_colors__the_importing_file_must_win_over_the_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, 'colors.css', '@define-color window_bg_color #111111;\n')
            main = self._write(tmp, 'gtk.css', '@import url("colors.css");\n'
                                               '@define-color window_bg_color #222222;\n')

            colors = stylesheet.parse_gtk_matugen_colors(sources=(main,))

        self.assertEqual('#222222', colors.get('window_bg_color'))

    def test__parse_gtk_matugen_colors__it_should_accept_alpha_names_and_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = self._write(tmp, 'gtk.css',
                               '@define-color theme_bg_color #123456;\n'
                               '@define-color window_bg_color @theme_bg_color;\n'
                               '@define-color card_bg_color alpha(@theme_bg_color, 0.5);\n'
                               '@define-color window_fg_color white;\n'
                               '@define-color accent_color rgba(1, 2, 3, 0.4);\n')

            colors = stylesheet.parse_gtk_matugen_colors(sources=(main,))

        self.assertEqual('#123456', colors.get('window_bg_color'))
        self.assertEqual('#123456', colors.get('card_bg_color'))
        self.assertEqual('white', colors.get('window_fg_color'))
        self.assertEqual('rgba(1, 2, 3, 0.4)', colors.get('accent_color'))

    def test__parse_gtk_matugen_colors__it_should_discard_unresolvable_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = self._write(tmp, 'gtk.css',
                               '@define-color a @b;\n'
                               '@define-color b @a;\n'
                               '@define-color ok #010203;\n')

            colors = stylesheet.parse_gtk_matugen_colors(sources=(main,))

        self.assertEqual({'ok': '#010203'}, colors)

    def test__parse_gtk_matugen_colors__the_last_source_must_win(self):
        with tempfile.TemporaryDirectory() as tmp:
            system = self._write(tmp, 'system.css', '@define-color window_bg_color #000000;\n')
            user = self._write(tmp, 'user.css', '@define-color window_bg_color #ffffff;\n')

            colors = stylesheet.parse_gtk_matugen_colors(sources=(system, user))

        self.assertEqual('#ffffff', colors.get('window_bg_color'))

    def test__parse_gtk_matugen_colors__it_should_ignore_missing_files(self):
        self.assertEqual({}, stylesheet.parse_gtk_matugen_colors(sources=('/tmp/does-not-exist-bauh.css',)))


class ColorUtilsTest(TestCase):

    def test__is_dark_color__it_should_detect_dark_and_light_backgrounds(self):
        self.assertTrue(stylesheet.is_dark_color('#161B22'))
        self.assertTrue(stylesheet.is_dark_color('#000'))
        self.assertFalse(stylesheet.is_dark_color('#FFFFFF'))
        self.assertFalse(stylesheet.is_dark_color('white'))
        self.assertFalse(stylesheet.is_dark_color(None))

    def test__contrast_color__it_should_return_the_readable_foreground(self):
        self.assertEqual('#FFFFFF', stylesheet.contrast_color('#161B22'))
        self.assertEqual('#000000', stylesheet.contrast_color('#FFFFFF'))

    def test__blend_colors__it_should_mix_two_hexadecimal_colors(self):
        self.assertEqual('#808080', stylesheet.blend_colors('#FFFFFF', '#000000', 0.5))
        self.assertEqual('#FFFFFF', stylesheet.blend_colors('#FFFFFF', '#000000', 1))

    def test__blend_colors__it_should_return_the_first_color_when_it_cannot_parse(self):
        # 'white' sí se interpreta (normalize_color traduce los nombres CSS); lo que no se
        # puede leer es un valor que no es un color en ningún formato
        self.assertEqual('#808080', stylesheet.blend_colors('white', '#000000', 0.5))
        self.assertEqual('var(--acento)', stylesheet.blend_colors('var(--acento)', '#000000', 0.5))

    def test__valid_color__it_should_reject_expressions_that_break_the_stylesheet(self):
        self.assertEqual('#161B22', stylesheet.valid_color('#161B22'))
        self.assertEqual('rgba(0, 0, 0, 0.5)', stylesheet.valid_color('rgba(0, 0, 0, 0.5)'))
        self.assertIsNone(stylesheet.valid_color('red; } QWidget { color: blue'))
        self.assertIsNone(stylesheet.valid_color('#12'))
        self.assertIsNone(stylesheet.valid_color(None))


# colores GTK/Matugen de ejemplo (paleta clara) usados por los tests del mapeo dinámico
DYNAMIC_COLORS = {
    'window_bg_color': '#FFFFFF',
    'view_bg_color': '#FAFAFA',
    'window_fg_color': '#101010',
    'accent_color': '#0066CC',
    'card_bg_color': '#EEEEEE',
    'sidebar_bg_color': '#F2F2F2'
}


class DynamicOverridesTest(TestCase):

    def test__build_dynamic_var_overrides__it_should_also_override_the_derived_variables(self):
        overrides = stylesheet.build_dynamic_var_overrides(DYNAMIC_COLORS, fallbacks={})

        self.assertEqual('#FFFFFF', overrides['outer_widget.background.color'])
        self.assertEqual('#0066CC', overrides['color.primary'])
        # derivadas que antes se quedaban con los valores oscuros de Aurora
        self.assertNotIn(overrides['disabled.color'], ('#484F58', None))
        self.assertNotIn(overrides['font.color.muted'], ('#8B949E', None))
        self.assertEqual('#EEEEEE', overrides['color.surface.light'])

    def test__build_dynamic_var_overrides__it_should_fall_back_to_aurora_values(self):
        overrides = stylesheet.build_dynamic_var_overrides({})
        aurora_vars = stylesheet.read_theme_vars('aurora')

        self.assertEqual(aurora_vars['outer_widget.background.color'],
                         overrides['outer_widget.background.color'])
        self.assertEqual(aurora_vars['color.primary'], overrides['color.primary'])
        self.assertEqual(aurora_vars['color.error'], overrides['color.error'])

    def test__read_theme_vars__matugen_overrides_must_reach_the_derived_variables(self):
        themes = stylesheet.read_default_themes()
        theme_vars = stylesheet.read_theme_vars('matugen', themes, DYNAMIC_COLORS)

        # scrollbar.handle deriva de @color.surface.lighter en aurora.vars
        self.assertEqual('#EEEEEE', theme_vars['scrollbar.handle.background.color'])
        # menu.item.selected deriva de @color.primary.dim
        self.assertEqual('#0066CC', theme_vars['menu.item.selected.background.color'])
        self.assertEqual('#FFFFFF', theme_vars['outer_widget.background.color'])

    def test__process_theme__matugen_must_not_keep_the_aurora_dark_palette(self):
        themes = stylesheet.read_default_themes()
        metadata = stylesheet.read_theme_metada(key='matugen', file_path=themes['matugen'])

        with open(themes['matugen']) as f:
            theme_str = f.read()

        processed = stylesheet.process_theme(file_path=themes['matugen'], theme_str=theme_str,
                                             metadata=metadata, available_themes=themes,
                                             dynamic_colors=DYNAMIC_COLORS)

        self.assertIsNotNone(processed)
        qss = processed[0]
        self.assertIn('#0066CC', qss)
        self.assertNotIn('#484F58', qss)  # color.surface.lighter de Aurora
        self.assertNotIn('#30363D', qss)  # color.surface.light de Aurora

    def test__process_theme__it_should_resolve_every_variable_of_the_dynamic_themes(self):
        themes = stylesheet.read_default_themes()

        for key in ('matugen', 'gtk', 'aurora'):
            metadata = stylesheet.read_theme_metada(key=key, file_path=themes[key])

            with open(themes[key]) as f:
                theme_str = f.read()

            processed = stylesheet.process_theme(file_path=themes[key], theme_str=theme_str,
                                                 metadata=metadata, available_themes=themes)

            self.assertIsNotNone(processed, key)
            self.assertNotIn('@color.', processed[0], key)
            self.assertNotIn('@font.', processed[0], key)


class CustomThemeCssTest(TestCase):

    def test__gen_custom_theme_css__it_should_return_nothing_when_disabled(self):
        config = {'custom_theme': {'enabled': False, 'background_color': '#000000'}}

        self.assertEqual('', stylesheet.gen_custom_theme_css(config))

    def test__gen_custom_theme_css__it_should_apply_the_colors_when_enabled(self):
        config = {'custom_theme': {'enabled': True, 'background_color': '#000000',
                                   'text_color': '#FFFFFF', 'accent_color': '#FF4500'}}

        css = stylesheet.gen_custom_theme_css(config)

        self.assertIn('background-color: #000000', css)
        self.assertIn('color: #FFFFFF', css)
        self.assertIn('#FF4500', css)

    def test__gen_custom_theme_css__it_should_discard_invalid_colors(self):
        config = {'custom_theme': {'enabled': True,
                                   'background_color': '#000000; } QWidget { color: red',
                                   'text_color': '#FFFFFF'}}

        css = stylesheet.gen_custom_theme_css(config)

        self.assertNotIn('QWidget { color: red', css)
        self.assertIn('color: #FFFFFF', css)

    def test__gen_custom_theme_css__the_image_path_must_be_quoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = os.path.join(tmp, 'my picture (1).png')

            with open(image, 'wb') as f:
                f.write(b'x')

            config = {'custom_theme': {'enabled': True, 'background_image': image}}
            css = stylesheet.gen_custom_theme_css(config)

        self.assertIn(f'url("{image}")', css)

    def test__process_theme__the_custom_css_must_be_added_only_once(self):
        themes = stylesheet.read_default_themes()
        metadata = stylesheet.read_theme_metada(key='aurora', file_path=themes['aurora'])

        with open(themes['aurora']) as f:
            theme_str = f.read()

        config = {'custom_theme': {'enabled': True, 'background_color': '#010203'}}
        processed = stylesheet.process_theme(file_path=themes['aurora'], theme_str=theme_str,
                                             metadata=metadata, available_themes=themes,
                                             app_config=config)

        self.assertEqual(1, processed[0].count('/* Custom Theme Overrides */'))
        self.assertTrue(processed[0].rstrip().endswith('}'))

    def test__process_theme__it_should_not_add_the_custom_css_when_disabled(self):
        themes = stylesheet.read_default_themes()
        metadata = stylesheet.read_theme_metada(key='aurora', file_path=themes['aurora'])

        with open(themes['aurora']) as f:
            theme_str = f.read()

        config = {'custom_theme': {'enabled': False, 'background_color': '#010203'}}
        processed = stylesheet.process_theme(file_path=themes['aurora'], theme_str=theme_str,
                                             metadata=metadata, available_themes=themes,
                                             app_config=config)

        self.assertNotIn('/* Custom Theme Overrides */', processed[0])
        self.assertNotIn('#010203', processed[0])


class VarFileTest(TestCase):

    def test__read_var_file__it_should_keep_values_containing_an_equal_sign(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(f'{tmp}/t.vars', 'w') as f:
                f.write('a=url(data:image/svg+xml;base64,AA==)\nb=#fff\n')

            var_map = stylesheet._read_var_file(f'{tmp}/t.qss')

        self.assertEqual('url(data:image/svg+xml;base64,AA==)', var_map['a'])
        self.assertEqual('#fff', var_map['b'])

    def test__read_var_file__the_overrides_must_be_applied_before_resolving_the_vars(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(f'{tmp}/t.vars', 'w') as f:
                f.write('base=#000000\nderived=@base\n')

            var_map = stylesheet._read_var_file(f'{tmp}/t.qss', overrides={'base': '#FFFFFF'})

        self.assertEqual('#FFFFFF', var_map['base'])
        self.assertEqual('#FFFFFF', var_map['derived'])

@unittest.skipUnless(PYQT5_AVAILABLE, 'PyQt5 no disponible')
class ThemeWatcherTest(TestCase):

    """Comprueba el vigilante de temas de bauh/context.py."""

    def setUp(self):
        # Se crea una QApplication, no una QCoreApplication: la instancia es unica por proceso
        # y la comparten todos los tests. Con una QCoreApplication, el 'QApplication.instance()'
        # de los tests que construyen widgets devuelve ese objeto sin GUI y Qt aborta el proceso
        # entero con «Cannot create a QWidget without QApplication».
        from PyQt5.QtWidgets import QApplication

        from bauh import context

        self.context = context
        self.app = QApplication.instance() or QApplication([])
        context._THEME_WATCHER = None
        context._THEME_WATCHER_ENABLED = True
        self.logger = logging.getLogger('bauh-test-theme-watcher')
        self.logger.addHandler(logging.NullHandler())
        self.logger.propagate = False
        self.themes = stylesheet.read_default_themes()

    def tearDown(self):
        if self.context._THEME_WATCHER is not None:
            self.context._THEME_WATCHER.stop()

        self.context._THEME_WATCHER = None
        self.context._THEME_WATCHER_ENABLED = True
        self.app.processEvents()

    def _update(self, theme_key: str):
        return self.context.update_theme_watcher(theme_key=theme_key, app=self.app,
                                                 logger=self.logger, available_themes=self.themes)

    def test__update_theme_watcher__it_should_only_be_created_for_dynamic_themes(self):
        self.assertIsNone(self._update('light'))
        self.assertIsNone(self.context._THEME_WATCHER)

        watcher = self._update('matugen')
        self.assertIsNotNone(watcher)
        self.assertEqual('matugen', watcher.kind)

    def test__update_theme_watcher__it_should_be_destroyed_when_the_theme_stops_being_dynamic(self):
        watcher = self._update('matugen')
        self.assertIsNotNone(watcher)

        self.assertIsNone(self._update('aurora'))
        self.assertIsNone(self.context._THEME_WATCHER)

    def test__update_theme_watcher__it_should_be_recreated_when_the_dynamic_kind_changes(self):
        matugen_watcher = self._update('matugen')
        gtk_watcher = self._update('gtk')

        self.assertIsNot(matugen_watcher, gtk_watcher)
        self.assertEqual('gtk', gtk_watcher.kind)

    def test__update_theme_watcher__it_should_be_reused_for_the_same_kind(self):
        first = self._update('matugen')
        second = self._update('matugen')

        self.assertIs(first, second)

    def test__update_theme_watcher__it_must_not_be_installed_when_disabled(self):
        self.context.disable_theme_watcher()

        self.assertIsNone(self._update('matugen'))
        self.assertIsNone(self.context._THEME_WATCHER)

    def test__theme_watcher__it_should_watch_the_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            colors = os.path.join(tmp, 'colors-gtk.css')

            with open(colors, 'w') as f:
                f.write('@define-color window_bg_color #000000;')

            watcher = self.context.ThemeWatcher(kind='matugen', app=self.app,
                                                logger=self.logger, paths=(colors,))
            try:
                self.assertIn(colors, watcher._watcher.files())
                self.assertIn(tmp, watcher._watcher.directories())
            finally:
                watcher.stop()

    def test__theme_watcher__it_should_re_add_a_path_after_an_atomic_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            colors = os.path.join(tmp, 'colors-gtk.css')

            with open(colors, 'w') as f:
                f.write('@define-color window_bg_color #000000;')

            watcher = self.context.ThemeWatcher(kind='matugen', app=self.app,
                                                logger=self.logger, paths=(colors,))
            try:
                watcher._watcher.removePath(colors)  # así queda el vigilante tras un rename
                self.assertNotIn(colors, watcher._watcher.files())

                watcher.refresh_paths()
                self.assertIn(colors, watcher._watcher.files())
            finally:
                watcher.stop()

    def test__theme_watcher__it_should_watch_a_file_created_after_the_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            colors = os.path.join(tmp, 'colors-gtk.css')
            watcher = self.context.ThemeWatcher(kind='matugen', app=self.app,
                                                logger=self.logger, paths=(colors,))
            try:
                self.assertEqual([], watcher._watcher.files())
                self.assertIn(tmp, watcher._watcher.directories())

                with open(colors, 'w') as f:
                    f.write('@define-color window_bg_color #000000;')

                watcher.refresh_paths()
                self.assertIn(colors, watcher._watcher.files())
            finally:
                watcher.stop()

    def test__theme_watcher__several_events_must_trigger_a_single_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            colors = os.path.join(tmp, 'colors-gtk.css')

            with open(colors, 'w') as f:
                f.write('@define-color window_bg_color #000000;')

            watcher = self.context.ThemeWatcher(kind='matugen', app=self.app,
                                                logger=self.logger, paths=(colors,))
            watcher.DEBOUNCE_MS = 0

            shared_config = {'ui': {'theme': 'gtk'}}

            with patch.object(self.context, 'set_theme') as set_theme, \
                    patch.object(self.context, 'read_shared_config', return_value=shared_config):
                try:
                    watcher._on_path_changed(colors)
                    watcher._on_path_changed(colors)
                    watcher._on_path_changed(colors)
                    self.assertEqual(0, set_theme.call_count)

                    for _ in range(20):
                        self.app.processEvents()
                finally:
                    watcher.stop()

            set_theme.assert_called_once()
            # el tema se relee de la configuración compartida, no de un dict capturado al arrancar
            self.assertEqual('gtk', set_theme.call_args.kwargs['theme_key'])
            self.assertIs(shared_config, set_theme.call_args.kwargs['app_config'])

    def test__theme_watcher__it_must_not_reload_without_a_configured_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            colors = os.path.join(tmp, 'colors-gtk.css')

            with open(colors, 'w') as f:
                f.write('@define-color window_bg_color #000000;')

            watcher = self.context.ThemeWatcher(kind='matugen', app=self.app,
                                                logger=self.logger, paths=(colors,))
            watcher.DEBOUNCE_MS = 0

            with patch.object(self.context, 'set_theme') as set_theme, \
                    patch.object(self.context, 'read_shared_config', return_value={'ui': {'theme': None}}):
                try:
                    watcher._on_path_changed(colors)

                    for _ in range(20):
                        self.app.processEvents()
                finally:
                    watcher.stop()

            set_theme.assert_not_called()

    def test__theme_watcher__a_stopped_watcher_must_not_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            colors = os.path.join(tmp, 'colors-gtk.css')

            with open(colors, 'w') as f:
                f.write('@define-color window_bg_color #000000;')

            watcher = self.context.ThemeWatcher(kind='matugen', app=self.app,
                                                logger=self.logger, paths=(colors,))
            watcher.DEBOUNCE_MS = 0

            with patch.object(self.context, 'set_theme') as set_theme, \
                    patch.object(self.context, 'read_shared_config', return_value={'ui': {'theme': 'matugen'}}):
                watcher._on_path_changed(colors)
                watcher.stop()

                for _ in range(20):
                    self.app.processEvents()

            set_theme.assert_not_called()


class NormalizeColorTest(TestCase):
    """Los ficheros de GTK y Matugen no solo traen hexadecimal."""

    def test_hexadecimal_is_expanded_to_six_digits(self):
        self.assertEqual('#FFFFFF', stylesheet.normalize_color('#fff'))
        self.assertEqual('#1E1E2E', stylesheet.normalize_color('#1e1e2e'))
        self.assertEqual('#1E1E2E', stylesheet.normalize_color('#1e1e2eff'))

    def test_rgb_and_rgba_are_understood(self):
        # libadwaita y varias plantillas de matugen escriben así los colores
        self.assertEqual('#1E1E2E', stylesheet.normalize_color('rgb(30, 30, 46)'))
        self.assertEqual('#1E1E2E', stylesheet.normalize_color('rgba(30, 30, 46, 0.9)'))
        self.assertEqual('#1E1E2E', stylesheet.normalize_color('rgb(11.8%, 11.8%, 18%)'))

    def test_css_names_are_understood(self):
        self.assertEqual('#FFFFFF', stylesheet.normalize_color('white'))
        self.assertEqual('#000000', stylesheet.normalize_color('black'))

    def test_unparseable_values_return_none(self):
        for value in (None, '', 'var(--acento)', 'rgb(a, b, c)', '#12345'):
            with self.subTest(value=value):
                self.assertIsNone(stylesheet.normalize_color(value))

    def test_a_dark_rgb_background_is_recognised_as_dark(self):
        # antes solo se leía hexadecimal, así que is_dark_color devolvía False y la aplicación
        # ponía una paleta clara sobre una hoja de estilo oscura
        self.assertTrue(stylesheet.is_dark_color('rgb(30, 30, 46)'))
        self.assertEqual('#FFFFFF', stylesheet.contrast_color('rgb(30, 30, 46)'))


class PrimaryButtonOverridesTest(TestCase):
    """El botón primario debe seguir al acento del sistema también al pasar el ratón."""

    def test_hover_and_pressed_derive_from_the_accent(self):
        overrides = stylesheet.build_dynamic_var_overrides({'accent_color': '#B4A0F5',
                                                            'window_bg_color': '#1E1E2E',
                                                            'window_fg_color': '#CDD6F4'})

        for key in ('button_ok.hover.background.color', 'button_ok.pressed.background.color'):
            with self.subTest(key=key):
                # el verde fijo de Aurora rompía la sincronización con el fondo de pantalla
                self.assertNotIn(overrides[key], ('#2EA043', '#1A7F37'))
                self.assertTrue(overrides[key].startswith('#'))

        self.assertNotEqual(overrides['button_ok.background.color'],
                            overrides['button_ok.hover.background.color'])
