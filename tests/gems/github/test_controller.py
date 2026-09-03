import os
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

from bauh.api.abstract.controller import SoftwareAction
from bauh.api.abstract.view import FormComponent
from bauh.gems.github import gitrepo
from bauh.gems.github.build_detector import BuildMethod
from bauh.gems.github.controller import GitHubManager
from bauh.gems.github.model import GitHubPackage


class _SafeText(str):
    """Texto de prueba que acepta cualquier número de argumentos en format()."""

    def format(self, *args, **kwargs):
        extra = ' '.join(str(arg) for arg in args)
        return f'{str(self)} {extra}'.strip()


class _DummyI18n(dict):
    """i18n mínimo: devuelve la propia clave, tolerante a cualquier formateo."""

    def __getitem__(self, item):
        return _SafeText(item)

    def get(self, key, default=None):
        return self[key]


def _new_manager(repos_dir: str, **config) -> GitHubManager:
    context = Mock()
    manager = GitHubManager(context)
    manager.i18n = _DummyI18n()
    manager.logger = Mock()
    manager.configman = Mock()
    defaults = {'repos_dir': repos_dir, 'clone_only': True, 'github_token': None,
                'search_enabled': False, 'search_limit': 10, 'check_updates': False}
    defaults.update(config)
    manager.configman.get_config.return_value = defaults
    return manager


class GitRepoParsingTest(unittest.TestCase):

    def test_normalize_remote_url__https(self):
        self.assertEqual('https://github.com/owner/repo',
                         gitrepo.normalize_remote_url('https://github.com/owner/repo.git'))

    def test_normalize_remote_url__ssh(self):
        self.assertEqual('https://github.com/owner/repo',
                         gitrepo.normalize_remote_url('git@github.com:owner/repo.git'))

    def test_parse_github_url(self):
        self.assertEqual(('owner', 'repo'),
                         gitrepo.parse_github_url('https://github.com/owner/repo'))
        self.assertEqual(('owner', 'repo'),
                         gitrepo.parse_github_url('https://github.com/owner/repo/tree/main'))
        self.assertIsNone(gitrepo.parse_github_url('https://gitlab.com/owner/repo'))
        self.assertIsNone(gitrepo.parse_github_url('firefox'))

    def test_same_repository(self):
        self.assertTrue(gitrepo.same_repository('git@github.com:owner/repo.git',
                                                'https://github.com/owner/repo'))
        self.assertFalse(gitrepo.same_repository('https://github.com/owner1/repo',
                                                 'https://github.com/owner2/repo'))
        self.assertFalse(gitrepo.same_repository(None, 'https://github.com/owner/repo'))

    def test_parse_remote_url(self):
        config = ('[core]\n\trepositoryformatversion = 0\n'
                  '[remote "origin"]\n'
                  '\turl = https://github.com/owner/repo.git\n'
                  '\tfetch = +refs/heads/*:refs/remotes/origin/*\n')

        self.assertEqual('https://github.com/owner/repo',
                         gitrepo.parse_remote_url(config))

    def test_parse_remote_url__missing_remote(self):
        self.assertIsNone(gitrepo.parse_remote_url('[core]\n\tbare = false\n'))

    def test_parse_head_branch(self):
        self.assertEqual('main', gitrepo.parse_head_branch('ref: refs/heads/main\n'))
        self.assertEqual('feature/x',
                         gitrepo.parse_head_branch('ref: refs/heads/feature/x\n'))
        self.assertIsNone(gitrepo.parse_head_branch('a1b2c3d4\n'))


class GitHubManagerDefaultsTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='bauh-github-ctrl-')
        self.manager = _new_manager(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_is_default_enabled__must_be_opt_in(self):
        self.assertFalse(self.manager.is_default_enabled())

    def test_prepare__must_not_create_the_repositories_directory(self):
        repos_dir = os.path.join(self.dir, 'never-created')
        manager = _new_manager(repos_dir)

        manager.prepare(None, None, True)

        self.assertFalse(os.path.exists(repos_dir))

    def test_requires_root__install_of_an_unclonned_repo_when_building(self):
        manager = _new_manager(self.dir, clone_only=False)
        pkg = GitHubPackage(name='repo', owner='owner', repo_name='repo')

        self.assertTrue(manager.requires_root(SoftwareAction.INSTALL, pkg))

    def test_requires_root__must_be_false_in_clone_only_mode(self):
        pkg = GitHubPackage(name='repo', owner='owner', repo_name='repo')

        self.assertFalse(self.manager.requires_root(SoftwareAction.INSTALL, pkg))

    def test_requires_root__uninstall_only_for_pacman_artifacts(self):
        pkg = GitHubPackage(name='repo', owner='owner', repo_name='repo',
                            build_method=BuildMethod.PKGBUILD.value,
                            installed_artifacts=['ripgrep'])
        self.manager.registry = Mock()
        self.manager.registry.get.return_value = None

        self.assertTrue(self.manager.requires_root(SoftwareAction.UNINSTALL, pkg))

        pkg.build_method = BuildMethod.CARGO.value
        self.assertFalse(self.manager.requires_root(SoftwareAction.UNINSTALL, pkg))

    def test_requires_root__must_be_false_for_other_packages(self):
        self.assertFalse(self.manager.requires_root(SoftwareAction.INSTALL, None))


class GitHubManagerSearchTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='bauh-github-search-')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_search__plain_text_must_not_hit_the_api_while_disabled(self):
        manager = _new_manager(self.dir)
        manager._get_json = Mock()

        result = manager.search('firefox')

        self.assertEqual(0, result.total)
        manager._get_json.assert_not_called()

    def test_search__the_gh_prefix_forces_a_search(self):
        manager = _new_manager(self.dir)
        manager._search_github_api = Mock(return_value=[])

        manager.search('gh:firefox')

        manager._search_github_api.assert_called_once_with('firefox', 10)

    def test_search__a_url_always_works(self):
        manager = _new_manager(self.dir)
        manager._fetch_repo_info = Mock(return_value={
            'name': 'repo', 'owner': {'login': 'owner'},
            'html_url': 'https://github.com/owner/repo', 'default_branch': 'main'})

        result = manager.search('https://github.com/owner/repo')

        manager._fetch_repo_info.assert_called_once_with('owner', 'repo')
        self.assertEqual(1, result.total)
        self.assertEqual(os.path.join(self.dir, 'owner', 'repo'),
                         result.new[0].clone_path)

    def test_search__must_discard_a_repository_with_an_unusable_name(self):
        manager = _new_manager(self.dir, search_enabled=True)
        manager._search_github_api = Mock(return_value=[
            {'name': '..', 'owner': {'login': 'owner'}},
            {'name': 'good', 'owner': {'login': 'owner'}}])

        result = manager.search('anything')

        self.assertEqual(1, result.total)
        self.assertEqual('good', result.new[0].name)

    def test_search__empty_query(self):
        manager = _new_manager(self.dir)

        self.assertEqual(0, manager.search('   ').total)


class GitHubManagerApiTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='bauh-github-api-')
        self.manager = _new_manager(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_api_headers__without_token(self):
        headers = self.manager._api_headers()

        self.assertEqual('application/vnd.github+json', headers['Accept'])
        self.assertNotIn('Authorization', headers)

    def test_api_headers__with_token(self):
        manager = _new_manager(self.dir, github_token='  abc123 ')

        self.assertEqual('Bearer abc123', manager._api_headers()['Authorization'])

    def test_get_json__must_use_params_instead_of_string_interpolation(self):
        response = Mock(status_code=200)
        response.json.return_value = {'items': []}
        self.manager.http_client.get.return_value = response

        self.manager._search_github_api('a b', 5)

        kwargs = self.manager.http_client.get.call_args[1]
        self.assertEqual({'q': 'a b', 'sort': 'stars', 'order': 'desc', 'per_page': 5},
                         kwargs['params'])

    def test_get_json__rate_limit_must_produce_a_warning(self):
        self.manager.http_client.get.return_value = Mock(status_code=403)

        self.assertEqual([], self.manager._search_github_api('x', 5))

        warnings = self.manager.list_warnings(internet_available=True)
        self.assertEqual(1, len(warnings))
        self.assertIn('github.warning.rate_limited', warnings[0])

    def test_get_json__unauthorized_must_report_a_bad_token(self):
        self.manager.http_client.get.return_value = Mock(status_code=401)
        self.manager._search_github_api('x', 5)

        self.assertIn('github.warning.bad_token',
                      self.manager.list_warnings(internet_available=True)[0])

    def test_get_json__404_is_not_a_warning(self):
        self.manager.http_client.get.return_value = Mock(status_code=404)
        self.manager._search_github_api('x', 5)

        self.assertIsNone(self.manager.list_warnings(internet_available=True))

    def test_get_json__must_cache_the_response(self):
        response = Mock(status_code=200)
        response.json.return_value = {'items': []}
        self.manager.http_client.get.return_value = response

        self.manager._search_github_api('x', 5)
        self.manager._search_github_api('x', 5)

        self.assertEqual(1, self.manager.http_client.get.call_count)

    def test_list_warnings__no_internet(self):
        warnings = self.manager.list_warnings(internet_available=False)

        self.assertIn('github.no_internet', warnings[0])


class GitHubManagerUninstallTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='bauh-github-uninstall-')
        self.clone = os.path.join(self.dir, 'owner', 'repo')
        os.makedirs(os.path.join(self.clone, '.git'))
        self.manager = _new_manager(self.dir)
        self.manager.registry = Mock()
        self.manager.registry.get.return_value = None

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _pkg(self, **kwargs):
        return GitHubPackage(name='repo', owner='owner', repo_name='repo',
                             clone_path=self.clone, cloned=True, installed=True, **kwargs)

    def test_uninstall__must_remove_the_clone(self):
        result = self.manager.uninstall(self._pkg(), None, Mock())

        self.assertTrue(result.success)
        self.assertFalse(os.path.exists(self.clone))

    def test_uninstall__must_refuse_a_path_outside_the_repositories_directory(self):
        outside = tempfile.mkdtemp(prefix='bauh-github-outside-')

        try:
            pkg = self._pkg()
            pkg.clone_path = outside

            result = self.manager.uninstall(pkg, None, Mock())

            self.assertFalse(result.success)
            self.assertTrue(os.path.isdir(outside))
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_uninstall__must_refuse_the_home_directory(self):
        pkg = self._pkg()
        pkg.clone_path = os.path.expanduser('~')

        result = self.manager.uninstall(pkg, None, Mock())

        self.assertFalse(result.success)

    @patch('bauh.gems.github.controller.ProcessHandler')
    @patch('bauh.gems.github.controller.SimpleProcess')
    def test_uninstall__must_undo_a_pacman_installation(self, simple_process: Mock,
                                                        process_handler: Mock):
        process_handler.return_value.handle_simple.return_value = (True, '')
        self.manager.registry.get.return_value = {'build_method': BuildMethod.PKGBUILD.value,
                                                  'artifacts': ['ripgrep']}

        result = self.manager.uninstall(self._pkg(), 'secret', Mock())

        self.assertTrue(result.success)
        self.assertEqual(['pacman', '-R', '--noconfirm', 'ripgrep'],
                         simple_process.call_args[0][0])
        self.assertEqual('secret', simple_process.call_args[1]['root_password'])

    @patch('bauh.gems.github.controller.ProcessHandler')
    @patch('bauh.gems.github.controller.SimpleProcess')
    def test_uninstall__must_undo_a_cargo_installation_without_root(self, simple_process: Mock,
                                                                    process_handler: Mock):
        process_handler.return_value.handle_simple.return_value = (True, '')
        self.manager.registry.get.return_value = {'build_method': BuildMethod.CARGO.value,
                                                  'artifacts': ['ripgrep']}

        self.manager.uninstall(self._pkg(), 'secret', Mock())

        self.assertEqual(['cargo', 'uninstall', 'ripgrep'], simple_process.call_args[0][0])
        self.assertIsNone(simple_process.call_args[1]['root_password'])

    @patch('bauh.gems.github.controller.ProcessHandler')
    @patch('bauh.gems.github.controller.SimpleProcess')
    def test_uninstall__a_failed_removal_must_keep_the_clone(self, simple_process: Mock,
                                                             process_handler: Mock):
        process_handler.return_value.handle_simple.return_value = (False, '')
        self.manager.registry.get.return_value = {'build_method': BuildMethod.PKGBUILD.value,
                                                  'artifacts': ['ripgrep']}

        result = self.manager.uninstall(self._pkg(), 'secret', Mock())

        self.assertFalse(result.success)
        self.assertTrue(os.path.isdir(self.clone))


class GitHubManagerInstallTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='bauh-github-install-')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _prepare_clone(self, manager, *files):
        clone = os.path.join(self.dir, 'owner', 'repo')
        os.makedirs(os.path.join(clone, '.git'), exist_ok=True)

        for name in files:
            with open(os.path.join(clone, name), 'w') as handle:
                handle.write('')

        with open(os.path.join(clone, '.git', 'config'), 'w') as handle:
            handle.write('[remote "origin"]\n\turl = https://github.com/owner/repo\n')

        with open(os.path.join(clone, '.git', 'HEAD'), 'w') as handle:
            handle.write('ref: refs/heads/main\n')

        manager._clone_or_update = Mock(return_value=True)
        return clone

    def _pkg(self):
        return GitHubPackage(name='repo', owner='owner', repo_name='repo',
                             repo_url='https://github.com/owner/repo')

    def test_install__must_reject_a_malicious_repository_name(self):
        manager = _new_manager(self.dir)
        pkg = GitHubPackage(name='..', owner='owner', repo_name='..')

        result = manager.install(pkg, None, None, Mock())

        self.assertFalse(result.success)

    @patch('bauh.gems.github.controller.ProcessHandler')
    @patch('bauh.gems.github.controller.SimpleProcess')
    def test_install__the_clone_url_must_be_derived_from_validated_components(
            self, simple_process: Mock, process_handler: Mock):
        manager = _new_manager(self.dir)
        process_handler.return_value.handle_simple.return_value = (True, '')
        pkg = self._pkg()
        pkg.repo_url = '--upload-pack=touch /tmp/pwned'

        manager.install(pkg, None, None, Mock())

        command = simple_process.call_args[0][0]
        self.assertEqual(['git', 'clone', '--', 'https://github.com/owner/repo.git'],
                         command[:4])

    def test_install__clone_only_must_not_build(self):
        manager = _new_manager(self.dir)
        self._prepare_clone(manager, 'PKGBUILD')
        manager._build_and_install = Mock()

        result = manager.install(self._pkg(), None, None, Mock())

        self.assertTrue(result.success)
        manager._build_and_install.assert_not_called()

    @patch('bauh.gems.github.controller.ProcessHandler')
    @patch('bauh.gems.github.controller.SimpleProcess')
    def test_install__must_ask_for_confirmation_before_building(self, simple_process: Mock,
                                                                process_handler: Mock):
        manager = _new_manager(self.dir, clone_only=False)
        clone = self._prepare_clone(manager, 'Cargo.toml')
        watcher = Mock()
        watcher.request_confirmation.return_value = False

        with patch('bauh.gems.github.controller.shutil.which', return_value='/usr/bin/cargo'):
            result = manager.install(self._pkg(), None, None, watcher)

        watcher.request_confirmation.assert_called_once()
        simple_process.assert_not_called()
        self.assertTrue(result.success)
        self.assertTrue(os.path.isdir(clone))

    @patch('bauh.gems.github.controller.ProcessHandler')
    @patch('bauh.gems.github.controller.SimpleProcess')
    def test_install__the_build_must_never_receive_the_root_password(self,
                                                                     simple_process: Mock,
                                                                     process_handler: Mock):
        manager = _new_manager(self.dir, clone_only=False)
        self._prepare_clone(manager, 'Cargo.toml')
        process_handler.return_value.handle_simple.return_value = (True, '')
        watcher = Mock()
        watcher.request_confirmation.return_value = True

        with patch('bauh.gems.github.controller.shutil.which', return_value='/usr/bin/cargo'):
            manager.install(self._pkg(), 'secret', None, watcher)

        self.assertEqual(['cargo', 'install', '--path', '.', '--locked'],
                         simple_process.call_args[0][0])
        self.assertNotIn('root_password', simple_process.call_args[1])

    @patch('bauh.gems.github.controller.ProcessHandler')
    @patch('bauh.gems.github.controller.SimpleProcess')
    def test_install__the_build_must_not_go_through_a_shell(self, simple_process: Mock,
                                                            process_handler: Mock):
        manager = _new_manager(self.dir, clone_only=False)
        self._prepare_clone(manager, 'Cargo.toml')
        process_handler.return_value.handle_simple.return_value = (True, '')
        watcher = Mock()
        watcher.request_confirmation.return_value = True

        with patch('bauh.gems.github.controller.shutil.which', return_value='/usr/bin/cargo'):
            manager.install(self._pkg(), None, None, watcher)

        command = simple_process.call_args[0][0]
        self.assertNotIn('bash', command)
        self.assertNotIn('-c', command)

    @patch('bauh.gems.github.controller.ProcessHandler')
    @patch('bauh.gems.github.controller.SimpleProcess')
    def test_install__a_failed_build_must_not_be_reported_as_installed(self,
                                                                       simple_process: Mock,
                                                                       process_handler: Mock):
        manager = _new_manager(self.dir, clone_only=False)
        self._prepare_clone(manager, 'Cargo.toml')
        process_handler.return_value.handle_simple.return_value = (False, 'boom')
        watcher = Mock()
        watcher.request_confirmation.return_value = True

        with patch('bauh.gems.github.controller.shutil.which', return_value='/usr/bin/cargo'):
            result = manager.install(self._pkg(), None, None, watcher)

        self.assertFalse(result.success)

    @patch('bauh.gems.github.controller.ProcessHandler')
    @patch('bauh.gems.github.controller.SimpleProcess')
    def test_install__pkgbuild_must_build_as_user_and_install_with_pacman(self,
                                                                          simple_process: Mock,
                                                                          process_handler: Mock):
        manager = _new_manager(self.dir, clone_only=False)
        clone = self._prepare_clone(manager, 'PKGBUILD')

        with open(os.path.join(clone, 'ripgrep-13.0.0-1-x86_64.pkg.tar.zst'), 'w') as handle:
            handle.write('')

        process_handler.return_value.handle_simple.return_value = (True, '')
        manager.registry = Mock()
        watcher = Mock()
        watcher.request_confirmation.return_value = True

        with patch('bauh.gems.github.controller.shutil.which', return_value='/usr/bin/makepkg'):
            result = manager.install(self._pkg(), 'secret', None, watcher)

        self.assertTrue(result.success)
        calls = simple_process.call_args_list

        build_cmd = calls[0][0][0]
        self.assertEqual(['makepkg', '-s', '--noconfirm'], build_cmd)
        self.assertNotIn('root_password', calls[0][1])

        install_cmd = calls[1][0][0]
        self.assertEqual(['pacman', '-U', '--noconfirm'], install_cmd[:3])
        self.assertEqual('secret', calls[1][1]['root_password'])

        manager.registry.record.assert_called_once()
        self.assertEqual(['ripgrep'], manager.registry.record.call_args[0][2])

    def test_install__python_without_pipx_must_explain_and_not_build(self):
        manager = _new_manager(self.dir, clone_only=False)
        self._prepare_clone(manager, 'pyproject.toml')
        watcher = Mock()

        with patch('bauh.gems.github.controller.shutil.which', return_value=None):
            result = manager.install(self._pkg(), None, None, watcher)

        self.assertTrue(result.success)
        watcher.request_confirmation.assert_not_called()
        body = watcher.show_message.call_args[1]['body']
        self.assertIn('github.missing_pipx.body', body)

    def test_install__an_unsupported_method_must_only_clone(self):
        manager = _new_manager(self.dir, clone_only=False)
        self._prepare_clone(manager, 'Makefile')
        watcher = Mock()

        result = manager.install(self._pkg(), None, None, watcher)

        self.assertTrue(result.success)
        watcher.request_confirmation.assert_not_called()


class GitHubManagerSettingsTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='bauh-github-settings-')
        self.manager = _new_manager(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _form(self):
        views = list(self.manager.get_settings())
        self.assertEqual(1, len(views))
        return views[0], views[0].component.get_component_by_idx(0, FormComponent)

    def test_get_settings__must_expose_every_option(self):
        _, form = self._form()

        for id_ in ('repos_dir', 'clone_only', 'search_enabled', 'search_limit',
                    'check_updates', 'github_token'):
            self.assertIsNotNone(form.get_component(id_), id_)

    def test_save_settings__must_persist_the_values(self):
        view, form = self._form()
        form.get_component('search_limit').set_value('25')
        form.get_component('github_token').set_value('  tok  ')

        saved, errors = self.manager.save_settings(view.component)

        self.assertTrue(saved)
        self.assertIsNone(errors)
        config = self.manager.configman.save_config.call_args[0][0]
        self.assertEqual(25, config['search_limit'])
        self.assertEqual('tok', config['github_token'])
        self.assertTrue(config['clone_only'])

    def test_save_settings__an_empty_token_becomes_none(self):
        view, form = self._form()
        form.get_component('github_token').set_value('   ')

        self.manager.save_settings(view.component)

        self.assertIsNone(self.manager.configman.save_config.call_args[0][0]['github_token'])

    def test_clear_data__must_keep_the_clones(self):
        clone = os.path.join(self.dir, 'owner', 'repo')
        os.makedirs(clone)

        self.manager.clear_data()

        self.assertTrue(os.path.isdir(clone))


class GitHubManagerReadInstalledTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='bauh-github-read-')
        self.manager = _new_manager(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _make_clone(self, *parts):
        clone = os.path.join(self.dir, *parts)
        os.makedirs(os.path.join(clone, '.git'))

        with open(os.path.join(clone, '.git', 'config'), 'w') as handle:
            handle.write(f'[remote "origin"]\n\turl = https://github.com/'
                         f'{parts[0]}/{parts[-1]}\n')

        with open(os.path.join(clone, '.git', 'HEAD'), 'w') as handle:
            handle.write('ref: refs/heads/main\n')

        return clone

    def test_read_installed__owner_layout(self):
        self._make_clone('owner', 'repo')

        result = self.manager.read_installed()

        self.assertEqual(1, result.total)
        pkg = result.installed[0]
        self.assertEqual('owner', pkg.owner)
        self.assertEqual('repo', pkg.repo_name)
        self.assertEqual('main', pkg.version)

    def test_read_installed__two_owners_with_the_same_repo_name(self):
        self._make_clone('owner1', 'dotfiles')
        self._make_clone('owner2', 'dotfiles')

        result = self.manager.read_installed()

        self.assertEqual(2, result.total)
        self.assertEqual({'owner1', 'owner2'}, {p.owner for p in result.installed})

    def test_read_installed__legacy_flat_layout_is_still_recognised(self):
        clone = os.path.join(self.dir, 'dotfiles')
        os.makedirs(os.path.join(clone, '.git'))

        with open(os.path.join(clone, '.git', 'config'), 'w') as handle:
            handle.write('[remote "origin"]\n\turl = https://github.com/owner/dotfiles\n')

        result = self.manager.read_installed()

        self.assertEqual(1, result.total)
        self.assertEqual('owner', result.installed[0].owner)

    def test_read_installed__must_ignore_directories_without_git(self):
        os.makedirs(os.path.join(self.dir, 'owner', 'not-a-repo'))

        self.assertEqual(0, self.manager.read_installed().total)

    def test_read_installed__empty_directory(self):
        self.assertEqual(0, self.manager.read_installed().total)


if __name__ == '__main__':
    unittest.main()
