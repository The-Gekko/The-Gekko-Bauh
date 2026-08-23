# Documentación técnica del proyecto

## 1. Resumen

`bauh` es una aplicación Python con interfaz gráfica Qt para buscar, instalar,
desinstalar, actualizar, ejecutar y administrar software Linux desde distintos
formatos y fuentes. El código utiliza una arquitectura de gestores de paquetes
intercambiables, llamados **gems**. Cada gem adapta una fuente o tecnología a
los contratos comunes definidos en `bauh/api/abstract/`.

La versión declarada en el código es `0.10.8`. El punto de entrada principal es
`bauh.app:main`; también existen una aplicación para la bandeja del sistema y
una interfaz de línea de comandos limitada a la consulta de actualizaciones.

El README describe este repositorio como un fork orientado especialmente a
Arch Linux y Chaotic AUR. Sin embargo, el árbol de código conserva gestores para
Arch/AUR, AppImage, Debian, eopkg, Flatpak, GitHub, Snap y aplicaciones Web.
La disponibilidad real de cada gestor depende de la distribución, comandos,
servicios y configuración presentes en el sistema anfitrión.

## 2. Estructura general

```text
.
├── bauh/                       # Código fuente Python del paquete
│   ├── api/                    # Contratos, HTTP, rutas y usuario
│   ├── cli/                    # Entrada y comandos de consola
│   ├── commons/                # Utilidades compartidas
│   ├── gems/                   # Adaptadores de fuentes/formats de software
│   ├── view/                   # Configuración, lógica de aplicación y UI Qt
│   ├── app.py                  # Entrada GUI y bandeja
│   ├── app_args.py             # Argumentos de la GUI
│   ├── context.py              # Inicialización de QApplication, tema e i18n
│   ├── manage.py               # Ensamblaje del panel de administración
│   ├── stylesheet.py            # Lectura y procesamiento de temas
│   └── tray.py                  # Integración de la bandeja del sistema
├── tests/                      # Pruebas unitarias y de componentes
├── linux_dist/                 # Material específico para distribución
├── .github/                    # Plantillas de GitHub
├── build/                      # Salida generada de construcción; no es fuente
├── bauh.egg-info/              # Metadatos generados por setuptools
├── install.sh                  # Instalador automatizado
├── requirements.txt            # Dependencias de ejecución
├── setup.py                    # Configuración de setuptools y entry points
├── setup.cfg                   # Metadatos adicionales del paquete
├── pyproject.toml              # Backend de construcción PEP 517/518
├── MANIFEST.in                 # Archivos incluidos en la distribución
├── README.md                   # Presentación, instalación y características
├── CONTRIBUTING.md             # Reglas para contribuir
├── CHANGELOG.md                # Historial de cambios
├── CREDITS.md                  # Créditos y procedencia
└── LICENSE                     # Licencia zlib/libpng
```

Los directorios `__pycache__/`, `build/` y `bauh.egg-info/` son generados o
auxiliares. La implementación que debe modificarse está en `bauh/` y las
pruebas en `tests/`.

### Archivos de soporte en la raíz

| Archivo | Responsabilidad |
|---|---|
| `README.md` | Presenta el proyecto, requisitos, características, instalación y limitaciones del fork. |
| `CONTRIBUTING.md` | Define cómo reportar errores, proponer cambios, mantener estilo y añadir traducciones. |
| `CHANGELOG.md` | Registra características, mejoras, correcciones y cambios de distribución por versión. |
| `CREDITS.md` | Documenta autores, procedencia y atribuciones. |
| `LICENSE` | Contiene los términos de la licencia zlib/libpng. |
| `install.sh` | Automatiza la instalación indicada por el proyecto. |
| `requirements.txt` | Lista las dependencias Python de ejecución. |
| `setup.py` | Configura setuptools, metadatos, paquetes, datos incluidos y comandos instalables. |
| `setup.cfg` | Añade metadatos de setuptools, actualmente la ruta de descripción. |
| `pyproject.toml` | Declara el sistema moderno de construcción basado en setuptools. |
| `MANIFEST.in` | Controla archivos adicionales incluidos en los paquetes fuente. |

## 3. Arquitectura y flujo de ejecución

### 3.1 Inicio de la aplicación gráfica

1. El entry point `bauh` invoca `bauh.app:main`.
2. `bauh/app.py` instala un manejador de mensajes Qt, habilita `faulthandler`,
   prepara variables de entorno para Qt/Wayland, lee argumentos y carga la
   configuración global mediante `CoreConfigManager`.
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
ventana. `bauh/cli/cli_args.py` actualmente define el subcomando `updates` y
su formato `text` o `json`. `CLIManager.list_updates()` consulta al gestor
genérico y muestra las actualizaciones disponibles.

### 3.3 Descubrimiento de gestores

`bauh/view/core/gems.py` recorre subdirectorios de `bauh/gems/`, importa el
`controller.py` de cada uno y busca una clase que herede directamente de
`SoftwareManager`. Los gestores pueden desactivarse mediante la configuración
`gems` o mediante `/etc/bauh/gems.forbidden`. Al cargarlos también se incorporan
sus traducciones.

Cada gestor informa qué tipos de paquete administra y si puede trabajar en el
sistema actual. `GenericSoftwareManager` crea un mapa tipo -> gestor y delega
en él operaciones como búsqueda, lectura de instalados, instalación,
desinstalación, actualización, downgrade, historial e información.

### 3.4 Modelo y vista

Los gestores producen objetos derivados de `SoftwarePackage` y resultados
`SearchResult`. La capa Qt los transforma en `PackageView`, los muestra en
`PackagesTable` y ejecuta las operaciones mediante clases de trabajo/hilos.
Los contratos de `api.abstract` mantienen desacoplada la lógica de cada gestor
de la interfaz.

### 3.5 Configuración, caché e idioma

- `CoreConfigManager` usa YAML y crea una configuración por defecto con idioma,
  tema, descargas, cachés, sugerencias, copias de seguridad y opciones de UI.
- `ApplicationContext` transporta dependencias compartidas: HTTP, i18n,
  descargador, cachés, logger, distribución, conectividad y privilegios.
- `view/util/cache.py` mantiene cachés en memoria; `view/util/disk.py` carga
  datos persistidos de forma asíncrona.
- `view/util/translation.py` carga diccionarios de idioma desde los recursos
  comunes y desde cada gem.
- `stylesheet.py` y `context.py` cargan temas QSS predeterminados o temas del
  usuario. Entre los recursos del árbol aparecen `light`, `aurora`, `sublime`,
  `knight` y `default`.

## 4. Descripción de archivos y módulos

### 4.1 Raíz del paquete `bauh/`

| Archivo | Responsabilidad |
|---|---|
| `bauh/__init__.py` | Declara `__version__`, `__app_name__` y `ROOT_DIR`, usados por el empaquetado y la aplicación. |
| `bauh/app.py` | Entrada GUI; prepara Qt, argumentos, logging, escalado, modo offline, modo bandeja y ciclo de eventos. |
| `bauh/app_args.py` | Define `--logs`, `--offline`, `--suggestions`, `--tray`, `--settings` y `--reset`. |
| `bauh/context.py` | Crea `QApplication`, configura estilo/paleta, temas e internacionalización. |
| `bauh/manage.py` | Construye el contexto de la aplicación, carga gems, crea el gestor genérico y selecciona ventana de ajustes o panel principal. |
| `bauh/stylesheet.py` | Lee metadatos y archivos de temas, resuelve herencia/procesamiento y genera QSS. |
| `bauh/tray.py` | Punto de entrada y utilidades para crear la aplicación asociada a la bandeja. |

Los `__init__.py` restantes son marcadores de paquete y, cuando corresponde,
exponen nombres del subpaquete.

### 4.2 API común: `bauh/api/`

| Archivo | Responsabilidad |
|---|---|
| `api/exception.py` | Excepciones compartidas, incluida la ausencia de conexión. |
| `api/http.py` | Cliente HTTP común usado por gestores, descargas y consultas remotas. |
| `api/paths.py` | Rutas de configuración, caché, logs y otros directorios de usuario. |
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
| `system.py` | Consultas y operaciones dependientes del sistema operativo. |
| `util.py` | Funciones generales: procesos, archivos, comandos y transformación de datos. |
| `version_util.py` | Comparación y normalización de versiones. |
| `view_utils.py` | Ayudas compartidas para preparar datos de la vista. |

### 4.4 Lógica central de la aplicación: `bauh/view/core/`

| Archivo | Responsabilidad |
|---|---|
| `config.py` | Configuración YAML global, valores por defecto y opciones de UI, descargas, backup y gems. |
| `controller.py` | `GenericSoftwareManager`; agrega gestores y coordina búsquedas, paquetes instalados, acciones, actualizaciones, cachés y Timeshift. |
| `downloader.py` | Descargador adaptable basado en HTTP, con opciones de SSL y multihilo. |
| `gems.py` | Descubrimiento dinámico, carga, activación y traducción de gestores. |
| `settings.py` | Coordinación de vistas/controladores de ajustes de los gestores y de la aplicación. |
| `suggestions.py` | Carga del mapa de sugerencias y aplicación de recomendaciones. |
| `timeshift.py` | Integración con Timeshift para copias de seguridad o acciones relacionadas. |
| `tray_client.py` | Comunicación/notificaciones dirigidas a la bandeja del sistema. |
| `update.py` | Comprobación de nuevas versiones o actualizaciones de la aplicación. |

### 4.5 Utilidades de la vista: `bauh/view/util/`

| Archivo | Responsabilidad |
|---|---|
| `cache.py` | Caché en memoria con expiración, incluyendo caché de iconos. |
| `disk.py` | Lectura y escritura asíncrona de caché persistente. |
| `logs.py` | Creación y configuración de loggers y archivos de log. |
| `resource.py` | Obtención de rutas para iconos, locales y recursos de cada tema. |
| `translation.py` | Carga de locales y clase `I18n` para resolver textos traducidos. |
| `util.py` | Utilidades de UI, distribución, iconos, limpieza de archivos y reinicio. |

### 4.6 Interfaz Qt: `bauh/view/qt/`

| Archivo o directorio | Responsabilidad |
|---|---|
| `root.py` | Diálogos raíz y componentes base de ventanas. |
| `view_index.py` | Índices de paquetes mostrados para búsquedas y actualizaciones eficientes. |
| `view_model.py` | Adaptación de `SoftwarePackage` al modelo observable de la UI. |
| `apps_table.py` | Tabla de paquetes, columnas, selección y control de actualizaciones. |
| `components.py` | Componentes Qt reutilizables de alto nivel. |
| `commons.py` | Filtros, cálculos y utilidades específicas de la vista. |
| `dialog.py` | Diálogos genéricos de confirmación, errores y mensajes. |
| `info.py` | Ventana de información detallada de un paquete. |
| `history.py` | Ventana para mostrar historial de versiones/commits. |
| `about.py` | Diálogo de información de la aplicación. |
| `prepare.py` | Panel de inicialización y preparación de gestores/datos. |
| `settings.py` | Ventana de configuración. |
| `screenshots.py` | Descarga y visualización de capturas de pantalla. |
| `systray.py` | Icono, menú y acciones de la bandeja. |
| `qt_utils.py` | Utilidades geométricas y auxiliares de Qt. |
| `thread.py` | Clases de trabajos Qt y señales para acciones asíncronas. |
| `threads/base.py` | Base común para trabajos/hilos Qt. |
| `threads/info.py` | Trabajos asíncronos de carga de información. |
| `threads/management.py` | Trabajos de instalación, eliminación, actualización y acciones de gestión. |
| `threads/search.py` | Trabajos de búsqueda y carga de resultados. |
| `threads/util.py` | Funciones auxiliares para hilos y señales. |
| `window.py` | Módulo Qt de compatibilidad y componentes de ventana de nivel superior. |
| `components/builder.py` | Constructores de widgets y layouts. |
| `components/buttons.py` | Botones e iconos interactivos. |
| `components/inputs.py` | Barras de búsqueda y entradas. |
| `components/layout.py` | Helpers de distribución/layout. |
| `components/manager.py` | Registro y administración de componentes Qt. |
| `components/selects.py` | Combos, selectores y controles de selección. |
| `window/manage_window.py` | Ventana principal: búsqueda, filtros, tabla, acciones, actualización y señales. |
| `window/constants.py` | Identificadores y constantes de componentes de la ventana. |
| `window/mixins/actions.py` | Acciones de instalación, eliminación, actualización, ejecución y diálogos. |
| `window/mixins/filters.py` | Lógica de filtrado por tipo, categoría, nombre, estado y verificación. |
| `window/mixins/ui.py` | Construcción y actualización visual de la ventana principal. |

### 4.7 Gestores de software: `bauh/gems/`

Todos los gestores siguen aproximadamente el patrón `config.py` + `model.py` +
`controller.py` + módulos auxiliares + `resources/`. `model.py` representa los
paquetes de esa tecnología; `controller.py` implementa `SoftwareManager`; los
restantes encapsulan consultas, comandos, workers, configuración o UI propia.

| Gem | Archivos principales y función |
|---|---|
| `appimage/` | `config.py` define opciones; `model.py` representa AppImages; `controller.py` gestiona el ciclo de vida; `query.py` consulta el catálogo; `util.py` manipula archivos/metadata; `worker.py` ejecuta tareas de búsqueda y actualización; `resources/` contiene iconos y locales. |
| `arch/` | `controller.py` integra el gestor; `pacman.py` ejecuta operaciones de Pacman; `aur.py` consulta AUR; `makepkg.py`, `pkgbuild.py`, `git.py` y `gpg.py` soportan compilación/verificación; `dependencies.py`, `updates.py`, `rebuild_detector.py` y `sorting.py` resuelven dependencias, actualizaciones y orden; `database.py`, `mapper.py` y `model.py` representan datos; `config.py`, `confirmation.py`, `message.py`, `output.py`, `worker.py`, `download.py`, `disk.py`, `mirrors.py`, `cpu_manager.py`, `proc_util.py`, `sshell.py` y `exceptions.py` completan configuración, procesos, descarga, salida y errores; `suggestions.py` aporta recomendaciones; `resources/` contiene locales/iconos. |
| `debian/` | `controller.py` adapta APT; `aptitude.py` ejecuta consultas/operaciones; `index.py` indexa paquetes; `common.py`, `config.py`, `model.py`, `tasks.py`, `suggestions.py` y `gui.py` aportan datos, configuración, tareas, sugerencias y vistas auxiliares; `resources/` contiene recursos. |
| `eopkg/` | `controller.py` adapta Solus/eopkg; `model.py` representa paquetes; `config.py` contiene configuración; `resources/` contiene recursos. |
| `flatpak/` | `controller.py` implementa el gestor; `flatpak.py` encapsula comandos/consultas de Flatpak; `worker.py` ejecuta tareas; `model.py`, `config.py` y `constants.py` definen datos, opciones y constantes; `resources/` contiene recursos. |
| `github/` | `controller.py` integra repositorios de GitHub como fuente; `model.py` representa proyectos; `build_detector.py` detecta necesidades de construcción; `config.py` y `resources/` completan opciones y recursos. |
| `snap/` | `controller.py` implementa gestión Snap; `snap.py` encapsula operaciones; `snapd.py` trata la comunicación/servicio snapd; `model.py`, `config.py` y `resources/` definen datos, configuración y recursos. |
| `web/` | `controller.py` gestiona aplicaciones web; `search.py` busca o interpreta URLs; `nativefier.py` genera aplicaciones empaquetadas; `environment.py` prepara el entorno; `worker.py` ejecuta tareas; `model.py`, `config.py`, `suggestions.py` y `resources/` completan el gestor. |

### 4.8 Recursos

| Ruta | Contenido |
|---|---|
| `bauh/view/resources/locale/` | Traducciones de la interfaz común. |
| `bauh/view/resources/img/` | Iconos e imágenes generales. |
| `bauh/view/resources/style/` | Temas Qt/QSS, variables, metadatos e imágenes asociadas. |
| `bauh/gems/*/resources/locale/` | Traducciones específicas de cada gem. |
| `bauh/gems/*/resources/img/` | Iconos y recursos gráficos específicos de cada formato. |
| `bauh/desktop/` o archivos equivalentes incluidos en la distribución | Archivos `.desktop` para registrar la aplicación y la bandeja. En el árbol fuente actual los artefactos visibles están bajo `build/lib/bauh/desktop/`. |

Los archivos `.qss` definen estilos Qt, los `.vars` contienen variables de
tema, los `.meta` describen temas y los `.svg`/otros formatos son recursos
gráficos. No contienen lógica de negocio.

## 5. Pruebas

La carpeta `tests/` está organizada de forma paralela a la implementación:

| Ruta | Cobertura observada |
|---|---|
| `tests/api/abstract/` | Modelos y contratos abstractos. |
| `tests/common/` y `tests/commons/` | Utilidades, versiones, sistema y helpers de vista. |
| `tests/gems/appimage/` | Utilidades de AppImage. |
| `tests/gems/arch/` | AUR, Pacman, ordenación, actualizaciones y mapeo de datos. |
| `tests/gems/debian/` | APT, índice y controlador Debian. |
| `tests/gems/flatpak/` | Controlador, worker y operaciones Flatpak. |
| `tests/gems/web/` | Controlador Web. |
| `tests/view/core/` | Procesamiento de estilos. |
| `tests/view/qt/` | `ManageWindow` y `view_model`. |

Los nombres disponibles indican cobertura de lógica central y de varios
gestores, aunque no todos los módulos tienen un archivo de prueba dedicado.

Los `__init__.py` presentes en `bauh/`, `api/`, `cli/`, `commons/`, `gems/`,
`view/` y sus subdirectorios permiten que Python trate esas carpetas como
paquetes; no representan un flujo de negocio independiente salvo el
`bauh/__init__.py` descrito anteriormente.

## 6. Empaquetado y ejecución

### Dependencias declaradas

`requirements.txt` declara:

- `PyQt5` para la interfaz.
- `requests` para HTTP y descargas.
- `colorama` para salida coloreada de consola.
- `PyYAML` para configuración y datos YAML.
- `python-dateutil` para fechas.

`setup.py` requiere Python `>=3.8`, descubre paquetes con setuptools y registra
los siguientes comandos:

```text
bauh      -> bauh.app:main
bauh-tray -> bauh.app:tray
bauh-cli  -> bauh.cli.app:main
```

`BAUH_SETUP_NO_REQS` permite construir sin leer dependencias desde
`requirements.txt`. `pyproject.toml` usa `setuptools.build_meta` y requiere
`setuptools>=42` y `wheel` para la construcción.

### Ejemplos de uso

```bash
bauh --logs
bauh --offline
bauh --settings
bauh --reset
bauh-cli updates
bauh-cli updates --format json
```

La forma recomendada de instalación y los requisitos específicos de Arch están
descritos en `README.md`. En particular, el README indica que el fork espera
Chaotic AUR habilitado para el escenario Arch previsto.

## 7. Consideraciones de mantenimiento

- Para añadir un nuevo backend, lo normal es crear un subdirectorio bajo
  `bauh/gems/`, implementar un `SoftwareManager` en `controller.py`, sus
  modelos y recursos, y dejar que `gems.load_managers()` lo descubra.
- La comunicación entre backend y UI debe realizarse mediante los contratos de
  `bauh/api/abstract/`; así se evita acoplar un gestor a widgets Qt concretos.
- Las operaciones potencialmente lentas deben mantenerse en workers/hilos y
  reportar su estado mediante los mecanismos de `bauh/view/qt/threads/`.
- Los cambios de textos deben incluir las traducciones comunes y, cuando
  corresponda, las de cada gem. `CONTRIBUTING.md` enumera las rutas de locales.
- `build/`, `bauh.egg-info/` y `__pycache__/` deben considerarse salidas
  generadas y no la fuente canónica para realizar cambios.

## 8. Observaciones del estado actual

- La aplicación conserva una base amplia de gestores multiplataforma, aunque
  la documentación de producto del README enfatiza Arch Linux.
- La CLI expone actualmente la consulta de actualizaciones; la mayoría de las
  operaciones de gestión están integradas en la GUI.
- La selección efectiva de gestores depende de `can_work()`, la configuración
  `gems`, el archivo `/etc/bauh/gems.forbidden` y las herramientas instaladas.
- La versión del código (`0.10.8`) coincide con la versión destacada en el
  README.
