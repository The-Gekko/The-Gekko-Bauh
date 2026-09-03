__version__ = '0.10.8+gekko.1'
__app_name__ = 'bauh'

# Nombre visible del fork. Se usa en la interfaz («Acerca de», bandeja) y en los
# lanzadores .desktop; el identificador técnico sigue siendo __app_name__ para no
# romper rutas de configuración ni el nombre del ejecutable.
__display_name__ = 'bauh Gekko Edition'

# Repositorio de este fork: es el que se consulta para buscar actualizaciones y
# el que se muestra en la documentación y en los informes de error.
__repo_url__ = 'https://github.com/The-Gekko/Bauh-Fork-The-Gekko'

# Proyecto original del que deriva el fork. Se conserva para dar crédito y para
# poder distinguir las versiones «0.10.8» de upstream de las «0.10.8+gekko.N».
__upstream_url__ = 'https://github.com/vinifmor/bauh'

import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
