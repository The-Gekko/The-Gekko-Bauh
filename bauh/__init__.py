__version__ = '0.10.8+gekko.1'

# Identificador de la aplicación: nombre del ejecutable y de los lanzadores, icono del
# tema y raíz de los directorios de configuración, caché y datos del usuario. Es propio
# del proyecto y NO coincide con el nombre del paquete Python.
__app_name__ = 'gekko-bauh'

# Nombre del paquete Python que contiene el código. Se conserva heredado del proyecto
# original para poder seguir integrando sus correcciones sin reescribir cada import.
# Úsalo donde haga falta una ruta de módulo (por ejemplo en unittest.mock.patch):
# __app_name__ no sirve para eso porque lleva un guion.
__package_name__ = 'bauh'

# Nombre visible en la interfaz («Acerca de», bandeja, títulos de ventana) y en los
# lanzadores .desktop.
__display_name__ = 'bauh Gekko Edition'

# Repositorio de este proyecto: es el que se consulta para buscar actualizaciones y el
# que se muestra en la documentación y en los informes de error.
__repo_url__ = 'https://github.com/The-Gekko/Bauh-Fork-The-Gekko'

# Proyecto original del que deriva este. Se conserva para dar crédito y para poder
# distinguir sus versiones «0.10.8» de las «0.10.8+gekko.N» de este proyecto.
__upstream_url__ = 'https://github.com/vinifmor/bauh'

import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
