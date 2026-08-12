# AGENTS.md

Fork de `vinifmor/bauh` (PyQt5, Python 3.8–3.14) orientado a **Arch Linux / Garuda (Chaotic AUR)** y **Solus (eopkg)**. Docs y commits en español; mantén ese idioma. Entry points: `bauh.app:main` (GUI), `bauh.app:tray`, `bauh.cli.app:main` (CLI, solo subcomando `updates`). La versión vive en `bauh/__init__.py` y la lee `setup.py`.

## Arquitectura

- Los backends son **gems** en `bauh/gems/<nombre>/`. `bauh/view/core/gems.py` importa el `controller.py` de cada subdirectorio y registra toda clase que herede directamente de `SoftwareManager`. Backend nuevo = crear subdir con `controller.py` + `model.py` + `resources/` (icono + locales).
- Las gems **nunca importan widgets Qt**: comunican vía contratos de `bauh/api/abstract/`. Operaciones lentas → workers de `bauh/view/qt/threads/`.
- `build/`, `bauh.egg-info/`, `__pycache__/` son generados; no editar. **Gotcha**: un `build/lib/` obsoleto con archivos ya borrados del árbol se cuela en el wheel que instala `install.sh` (pip no limpia `build/`). Antes de reinstalar: `rm -rf build bauh.egg-info` y limpiar el caché de pip/uv.

## Objetivos de distro (verifica la wiki correspondiente antes de tocar)

- **Arch/Garuda**: `gems/arch` (pacman + AUR + Chaotic AUR). Garuda trae `[chaotic-aur]` activo por defecto (línea `Include = /etc/pacman.d/chaotic-mirrorlist`); un Arch limpio puede no tenerlo. El fork asume Chaotic AUR habilitado.
- **Solus**: `gems/eopkg`. Trampas documentadas y verificadas contra el código fuente de `getsolus/eopkg`:
  - `eopkg -N` = `--no-color` (suprime el color de salida), **NO** desactiva prompts. Para no interactivo el flag correcto es `-y` / `--yes-all`.
  - El commit que añadió `-N` lo etiquetó mal ("disable interactive prompts"); en realidad estabiliza el parseo del output. No repliques esa afirmación en código nuevo.
  - `_execute_eopkg` fuerza `LANG=en_US.UTF-8` y limpia secuencias ANSI con regex; los comandos mutantes llevan `-y -N`. Mantén ese patrón en comandos eopkg nuevos.
  - Solus se detecta por presencia de `eopkg` (`shutil.which`) en `can_work()`.

## Tests

- `unittest` puro, sin pytest. Verificación rápida sin PyQt5: `python3 -m unittest discover -s tests/common`. Completo: `python3 -m unittest discover -s tests`.
- Algunos módulos fallan **al importar** si falta `colorama`/`PyQt5` en el entorno (arch/test_pacman, arch/test_updates, web/test_controller, view/qt): no significa que estén rotos.

## Build / instalar

- Build PEP 517 (`pyproject.toml`, `setuptools.build_meta`). `BAUH_SETUP_NO_REQS` omite leer `requirements.txt`.
- `./install.sh [--yes]` instala vía **pipx** (requiere `python-pipx`, Python 3.8–3.14). `PYTHON_BIN` elige el intérprete. Detecta y ofrece desinstalar el `bauh` de repositorio (pacman o eopkg) para evitar conflictos, y avisa si falta `[chaotic-aur]`.
- Releases: fuente `bauh-fork-the-gekko-<versión>.tar.zst` + manifiesto `<target>.manifest.json` con SHA-256 (ver `releases/dist/`).

## Convenciones

- Traducciones: cada idioma necesita archivo en `bauh/view/resources/locale` **y** en los `resources/locale` de cada gem (lista completa en CONTRIBUTING.md). eopkg tiene `en` y `es`.
- PEP 8 (según CONTRIBUTING.md).
- Remotes: `origin` = fork The-Gekko, `upstream` = `vinifmor/bauh`. Rama `master`.
- Hay WIP sin commitear (refactor del diálogo modal de contraseña + cambio de icono a `gekko-bauh.png`, imagen generada por IA); no revertirlo.

Referencias canónicas: wiki.archlinux.org, help.getsol.us, wiki.garudalinux.org, aur.chaotic.cx.
