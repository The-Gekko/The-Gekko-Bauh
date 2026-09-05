# Cómo se prueba este proyecto

La suite usa `unittest` de la biblioteca estándar, sin pytest.

**Requisito previo: un entorno virtual con `requirements-dev.txt`.** Sin `pyyaml` y
`colorama`, `unittest discover` falla al **importar** 25 módulos de test (22 por `yaml` y 3
por `colorama`: los que cargan `bauh.api.abstract.controller` o `bauh.commons.config`), y
esos fallos de importación cuentan como errores, no como tests omitidos. Con el Python del
sistema y sin esas dependencias la suite termina en `FAILED (errors=25, ...)`, y eso no
significa que el código esté roto.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt          # suite sin Qt
.venv/bin/python -m unittest discover -s tests -t .
```

Los tests que necesitan PyQt5 se saltan solos si no está instalado, así que el comando
anterior funciona igual en un entorno sin Qt. Para ejecutarlos, instala también
`requirements.txt` (trae PyQt5) y usa la plataforma `offscreen`:

```bash
.venv/bin/pip install -r requirements.txt
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -t .
```

## Qué cubre cada carpeta

| Carpeta | Qué prueba |
|---|---|
| `tests/api/`, `tests/commons/`, `tests/common/` | Utilidades compartidas: rutas, configuración, ejecución de procesos, contraseña de root. |
| `tests/gems/<gem>/` | Cada backend por separado, parcheando la frontera con el sistema. |
| `tests/view/` | Temas, hojas de estilo, modelo de la tabla y ciclo de vida de las ventanas. |
| `tests/integration/` | Las gems contra **binarios simulados en el `PATH`** (ver abajo). |
| `tests/installer/` | `tools/check_locales.py`, `tools/build-gekkoapp-release.sh` y el empaquetado (`pyproject.toml`, `.desktop`, invariantes de `install.sh`). Los 26 casos de `install.sh` viven en `tests/installer/run_tests.sh`. |
| `tests/packaging/` | Las recetas del AUR (que `PKGBUILD` y `.SRCINFO` concuerden) y el workflow de release. |

## Tests de integración con binarios simulados

Las gems no llaman a una API: lanzan `pacman`, `eopkg` o `flatpak` y analizan su salida. Un
test que parchea `subprocess` comprueba lo que la gem *cree* que ejecuta, no lo que el
sistema *recibe*: con esa frontera parcheada, una orden mal construida pasa desapercibida.

`tests/integration/harness.py` sustituye el binario, no la función. Crea un script en un
directorio temporal, lo antepone al `PATH`, le dicta lo que debe imprimir y registra cada
invocación con sus argumentos:

```python
from tests.integration.harness import FakeBinaries

with FakeBinaries({'eopkg': {'li': {'stdout': 'vlc - VLC media player\n'}}}) as fakes:
    index = manager._read_installed_index()
    calls = fakes.calls('eopkg')

assert calls[0] == ['li', '--no-color']
```

Cada respuesta se indexa por el primer argumento que no empieza por `-` (el subcomando);
la clave `'*'` responde a cualquiera. Se puede fijar `stdout`, `stderr` y `code`.

**Detalle importante**: `bauh/commons/system.py` fotografía el `PATH` al importarse
(`PATH = os.getenv('PATH')`) y `gen_env()` reparte esa copia a todos los subprocesos, así
que cambiar `os.environ['PATH']` no basta. `FakeBinaries` sustituye también la constante del
módulo y la restaura al salir.

Estas pruebas cubren dos cosas que las unitarias no pueden:

1. **Los argumentos que llegan de verdad al proceso.** Los comandos se construyen como listas
   y se ejecutan sin shell, de modo que un término de búsqueda como
   `firefox; touch /tmp/x #` llega como un único argumento en vez de convertirse en dos
   órdenes. Hay un test por cada entrada de texto libre que acaba en un comando.
2. **El análisis de la salida real.** Las fixtures son recortes de salidas reales de pacman,
   eopkg y flatpak, incluidas las que el dueño del proyecto aportó desde Solus.

## Tests del instalador

`install.sh` se prueba aparte, en bash, dentro de un `HOME` de mentira y con `pipx`, `uv`,
`curl` y `sudo` simulados:

```bash
bash tests/installer/run_tests.sh
```

Son 26 casos: instalación local y remota, backend uv de pipx (`UV_NO_BUILD_PACKAGE`
separada por espacios y `PIP_ONLY_BINARY` por comas; el `pipx` falso aborta con comas
igual que uv), `--allow-build-from-source`, `--ref` rechazado en modo local, instalación
local desde una copia limpia (sin `build/`, `dist/`, `*.egg-info`, `__pycache__` ni
`.git`), reinstalación del mismo commit, `--force`, `--ref` remoto, respaldo de iconos,
migración desde el entorno antiguo, desinstalación con y sin `--purge` (también con
`XDG_DATA_HOME` igual a `~/.local/share`, sin rutas repetidas), conservación de los
clones de la gem GitHub y respeto por una instalación ajena del bauh oficial. Ninguno usa
red ni `sudo` de verdad; el `uv` falso solo existe para que `install.sh` no fuerce
`--backend pip`.

## Comprobación de traducciones

```bash
python tools/check_locales.py           # bloqueante: falla si falta una clave
python tools/check_locales.py --report  # informe completo, nunca falla
```

Exige que los diez idiomas (`ca`, `de`, `en`, `es`, `fr`, `it`, `pt`, `ru`, `tr`, `zh`)
cubran todas las claves de `en` en **todos** los directorios de locale, y que ninguno falte
por completo.

## Lo que ejecuta la integración continua

`.github/workflows/ci.yml` corre siete trabajos (los nombres son los `id` de los jobs):

| Trabajo | Nombre visible | Qué hace |
|---|---|---|
| `tests` | tests (py3.9/3.12/3.14, sin Qt) | La suite **sin PyQt5** en Python 3.9, 3.12 y 3.14. Garantiza que ningún módulo importe Qt en el nivel superior. |
| `qt` | tests con PyQt5 (offscreen) | La suite **completa** con Qt `offscreen` en 3.12, instalando `requirements.txt` solo desde wheels. |
| `lint` | lint (ruff + shellcheck) | `ruff check bauh tests tools` (bloqueante), un informe de la deuda heredada (no bloquea), `ruff` estricto sobre `tools`, `tests/installer` y `bauh/__init__.py`, `bash -n` y `shellcheck` sobre `install.sh`, `tests/installer/run_tests.sh` y `tools/build-gekkoapp-release.sh`. |
| `installer` | tests del instalador | Los 26 casos de `tests/installer/run_tests.sh`. |
| `build` | build + twine check | `python -m build`, `twine check` y comprobación de que el wheel lleva locales, imágenes, estilos, lanzadores y los datos vendorizados de la gem Arch. |
| `integration` | integracion (binarios simulados) | `tests/integration/` con `pacman`, `eopkg` y `flatpak` simulados. |
| `locales` | paridad de traducciones | Informe de traducciones y puerta bloqueante. |

El workflow de release (`release.yml`, etiquetas `v*`) no repite la suite: construye el
wheel y el sdist, genera el artefacto de GekkoApp con `tools/build-gekkoapp-release.sh` y
publica todo con `SHA256SUMS` (ver `docs/DISTRIBUCION.md`).

## Escribir un test nuevo

- Si el test necesita PyQt5, importa dentro del test o del `setUp`, nunca en el nivel de
  módulo: `unittest discover` falla al recolectar antes de poder saltarse nada. Protege la
  clase con
  `@unittest.skipUnless(importlib.util.find_spec('PyQt5') is not None, 'PyQt5 no disponible')`.
- Para parchear rutas de módulo usa `__package_name__`, no `__app_name__`:
  `patch(f'{__package_name__}.gems.arch.controller.pacman')`. `__app_name__` vale
  `gekko-bauh`, que lleva un guion y no es una ruta de módulo válida.
- Si necesitas una `QApplication`, usa `QApplication.instance() or QApplication([])`. Nunca
  crees una `QCoreApplication`: la instancia es única por proceso, y una sin GUI hace que
  Qt aborte el proceso entero en cuanto otro test construya un widget.
