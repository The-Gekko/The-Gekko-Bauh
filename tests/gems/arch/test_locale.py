import os
import warnings
from typing import Dict
from unittest import TestCase

from bauh.gems.arch import ROOT_DIR

LOCALE_DIR = f'{ROOT_DIR}/resources/locale'
REFERENCE_LANG = 'en'


def read_locale(lang: str) -> Dict[str, str]:
    keys = {}

    with open(f'{LOCALE_DIR}/{lang}', encoding='utf-8') as f:
        for line in f:
            stripped = line.rstrip('\n')

            if stripped.strip():
                keys[stripped.split('=', 1)[0]] = stripped.split('=', 1)[1]

    return keys


def list_langs() -> list:
    return sorted(f for f in os.listdir(LOCALE_DIR) if not f.endswith('.py') and f != '__pycache__')


class ArchLocaleTest(TestCase):
    """Coherencia de las traducciones de la gem arch (F74)."""

    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        cls.reference = read_locale(REFERENCE_LANG)

    @staticmethod
    def read_lines(lang: str) -> list:
        with open(f'{LOCALE_DIR}/{lang}', encoding='utf-8') as f:
            return f.readlines()

    def test_every_line_has_a_key_and_a_value(self):
        for lang in list_langs():
            with self.subTest(lang=lang):
                for number, line in enumerate(self.read_lines(lang), start=1):
                    if line.strip():
                        self.assertIn('=', line, f'{lang}:{number} sin separador "="')

    def test_no_duplicated_keys(self):
        for lang in list_langs():
            with self.subTest(lang=lang):
                seen = set()

                for number, line in enumerate(self.read_lines(lang), start=1):
                    if line.strip() and '=' in line:
                        key = line.split('=', 1)[0]
                        self.assertNotIn(key, seen, f'{lang}:{number} clave duplicada: {key}')
                        seen.add(key)

    def test_no_literal_newline_sequences(self):
        for lang in list_langs():
            with self.subTest(lang=lang):
                for key, value in read_locale(lang).items():
                    self.assertNotIn('\\n', value, f'{lang}: la clave {key} contiene "\\n" literal')

    def test_all_languages_have_the_same_keys_as_english(self):
        for lang in list_langs():
            if lang == REFERENCE_LANG:
                continue

            with self.subTest(lang=lang):
                keys = set(read_locale(lang).keys())
                self.assertEqual(set(), set(self.reference.keys()) - keys, f'{lang}: claves ausentes')
                self.assertEqual(set(), keys - set(self.reference.keys()), f'{lang}: claves sobrantes')

    def test_the_switch_to_repository_action_is_translated(self):
        expected = {'arch.action.switch_to_repo',
                    'arch.action.switch_to_repo.desc',
                    'arch.action.switch_to_repo.status',
                    'arch.action.switch_to_repo.confirm',
                    'arch.action.db_locked.running',
                    'arch.info.07_repo_available',
                    'arch.package.repo_available'}

        for lang in list_langs():
            with self.subTest(lang=lang):
                keys = read_locale(lang)

                for key in expected:
                    self.assertIn(key, keys)
                    self.assertTrue(keys[key].strip(), f'{lang}: la clave {key} esta vacia')
