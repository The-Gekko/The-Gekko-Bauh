import logging
import tempfile
import warnings
from unittest import TestCase
from unittest.mock import Mock, patch

from bauh import __package_name__
from bauh.api.abstract.controller import SearchResult
from bauh.gems.arch import data as arch_data
from bauh.gems.arch.config import ArchConfigManager
from bauh.gems.arch.controller import ArchManager, TransactionContext
from bauh.gems.arch.mapper import AURDataMapper
from bauh.gems.arch.model import ArchPackage
from tests.gems.arch.test_model import new_i18n

CONTROLLER = f'{__package_name__}.gems.arch.controller'


def aur_api_data(name: str, description: str = 'AUR package', version: str = '1.0-1') -> dict:
    """Datos minimos con la forma que devuelve la API de AUR."""
    return {'ID': 1,
            'Name': name,
            'PackageBase': name,
            'Description': description,
            'Version': version,
            'Maintainer': 'someone',
            'URLPath': f'/cgit/aur.git/snapshot/{name}.tar.gz',
            'NumVotes': 10,
            'Popularity': 1.5,
            'OutOfDate': None,
            'FirstSubmitted': 1600000000,
            'LastModified': 1700000000}


def repo_search_data(repository: str, version: str = '1.0-1', description: str = 'Repository package') -> dict:
    """Datos con la forma que devuelve 'pacman.search'."""
    return {'repository': repository, 'version': version, 'description': description}


def new_manager(config: dict) -> ArchManager:
    """Instancia de ArchManager con lo minimo para ejercitar los metodos probados.

    Se evita el constructor real porque exige un ApplicationContext completo.
    """
    manager = ArchManager.__new__(ArchManager)
    i18n = new_i18n()
    logger = logging.getLogger('arch-tests')
    logger.addHandler(logging.NullHandler())

    manager.i18n = i18n
    manager.logger = logger
    manager.categories = {}
    manager.configman = Mock()
    manager.configman.get_config.return_value = config
    manager.aur_mapper = AURDataMapper(http_client=Mock(), i18n=i18n, logger=logger)
    manager.aur_client = Mock()
    manager.index_aur = None
    return manager


def base_config(**overrides) -> dict:
    config = ArchConfigManager().get_default_config()
    config.update(overrides)
    return config


class SearchDeduplicationTest(TestCase):
    """Deduplicacion repositorio/AUR sobre el search() real."""

    def _run_search(self, manager: ArchManager, repositories: dict, aur_results: dict,
                    installed: list = None):
        installed = installed or []
        installed_names = {p.name for p in installed}

        def fill_installed(_self, _query, res):
            res['installed'] = installed_names
            res['installed_matches'] = set()

        def fill_repos(_self, _query, output):
            output['repositories'] = dict(repositories)

        def fill_aur(_self, _query, output):
            output['aur'] = dict(aur_results)

        with patch(f'{CONTROLLER}.aur.is_supported', return_value=True), \
                patch.object(ArchManager, '_ArchManager__fill_search_installed_and_matched', autospec=True,
                             side_effect=fill_installed), \
                patch.object(ArchManager, '_fill_repos_search_results', autospec=True, side_effect=fill_repos), \
                patch.object(ArchManager, '_fill_aur_search_results', autospec=True, side_effect=fill_aur), \
                patch.object(ArchManager, 'read_installed', autospec=True,
                             return_value=SearchResult(installed=list(installed), new=[], total=len(installed))):
            return manager.search(words='yay', disk_loader=None)

    def test_search__the_aur_duplicate_is_discarded_by_default(self):
        # no hace falta activar nada: compilar desde AUR algo que ya existe compilado en un
        # repositorio habilitado nunca es lo que el usuario quiere ver dos veces
        manager = new_manager(base_config())

        res = self._run_search(manager,
                               repositories={'yay': repo_search_data('chaotic-aur')},
                               aur_results={'yay': aur_api_data('yay')})

        self.assertEqual(1, len(res.new))
        self.assertEqual('yay', res.new[0].name)
        self.assertEqual('chaotic-aur', res.new[0].repository)
        self.assertEqual(1, res.total)

    def test_search__aur_only_packages_are_kept(self):
        manager = new_manager(base_config())

        res = self._run_search(manager,
                               repositories={'yay': repo_search_data('chaotic-aur')},
                               aur_results={'yay': aur_api_data('yay'), 'paru': aur_api_data('paru')})

        names = sorted(p.name for p in res.new)
        self.assertEqual(['paru', 'yay'], names)
        self.assertEqual('aur', next(p.repository for p in res.new if p.name == 'paru'))

    def test_search__variants_are_never_discarded_only_annotated(self):
        manager = new_manager(base_config())

        res = self._run_search(manager,
                               repositories={'yay': repo_search_data('chaotic-aur')},
                               aur_results={'yay': aur_api_data('yay'),
                                            'yay-git': aur_api_data('yay-git')})

        names = sorted(p.name for p in res.new)
        self.assertEqual(['yay', 'yay-git'], names)

        variant = next(p for p in res.new if p.name == 'yay-git')
        self.assertIn(manager.i18n['arch.variant.development'].format('yay'), variant.description)


class SearchVariantAnnotationTest(TestCase):

    def setUp(self):
        self.manager = new_manager(base_config())

    def test_annotate__binary_variant_when_the_base_is_in_the_results(self):
        base = ArchPackage(name='brave', repository='aur', description='Web browser', i18n=self.manager.i18n)
        variant = ArchPackage(name='brave-bin', repository='aur', description='Web browser',
                              i18n=self.manager.i18n)
        result = SearchResult(installed=[], new=[base, variant], total=2)

        self.manager._annotate_search_variants(result)

        expected = self.manager.i18n['arch.variant.binary'].format('brave')
        self.assertEqual('Web browser', base.description)
        self.assertEqual(f'Web browser [{expected}]', variant.description)

    def test_annotate__development_variant_when_the_base_comes_from_a_repository(self):
        repo_pkg = ArchPackage(name='mangohud', repository='extra', description='Overlay',
                               i18n=self.manager.i18n)
        variant = ArchPackage(name='mangohud-git', repository='aur', description='Overlay',
                              i18n=self.manager.i18n)
        result = SearchResult(installed=[], new=[repo_pkg, variant], total=2)

        self.manager._annotate_search_variants(result)

        expected = self.manager.i18n['arch.variant.development'].format('mangohud')
        self.assertEqual(f'Overlay [{expected}]', variant.description)

    def test_annotate__no_annotation_when_the_base_is_absent(self):
        variant = ArchPackage(name='brave-bin', repository='aur', description='Web browser',
                              i18n=self.manager.i18n)
        result = SearchResult(installed=[], new=[variant], total=1)

        self.manager._annotate_search_variants(result)

        self.assertEqual('Web browser', variant.description)

    def test_annotate__repository_packages_are_never_annotated(self):
        base = ArchPackage(name='brave', repository='extra', description='Web browser', i18n=self.manager.i18n)
        repo_variant = ArchPackage(name='brave-bin', repository='chaotic-aur', description='Web browser',
                                   i18n=self.manager.i18n)
        result = SearchResult(installed=[], new=[base, repo_variant], total=2)

        self.manager._annotate_search_variants(result)

        self.assertEqual('Web browser', repo_variant.description)

    def test_annotate__is_idempotent(self):
        base = ArchPackage(name='brave', repository='aur', description='Web browser', i18n=self.manager.i18n)
        variant = ArchPackage(name='brave-bin', repository='aur', description='Web browser',
                              i18n=self.manager.i18n)
        result = SearchResult(installed=[], new=[base, variant], total=2)

        self.manager._annotate_search_variants(result)
        first = variant.description
        self.manager._annotate_search_variants(result)

        self.assertEqual(first, variant.description)

    def test_annotate__variant_without_description(self):
        base = ArchPackage(name='brave', repository='aur', i18n=self.manager.i18n)
        variant = ArchPackage(name='brave-git', repository='aur', i18n=self.manager.i18n)
        result = SearchResult(installed=[], new=[base, variant], total=2)

        self.manager._annotate_search_variants(result)

        self.assertEqual(self.manager.i18n['arch.variant.development'].format('brave'), variant.description)


class GetInfoTest(TestCase):

    def setUp(self):
        self.manager = new_manager(base_config())

    def test_get_info__repository_package_exposes_its_origin(self):
        pkg = ArchPackage(name='yay', repository='chaotic-aur', i18n=self.manager.i18n)

        with patch(f'{CONTROLLER}.pacman.get_info_dict',
                   return_value={'repository': 'chaotic-aur', 'version': '12.0-1', 'description': 'AUR helper'}):
            info = self.manager.get_info(pkg)

        self.assertEqual('chaotic-aur', info['02_repository'])
        self.assertNotIn('repository', info)
        self.assertNotIn('02_variant', info)

    def test_get_info__aur_package_exposes_aur_as_its_origin(self):
        pkg = ArchPackage(name='yay', repository='aur', i18n=self.manager.i18n)

        with patch.object(ArchManager, '_get_info_aur_pkg', autospec=True, return_value={'02_name': 'yay'}):
            info = self.manager.get_info(pkg)

        self.assertEqual('AUR', info['02_repository'])

    def test_get_info__aur_variant_exposes_the_variant_label(self):
        pkg = ArchPackage(name='yay-git', repository='aur', i18n=self.manager.i18n)

        with patch.object(ArchManager, '_get_info_aur_pkg', autospec=True, return_value={'02_name': 'yay-git'}):
            info = self.manager.get_info(pkg)

        self.assertEqual(self.manager.i18n['arch.variant.development'].format('yay'), info['02_variant'])


class SwitchToRepositoryBinaryTest(TestCase):

    def _context(self, config: dict) -> TransactionContext:
        return TransactionContext(aur_supported=True, arch_config=config, name='yay', repository='aur')

    def test_switch__disabled_by_default(self):
        manager = new_manager(base_config())
        pkg = ArchPackage(name='yay', repository='aur', i18n=manager.i18n)
        watcher = Mock()

        with patch(f'{CONTROLLER}.pacman.map_repositories', return_value={'yay': 'chaotic-aur'}) as map_repos:
            switched = manager.switch_to_repository_binary(pkg=pkg, context=self._context(base_config()),
                                                           watcher=watcher)

        self.assertFalse(switched)
        self.assertEqual('aur', pkg.repository)
        map_repos.assert_not_called()
        watcher.request_confirmation.assert_not_called()

    def test_switch__enabled_and_confirmed_switches_the_origin(self):
        config = base_config(prefer_repository_binary=True)
        manager = new_manager(config)
        pkg = ArchPackage(name='yay', repository='aur', i18n=manager.i18n)
        context = self._context(config)
        watcher = Mock()
        watcher.request_confirmation.return_value = True

        with patch(f'{CONTROLLER}.pacman.map_repositories', return_value={'yay': 'chaotic-aur'}):
            switched = manager.switch_to_repository_binary(pkg=pkg, context=context, watcher=watcher)

        self.assertTrue(switched)
        self.assertEqual('chaotic-aur', pkg.repository)
        self.assertEqual('chaotic-aur', context.repository)
        self.assertFalse(context.update_aur_index)
        watcher.request_confirmation.assert_called_once()

    def test_switch__enabled_but_denied_keeps_the_aur_origin(self):
        config = base_config(prefer_repository_binary=True)
        manager = new_manager(config)
        pkg = ArchPackage(name='yay', repository='aur', i18n=manager.i18n)
        watcher = Mock()
        watcher.request_confirmation.return_value = False

        with patch(f'{CONTROLLER}.pacman.map_repositories', return_value={'yay': 'chaotic-aur'}):
            switched = manager.switch_to_repository_binary(pkg=pkg, context=self._context(config), watcher=watcher)

        self.assertFalse(switched)
        self.assertEqual('aur', pkg.repository)

    def test_switch__no_repository_binary_available(self):
        config = base_config(prefer_repository_binary=True)
        manager = new_manager(config)
        pkg = ArchPackage(name='paru', repository='aur', i18n=manager.i18n)
        watcher = Mock()

        with patch(f'{CONTROLLER}.pacman.map_repositories', return_value={}):
            switched = manager.switch_to_repository_binary(pkg=pkg, context=self._context(config), watcher=watcher)

        self.assertFalse(switched)
        self.assertEqual('aur', pkg.repository)
        watcher.request_confirmation.assert_not_called()

    def test_switch__installed_packages_are_never_switched(self):
        config = base_config(prefer_repository_binary=True)
        manager = new_manager(config)
        pkg = ArchPackage(name='yay', repository='aur', installed=True, i18n=manager.i18n)

        with patch(f'{CONTROLLER}.pacman.map_repositories', return_value={'yay': 'chaotic-aur'}) as map_repos:
            switched = manager.switch_to_repository_binary(pkg=pkg, context=self._context(config), watcher=Mock())

        self.assertFalse(switched)
        map_repos.assert_not_called()

    def test_switch__repositories_disabled_does_nothing(self):
        config = base_config(prefer_repository_binary=True, repositories=False)
        manager = new_manager(config)
        pkg = ArchPackage(name='yay', repository='aur', i18n=manager.i18n)

        with patch(f'{CONTROLLER}.pacman.map_repositories', return_value={'yay': 'chaotic-aur'}) as map_repos:
            switched = manager.switch_to_repository_binary(pkg=pkg, context=self._context(config), watcher=Mock())

        self.assertFalse(switched)
        map_repos.assert_not_called()

    def test_find_repository_binary__ignores_the_aur_repository(self):
        manager = new_manager(base_config())

        with patch(f'{CONTROLLER}.pacman.map_repositories', return_value={'yay': 'aur'}):
            self.assertIsNone(manager.find_repository_binary('yay'))

    def test_find_repository_binary__errors_are_swallowed(self):
        manager = new_manager(base_config())

        with patch(f'{CONTROLLER}.pacman.map_repositories', side_effect=OSError('boom')):
            self.assertIsNone(manager.find_repository_binary('yay'))


class EnsureCategoriesTest(TestCase):

    def test_ensure_categories__falls_back_to_the_vendored_copy(self):
        manager = new_manager(base_config())

        real_read_categories = arch_data.read_categories

        with tempfile.TemporaryDirectory() as tmp:
            def read_without_cache(logger=None):
                return real_read_categories(cache_file_path=f'{tmp}/missing.txt', logger=logger)

            with patch(f'{CONTROLLER}.arch_data.read_categories', side_effect=read_without_cache):
                manager._ensure_categories()

        self.assertTrue(manager.categories)
        self.assertEqual(['Game'], manager.categories['0ad'])

    def test_ensure_categories__does_not_override_the_downloaded_ones(self):
        manager = new_manager(base_config())
        manager.categories = {'vlc': ['AudioVideo']}

        manager._ensure_categories()

        self.assertEqual({'vlc': ['AudioVideo']}, manager.categories)


class ArchConfigTest(TestCase):

    def test_prefer_repository_binary_defaults_to_false(self):
        self.assertIs(False, ArchConfigManager().get_default_config()['prefer_repository_binary'])

class PreferRepositoryResultsTest(TestCase):
    """Deduplicacion de resultados de busqueda repositorio/AUR (F16)."""

    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings('ignore', category=DeprecationWarning)

    def test_prefer_repository_results__discards_the_aur_duplicate(self):
        search_output = {'repositories': {'brave-bin': {'repository': 'chaotic-aur', 'version': '1.60-1'}},
                         'aur': {'brave-bin': {'Name': 'brave-bin'}, 'solo-aur': {'Name': 'solo-aur'}}}

        discarded = ArchManager.prefer_repository_results(search_output)

        self.assertEqual({'brave-bin'}, discarded)
        self.assertEqual({'solo-aur'}, set(search_output['aur'].keys()))
        self.assertEqual({'brave-bin'}, set(search_output['repositories'].keys()))

    def test_prefer_repository_results__nothing_to_discard(self):
        search_output = {'repositories': {'firefox': {}}, 'aur': {'solo-aur': {}}}

        self.assertEqual(set(), ArchManager.prefer_repository_results(search_output))
        self.assertEqual({'solo-aur'}, set(search_output['aur'].keys()))

    def test_prefer_repository_results__no_repository_results(self):
        search_output = {'repositories': {}, 'aur': {'solo-aur': {}}}

        self.assertEqual(set(), ArchManager.prefer_repository_results(search_output))
        self.assertEqual({'solo-aur'}, set(search_output['aur'].keys()))

    def test_prefer_repository_results__no_aur_results(self):
        search_output = {'repositories': {'firefox': {}}, 'aur': {}}

        self.assertEqual(set(), ArchManager.prefer_repository_results(search_output))


class FillRepositoryAvailabilityTest(TestCase):
    """Anotacion del repositorio binario disponible para paquetes del AUR (F16)."""

    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings('ignore', category=DeprecationWarning)

    @staticmethod
    def _pkg(name: str, repository: str, installed: bool = True) -> ArchPackage:
        return ArchPackage(name=name, repository=repository, installed=installed)

    def test_fill_repository_availability__marks_the_aur_package(self):
        aur_pkg = self._pkg('brave-bin', 'aur')
        repo_pkg = self._pkg('firefox', 'extra')

        ArchManager.fill_repository_availability([aur_pkg, repo_pkg],
                                                 {'brave-bin': 'chaotic-aur', 'firefox': 'extra'})

        self.assertEqual('chaotic-aur', aur_pkg.repo_available)
        self.assertIsNone(repo_pkg.repo_available)

    def test_fill_repository_availability__aur_package_not_available(self):
        aur_pkg = self._pkg('solo-aur', 'aur')

        ArchManager.fill_repository_availability([aur_pkg], {'brave-bin': 'chaotic-aur'})

        self.assertIsNone(aur_pkg.repo_available)

    def test_fill_repository_availability__not_installed_packages_are_ignored(self):
        aur_pkg = self._pkg('brave-bin', 'aur', installed=False)

        ArchManager.fill_repository_availability([aur_pkg], {'brave-bin': 'chaotic-aur'})

        self.assertIsNone(aur_pkg.repo_available)

    def test_fill_repository_availability__empty_map(self):
        aur_pkg = self._pkg('brave-bin', 'aur')

        ArchManager.fill_repository_availability([aur_pkg], {})

        self.assertIsNone(aur_pkg.repo_available)


class SwitchToRepositoryActionTest(TestCase):
    """Accion personalizada de cambio al binario del repositorio (F16)."""

    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings('ignore', category=DeprecationWarning)

    def test_get_custom_actions__offered_when_a_repository_binary_exists(self):
        pkg = ArchPackage(name='brave-bin', repository='aur', installed=True)
        pkg.repo_available = 'chaotic-aur'

        methods = {a.manager_method for a in pkg.get_custom_actions()}

        self.assertIn('switch_to_repository', methods)

    def test_get_custom_actions__not_offered_without_a_repository_binary(self):
        pkg = ArchPackage(name='solo-aur', repository='aur', installed=True)

        methods = {a.manager_method for a in pkg.get_custom_actions()}

        self.assertNotIn('switch_to_repository', methods)

    def test_get_custom_actions__not_offered_for_repository_packages(self):
        pkg = ArchPackage(name='firefox', repository='extra', installed=True)

        self.assertIsNone(pkg.get_custom_actions())

    def test_action_requires_root_and_has_i18n_keys(self):
        action = ArchPackage.action_switch_to_repository()

        self.assertTrue(action.requires_root)
        self.assertEqual('switch_to_repository', action.manager_method)
        self.assertEqual('arch.action.switch_to_repo', action.i18n_label_key)
        self.assertEqual('arch.action.switch_to_repo.status', action.i18n_status_key)
        self.assertEqual('arch.action.switch_to_repo.confirm', action.i18n_confirm_key)
        self.assertEqual('arch.action.switch_to_repo.desc', action.i18n_description_key)

    def test_the_manager_exposes_the_action_method(self):
        self.assertTrue(callable(getattr(ArchManager, 'switch_to_repository', None)))
