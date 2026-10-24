import os
import tempfile
from unittest import TestCase, skipUnless
from unittest.mock import patch

from bauh.view.core import matugen

try:
    import tomllib
except ImportError:  # Python < 3.11: register() no puede validar el TOML
    tomllib = None


class MatugenRegistrationTest(TestCase):
    """La plantilla de bauh se declara en la configuración de matugen sin estropear la del usuario."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.config = os.path.join(self.tmp, 'matugen', 'config.toml')
        self.template = os.path.join(self.tmp, 'matugen', 'templates', 'gekko-bauh.css')
        self.output = '~/.config/gekko-bauh/matugen-colors.css'

    def tearDown(self):
        self._tmp.cleanup()

    def _register(self):
        return matugen.register(config_file=self.config, template_file=self.template, output_file=self.output)

    def _read(self, path: str) -> str:
        with open(path, encoding='utf-8') as f:
            return f.read()

    def _write_config(self, content: str):
        os.makedirs(os.path.dirname(self.config), exist_ok=True)

        with open(self.config, 'w', encoding='utf-8') as f:
            f.write(content)

    def test_the_bundled_template_uses_the_matugen_syntax_and_the_names_bauh_reads(self):
        # misma forma que el ejemplo oficial de matugen 4.2 (example/colors.whatever-extension)
        content = self._read(matugen.bundled_template_path())

        self.assertIn('@define-color accent_color {{ colors.primary.default.hex }};', content)
        self.assertIn('@define-color window_bg_color {{ colors.surface.default.hex }};', content)
        self.assertIn('@define-color border_color {{ colors.outline_variant.default.hex }};', content)

    def test_without_a_config_it_creates_one_with_the_template(self):
        ok, backup = self._register()

        self.assertTrue(ok)
        self.assertIsNone(backup)
        self.assertEqual(self._read(matugen.bundled_template_path()), self._read(self.template))

        content = self._read(self.config)
        self.assertTrue(content.startswith('[config]\n'))
        self.assertIn('[templates.gekko-bauh]', content)
        self.assertIn(f"input_path = '{self.template}'", content)
        self.assertIn(f"output_path = '{self.output}'", content)
        self.assertTrue(matugen.is_registered(self.config))

    def test_it_appends_to_the_existing_config_and_keeps_a_copy(self):
        original = "[config]\nreload_apps = true\n\n[templates.kitty]\ninput_path = 'a'\noutput_path = 'b'\n"
        self._write_config(original)

        ok, backup = self._register()

        self.assertTrue(ok)
        self.assertEqual(original, self._read(backup))
        content = self._read(self.config)
        self.assertTrue(content.startswith(original.rstrip('\n')))
        self.assertIn('[templates.gekko-bauh]', content)

    @skipUnless(tomllib, 'tomllib requiere Python 3.11+')
    def test_the_result_is_valid_toml(self):
        self._write_config("[config]\n\n[templates.kitty]\ninput_path = 'a'\noutput_path = 'b'\n")
        self._register()

        parsed = tomllib.loads(self._read(self.config))
        self.assertEqual(self.template, parsed['templates']['gekko-bauh']['input_path'])
        self.assertEqual('a', parsed['templates']['kitty']['input_path'])

    def test_registering_twice_does_not_duplicate_the_section(self):
        self._register()
        ok, backup = self._register()

        self.assertTrue(ok)
        self.assertIsNone(backup)
        self.assertEqual(1, self._read(self.config).count('[templates.gekko-bauh]'))

    def test_an_inline_entry_also_counts_as_registered(self):
        self._write_config("[templates]\ngekko-bauh = { input_path = 'x', output_path = 'y' }\n")

        self.assertTrue(matugen.is_registered(self.config))

    def test_other_templates_do_not_count_as_registered(self):
        self._write_config("[templates.gekko-bauh-old-theme]\ninput_path = 'x'\n")

        self.assertFalse(matugen.is_registered(self.config))

    @skipUnless(tomllib, 'tomllib requiere Python 3.11+')
    def test_a_broken_config_is_not_touched(self):
        broken = '[config\nreload_apps = true\n'
        self._write_config(broken)

        ok, error = self._register()

        self.assertFalse(ok)
        self.assertTrue(error)
        self.assertEqual(broken, self._read(self.config))
        self.assertFalse([f for f in os.listdir(os.path.dirname(self.config)) if '.bak-gekko-bauh-' in f])

    def test_is_installed_looks_for_the_matugen_command(self):
        with patch('bauh.view.core.matugen.shutil.which', return_value=None):
            self.assertFalse(matugen.is_installed())

        with patch('bauh.view.core.matugen.shutil.which', return_value='/usr/bin/matugen'):
            self.assertTrue(matugen.is_installed())
