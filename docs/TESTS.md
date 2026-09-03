# Cómo se prueba este proyecto

La suite usa `unittest` de la biblioteca estándar, sin pytest. Se ejecuta entera con:

```bash
python -m unittest discover -s tests -t .
```

Los tests que necesitan PyQt5 se saltan solos si no está instalado, así que el comando
anterior funciona igual en un entorno sin Qt. Para ejecutarlos, instala PyQt5 y usa la
plataforma `offscreen`:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -t .
```

## Qué cubre cada carpeta

| Carpeta | Qué prueba |
|---|---|
| `tests/api/`, `tests/commons/`, `tests/common/` | Utilidades compartidas: rutas, configuración, ejecución de procesos, contraseña de root. |
| `tests/gems/<gem>/` | Cada backend por separado, parcheando la frontera con el sistema. |
| `tests/view/` | Temas, hojas de estilo, modelo de la tabla y ciclo de vida de las ventanas. |
| `tests/integration/` | Las gems contra **binarios simulados en el `PATH`** (ver abajo). |
| `tests/installer/` | `tools/check_locales.py` y el empaquetado. Los 21 casos de `install.sh` viven en `tests/installer/run_tests.sh`. |
| `tests/packaging/` | Las recetas del AUR: que `PKGBUILD` y `.SRCINFO` concuerden. |

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

`install.sh` se prueba aparte, en bash, dentro de un `HOME` de mentira y con `pipx`, `curl`
y `sudo` simulados:

```bash
bash tests/installer/run_tests.sh
```

Son 21 casos: instalación local y remota, reinstalación del mismo commit, `--force`,
`--ref`, respaldo de iconos, migración desde el entorno antiguo, desinstalación con y sin
`--purge`, conservación de los clones de la gem GitHub y respeto por una instalación ajena
del bauh oficial. Ninguno usa red ni `sudo` de verdad.

## Comprobación de traducciones

```bash
python tools/check_locales.py           # bloqueante: falla si falta una clave
python tools/check_locales.py --report  # informe completo, nunca falla
```

Exige que los diez idiomas (`ca`, `de`, `en`, `es`, `fr`, `it`, `pt`, `ru`, `tr`, `zh`)
cubran todas las claves de `en` en **todos** los directorios de locale, y que ninguno falte
por completo.

## Lo que ejecuta la integración continua

`.github/workflows/ci.yml` corre seis trabajos:

| Trabajo | Qué hace |
|---|---|
| `tests` | La suite **sin PyQt5** en Python 3.9, 3.12 y 3.14. Garantiza que ningún módulo importe Qt en el nivel superior. |
| `tests-qt` | La suite **completa** con Qt `offscreen` en 3.12. |
| `lint` | `ruff check bauh tests tools`. |
| `installer` | `shellcheck` sobre los dos scripts y los 21 casos de `run_tests.sh`. |
| `build` | `python -m build`, `twine check` y comprobación de que el wheel lleva locales, imágenes, estilos, lanzadores y los datos vendorizados de la gem Arch. |
| `locales` | Informe de traducciones y puerta bloqueante. |

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
