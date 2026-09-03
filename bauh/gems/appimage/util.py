import os
import re
from typing import Optional

RE_DESKTOP_EXEC = re.compile(r'(\n?\s*\w*Exec\s*=(.+))')
RE_MANY_SPACES = re.compile(r'\s+')


def find_appimage_file(folder: str) -> Optional[str]:
    """Ruta del fichero .AppImage dentro de un directorio de instalación.

    Se prefiere el que esté directamente en la raíz; si no lo hay, se busca en los
    subdirectorios. La ruta se compone con el directorio que se está recorriendo, no con el
    de partida: antes se devolvía «<raíz>/<nombre>» aunque el fichero estuviera dentro de una
    subcarpeta, con lo que la ruta no existía y la aplicación no arrancaba.

    El orden es estable (alfabético) para que dos ejecuciones den siempre lo mismo cuando hay
    más de un .AppImage: `os.walk` no garantiza ningún orden.
    """
    found = []

    for root, _, files in os.walk(folder):
        for file_name in sorted(files):
            if file_name.lower().endswith('.appimage'):
                found.append(os.path.join(root, file_name))

    if not found:
        return None

    # los de la raíz primero; entre iguales, por profundidad y luego alfabéticamente
    found.sort(key=lambda path: (os.path.dirname(path) != folder, path.count(os.sep), path))
    return found[0]


def replace_desktop_entry_exec_command(desktop_entry: str, appname: str, file_path: str) -> str:
    execs = RE_DESKTOP_EXEC.findall(desktop_entry)

    if not execs:
        return desktop_entry

    final_entry = desktop_entry
    treated_name = appname.strip().lower()

    for exec_groups in execs:
        full_match = exec_groups[0]

        if full_match.strip().startswith("TryExec"):  # TryExec cause issues in some DE to display the app icon
            final_entry = final_entry.replace(full_match, "")
            continue

        cmd = RE_MANY_SPACES.sub(' ', exec_groups[1].strip())
        if cmd:
            words = cmd.split(' ')
            changed = False

            for idx in range(len(words)):
                if words[idx].lower() == treated_name:
                    words[idx] = f'"{file_path}"'
                    changed = True
                    break

            if not changed:
                words = [f'"{file_path}"']

            final_entry = final_entry.replace(full_match, full_match.replace(exec_groups[1], ' '.join(words)))

    return final_entry
