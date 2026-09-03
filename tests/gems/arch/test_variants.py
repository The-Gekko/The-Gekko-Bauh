from unittest import TestCase

from bauh.gems.arch import variants


class SplitVariantTest(TestCase):

    def test_split_variant__binary_suffix(self):
        self.assertEqual(('yay', variants.VARIANT_BINARY), variants.split_variant('yay-bin'))

    def test_split_variant__development_suffixes(self):
        for suffix in ('git', 'svn', 'hg', 'bzr', 'cvs', 'nightly'):
            with self.subTest(suffix=suffix):
                self.assertEqual(('yay', variants.VARIANT_DEVELOPMENT), variants.split_variant(f'yay-{suffix}'))

    def test_split_variant__plain_name_is_not_a_variant(self):
        self.assertEqual(('yay', None), variants.split_variant('yay'))

    def test_split_variant__unknown_suffix_is_not_a_variant(self):
        self.assertEqual(('firefox-developer-edition', None),
                         variants.split_variant('firefox-developer-edition'))

    def test_split_variant__only_one_suffix_is_stripped(self):
        self.assertEqual(('yay-bin', variants.VARIANT_DEVELOPMENT), variants.split_variant('yay-bin-git'))

    def test_split_variant__too_short_base_is_rejected(self):
        self.assertEqual(('a-bin', None), variants.split_variant('a-bin'))

    def test_split_variant__none_and_empty(self):
        self.assertEqual((None, None), variants.split_variant(None))
        self.assertEqual(('', None), variants.split_variant(''))

    def test_split_variant__is_case_insensitive_on_the_suffix(self):
        self.assertEqual(('yay', variants.VARIANT_BINARY), variants.split_variant('yay-BIN'))


class HelpersTest(TestCase):

    def test_get_base_package_name(self):
        self.assertEqual('yay', variants.get_base_package_name('yay-git'))
        self.assertEqual('yay', variants.get_base_package_name('yay'))

    def test_get_variant_type(self):
        self.assertEqual(variants.VARIANT_BINARY, variants.get_variant_type('brave-bin'))
        self.assertEqual(variants.VARIANT_DEVELOPMENT, variants.get_variant_type('brave-git'))
        self.assertIsNone(variants.get_variant_type('brave'))

    def test_is_variant(self):
        self.assertTrue(variants.is_variant('mangohud-git'))
        self.assertFalse(variants.is_variant('mangohud'))

    def test_group_by_base_name(self):
        groups = variants.group_by_base_name(('yay', 'yay-bin', 'yay-git', 'paru', 'zoom'))

        self.assertEqual({'yay': ['yay', 'yay-bin', 'yay-git'],
                          'paru': ['paru'],
                          'zoom': ['zoom']}, groups)

    def test_group_by_base_name__ignores_empty_names(self):
        self.assertEqual({'yay': ['yay']}, variants.group_by_base_name(('yay', '', None)))
