import os
import tempfile
from unittest import TestCase
from unittest.mock import Mock

import requests

from bauh.gems.arch import VENDORED_CATEGORIES_FILE_PATH, VENDORED_GPG_SERVERS_FILE_PATH
from bauh.gems.arch import data as arch_data


class FakeResponse:
    """Respuesta HTTP minima equivalente a la de 'requests'."""

    def __init__(self, text: str):
        self.text = text
        self.status_code = 200


def offline_http_client() -> Mock:
    """Cliente HTTP que simula la red caida."""
    client = Mock()
    client.get.side_effect = requests.exceptions.ConnectionError('network is down')
    return client


class ParseCategoriesTest(TestCase):

    def test_parse_categories__ignores_comments_blank_lines_and_malformed_entries(self):
        content = ('# cabecera de procedencia\n'
                   '\n'
                   'firefox=Network,WebBrowser\n'
                   '   \n'
                   'linea-sin-igual\n'
                   '=Game\n'
                   'gimp=Graphics\n')

        categories = arch_data.parse_categories(content)

        self.assertEqual({'firefox': ['Network', 'WebBrowser'], 'gimp': ['Graphics']}, categories)

    def test_parse_categories__none_and_empty_return_empty_dict(self):
        self.assertEqual({}, arch_data.parse_categories(None))
        self.assertEqual({}, arch_data.parse_categories(''))

    def test_parse_gpg_servers__ignores_comments_and_duplicates(self):
        content = ('# cabecera\n'
                   'keyserver.ubuntu.com\n'
                   '\n'
                   'keys.openpgp.org\n'
                   'keyserver.ubuntu.com\n')

        self.assertEqual(['keyserver.ubuntu.com', 'keys.openpgp.org'], arch_data.parse_gpg_servers(content))

    def test_parse_gpg_servers__none_returns_empty_list(self):
        self.assertEqual([], arch_data.parse_gpg_servers(None))


class VendoredFilesTest(TestCase):

    def test_vendored_files_exist(self):
        self.assertTrue(os.path.isfile(VENDORED_CATEGORIES_FILE_PATH))
        self.assertTrue(os.path.isfile(VENDORED_GPG_SERVERS_FILE_PATH))

    def test_vendored_categories_have_the_expected_format(self):
        with open(VENDORED_CATEGORIES_FILE_PATH) as f:
            content = f.read()

        for line in content.split('\n'):
            stripped = line.strip()

            if not stripped or stripped.startswith('#'):
                continue

            self.assertIn('=', stripped, f"line without '=': {stripped}")
            name, _, cats = stripped.partition('=')
            self.assertTrue(name.strip(), f'entry without a package name: {stripped}')
            self.assertTrue([c for c in cats.split(',') if c.strip()], f'entry without categories: {stripped}')

    def test_vendored_categories_declare_their_origin_and_license(self):
        with open(VENDORED_CATEGORIES_FILE_PATH) as f:
            header = [ln for ln in f.read().split('\n') if ln.startswith('#')]

        joined = '\n'.join(header)
        self.assertIn('bauh-files', joined)
        self.assertIn('2026-08-23', joined)
        self.assertIn('zlib/libpng', joined)

    def test_vendored_gpg_servers_declare_their_origin_and_license(self):
        with open(VENDORED_GPG_SERVERS_FILE_PATH) as f:
            header = [ln for ln in f.read().split('\n') if ln.startswith('#')]

        joined = '\n'.join(header)
        self.assertIn('bauh-files', joined)
        self.assertIn('2026-08-23', joined)
        self.assertIn('zlib/libpng', joined)

    def test_read_vendored_categories__parses_a_meaningful_amount_of_entries(self):
        categories = arch_data.read_vendored_categories()

        self.assertGreater(len(categories), 100)
        self.assertEqual(['Game'], categories['0ad'])
        self.assertIn('Game', categories['yuzu-mainline-bin'])

    def test_read_vendored_gpg_servers__returns_at_least_one_server(self):
        servers = arch_data.read_vendored_gpg_servers()

        self.assertTrue(servers)
        self.assertEqual('keyserver.ubuntu.com', servers[0])


class ReadCategoriesTest(TestCase):

    def test_read_categories__no_cache_falls_back_to_the_vendored_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            categories = arch_data.read_categories(cache_file_path=f'{tmp}/missing/categories.txt')

        self.assertEqual(arch_data.read_vendored_categories(), categories)

    def test_read_categories__empty_cache_falls_back_to_the_vendored_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = f'{tmp}/categories.txt'

            with open(cache_path, 'w') as f:
                f.write('\n')

            categories = arch_data.read_categories(cache_file_path=cache_path)

        self.assertEqual(arch_data.read_vendored_categories(), categories)

    def test_read_categories__cache_wins_over_the_vendored_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = f'{tmp}/categories.txt'

            with open(cache_path, 'w') as f:
                f.write('vlc=AudioVideo\n')

            categories = arch_data.read_categories(cache_file_path=cache_path)

        self.assertEqual({'vlc': ['AudioVideo']}, categories)


class GpgServersTest(TestCase):

    def test_get_gpg_servers__network_down_and_no_cache_returns_the_vendored_copy(self):
        client = offline_http_client()

        with tempfile.TemporaryDirectory() as tmp:
            servers = arch_data.get_gpg_servers(http_client=client, cache_file_path=f'{tmp}/gpgservers.txt')

        self.assertEqual(arch_data.read_vendored_gpg_servers(), servers)
        client.get.assert_called_once()

    def test_get_first_gpg_server__network_down_returns_the_vendored_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = arch_data.get_first_gpg_server(http_client=offline_http_client(),
                                                    cache_file_path=f'{tmp}/gpgservers.txt')

        self.assertEqual('keyserver.ubuntu.com', server)

    def test_get_first_gpg_server__no_http_client_returns_the_vendored_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = arch_data.get_first_gpg_server(http_client=None,
                                                    cache_file_path=f'{tmp}/gpgservers.txt')

        self.assertEqual('keyserver.ubuntu.com', server)

    def test_get_gpg_servers__cache_is_used_when_the_download_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = f'{tmp}/gpgservers.txt'

            with open(cache_path, 'w') as f:
                f.write('keys.openpgp.org\n')

            servers = arch_data.get_gpg_servers(http_client=offline_http_client(), cache_file_path=cache_path)

        self.assertEqual(['keys.openpgp.org'], servers)

    def test_get_gpg_servers__successful_download_refreshes_the_cache(self):
        client = Mock()
        client.get.return_value = FakeResponse('pgp.mit.edu\nkeyserver.ubuntu.com\n')

        with tempfile.TemporaryDirectory() as tmp:
            cache_path = f'{tmp}/gpgservers.txt'
            servers = arch_data.get_gpg_servers(http_client=client, cache_file_path=cache_path)

            with open(cache_path) as f:
                cached = f.read()

        self.assertEqual(['pgp.mit.edu', 'keyserver.ubuntu.com'], servers)
        self.assertEqual('pgp.mit.edu\nkeyserver.ubuntu.com\n', cached)

    def test_refresh_gpg_servers__empty_response_does_not_create_the_cache(self):
        client = Mock()
        client.get.return_value = None

        with tempfile.TemporaryDirectory() as tmp:
            cache_path = f'{tmp}/gpgservers.txt'
            servers = arch_data.refresh_gpg_servers(http_client=client, cache_file_path=cache_path)

            self.assertEqual([], servers)
            self.assertFalse(os.path.exists(cache_path))
