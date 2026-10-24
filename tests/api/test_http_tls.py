import inspect
import logging
from unittest import TestCase
from unittest.mock import MagicMock, patch

from bauh.api.http import HttpClient
from bauh.view.core.config import CoreConfigManager
from bauh.view.core.downloader import AdaptableFileDownloader, SelfFileDownloader


class TlsAlwaysVerifiedTest(TestCase):
    """La opción para descargar sin verificar el certificado TLS se retiró: que no vuelva."""

    def setUp(self):
        self.client = HttpClient(logging.getLogger('test'), max_attempts=1, sleep=0)

    def test_there_is_no_way_to_ask_for_an_unverified_request(self):
        self.assertNotIn('ignore_ssl', inspect.signature(HttpClient.get).parameters)
        self.assertNotIn('check_ssl', inspect.signature(HttpClient.__init__).parameters)
        self.assertNotIn('check_ssl', inspect.signature(AdaptableFileDownloader.__init__).parameters)
        self.assertNotIn('check_ssl', inspect.signature(SelfFileDownloader.__init__).parameters)

    def test_requests_keep_the_default_verification(self):
        response = MagicMock(status_code=200, headers={})

        with patch.object(self.client.session, 'get', return_value=response) as get, \
                patch.object(self.client.session, 'head', return_value=response) as head:
            self.client.get('https://example.org')
            self.client.get_content_length_in_bytes('https://example.org')
            self.client.exists('https://example.org')

        # requests verifica el certificado salvo que se le pase verify=False
        for call in (*get.call_args_list, *head.call_args_list):
            self.assertNotEqual(False, call.kwargs.get('verify', True), call)

    def test_axel_is_never_told_to_skip_the_certificate(self):
        downloader = AdaptableFileDownloader(logger=logging.getLogger('test'), multithread_enabled=True,
                                             i18n=MagicMock(), http_client=self.client, multithread_client='axel')

        with patch('bauh.view.core.downloader.SimpleProcess') as process:
            downloader._get_axel_process(url='https://example.org/a.AppImage', output_path='/tmp/a.AppImage',
                                         cwd='/tmp', root_password=None, threads=4)

        self.assertNotIn('-k', process.call_args.kwargs['cmd'])

    def test_the_default_configuration_has_no_ssl_switch(self):
        self.assertNotIn('check_ssl', CoreConfigManager().get_default_config()['download'])
