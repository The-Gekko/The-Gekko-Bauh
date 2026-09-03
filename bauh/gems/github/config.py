from bauh.commons.config import YAMLConfigManager
from bauh.gems.github import CONFIG_FILE, DEFAULT_REPOS_DIR

# número máximo de repositorios devueltos por una búsqueda de texto
DEFAULT_SEARCH_LIMIT = 10

# segundos que se conservan en memoria los resultados de la API de GitHub
DEFAULT_CACHE_EXPIRATION = 300


class GitHubConfigManager(YAMLConfigManager):

    def __init__(self):
        super(GitHubConfigManager, self).__init__(config_file_path=CONFIG_FILE)

    def get_default_config(self) -> dict:
        return {
            'repos_dir': DEFAULT_REPOS_DIR,
            # por defecto la gem sólo clona: construir el código de un repositorio
            # arbitrario ejecuta código de terceros y debe ser una decisión explícita
            'clone_only': True,
            # token personal opcional: sin él la API pública limita a ~10 peticiones/minuto
            'github_token': None,
            # las búsquedas de texto libre golpean la API en cada pulsación, así que están
            # desactivadas salvo que se pidan con el prefijo 'gh:' o se activen aquí
            'search_enabled': False,
            'search_limit': DEFAULT_SEARCH_LIMIT,
            # 'git fetch' + 'git rev-list HEAD..@{u} --count' al listar actualizaciones
            'check_updates': True,
        }
