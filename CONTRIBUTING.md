# Cómo contribuir a bauh Gekko Edition

Gracias por tu interés. Este documento explica cómo preparar el entorno, cómo
probar y qué convenciones seguimos. Si el cambio que propones no es específico
del fork (un arreglo en la gem Arch, una traducción, un fallo de la interfaz),
considera enviarlo **también** al proyecto original
[vinifmor/bauh](https://github.com/vinifmor/bauh); ver
[docs/SINCRONIZACION_UPSTREAM.md](docs/SINCRONIZACION_UPSTREAM.md).

## Formas de contribuir

- Reportar errores con la [plantilla de issue](.github/ISSUE_TEMPLATE/bug_report.md).
- Proponer mejoras (pregúntate antes si sirven a más de una persona).
- Corregir errores o implementar mejoras mediante pull request.
- Añadir o corregir traducciones.

## Reportar errores

- Actualiza primero a la versión actual de `master`
  (`install.sh --force`) y comprueba que el error sigue ocurriendo.
- Indica el commit instalado (`cat "$(pipx environment --value PIPX_LOCAL_VENVS)/gekko-bauh/.gekko-source-ref"`),
  la salida de `pipx list`, la distribución, el entorno de escritorio o
  compositor (X11/Wayland) y la versión de Python.
- Adjunta la salida de `gekko-bauh --logs` reproduciendo el problema.
- Si el mismo error ocurre con el bauh oficial, repórtalo en el upstream y
  enlaza el issue aquí.

## Entorno de desarrollo

Requisitos: Python 3.9 o superior (3.12+ recomendado; ver la nota de
compatibilidad en `README.md`) y, para ejecutar la interfaz o sus tests, PyQt5.

Con `venv`:

```bash
git clone https://github.com/The-Gekko/Bauh-Fork-The-Gekko.git
cd Bauh-Fork-The-Gekko
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/pip install -e .
```

Con [uv](https://github.com/astral-sh/uv):

```bash
uv venv .venv
uv pip install -r requirements.txt -r requirements-dev.txt -e .
```

`requirements.txt` contiene las dependencias de ejecución (PyQt5, requests,
colorama, PyYAML, python-dateutil) y `requirements-dev.txt` las de desarrollo
(`ruff`, `build`, `twine`, `lxml`, `beautifulsoup4`...). PyQt5 es **opcional**
para trabajar en las gems o en `commons/`: los tests que lo necesitan se omiten
automáticamente cuando no está instalado. Para probar la aplicación instalada
como lo hace un usuario, `./install.sh` desde el checkout la instala con pipx.

## Ejecutar los tests

La suite usa `unittest` de la biblioteca estándar (no pytest). Los tests de la
interfaz necesitan una plataforma Qt sin pantalla:

```bash
# Suite completa (con PyQt5 instalado)
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests

# Solo lo que no depende de Qt (por ejemplo, sin PyQt5 en el entorno)
.venv/bin/python -m unittest discover -s tests/common
.venv/bin/python -m unittest discover -s tests/gems

# Un módulo concreto
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest tests.view.core.test_stylesheet -v
```

Reglas para los tests nuevos:

- `unittest` puro, un archivo `test_*.py` junto al módulo que cubre
  (`tests/<ruta espejo>/`), con `__init__.py` en los directorios nuevos.
- Los tests que importan Qt se decoran con
  `@unittest.skipUnless(importlib.util.find_spec('PyQt5') is not None, 'PyQt5 no disponible')`
  y se ejecutan con `QT_QPA_PLATFORM=offscreen`.
- Sin acceso a red ni a `sudo`; simula los procesos externos con
  `unittest.mock`.
- Todo cambio funcional lleva su test; la suite completa debe seguir en verde.

## Lint y comprobaciones estáticas

```bash
.venv/bin/ruff check bauh tests            # estilo y errores (configuración en pyproject.toml)
shellcheck install.sh                      # el instalador es bash
.venv/bin/python -m py_compile <archivo>   # compilación rápida de un archivo
python3 tools/check_locales.py             # paridad de claves entre idiomas
```

La CI (GitHub Actions) ejecuta la suite en Python 3.9, 3.12 y 3.14, `ruff`,
`shellcheck`, `python -m build` y `tools/check_locales.py`. Un pull request no
se integra con la CI en rojo.

## Traducciones e internacionalización

Los textos visibles en la interfaz **nunca** se escriben directamente en el
código: siempre pasan por `i18n` con una clave definida en los archivos de
locale. Formato: un archivo por idioma (código ISO de dos letras: `en`, `es`,
`pt`, ...), una línea `clave=valor` por texto, **sin secuencias `\n`** (usa
`<br>` si necesitas un salto de línea en un cuadro de diálogo). Toda clave
nueva debe existir como mínimo en `en` y `es`; añade el resto de idiomas del
directorio traduciendo tú (o copiando el inglés si no dominas el idioma, para
que `tools/check_locales.py` no falle).

Directorios de locale:

- `bauh/view/resources/locale/` (interfaz común; incluye las subcarpetas
  `about/` y `tray/`)
- `bauh/gems/appimage/resources/locale/`
- `bauh/gems/arch/resources/locale/`
- `bauh/gems/debian/resources/locale/`
- `bauh/gems/eopkg/resources/locale/`
- `bauh/gems/flatpak/resources/locale/`
- `bauh/gems/github/resources/locale/`
- `bauh/gems/snap/resources/locale/`
- `bauh/gems/web/resources/locale/`

Idiomas presentes: `ca`, `de`, `en`, `es`, `fr`, `it`, `pt`, `ru`, `tr` y `zh`,
los diez en **todos** los directorios anteriores. `tools/check_locales.py` exige
esa paridad y falla si un directorio se queda sin uno de ellos, así que al añadir
un idioma nuevo crea el archivo en todos.

## Tests

El detalle completo (qué cubre cada carpeta, cómo funciona el arnés de binarios simulados
y qué ejecuta la integración continua) está en [docs/TESTS.md](docs/TESTS.md).

## Estilo de código

- [PEP 8](https://www.python.org/dev/peps/pep-0008/) y lo que dicte `ruff`.
- Identificadores (variables, funciones, clases, claves de configuración) en
  **inglés**; comentarios, docstrings y documentación en **español**.
- Sé conservador con el código heredado del upstream: cambios mínimos,
  acotados y con test. Cuanto menos divergimos, más fácil es sincronizar.
- Respeta los contratos públicos que usan varias partes del código:
  `SoftwareManager` (`bauh/api/abstract/controller.py`), los nombres
  exportados por `bauh/view/qt/thread.py`, `set_theme(theme_key, app, logger,
  app_config=None)` en `bauh/stylesheet.py`, `RootDialog.ask_password(...)` y
  `CoreConfigManager.get_config()/save_config()`.
- Las acciones con privilegios reciben la contraseña por `stdin`
  (`sudo -S -k`), nunca por argumento, y los comandos externos se construyen
  como listas de argumentos.

## Commits, ramas y pull requests

- **Mensajes de commit en español**, en imperativo, con prefijo de tipo y
  ámbito opcional: `feat(arch): ...`, `fix(theme): ...`, `docs: ...`,
  `test: ...`, `chore: ...`, `refactor: ...`, `security: ...`.
  Ejemplo: `fix(eopkg): leer la versión instalada desde "eopkg info"`.
- Un cambio por commit; los cambios en archivos que el upstream mantiene
  activos (`bauh/gems/arch`, `bauh/view/qt`) van en commits separados de los
  de tema o documentación para facilitar los merges.
- **Nunca se hace push directo a `master`**: crea una rama
  (`feat/...`, `fix/...`, `docs/...`), abre un pull request y espera a que la
  CI esté en verde y haya revisión. `master` es lo que instala `install.sh`,
  así que también está prohibido reescribir su historial (rebase o force
  push).
- En el pull request explica qué cambia y por qué, enlaza el issue si lo hay
  y marca la lista de comprobación de la plantilla (tests, lint, traducciones,
  CHANGELOG).
- Añade una línea en la sección de la versión en curso de `CHANGELOG.md`
  cuando el cambio sea visible para el usuario.

## Versiones y etiquetas

La versión vive en `bauh/__init__.py` con el esquema PEP 440
`<versión upstream>+gekko.N` (por ejemplo `0.10.8+gekko.1`) y la etiqueta git
equivalente `v<versión upstream>-gekko.N`. Solo el mantenedor publica
versiones; el procedimiento y la relación con las versiones del upstream están
en [docs/SINCRONIZACION_UPSTREAM.md](docs/SINCRONIZACION_UPSTREAM.md).
