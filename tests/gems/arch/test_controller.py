import warnings
from unittest import TestCase

from bauh.gems.arch.controller import ArchManager
from bauh.gems.arch.model import ArchPackage


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
