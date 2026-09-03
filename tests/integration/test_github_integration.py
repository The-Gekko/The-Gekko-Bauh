"""La gem GitHub contra un binario `git` simulado en el PATH.

Es la única gem que ejecuta órdenes con datos que vienen de una API externa (el propietario y
el nombre del repositorio) y que además compila código de terceros. Estas pruebas comprueban
que lo que llega a `git` es exactamente lo que se espera, sin pasar por un shell.
"""

import logging
import unittest
from unittest.mock import Mock

from bauh.gems.github import paths
from bauh.gems.github.controller import GitHubManager
from bauh.gems.github.model import GitHubPackage
from tests.integration.harness import FakeBinaries



def new_manager(repos_dir: str) -> GitHubManager:
    manager = GitHubManager.__new__(GitHubManager)
    logger = logging.getLogger('github-integration')
    logger.addHandler(logging.NullHandler())

    manager.i18n = {}
    manager.logger = logger
    manager.configman = Mock()
    manager.configman.get_config.return_value = {'repos_dir': repos_dir, 'clone_only': True}
    return manager


class GitCommandIntegrationTest(unittest.TestCase):
    """Los argumentos que recibe git."""

    def test_clone_uses_a_double_dash_and_a_url_built_from_validated_parts(self):
        pkg = GitHubPackage(name='proyecto', owner='usuario', repo_name='proyecto')

        url = GitHubManager._clone_url(pkg)

        # la URL se compone aquí, no se toma de la API: así git nunca recibe una cadena
        # arbitraria que pudiera empezar por '-' y ser leída como una opción
        self.assertEqual('https://github.com/usuario/proyecto.git', url)

    def test_a_repository_name_that_looks_like_an_option_is_refused(self):
        for owner, repo in (('--upload-pack=touch /tmp/x', 'proyecto'),
                            ('usuario', '--upload-pack=id'),
                            ('..', 'proyecto'),
                            ('usuario', '.git'),
                            ('usu/ario', 'proyecto')):
            with self.subTest(owner=owner, repo=repo):
                pkg = GitHubPackage(name=repo, owner=owner, repo_name=repo)
                self.assertIsNone(GitHubManager._clone_url(pkg))

    def test_a_clone_path_never_escapes_the_repos_dir(self):
        for owner, repo in (('..', 'x'), ('usuario', '..'), ('../../etc', 'passwd')):
            with self.subTest(owner=owner, repo=repo):
                self.assertIsNone(paths.build_clone_path('/repos', owner, repo))

    def test_the_git_binary_receives_the_arguments_as_a_list(self):
        responses = {'git': {'*': {'stdout': 'abc123\n'}}}
        manager = new_manager('/repos')

        with FakeBinaries(responses) as fakes:
            ok, output = manager._run_git(['log', '-1', '--format=%H'], cwd='.')
            calls = fakes.calls('git')

        self.assertTrue(ok)
        self.assertEqual('abc123', output)
        self.assertEqual([['log', '-1', '--format=%H']], calls)

    def test_an_argument_with_metacharacters_arrives_literal(self):
        responses = {'git': {'*': {'stdout': ''}}}
        manager = new_manager('/repos')
        argumento = 'rama; touch /tmp/x'

        with FakeBinaries(responses) as fakes:
            manager._run_git(['checkout', argumento], cwd='.')
            calls = fakes.calls('git')

        self.assertEqual([['checkout', argumento]], calls)

    def test_a_failing_git_reports_the_failure_without_raising(self):
        responses = {'git': {'*': {'stdout': '', 'stderr': 'fatal: not a git repository', 'code': 128}}}
        manager = new_manager('/repos')

        with FakeBinaries(responses):
            ok, output = manager._run_git(['status'], cwd='.')

        self.assertFalse(ok)
        self.assertEqual('', output)


if __name__ == '__main__':
    unittest.main()
