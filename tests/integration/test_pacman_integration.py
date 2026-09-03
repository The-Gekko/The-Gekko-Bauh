"""El módulo `pacman` contra un binario `pacman` simulado en el PATH.

El cambio de `shell=True` a listas de argumentos es invisible para los tests que parchean
`_run`: comprueban lo que se le pasa, no lo que llega al proceso. Aquí se ejecuta de verdad,
así que un nombre de paquete con metacaracteres tiene que llegar literal al binario.
"""

import os
import unittest

from bauh.gems.arch import pacman
from tests.integration.harness import FakeBinaries

SEARCH_OUTPUT = """chaotic-aur/yay 12.4.2-1
    Yet another yogurt. Pacman wrapper and AUR helper written in go.
extra/mangohud 0.7.2-1
    A Vulkan overlay layer for monitoring FPS and temperatures.
"""

INFO_OUTPUT = """Repository      : chaotic-aur
Name            : brave-bin
Version         : 1.60.114-1
Description     : Web browser

Repository      : extra
Name            : firefox
Version         : 121.0-1
Description     : Web browser
"""


class PacmanNoShellIntegrationTest(unittest.TestCase):
    """Los argumentos llegan literales al proceso: nada se interpreta como shell."""

    def test_a_search_term_with_shell_metacharacters_arrives_literal(self):
        responses = {'pacman': {'*': {'stdout': ''}}}
        malicious = 'firefox; touch /tmp/pwned'

        with FakeBinaries(responses) as fakes:
            pacman.search(malicious)
            calls = fakes.calls('pacman')

        # Con shell=True esto se habría partido en dos órdenes. Cada palabra llega como un
        # argumento independiente y ninguna se ejecuta.
        self.assertEqual([['-Ss', 'firefox;', 'touch', '/tmp/pwned']], calls)

    def test_a_package_name_with_backticks_arrives_literal(self):
        responses = {'pacman': {'*': {'stdout': ''}}}

        with FakeBinaries(responses) as fakes:
            pacman.get_info('firefox`id`', remote=True)
            calls = fakes.calls('pacman')

        self.assertEqual([['-Si', 'firefox`id`']], calls)

    def test_the_overwrite_wildcard_is_not_expanded_by_the_shell(self):
        # «--overwrite=*» debe llegar tal cual: si el shell lo expandiera contra el
        # directorio actual, pacman recibiría una lista de ficheros arbitraria
        responses = {'pacman': {'*': {'stdout': ''}}}

        with FakeBinaries(responses) as fakes:
            proc = pacman.upgrade_several(pkgnames=('brave-bin',), root_password=None,
                                          overwrite_conflicting_files=True)
            proc.instance.wait()

            for stream in (proc.instance.stdout, proc.instance.stderr):
                if stream is not None:
                    stream.close()

            calls = fakes.calls('pacman')

        self.assertEqual(1, len(calls))
        self.assertIn('--overwrite=*', calls[0])


class PacmanOutputIntegrationTest(unittest.TestCase):
    """Lo que la gem entiende de la salida real del binario."""

    def test_search_reads_the_repository_of_every_result(self):
        responses = {'pacman': {'*': {'stdout': SEARCH_OUTPUT}}}

        with FakeBinaries(responses):
            found = pacman.search('yay')

        self.assertEqual({'yay', 'mangohud'}, set(found))
        self.assertEqual('chaotic-aur', found['yay']['repository'])
        self.assertEqual('12.4.2-1', found['yay']['version'])

    def test_the_repository_map_keeps_chaotic_aur(self):
        responses = {'pacman': {'*': {'stdout': INFO_OUTPUT}}}

        with FakeBinaries(responses):
            res = pacman.map_available_repositories({'brave-bin', 'firefox'})

        self.assertEqual({'brave-bin': 'chaotic-aur', 'firefox': 'extra'}, res)

    def test_a_failing_binary_does_not_raise(self):
        responses = {'pacman': {'*': {'stdout': '', 'stderr': 'error: no results', 'code': 1}}}

        with FakeBinaries(responses):
            self.assertFalse(pacman.search('no-existe'))


if __name__ == '__main__':
    unittest.main()


class PacmanProcessReapingTest(unittest.TestCase):
    """Los procesos que se lanzan se recogen: ninguno queda como zombi."""

    @staticmethod
    def _own_zombies() -> int:
        count = 0

        for entry in os.listdir('/proc'):
            if not entry.isdigit():
                continue

            try:
                with open(f'/proc/{entry}/stat') as f:
                    fields = f.read().rsplit(')', 1)[1].split()
            except OSError:
                continue

            if fields and fields[0] == 'Z' and int(fields[1]) == os.getpid():
                count += 1

        return count

    def test_repeated_queries_leave_no_zombies(self):
        # antes cada consulta hacía `new_subprocess(...)` y recorría su salida sin esperar
        # nunca al hijo: veinte consultas dejaban veinte entradas en la tabla de procesos
        # durante toda la sesión, cada una ocupando un PID
        responses = {'pacman': {'*': {'stdout': 'core/zlib 1.3-1\n    Compression library\n'}}}
        before = self._own_zombies()

        with FakeBinaries(responses):
            for _ in range(20):
                pacman.get_repositories(('zlib',))

        self.assertEqual(before, self._own_zombies())

    def test_reading_dependencies_leaves_no_zombies(self):
        responses = {'pacman': {'*': {'stdout': 'Depends On     : glibc  gcc-libs\n'}}}
        before = self._own_zombies()

        with FakeBinaries(responses):
            for _ in range(10):
                deps = pacman.read_dependencies('firefox')

        self.assertEqual({'glibc', 'gcc-libs'}, deps)
        self.assertEqual(before, self._own_zombies())

    def test_provides_and_missing_are_read_without_a_grep_pipeline(self):
        responses = {'pacman': {'*': {'stdout': 'Provides       : libzlib.so  zlib-compat\n'}}}

        with FakeBinaries(responses) as fakes:
            provides = pacman.read_provides('zlib')
            calls = fakes.calls()

        self.assertEqual({'zlib', 'libzlib.so', 'zlib-compat'}, provides)
        # una sola llamada, sin encadenar un 'grep' por una tubería
        self.assertEqual([['-Si', 'zlib']], calls)
