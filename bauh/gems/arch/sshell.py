from typing import Optional, Tuple

from bauh.commons.system import execute_args


def mkdir(dir_path: str, parent: bool = True, custom_user: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Crea un directorio, opcionalmente como otro usuario del sistema.

    Se pasa la ruta como argumento, no interpolada en una línea de shell: el directorio de
    compilación se construye a partir de rutas de configuración que el usuario puede cambiar,
    y unas comillas o un « $ » ahí dentro cambiaban la orden que se acababa ejecutando.
    """
    args = ['mkdir']

    if parent:
        args.append('-p')

    args.append(dir_path)

    code, output = execute_args(args, custom_user=custom_user)
    return code == 0, output
