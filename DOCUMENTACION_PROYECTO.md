# Documentación técnica del proyecto

## 1. Resumen

`bauh` es una aplicación Python con interfaz gráfica Qt (PyQt5) para buscar,
instalar, desinstalar, actualizar, ejecutar y administrar software Linux desde
distintos formatos y fuentes. El código utiliza una arquitectura de gestores de
paquetes intercambiables, llamados **gems**. Cada gem adapta una fuente o
tecnología a los contratos comunes definidos en `bauh/api/abstract/`.

Este repositorio es **bauh Gekko Edition**, fork de
[vinifmor/bauh](https://github.com/vinifmor/bauh). La versión declarada en
`bauh/__init__.py` es `0.10.8+gekko.1` (PEP 440 con etiqueta local; etiqueta
git `v0.10.8-gekko.1`). El nombre de distribución es `bauh-gekko`; el paquete
importable sigue siendo `bauh` y los binarios `bauh`, `bauh-tray` y `bauh-cli`.
El punto de entrada principal es `bauh.app:main`; también existen una
aplicación para la bandeja del sistema y una interfaz de línea de comandos
limitada a la consulta de actualizaciones.

El alcance del fork son tres plataformas: Arch Linux y derivados (pacman, AUR y
cualquier repositorio adicional de pacman), Flatpak y Solus (eopkg). Esas tres
gems están activadas por defecto. El árbol conserva los gestores del upstream
para AppImage, Debian, Snap y Web, pero estos están **desactivados por defecto**
(`is_default_enabled()` devuelve `False`), sin soporte activo, y el usuario los
activa en `Ajustes → Tipos de aplicaciones`. La gem GitHub, propia del fork,
también es opt-in. La disponibilidad real de cada gestor
depende además de `can_work()`: comandos, servicios y configuración presentes
en el sistema anfitrión.

## 2. Estructura general

```text
.
├── bauh/                       # Código fuente Python del paquete
│   ├── api/                    # Contratos, HTTP, rutas y usuario
│   ├── cli/                    # Entrada y comandos de consola
│   ├── commons/                # Utilidades compartidas
│   ├── desktop/                # Archivos .desktop incluidos en la distribución
│   ├── gems/                   # Adaptadores de fuentes/formatos de software
│   ├── view/                   # Configuración, lógica de aplicación y UI Qt
│   ├── app.py                  # Entrada GUI y bandeja
│   ├── app_args.py             # Argumentos de la GUI
│   ├── context.py              # QApplication, tema, vigilante de temas e i18n
│   ├── manage.py               # Ensamblaje del panel de administración
│   ├── stylesheet.py           # Lectura y procesamiento de temas
│   └── tray.py                 # Integración de la bandeja del sistema
├── tests/                      # Pruebas unitarias (unittest)
├── tools/                      # Utilidades de desarrollo (check_locales.py)
├── docs/                       # Políticas del fork (migración, sincronización)
├── linux_dist/                 # Material de distribución (AppImage del upstream)
├── pictures/                   # Arte del fork e iconos por tamaño
├── .github/                    # Plantillas de issues/PR y flujos de CI
├── install.sh                  # Instalador/desinstalador por curl (pipx)
├── requirements.txt            # Dependencias de ejecución
├── requirements-dev.txt        # Dependencias de desarrollo
├── pyproject.toml              # Metadatos [project] y backend PEP 517/518
├── setup.py                    # Shim de compatibilidad (delega en pyproject)
├── setup.cfg                   # Metadatos adicionales del paquete
├── MANIFEST.in                 # Archivos incluidos en la distribución
├── README.md                   # Presentación, instalación y características
├── CONTRIBUTING.md             # Entorno, tests, lint, traducciones, commits
├── CHANGELOG.md                # Historial de cambios (fork arriba, upstream debajo)
├── CREDITS.md                  # Créditos, procedencia y aviso de versión alterada
├── DOCUMENTACION_PROYECTO.md   # Este documento
└── LICENSE                     # Licencia zlib/libpng
```

`__pycache__/`, `build/`, `dist/` y `*.egg-info/` son salidas generadas,
están en `.gitignore` y no forman parte del árbol fuente. La implementación
que debe modificarse está en `bauh/` y las pruebas en `tests/`.

### Archivos de soporte en la raíz

| Archivo | Responsabilidad |
|---|---|
| `README.md` | Presenta el fork: qué añade frente al upstream, requisitos, instalación, migración, limitaciones (Wayland), tests. |
| `CONTRIBUTING.md` | Entorno de desarrollo, ejecución de tests y lint, traducciones, convención de commits y flujo de PR. |
| `CHANGELOG.md` | Sección `[0.10.8+gekko.1]` del fork (con base upstream y contribuciones integradas) seguida del historial literal del upstream. |
| `CREDITS.md` | Autoría original, colaboradores upstream integrados, aportaciones del fork y aviso de versión alterada (cláusula 2 de zlib). |
| `docs/MIGRACION.md` | Convivencia con el bauh oficial, claves de configuración no compartidas y vuelta atrás. |
| `docs/SINCRONIZACION_UPSTREAM.md` | Política de merges con `vinifmor/bauh`, resolución de conflictos en archivos reestructurados y esquema de versiones. |
| `LICENSE` | Texto íntegro de la licencia zlib/libpng, sin modificar. |
| `install.sh` | Instala/actualiza/desinstala el fork con pipx; ver sección 6. |
| `requirements.txt` / `requirements-dev.txt` | Dependencias de ejecución / de desarrollo (ruff, build, twine, lxml, beautifulsoup4). |
| `pyproject.toml` | Sección `[project]` completa (nombre `bauh-gekko`, versión dinámica, dependencias, scripts, clasificadores) y `[build-system]` con setuptools. |
| `setup.py` | Shim mínimo para herramientas que aún lo invocan; no contiene metadatos propios. |
| `setup.cfg` | Metadatos residuales de setuptools. |
| `MANIFEST.in` | Archivos adicionales incluidos en la distribución fuente. |

## 3. Arquitectura y flujo de ejecución

### 3.1 Inicio de la aplicación gráfica

1. El entry point `bauh` invoca `bauh.app:main`.
2. `bauh/app.py` instala un manejador de mensajes Qt (silencia avisos
   conocidos de Wayland), habilita `faulthandler`, registra un
   `sys.excepthook` que envía las excepciones no controladas al log, instala
   manejadores de `SIGINT`/`SIGTERM` para cerrar Qt de forma ordenada, lee los
   argumentos y carga la configuración global mediante `CoreConfigManager`.
   En sesiones Wayland (`XDG_SESSION_TYPE=wayland`) fuerza
   `QT_QPA_PLATFORM=wayland` (arreglo integrado del upstream).
3. Según los argumentos, crea el panel normal con `bauh.manage`, o la bandeja
   con `bauh.tray`.
4. `bauh/manage.py` crea traducciones, cachés, cliente HTTP, descargador,
   `ApplicationContext` y todos los gestores detectados por `view.core.gems`.
5. Los gestores se envuelven en `GenericSoftwareManager`, que ofrece una API
   única a la interfaz. Las búsquedas y lecturas de paquetes pueden ejecutarse
   en hilos independientes por gestor.
6. Se crea `ManageWindow`, precedido normalmente por `PreparePanel`, y se
   inicia el ciclo de eventos Qt.

### 3.2 Inicio de la CLI

`bauh/cli/app.py` repite el ensamblaje de contexto y gestores sin crear una
ventana. `bauh/cli/cli_args.py` define el subcomando `updates` y su formato
`text` o `json`. `CLIManager.list_updates()` consulta al gestor genérico y
muestra las actualizaciones disponibles.

### 3.3 Descubrimiento de gestores

`bauh/view/core/gems.py` recorre subdirectorios de `bauh/gems/`, importa el
`controller.py` de cada uno y busca una clase que herede directamente de
`SoftwareManager`. La activación sigue esta lógica:

- Si `/etc/bauh/gems.forbidden` lista la gem, no se carga.
- Si `config.yml` no tiene la clave `gems` (valor `null`), cada gem queda
  activada según su propio `is_default_enabled()`: `True` para `arch`,
  `flatpak` y `eopkg` (esta última solo si `can_work()` encuentra el binario
  `eopkg`); `False` para `appimage`, `debian`, `snap`, `web` y `github`.
- Si `gems` es una lista, se activan exactamente las que aparecen en ella.
  La pestaña `Tipos de aplicaciones` de Ajustes escribe esa lista.

Al cargar cada gem se incorporan sus traducciones. Cada gestor informa qué
tipos de paquete administra y si puede trabajar en el sistema actual.
`GenericSoftwareManager` crea un mapa tipo -> gestor y delega en él
operaciones como búsqueda, lectura de instalados, instalación,
desinstalación, actualización, downgrade, historial e información.

### 3.4 Modelo y vista

Los gestores producen objetos derivados de `SoftwarePackage` y resultados
`SearchResult`. La capa Qt los transforma en `PackageView`, los muestra en
`PackagesTable` y ejecuta las operaciones mediante las clases de
`bauh/view/qt/thread.py` (subclases de `QThread` con señales). Los contratos
de `api.abstract` mantienen desacoplada la lógica de cada gestor de la
interfaz.

La ventana principal es `ManageWindow` (`bauh/view/qt/window/manage_window.py`),
compuesta por tres mixins con contrato documentado en su docstring:
`UiMixin` (construcción y refresco visual), `ActionsMixin` (instalar,
desinstalar, actualizar, ejecutar, diálogos) y `FiltersMixin` (filtros por
tipo, categoría, nombre, estado y verificación). La ventana rechaza el cierre
mientras hay una transacción en curso.

### 3.5 Configuración, caché, rutas e idioma

- `CoreConfigManager` (`bauh/view/core/config.py`) usa YAML y crea una
  configuración por defecto con idioma, tema (`ui.theme`, por defecto
  `aurora`), `custom_theme` (colores, opacidad e imagen de la pestaña
  Personalización), descargas, cachés, sugerencias, copias de seguridad y
  opciones de UI. Migra la clave antigua `ui.custom_theme` a la raíz.
- `bauh/api/paths.py` define las rutas: `~/.config/bauh` (configuración),
  `~/.cache/bauh` (caché), `~/.local/share/bauh` (datos y `themes/`),
  `$XDG_RUNTIME_DIR/bauh` (temporales y logs, con permisos `0700`; como
  root, rutas del sistema equivalentes).
- `ApplicationContext` transporta dependencias compartidas: HTTP, i18n,
  descargador, cachés, logger, distribución, conectividad y privilegios.
- `view/util/cache.py` mantiene cachés en memoria; `view/util/disk.py` carga
  datos persistidos de forma asíncrona.
- `view/util/translation.py` carga diccionarios de idioma desde los recursos
  comunes y desde cada gem. Todo texto visible pasa por `i18n`.
- `stylesheet.py` y `context.py` cargan temas QSS predeterminados o temas del
  usuario (sección 3.6).

### 3.6 Temas y temas dinámicos

Temas incluidos en `bauh/view/resources/style/`: `aurora` (por defecto),
`darcula`, `default`, `gtk`, `knight`, `light`, `matugen` y `sublime`. Cada
tema es un `.qss` con variables en `.vars` y metadatos en `.meta`
(`name`, `description[xx]`, `root_theme`, `abstract`). `read_default_themes()`
los descubre por nombre de archivo y `process_theme()` resuelve la herencia.

Los temas `gtk` y `matugen` declaran `root_theme=aurora`: heredan la hoja de
Aurora y sustituyen sus colores por los del sistema. `parse_gtk_matugen_colors()`
(`bauh/stylesheet.py`) lee las directivas `@define-color` de
`~/.cache/matugen/colors-gtk.css`, `~/.config/gtk-3.0/gtk.css`,
`~/.config/gtk-4.0/gtk.css` y `/etc/gtk-3.0/gtk.css`, y las mapea a las
variables del tema (fondo, vista, texto, barra lateral, acento).

`setup_theme_watcher()` (`bauh/context.py`) instala un `QFileSystemWatcher`
sobre esos archivos **solo cuando el tema activo es `gtk` o `matugen`**, con
debounce para agrupar escrituras consecutivas, y vuelve a llamar a
`set_theme(theme_key, app, logger, app_config)` al detectar cambios. La
ventana principal tiene un botón «Matugen» que activa ese tema y cuyo estado
persiste en la configuración. La firma de `set_theme` es un contrato público
del proyecto y no debe cambiar.

### 3.7 Privilegios y seguridad

`RootDialog` (`bauh/view/qt/root.py`) pide la contraseña con un diálogo modal
a nivel de aplicación (`ApplicationModal`, campo enmascarado, `Enter` para
confirmar) y expone `ask_password(...)` aceptando `parent`. La contraseña se
entrega a los procesos por `stdin` (`sudo -S -k`) y nunca como argumento; el
resultado se valida por código de retorno. Los comandos de pacman se
construyen como listas de argumentos y la entrada del usuario se sanea antes
de usarse en comandos.

## 4. Descripción de archivos y módulos

### 4.1 Raíz del paquete `bauh/`

| Archivo | Responsabilidad |
|---|---|
| `bauh/__init__.py` | Declara `__version__` (`0.10.8+gekko.1`), `__app_name__` (`bauh`) y `ROOT_DIR`. |
| `bauh/app.py` | Entrada GUI; prepara Qt, argumentos, logging, `excepthook`, señales, escalado, modo offline, modo bandeja y ciclo de eventos. |
| `bauh/app_args.py` | Define `--logs`, `--offline`, `--suggestions`, `--tray`, `--settings` y `--reset`. |
| `bauh/context.py` | Crea `QApplication`, configura estilo/paleta, temas, vigilante de temas e internacionalización. |
| `bauh/manage.py` | Construye el contexto de la aplicación, carga gems, crea el gestor genérico y selecciona ventana de ajustes o panel principal. |
| `bauh/stylesheet.py` | Lee metadatos y archivos de temas, resuelve herencia/procesamiento, mapea colores GTK/Matugen y genera QSS. |
| `bauh/tray.py` | Punto de entrada y utilidades para crear la aplicación asociada a la bandeja. |
| `bauh/desktop/*.desktop` | Entradas de escritorio de la aplicación y la bandeja incluidas en el paquete. |

### 4.2 API común: `bauh/api/`

| Archivo | Responsabilidad |
|---|---|
| `api/exception.py` | Excepciones compartidas, incluida la ausencia de conexión. |
| `api/http.py` | Cliente HTTP común usado por gestores, descargas y consultas remotas. |
| `api/paths.py` | Rutas de configuración, caché, datos, temporales (XDG) y logs. |
| `api/user.py` | Detección de usuario root y operaciones relacionadas con privilegios. |
| `api/abstract/cache.py` | Interfaces para fábricas y objetos de caché en memoria. |
| `api/abstract/context.py` | `ApplicationContext`, contenedor de servicios y estado compartido. |
| `api/abstract/controller.py` | `SoftwareManager`, resultados de búsqueda, acciones, requisitos de actualización y contratos de operaciones. |
| `api/abstract/disk.py` | Contratos para cargar/escribir caché de disco. |
| `api/abstract/download.py` | Interfaz de descarga de archivos. |
| `api/abstract/handler.py` | Interfaces para observar procesos y administrar tareas. |
| `api/abstract/model.py` | `SoftwarePackage`, acciones personalizadas, estados, actualizaciones e historial. |
| `api/abstract/view.py` | Modelos abstractos de componentes visuales y tipos de mensajes. |

La API abstracta define el protocolo que deben cumplir todos los gestores. Por
ejemplo, `SoftwareManager` exige métodos para buscar, leer instalados,
actualizar, instalar, desinstalar y ejecutar; `SoftwarePackage` normaliza los
datos que consume la UI.

### 4.3 Utilidades comunes: `bauh/commons/`

| Archivo | Responsabilidad |
|---|---|
| `boot.py` | Creación/gestión de archivos de configuración iniciales. |
| `category.py` | Constantes y utilidades de categorías de aplicaciones. |
| `config.py` | Gestor base de configuración YAML y persistencia de valores. |
| `custom_types.py` | Tipos auxiliares compartidos. |
| `html.py` | Formateo seguro o conveniente de fragmentos HTML mostrados en la UI. |
| `internet.py` | Comprobación de conectividad y soporte para modo offline. |
| `regex.py` | Expresiones regulares reutilizables, incluida la detección de URLs. |
| `resource.py` | Resolución de recursos comunes del paquete. |
| `singleton.py` | Implementación/utilidad de objetos singleton. |
| `suggestions.py` | Lectura y tratamiento común de sugerencias de software. |
| `system.py` | Ejecución de procesos (`SimpleProcess`, contraseña por `stdin`), consultas dependientes del sistema. |
| `util.py` | Funciones generales: procesos, archivos, comandos y transformación de datos. |
| `version_util.py` | Comparación y normalización de versiones. |
| `view_utils.py` | Ayudas compartidas para preparar datos de la vista. |

### 4.4 Lógica central de la aplicación: `bauh/view/core/`

| Archivo | Responsabilidad |
|---|---|
| `config.py` | Configuración YAML global, valores por defecto y opciones de UI, tema, descargas, backup y gems. |
| `controller.py` | `GenericSoftwareManager`; agrega gestores y coordina búsquedas, paquetes instalados, acciones, actualizaciones, cachés y Timeshift. |
| `downloader.py` | Descargador adaptable basado en HTTP, con opciones de SSL y multihilo. |
| `gems.py` | Descubrimiento dinámico, carga, activación (opt-in / `is_default_enabled`) y traducción de gestores. |
| `settings.py` | Coordinación de vistas/controladores de ajustes de los gestores y de la aplicación (incluida la pestaña Personalización). |
| `suggestions.py` | Carga del mapa de sugerencias y aplicación de recomendaciones. |
| `timeshift.py` | Integración con Timeshift para copias de seguridad (heredado del upstream). |
| `tray_client.py` | Comunicación/notificaciones dirigidas a la bandeja del sistema. |
| `update.py` | Comprobación de nuevas versiones del fork (releases de `The-Gekko/Bauh-Fork-The-Gekko`). |

### 4.5 Utilidades de la vista: `bauh/view/util/`

| Archivo | Responsabilidad |
|---|---|
| `cache.py` | Caché en memoria con expiración, incluyendo caché de iconos. |
| `disk.py` | Lectura y escritura asíncrona de caché persistente. |
| `logs.py` | Creación y configuración de loggers y archivos de log. |
| `resource.py` | Obtención de rutas para iconos, locales y recursos de cada tema. |
| `translation.py` | Carga de locales y clase `I18n` para resolver textos traducidos. |
| `util.py` | Utilidades de UI, distribución, iconos, limpieza de archivos (`--reset`) y reinicio. |

### 4.6 Interfaz Qt: `bauh/view/qt/`

| Archivo o directorio | Responsabilidad |
|---|---|
| `root.py` | `RootDialog`: petición modal de contraseña de administrador. |
| `view_index.py` | Índices de paquetes mostrados para búsquedas y actualizaciones eficientes. |
| `view_model.py` | Adaptación de `SoftwarePackage` al modelo observable de la UI. |
| `apps_table.py` | Tabla de paquetes, columnas, selección y control de actualizaciones (repintado suspendido durante el relleno). |
| `commons.py` | Filtros, cálculos y utilidades específicas de la vista. |
| `dialog.py` | Diálogos genéricos de confirmación, errores y mensajes. |
| `info.py` | Ventana de información detallada de un paquete. |
| `history.py` | Ventana para mostrar historial de versiones/commits. |
| `about.py` | Diálogo «Acerca de»: nombre visible, versión, enlaces al fork y al proyecto original. |
| `prepare.py` | Panel de inicialización y preparación de gestores/datos. |
| `settings.py` | Ventana de configuración (tipos de aplicaciones, interfaz, personalización, gems). |
| `screenshots.py` | Descarga y visualización de capturas de pantalla. |
| `systray.py` | Icono, menú y acciones de la bandeja. |
| `qt_utils.py` | Utilidades geométricas y auxiliares de Qt. |
| `thread.py` | **Único módulo de hilos**: trabajos Qt (`QThread`) y señales para búsqueda, información, instalación, eliminación, actualización, acciones personalizadas y utilidades. Sus nombres exportados son un contrato público. |
| `components/builder.py` | Constructores de widgets y layouts. |
| `components/buttons.py` | Botones e iconos interactivos. |
| `components/inputs.py` | Barras de búsqueda y entradas. |
| `components/layout.py` | Helpers de distribución/layout. |
| `components/manager.py` | Registro y administración de componentes Qt. |
| `components/selects.py` | Combos, selectores y controles de selección. |
| `window/manage_window.py` | Ventana principal: búsqueda, filtros, tabla, acciones, actualización, botón Matugen, bloqueo de cierre en transacciones. |
| `window/constants.py` | Identificadores y constantes de componentes de la ventana. |
| `window/mixins/actions.py` | Acciones de instalación, eliminación, actualización, ejecución y diálogos. |
| `window/mixins/filters.py` | Lógica de filtrado por tipo, categoría, nombre, estado y verificación. |
| `window/mixins/ui.py` | Construcción y actualización visual de la ventana principal. |

Los antiguos `bauh/view/qt/window.py`, `bauh/view/qt/components.py` y el
paquete `bauh/view/qt/threads/` se eliminaron: eran restos de la refactorización
y su contenido vive en `window/`, `components/` y `thread.py`. Si un merge del
upstream los reintroduce, se acepta el borrado y se porta el cambio (ver
`docs/SINCRONIZACION_UPSTREAM.md`).

### 4.7 Gestores de software: `bauh/gems/`

Todos los gestores siguen aproximadamente el patrón `config.py` + `model.py` +
`controller.py` + módulos auxiliares + `resources/`. `model.py` representa los
paquetes de esa tecnología; `controller.py` implementa `SoftwareManager`; los
restantes encapsulan consultas, comandos, workers, configuración o UI propia.

| Gem | Activa por defecto | Archivos principales y función |
|---|---|---|
| `arch/` | Sí (si hay `pacman`) | `controller.py` integra el gestor (búsqueda con deduplicación repositorio/AUR, acción «Cambiar al binario del repositorio»); `pacman.py` ejecuta operaciones de Pacman con listas de argumentos (`get_databases` reconoce repositorios con guion); `aur.py` consulta AUR; `makepkg.py`, `pkgbuild.py`, `git.py` y `gpg.py` soportan compilación/verificación; `dependencies.py`, `updates.py`, `rebuild_detector.py` y `sorting.py` resuelven dependencias, actualizaciones y orden; `database.py`, `mapper.py` y `model.py` representan datos; `config.py`, `confirmation.py`, `message.py`, `output.py`, `worker.py`, `download.py`, `disk.py`, `mirrors.py`, `cpu_manager.py`, `proc_util.py`, `sshell.py` y `exceptions.py` completan configuración, procesos, descarga, salida y errores; `suggestions.py` aporta recomendaciones. |
| `eopkg/` | Sí (si hay `eopkg`) | Propia del fork. `controller.py` adapta Solus/eopkg (búsqueda, instalados con versión, `list-upgrades`, instalar/eliminar/actualizar con `-y`; `-N` solo desactiva el color); `model.py` representa paquetes; `config.py` (`search_limit`). |
| `github/` | No (opt-in) | Propia del fork. `controller.py` clona repositorios en `repos_dir` (`~/BauhRepos`), detecta el método de build con `build_detector.py`, muestra el comando, pide confirmación y separa compilación (usuario) de instalación (root); `model.py` representa proyectos; `config.py` (`repos_dir`, `clone_only`). |
| `appimage/` | No (opt-in) | `controller.py`, `query.py`, `util.py`, `worker.py`: ciclo de vida de AppImages desde la base de datos del upstream. |
| `debian/` | No (opt-in) | `controller.py`, `aptitude.py`, `index.py`, `tasks.py`, `gui.py`: APT/aptitude. |
| `flatpak/` | Sí (si hay `flatpak`) | Dentro del alcance del fork. `controller.py`, `flatpak.py`, `worker.py`, `constants.py`. |
| `snap/` | No (opt-in) | `controller.py`, `snap.py`, `snapd.py`. |
| `web/` | No (opt-in) | `controller.py`, `search.py`, `nativefier.py`, `environment.py`, `worker.py`: aplicaciones web empaquetadas con nativefier. |

Cada gem tiene `resources/locale/` (traducciones) y, cuando aplica,
`resources/img/`. Las gems `eopkg` y `github` disponen por ahora de `en` y
`es`; el resto de `ca`, `de`, `en`, `es`, `fr`, `it`, `pt`, `ru`, `tr` y `zh`.

### 4.8 Recursos

| Ruta | Contenido |
|---|---|
| `bauh/view/resources/locale/` | Traducciones de la interfaz común (`about/` y `tray/` como subcarpetas). |
| `bauh/view/resources/img/` | Iconos e imágenes generales (incluye `gekko-bauh.png`). |
| `bauh/view/resources/style/` | Temas Qt/QSS (`.qss`, `.vars`, `.meta`, `img/`). |
| `bauh/gems/*/resources/locale/` | Traducciones específicas de cada gem. |
| `bauh/gems/*/resources/img/` | Iconos y recursos gráficos específicos de cada formato. |
| `bauh/desktop/` | `bauh.desktop` y `bauh_tray.desktop` con traducciones y `StartupWMClass=bauh`. |
| `pictures/` | `gekko-bauh.png` (arte del fork) e `icons/gekko-bauh-<N>.png` con N en 16, 32, 48, 64, 128, 256 y 512, usados por `install.sh`. |

Los archivos `.qss` definen estilos Qt, los `.vars` contienen variables de
tema, los `.meta` describen temas y los `.svg`/otros formatos son recursos
gráficos. No contienen lógica de negocio.

## 5. Pruebas

La suite usa `unittest` (sin pytest) y se ejecuta desde la raíz:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests
```

Los tests que necesitan Qt se saltan solos si PyQt5 no está instalado
(`@unittest.skipUnless(importlib.util.find_spec('PyQt5') is not None, ...)`).
La CI los ejecuta en Python 3.9, 3.12 y 3.14 junto con `ruff`, `shellcheck`,
`python -m build` y `tools/check_locales.py`.

La carpeta `tests/` está organizada de forma paralela a la implementación:

| Ruta | Cobertura observada |
|---|---|
| `tests/api/abstract/` | Modelos y contratos abstractos (`test_model.py`). |
| `tests/common/` y `tests/commons/` | Utilidades, versiones, sistema y helpers de vista. |
| `tests/gems/appimage/` | Utilidades de AppImage. |
| `tests/gems/arch/` | AUR, Pacman, ordenación, actualizaciones y mapeo de datos. |
| `tests/gems/debian/` | APT, índice y controlador Debian. |
| `tests/gems/flatpak/` | Controlador, worker y operaciones Flatpak. |
| `tests/gems/web/` | Controlador Web. |
| `tests/view/core/` | Configuración (`test_config.py`: `custom_theme` y migración), carga de gems (`test_gems.py`) y procesamiento de temas (`test_stylesheet.py`). |
| `tests/view/qt/` | `ManageWindow` y `view_model` (requieren PyQt5 y `QT_QPA_PLATFORM=offscreen`). |

Los cambios funcionales de cada frente (gems opt-in, `get_databases`,
deduplicación, `RootDialog`, hilos, seguridad de procesos, instalador) añaden
sus propios tests junto al módulo que cubren. Los nombres disponibles indican
cobertura de lógica central y de varios gestores, aunque no todos los módulos
tienen un archivo de prueba dedicado.

## 6. Empaquetado, instalación y ejecución

### Dependencias declaradas

`requirements.txt` declara `PyQt5`, `requests`, `colorama`, `PyYAML` y
`python-dateutil`. `requirements-dev.txt` añade las herramientas de desarrollo
(`ruff`, `build`, `twine`, `lxml`, `beautifulsoup4`).

### Metadatos y comandos

`pyproject.toml` contiene la sección `[project]` (nombre `bauh-gekko`, versión
leída de `bauh/__init__.py`, `requires-python`, dependencias, clasificadores,
URLs del fork y del upstream, licencia zlib/libpng) y registra los comandos:

```text
bauh      -> bauh.app:main
bauh-tray -> bauh.app:tray
bauh-cli  -> bauh.cli.app:main
```

`setup.py` es un shim de compatibilidad. La versión sigue el esquema
`<versión upstream>+gekko.N` y la etiqueta git `v<versión upstream>-gekko.N`
(ver `docs/SINCRONIZACION_UPSTREAM.md`).

### `install.sh`

Instalador y desinstalador en bash pensado para `curl ... | bash`:

- Comprueba `curl`, la versión de Python (`PYTHON_BIN`) y `pipx` (lo instala
  con el gestor del sistema solo con `--install-pipx`).
- Resuelve el commit exacto de `master`, descarga ese commit y lo instala con
  `pipx install --python ... --force` en el entorno `bauh-gekko`; guarda el
  commit en `.gekko-source-ref` dentro del entorno para saltarse
  reconstrucciones innecesarias (`--force` las obliga). Migra el entorno
  `bauh` de versiones anteriores del fork.
- Detecta el paquete `bauh` del sistema y solo lo desinstala con
  `--remove-system-bauh`. `--yes` responde a las preguntas sin `sudo`.
- Instala `pictures/icons/gekko-bauh-<N>.png` en `hicolor` y un `.desktop`
  traducido con `StartupWMClass=bauh`; refresca las cachés del escritorio.
- `uninstall` elimina el entorno, el `.desktop` y los iconos;
  `uninstall --purge` borra además `~/.config/bauh`, `~/.cache/bauh`,
  `~/.local/share/bauh` y el directorio temporal, y ofrece restablecer
  `ui.theme` para volver al bauh oficial.

### Ejemplos de uso

```bash
bauh --logs
bauh --offline
bauh --settings
bauh --reset          # borra configuración, caché y temporales
bauh-cli updates
bauh-cli updates --format json
```

La forma recomendada de instalación, los requisitos y las limitaciones
conocidas (Wayland/xdg-shell, Python 3.8) están descritos en `README.md`; la
convivencia con el bauh oficial en `docs/MIGRACION.md`.

## 7. Consideraciones de mantenimiento

- Para añadir un nuevo backend, lo normal es crear un subdirectorio bajo
  `bauh/gems/`, implementar un `SoftwareManager` en `controller.py`, sus
  modelos y recursos, decidir `is_default_enabled()` (opt-in salvo que la gem
  sea segura y universal) y dejar que `gems.load_managers()` lo descubra.
- La comunicación entre backend y UI debe realizarse mediante los contratos de
  `bauh/api/abstract/`; así se evita acoplar un gestor a widgets Qt concretos.
- Las operaciones potencialmente lentas deben mantenerse en los hilos de
  `bauh/view/qt/thread.py` y reportar su estado mediante señales.
- Los cambios de textos deben incluir las traducciones comunes y, cuando
  corresponda, las de cada gem (`en` y `es` como mínimo; `CONTRIBUTING.md`
  enumera las rutas; `tools/check_locales.py` comprueba la paridad).
- Las acciones con privilegios usan `sudo -S -k` con la contraseña por
  `stdin`; los comandos externos se construyen como listas de argumentos.
- Mantén los contratos públicos: `SoftwareManager`, los nombres exportados por
  `bauh/view/qt/thread.py`, `set_theme(theme_key, app, logger, app_config=None)`,
  `RootDialog.ask_password(...)` con `parent` y
  `CoreConfigManager.get_config()/save_config()`.
- Sé conservador con el código heredado del upstream y sigue la política de
  `docs/SINCRONIZACION_UPSTREAM.md` para integrar sus cambios.

## 8. Observaciones del estado actual

- La aplicación conserva la base amplia de gestores del upstream, pero el
  producto se presenta para Arch/derivados y Solus; el resto de gems es opt-in.
- La CLI expone actualmente la consulta de actualizaciones; la mayoría de las
  operaciones de gestión están integradas en la GUI.
- La selección efectiva de gestores depende de `can_work()`,
  `is_default_enabled()`, la clave `gems` de la configuración, el archivo
  `/etc/bauh/gems.forbidden` y las herramientas instaladas.
- «Siempre al frente» del diálogo de contraseña no está garantizado en
  compositores Wayland que solo implementan `xdg-shell` (Hyprland, Niri);
  `README.md` documenta la limitación y una regla de ventana de ejemplo.
- Python 3.8 sigue declarado como mínimo pero está fuera de soporte; se
  mantiene «best effort» y la CI prueba 3.9, 3.12 y 3.14.
