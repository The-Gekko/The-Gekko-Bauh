import glob
import os
from unittest import TestCase

from bauh import ROOT_DIR as BAUH_ROOT_DIR
from bauh.gems.arch import ROOT_DIR
from bauh.gems.arch.model import ArchPackage
from bauh.view.util.translation import I18n

ARCH_LOCALE_DIR = f'{ROOT_DIR}/resources/locale'
VIEW_LOCALE_DIR = f'{BAUH_ROOT_DIR}/view/resources/locale'

NEW_ARCH_KEYS = ('arch.origin.aur',
                 'arch.variant.binary',
                 'arch.variant.development',
                 'arch.info.02_repository',
                 'arch.info.02_variant',
                 'arch.config.prefer_repository_binary',
                 'arch.config.prefer_repository_binary.tip',
                 'arch.install.repository_binary.title',
                 'arch.install.repository_binary.body')


def read_locale(file_path: str) -> dict:
    keys = {}

    with open(file_path) as f:
        for line in f.readlines():
            stripped = line.strip()

            if stripped:
                key, _, value = stripped.partition('=')
                keys[key.strip()] = value.strip()

    return keys


def locale_files(locale_dir: str) -> list:
    return [f for f in sorted(glob.glob(f'{locale_dir}/*')) if os.path.isfile(f) and not f.endswith('.py')]


def new_i18n(lang: str = 'en') -> I18n:
    keys = read_locale(f'{ARCH_LOCALE_DIR}/{lang}')
    keys.update(read_locale(f'{VIEW_LOCALE_DIR}/{lang}'))
    return I18n(current_key=lang, current_locale=keys, default_key=lang, default_locale=keys)


class ArchPackageOriginTest(TestCase):

    def setUp(self):
        self.i18n = new_i18n()

    def test_repository_label__repository_package_keeps_the_repository_name(self):
        for repository in ('core', 'extra', 'multilib', 'chaotic-aur'):
            with self.subTest(repository=repository):
                pkg = ArchPackage(name='yay', repository=repository, i18n=self.i18n)
                self.assertEqual(repository, pkg.repository_label)

    def test_repository_label__aur_package_is_translated(self):
        pkg = ArchPackage(name='yay', repository='aur', i18n=self.i18n)
        self.assertEqual('AUR', pkg.repository_label)

    def test_repository_label__unknown_origin(self):
        pkg = ArchPackage(name='yay', repository=None, i18n=self.i18n)
        self.assertEqual(self.i18n['unknown'], pkg.repository_label)

    def test_repository_label__without_i18n(self):
        self.assertEqual('AUR', ArchPackage(name='yay', repository='aur').repository_label)
        self.assertEqual('chaotic-aur', ArchPackage(name='yay', repository='chaotic-aur').repository_label)

    def test_name_tooltip__shows_the_translated_origin(self):
        pkg = ArchPackage(name='yay', repository='aur', i18n=self.i18n)
        self.assertIn('AUR', pkg.get_name_tooltip())

        repo_pkg = ArchPackage(name='yay', repository='chaotic-aur', i18n=self.i18n)
        self.assertIn('chaotic-aur', repo_pkg.get_name_tooltip())


class ArchPackageVariantTest(TestCase):

    def setUp(self):
        self.i18n = new_i18n()

    def test_variant_type_and_base(self):
        pkg = ArchPackage(name='mangohud-git', repository='aur', i18n=self.i18n)
        self.assertEqual('development', pkg.variant_type)
        self.assertEqual('mangohud', pkg.variant_base)

    def test_variant_type__plain_package(self):
        pkg = ArchPackage(name='mangohud', repository='aur', i18n=self.i18n)
        self.assertIsNone(pkg.variant_type)
        self.assertEqual('mangohud', pkg.variant_base)

    def test_get_variant_label__binary(self):
        pkg = ArchPackage(name='brave-bin', repository='aur', i18n=self.i18n)
        self.assertEqual(self.i18n['arch.variant.binary'].format('brave'), pkg.get_variant_label())

    def test_get_variant_label__development(self):
        pkg = ArchPackage(name='brave-git', repository='aur', i18n=self.i18n)
        self.assertEqual(self.i18n['arch.variant.development'].format('brave'), pkg.get_variant_label())

    def test_get_variant_label__plain_package_returns_none(self):
        self.assertIsNone(ArchPackage(name='brave', repository='aur', i18n=self.i18n).get_variant_label())

    def test_get_variant_label__without_i18n_returns_none(self):
        self.assertIsNone(ArchPackage(name='brave-bin', repository='aur').get_variant_label())


class ArchLocaleTest(TestCase):

    def test_new_keys_are_present_in_every_arch_locale(self):
        files = locale_files(ARCH_LOCALE_DIR)
        self.assertTrue(files)

        for file_path in files:
            keys = read_locale(file_path)

            for key in NEW_ARCH_KEYS:
                with self.subTest(locale=os.path.basename(file_path), key=key):
                    self.assertIn(key, keys)
                    self.assertTrue(keys[key], f'empty value for {key}')

    def test_variant_labels_have_exactly_one_placeholder(self):
        for file_path in locale_files(ARCH_LOCALE_DIR):
            keys = read_locale(file_path)

            for key in ('arch.variant.binary', 'arch.variant.development',
                        'arch.config.prefer_repository_binary.tip'):
                with self.subTest(locale=os.path.basename(file_path), key=key):
                    self.assertEqual(1, keys[key].count('{}'))

    def test_repository_binary_body_has_two_placeholders(self):
        for file_path in locale_files(ARCH_LOCALE_DIR):
            keys = read_locale(file_path)
            with self.subTest(locale=os.path.basename(file_path)):
                self.assertEqual(2, keys['arch.install.repository_binary.body'].count('{}'))

    def test_origin_column_key_is_present_in_every_view_locale(self):
        files = locale_files(VIEW_LOCALE_DIR)
        self.assertTrue(files)

        for file_path in files:
            with self.subTest(locale=os.path.basename(file_path)):
                keys = read_locale(file_path)
                self.assertIn('manage_window.columns.origin', keys)
                self.assertTrue(keys['manage_window.columns.origin'])
