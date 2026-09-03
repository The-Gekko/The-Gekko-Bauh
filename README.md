<div align="center">

# 🦎 bauh Gekko Edition

### Gestor gráfico de aplicaciones para Arch Linux (pacman + AUR + Chaotic AUR), Flatpak y Solus (eopkg)

<p align="center">
  <a href="https://github.com/The-Gekko/Bauh-Fork-The-Gekko/releases"><img src="https://img.shields.io/github/v/tag/The-Gekko/Bauh-Fork-The-Gekko?label=Versi%C3%B3n&sort=semver" alt="Versión"></a>
  <a href="https://github.com/The-Gekko/Bauh-Fork-The-Gekko/actions"><img src="https://img.shields.io/badge/CI-GitHub%20Actions-blue" alt="CI"></a>
  <a href="https://github.com/The-Gekko/Bauh-Fork-The-Gekko/blob/master/LICENSE"><img src="https://img.shields.io/github/license/The-Gekko/Bauh-Fork-The-Gekko?label=Licencia" alt="Licencia"></a>
</p>

<img src="pictures/gekko-bauh.png" width="320" alt="bauh Gekko Edition" style="border-radius: 24px;"/>

</div>

---

> **Proyecto independiente derivado de bauh.** `gekko-bauh` nació como fork de
> [`vinifmor/bauh`](https://github.com/vinifmor/bauh), creado por **Vinicius Moreira**,
> y hoy se desarrolla por separado con su propio rumbo, sus propias versiones y su
> propia identidad en el sistema. Es una **versión alterada** del software original
> en el sentido de la licencia zlib: no es bauh, no está respaldada por su autor y
> sus errores se reportan
> [aquí](https://github.com/The-Gekko/Bauh-Fork-The-Gekko/issues), nunca en el
> proyecto original. La mayor parte del código sigue siendo obra suya y de sus
> colaboradores: el crédito completo está en [CREDITS.md](CREDITS.md).
>
> Se instala como `gekko-bauh`, guarda su configuración en `~/.config/gekko-bauh` y
> convive sin interferir con una instalación del bauh oficial. Versión actual:
> `0.10.8+gekko.1` (etiqueta `v0.10.8-gekko.1`), construida sobre la rama `staging`
> del proyecto original. Detalles en [CHANGELOG.md](CHANGELOG.md).

**gekko-bauh** (se pronuncia _gueko baoo_) es una interfaz gráfica en PyQt5 para
buscar, instalar, actualizar y desinstalar software en Linux. Su alcance son tres
plataformas: **Arch Linux y derivados** (pacman, AUR y cualquier repositorio
adicional de pacman, por ejemplo Chaotic AUR), **Flatpak** y **Solus (eopkg)**.
Las tres vienen activadas de fábrica. Los demás formatos heredados del proyecto
original (AppImage, Snap, Web, Debian) siguen incluidos, pero **desactivados por
defecto** y sin soporte activo: se activan en `Ajustes → Tipos de aplicaciones`.

## Índice

- [Qué aporta este proyecto](#qué-aporta-este-proyecto)
- [Heredado del proyecto original](#heredado-del-proyecto-original)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Actualización](#actualización)
- [Desinstalación](#desinstalación)
- [Migración desde y hacia el bauh oficial](#migración-desde-y-hacia-el-bauh-oficial)
- [Wayland, Hyprland y Niri](#wayland-hyprland-y-niri)
- [Temas](#temas)
- [Configuración](#configuración)
- [Cómo ejecutar los tests](#cómo-ejecutar-los-tests)
- [Sincronización con upstream](#sincronización-con-upstream)
- [Compatibilidad con Python](#compatibilidad-con-python)
- [Contribuir](#contribuir)
- [Créditos](#créditos)
- [Licencia](#licencia)

## Qué aporta este proyecto

Todo lo que sigue está en este repositorio y **no** en `vinifmor/bauh`. Cada
punto es comprobable en el código o en la propia interfaz.

### Interfaz y temas

- **Tema Aurora** (oscuro, tema por defecto) y dos temas dinámicos:
  **GTK 3/4**, que toma los colores de `~/.config/gtk-3.0/gtk.css` y
  `~/.config/gtk-4.0/gtk.css`, y **Matugen**, que lee
  `~/.cache/matugen/colors-gtk.css`. Ambos se recargan solos cuando esos
  archivos cambian: el vigilante de archivos solo se activa con esos dos temas
  y agrupa los cambios rápidos (debounce) para no repintar la ventana varias
  veces seguidas. Ver `Ajustes → Interfaz → Tema`.
- **Botón Matugen** en la barra superior de la ventana principal para aplicar
  el tema dinámico con un clic; su estado persiste entre sesiones.
- **Pestaña «Personalización»** en Ajustes (traducida) para color de fondo,
  texto, acento, opacidad e imagen de fondo (clave `custom_theme` de
  `~/.config/gekko-bauh/config.yml`).
- **Identidad propia**: la ventana se llama «bauh Gekko Edition», el diálogo
  «Acerca de» enlaza a este repositorio y al proyecto original, y el aviso de nueva
  versión consulta las releases de este repositorio.
- **Diálogo de contraseña** (`RootDialog`) modal a nivel de aplicación, con
  campo enmascarado, foco automático y confirmación con `Enter`. Se abre sobre
  la ventana que lo pidió. Lo que **no** garantiza en Wayland se explica en
  [Wayland, Hyprland y Niri](#wayland-hyprland-y-niri).
- **Robustez**: la ventana no se puede cerrar mientras hay una transacción en
  curso (instalación, actualización, desinstalación); `Ctrl+C` y `SIGTERM`
  cierran la aplicación de forma ordenada; las excepciones no controladas se
  registran en el log en lugar de matar el proceso en silencio.
- **Tabla de paquetes sin parpadeo**: el repintado se suspende mientras se
  rellena la tabla (`setUpdatesEnabled(False)`).

### Gestores de paquetes (gems)

- **Arch**:
  - `get_databases` reconoce repositorios con guion o guion bajo
    (`chaotic-aur`, `arcolinux_repo`, ...), que antes se ignoraban.
  - La búsqueda deduplica los resultados que aparecen a la vez en un
    repositorio de pacman y en AUR, prefiriendo el binario del repositorio.
  - Los paquetes AUR ya instalados que existen en un repositorio habilitado
    muestran ese repositorio en la tabla y ofrecen la acción **«Cambiar al
    binario del repositorio»**, que reemplaza la copia compilada por el
    paquete precompilado. Funciona con cualquier repositorio de pacman; no es
    específico de Chaotic AUR.
- **eopkg (Solus)**: gem nueva. Se activa cuando existe el binario `eopkg`
  (no detecta «Solus» como tal). Lista los paquetes instalados con su versión
  real y detecta actualizaciones con `eopkg list-upgrades`.
- **GitHub**: gem nueva y **opt-in** para clonar un repositorio y compilarlo
  en tu equipo. Detecta el método de build (PKGBUILD, `setup.py`/`pyproject`,
  Cargo, ...), **muestra el comando exacto que va a ejecutar y pide
  confirmación** antes de lanzarlo, y separa la compilación (con tu usuario) de
  la instalación (con privilegios, solo si el método lo requiere). No existe
  ninguna «protección anti-scripts»: compilar código de terceros es tu
  responsabilidad. Los clones se guardan en `~/BauhRepos` (clave `repos_dir`
  de `~/.config/gekko-bauh/github.yml`).
- **Gems heredadas opt-in**: AppImage, Snap, Web y Debian vienen desactivadas
  y sin soporte activo. Se activan en `Ajustes → Tipos de aplicaciones` (o con
  la clave `gems` de `config.yml`). Arch, Flatpak y eopkg, que son el alcance
  del proyecto, siguen activadas por defecto.

### Seguridad

- La contraseña de administrador **nunca viaja como argumento** de un proceso:
  se entrega por `stdin` a `sudo -S -k` y se valida por el código de retorno,
  no analizando texto.
- Directorios temporales privados con permisos `0700` bajo `~/.cache/gekko-bauh/tmp`,
  comprobando dueño y que no sean un enlace simbólico
  (antes `/tmp/bauh@usuario`, una ruta predecible en un directorio compartido).
- Los comandos de pacman se construyen como listas de argumentos (sin pasar
  por un shell) y el saneado de la entrada del usuario se ha reforzado.

### Instalación y empaquetado

- **`install.sh`**: instalador y desinstalador por `curl` basado en `pipx`
  (ver [Instalación](#instalación)).
- **Identidad propia en el sistema**: distribución `gekko-bauh`, ejecutables
  `gekko-bauh`, `gekko-bauh-tray` y `gekko-bauh-cli`, configuración en
  `~/.config/gekko-bauh` y lanzador e icono propios. Nada de eso colisiona con
  una instalación del bauh oficial, y la primera ejecución copia los ajustes
  heredados de `~/.config/bauh` sin tocar el original. El paquete Python interno
  sigue llamándose `bauh` para poder integrar las correcciones del proyecto
  original. Versión PEP 440 `0.10.8+gekko.1`, `pyproject.toml` con la sección
  `[project]` completa.
- **CI en GitHub Actions**: la suite sin PyQt5 en Python 3.9, 3.12 y 3.14, y la
  suite completa con Qt offscreen en 3.12; `ruff`, `shellcheck` sobre
  `install.sh`, construcción del wheel y comprobación de paridad de
  traducciones (`tools/check_locales.py`).
- Compatibilidad con **Python 3.13 y 3.14**.
- Integrado el arreglo del upstream que fuerza `QT_QPA_PLATFORM=wayland` en
  sesiones Wayland (evitaba un cierre inesperado al arrancar en algunos
  equipos).

## Heredado del proyecto original

Estas funciones ya existían en `vinifmor/bauh`; aquí solo se mantienen y no
son mérito de este proyecto:

- Gestión completa de **pacman y AUR**: resolución de dependencias y
  conflictos, elección entre varios proveedores, actualización del sistema con
  un clic, downgrade, historial de versiones, limpieza de caché, `makepkg` con
  `MAKEFLAGS="-j$(nproc)"` (opción *optimizar compilación*).
- Integración con **`rebuild-detector`** para saber qué paquetes de AUR deben
  recompilarse tras actualizar una librería compartida.
- **Copias de seguridad con Timeshift** antes de actualizar.
- Lectura de instalados y búsquedas en paralelo, descargador propio en Python,
  filtro «verificado», icono de bandeja con aviso de actualizaciones y CLI
  `gekko-bauh-cli updates`.
- El gestor de **Flatpak** (búsqueda en Flathub, instalación por usuario o para
  todo el sistema, actualización de runtimes), que este proyecto mantiene dentro de su
  alcance.
- Los demás gestores, ya sin soporte activo: AppImage, Snap, Web (nativefier) y
  Debian.

## Requisitos

- **Distribución**: Arch Linux o derivado (Garuda, EndeavourOS, Manjaro,
  CachyOS, ...) con `pacman`; o Solus con `eopkg`. En otras distribuciones bauh
  arranca, pero solo con las gems cuyas herramientas encuentre instaladas.
- **Python** 3.9 a 3.14 (recomendado 3.12 o superior). Ver
  [Compatibilidad con Python](#compatibilidad-con-python).
- **pipx** (el instalador puede instalarlo por ti si le pasas
  `--install-pipx`).
- **Recomendado, no obligatorio**: un repositorio de binarios como
  [Chaotic AUR](https://aur.chaotic.cx/). Si está habilitado en
  `/etc/pacman.conf`, bauh lo trata como cualquier otro repositorio de pacman:
  prefiere su binario frente a AUR en las búsquedas y ofrece «Cambiar al
  binario del repositorio» para los paquetes que ya tengas compilados desde
  AUR. Sin él, todo funciona igual, compilando desde AUR.

## Instalación

### Por curl (recomendado)

```bash
curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash
```

Qué hace el instalador:

1. Comprueba `curl`, la versión de Python y `pipx`.
2. Resuelve el **commit exacto** de `master` en GitHub y descarga ese commit
   (no «lo que haya en master» en ese instante), de modo que la marca
   `.gekko-source-ref` que guarda dentro del entorno coincide siempre con el
   código instalado.
3. Instala el código en un entorno aislado de pipx llamado **`gekko-bauh`**,
   pasando `--python` con el intérprete elegido (`PYTHON_BIN`, por defecto
   `python3`). Si encuentra el entorno `bauh` de una versión anterior de este
   proyecto, lo **migra** a `gekko-bauh` y elimina el antiguo.
4. Instala el icono en los tamaños estándar de `hicolor` (16 a 512 px) y un
   `.desktop` con traducciones y `StartupWMClass=gekko-bauh` en
   `~/.local/share/applications/`, y refresca las cachés del escritorio.

Si detecta el bauh **oficial** instalado por pacman o eopkg, avisa del
conflicto pero **no lo desinstala** a menos que se lo pidas (ver flags).
Las preguntas se leen del terminal, así que funcionan aunque el script llegue
por tubería; sin terminal (CI, cron, systemd) la respuesta por defecto es «no».

| Opción | Efecto |
|---|---|
| `--force`, `-f` | Reconstruye el entorno pipx aunque ya esté instalado el mismo commit. |
| `--yes`, `-y` | Responde «sí» a las preguntas que **no** requieren `sudo`. No autoriza acciones con privilegios. |
| `--remove-system-bauh` | Autoriza desinstalar el paquete `bauh` de pacman/eopkg antes de instalar gekko-bauh. |
| `--install-pipx` | Autoriza instalar `pipx` con el gestor de paquetes del sistema si falta. |
| `PYTHON_BIN=/ruta/python3.x` | Intérprete que usará pipx para crear el entorno. |

Ejemplos:

```bash
# Reinstalar desde cero
curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- --force

# Automatizado y autorizando explícitamente las dos acciones con sudo
curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- --yes --install-pipx --remove-system-bauh
```

La lista completa y actualizada de opciones está en `install.sh --help`.

### Desde el AUR (Arch, Garuda, EndeavourOS…)

El proyecto se publica en el AUR como `gekko-bauh` (versión estable, construida
desde la etiqueta) y `gekko-bauh-git` (compila la rama `master`):

```bash
# con un ayudante del AUR
paru -S gekko-bauh      # o: yay -S gekko-bauh

# a mano
git clone https://aur.archlinux.org/gekko-bauh.git
cd gekko-bauh
makepkg -si
```

El paquete **convive con el `bauh` original**: los ejecutables (`gekko-bauh`,
`gekko-bauh-tray`, `gekko-bauh-cli`), el icono, los lanzadores y la
configuración (`~/.config/gekko-bauh`) llevan nombres propios, y el código se
instala en `/usr/share/gekko-bauh` en vez de en `site-packages`, así que pacman
no ve ni un fichero compartido. Puedes tener los dos a la vez.

Instala además lo que vayas a usar de sus dependencias opcionales: `flatpak`,
`git` y `base-devel` (gem de GitHub y compilación de paquetes del AUR),
`timeshift` (copias de seguridad), y `python-lxml` con `python-beautifulsoup4`
(gem web).

La receta vive en [`packaging/aur/`](packaging/aur) y el procedimiento de
publicación, en [`docs/DISTRIBUCION.md`](docs/DISTRIBUCION.md).

### Desde un checkout (contribuidores)

```bash
git clone https://github.com/The-Gekko/Bauh-Fork-The-Gekko.git
cd Bauh-Fork-The-Gekko
./install.sh          # detecta el checkout local y lo instala con pipx
```

### Manual con pipx o pip (avanzado)

```bash
pipx install --force "https://github.com/The-Gekko/Bauh-Fork-The-Gekko/archive/refs/heads/master.zip"
# o en un entorno virtual propio:
python3 -m venv bauh_env
bauh_env/bin/pip install "https://github.com/The-Gekko/Bauh-Fork-The-Gekko/archive/refs/heads/master.zip"
bauh_env/bin/bauh
```

> [!WARNING]
> `pip install bauh` o `pacman -S bauh` **no** instalan este proyecto: instalan el
> bauh original (PyPI / repositorios), sin el tema Aurora, las gems eopkg y
> GitHub, ni los cambios de la gem Arch.

### Desde GekkoApp

La opción *Tienda Bauh* de [GekkoApp](https://github.com/The-Gekko/GekkoApp)
ejecuta este mismo instalador.

## Actualización

Vuelve a ejecutar el comando de instalación. El instalador compara el commit
instalado (`.gekko-source-ref`) con el commit actual de `master` y solo
reconstruye el entorno si hay cambios; por eso actualizar es rápido y no
depende de que cambie el número de versión. Usa `--force` para reconstruir de
todos modos.

Desde la propia aplicación, el aviso de «nueva versión disponible» consulta
las releases de este repositorio.

### Verificar las descargas (SHA256)

Cada release publica un fichero `SHA256SUMS` con las sumas del wheel, del sdist
y del tarball de código fuente de esa etiqueta. Descárgalo junto a lo que te
lleves y comprueba antes de instalar:

```bash
sha256sum --check --ignore-missing SHA256SUMS
```

`--ignore-missing` hace que se comprueben solo los ficheros que hayas
descargado, sin fallar por los que no.

La instalación **por curl no usa ese fichero**: `install.sh` resuelve la
referencia que le pidas contra la API de GitHub, obtiene el SHA-1 del commit
exacto y descarga e instala ese commit, dejando la marca dentro del entorno de
pipx. La integridad viene ahí del identificador del commit y de HTTPS. Si
prefieres una comprobación explícita, instala desde el AUR (donde `makepkg`
valida la suma declarada en el PKGBUILD) o desde la release.

Los detalles están en
[`docs/DISTRIBUCION.md`](docs/DISTRIBUCION.md#6-verificar-las-sumas-antes-de-instalar).

## Desinstalación

```bash
curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- uninstall
```

Elimina el entorno pipx (`gekko-bauh`, y `bauh` si quedara de una versión
anterior), el `.desktop` y los iconos, y refresca las cachés del escritorio.
**No toca** tu configuración.

Para borrar **también** los datos de usuario:

```bash
curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- uninstall --purge
```

`--purge` elimina `~/.config/gekko-bauh`, `~/.cache/gekko-bauh`,
`~/.local/share/gekko-bauh` y el directorio temporal de la sesión, **conservando
`~/.local/share/gekko-bauh/github/repos`**, donde la gem GitHub clona tus
repositorios: pueden contener trabajo sin publicar, así que no se borran nunca
automáticamente (ni ese directorio ni el heredado `~/BauhRepos`).

Con `--purge` y sin él, el desinstalador **ofrece restablecer `ui.theme`** en
`~/.config/bauh/config.yml` si prefieres volver al bauh oficial, que no conoce
los temas Aurora, GTK ni Matugen y arrancaría sin hoja de estilos. Detalles en
[docs/MIGRACION.md](docs/MIGRACION.md).

## Migración desde y hacia el bauh oficial

Este proyecto y el bauh oficial **ya no comparten** configuración, caché ni
los datos de usuario. En resumen:

- **Venir del oficial**: ejecuta `install.sh`. La primera vez que abras
  `gekko-bauh`, tus ajustes y tus temas de usuario se **copian** de
  `~/.config/bauh` y `~/.local/share/bauh` a las rutas propias. El directorio
  original queda intacto, así que puedes seguir usando el bauh oficial en
  paralelo. Las gems AppImage/Snap/Web/Debian quedan desactivadas hasta que las
  marques en `Ajustes → Tipos de aplicaciones`.
- **Convivir con el oficial**: no hace falta desinstalarlo. Cada uno tiene su
  ejecutable, su lanzador, su icono y su configuración. Si aun así prefieres
  quitarlo, el instalador puede hacerlo con `--remove-system-bauh`.
- **Volver al oficial**: ejecuta `install.sh uninstall` (con `--purge` para
  borrar también los datos propios). El purgado **no toca** `~/.config/bauh`,
  que pertenece al oficial. Si vienes de una versión anterior de este proyecto,
  que sí escribía ahí, el desinstalador te ofrece devolver `ui.theme` a `light`:
  el oficial no conoce los temas Aurora, GTK ni Matugen y arrancaría sin hoja de
  estilos.

La guía completa, con la tabla de rutas y de claves de configuración que el
upstream no entiende, está en [docs/MIGRACION.md](docs/MIGRACION.md).

## Wayland, Hyprland y Niri

gekko-bauh funciona en sesiones Wayland (GNOME, KDE Plasma, Hyprland, Niri, Sway...)
y en X11. Al arrancar en una sesión Wayland fuerza `QT_QPA_PLATFORM=wayland`
(arreglo integrado desde el upstream).

**Limitación conocida**: el diálogo de contraseña pide al compositor quedarse
«siempre al frente» (`WindowStaysOnTopHint`) y recibir el foco
(`activateWindow`). En X11, GNOME y KDE eso funciona. En compositores que
implementan solo `xdg-shell` sin extensiones de gestión de ventanas (Hyprland,
Niri, Sway, river...) **el protocolo no permite** que una aplicación se ponga
por encima de las demás ni se dé el foco a sí misma: el diálogo puede abrirse
detrás de otra ventana o sin foco, y hay que traerlo con el atajo del
compositor. No es un fallo de la aplicación; se resuelve con una regla de ventana. El
diálogo se titula «Autenticación» (o su traducción) y la clase de la aplicación
es `gekko-bauh` (se declara con `setDesktopFileName`, así que coincide con el
`StartupWMClass` del lanzador):

```ini
# Hyprland (>= 0.50; en versiones anteriores sustituye "windowrule" por "windowrulev2")
windowrule = float, class:^(gekko-bauh)$, title:^(Autenticación|Authentication)$
windowrule = center, class:^(gekko-bauh)$, title:^(Autenticación|Authentication)$
windowrule = stayfocused, class:^(gekko-bauh)$, title:^(Autenticación|Authentication)$
```

```kdl
// Niri (~/.config/niri/config.kdl)
window-rule {
    match app-id="^gekko-bauh$" title="^(Autenticación|Authentication)$"
    open-floating true
    open-focused true
}
```

Comprueba la clase real que ve tu compositor con `hyprctl clients` o
`niri msg windows` mientras el diálogo está abierto; si no es `gekko-bauh`, abre
un issue indicando lo que aparece.

## Temas

Temas incluidos (`bauh/view/resources/style/`): `aurora` (por defecto),
`darcula`, `default`, `gtk`, `knight`, `light`, `matugen` y `sublime`. Los
temas `gtk` y `matugen` heredan de Aurora (`root_theme=aurora`) y sustituyen
sus colores por los del sistema. Puedes añadir temas propios en
`~/.local/share/gekko-bauh/themes/`; el formato (`.qss` + `.vars` + `.meta`) es el
del upstream.

## Configuración

| Ruta | Contenido |
|---|---|
| `~/.config/gekko-bauh/config.yml` | Configuración general: `gems` activas, `ui.theme`, `custom_theme`, actualizaciones, descargas, copias de seguridad. |
| `~/.config/gekko-bauh/<gem>.yml` | Configuración de cada gem (`arch.yml`, `eopkg.yml`, `github.yml`, ...). |
| `~/.cache/gekko-bauh/` | Caché de paquetes, iconos y sugerencias. |
| `~/.local/share/gekko-bauh/` | Datos compartidos y temas de usuario (`themes/`). |
| `~/.cache/gekko-bauh/tmp` | Archivos temporales de la sesión, con permisos `0700`. No se usa `$XDG_RUNTIME_DIR` porque es un tmpfs pequeño (10 % de la RAM). |
| `~/.cache/gekko-bauh/logs` | Logs de la sesión (`gekko-bauh --logs` los muestra además en el terminal). |
| `/etc/bauh/gems.forbidden`, `/etc/gekko-bauh/gems.forbidden` | Gems que el administrador prohíbe cargar (una por línea). Se leen las dos rutas y se unen: la heredada respeta una política que el sistema ya tuviera puesta. |

Argumentos útiles: `gekko-bauh --logs` (logs en el terminal), `gekko-bauh --settings`
(abre directamente los ajustes), `gekko-bauh --offline`, `gekko-bauh --reset` (borra
configuración, caché y temporales), `gekko-bauh-cli updates [--format json]`.

## Cómo ejecutar los tests

La suite usa `unittest` (sin pytest). Los tests de la interfaz necesitan PyQt5
y una plataforma Qt sin pantalla; si PyQt5 no está instalado se omiten solos.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests
```

Lint: `.venv/bin/ruff check bauh tests` y `shellcheck install.sh`. Paridad de
traducciones: `python3 tools/check_locales.py`. El detalle está en
[CONTRIBUTING.md](CONTRIBUTING.md).

## Sincronización con upstream

Este proyecto sigue a `vinifmor/bauh` (`master` y `staging`) mediante **merges** (no
rebase) sobre `master`, registra la base upstream de cada versión en el
`CHANGELOG.md` y numera sus versiones como `<versión upstream>+gekko.N`. La
política completa (remotes, cadencia, cómo se resuelven los conflictos en los
archivos que este proyecto reestructuró y cómo devolver arreglos al proyecto
original) está
en [docs/SINCRONIZACION_UPSTREAM.md](docs/SINCRONIZACION_UPSTREAM.md).

## Compatibilidad con Python

- **Soportado y probado en CI**: 3.9, 3.12 y 3.14 (3.10, 3.11 y 3.13 funcionan
  pero no se prueban en cada cambio).
- **3.8**: el código sigue declarando `>=3.8` y no se ha roto a propósito, pero
  Python 3.8 está fuera de soporte desde octubre de 2024 y las versiones
  actuales de `PyQt5-sip`, `requests` y `urllib3` ya no lo admiten. Se
  mantiene «best effort» y se retirará en una versión futura; ninguna de las
  distribuciones a las que va dirigido el proyecto (Arch y derivados, Solus) lo
  incluye.

## Contribuir

Lee [CONTRIBUTING.md](CONTRIBUTING.md): entorno de desarrollo, tests, lint,
traducciones, convención de commits y flujo de pull requests. Para reportar un
error usa la plantilla de issue (pide la salida de `gekko-bauh --logs`, `pipx list` y
el commit instalado).

## Créditos

`gekko-bauh` no existiría sin el trabajo del que parte. La mayor parte del código
de este repositorio no es nuestra.

- **Proyecto original**: [bauh](https://github.com/vinifmor/bauh), creado y
  mantenido por **Vinicius Moreira** ([@vinifmor](https://github.com/vinifmor)).
  Suya es la arquitectura de gems, el gestor de Arch y AUR con todo su manejo de
  dependencias, claves PGP y conflictos, la capa Qt, el sistema de temas y los
  diez idiomas de la interfaz. Este proyecto se limita a construir encima.
- **Colaboradores del proyecto original** cuyo trabajo se incluye aquí:
  albanobattistella, KoromeloDev, antipeth, Boria138, EGYT5453 y NoobKozlegeny,
  entre muchos otros en el historial anterior a la versión 0.10.7. El detalle
  está en [CREDITS.md](CREDITS.md) y [CHANGELOG.md](CHANGELOG.md).
- **Este proyecto**: [The-Gekko](https://github.com/The-Gekko). Lo que aporta,
  y solo eso, está listado en [Qué aporta este proyecto](#qué-aporta-este-proyecto).
- **Arte**: la imagen `pictures/gekko-bauh.png` fue **generada con IA**.

Si `gekko-bauh` te resulta útil, considera darle una estrella también al
[proyecto original](https://github.com/vinifmor/bauh).

## Licencia

Este software se distribuye bajo la licencia **zlib/libpng**, la misma del
proyecto original; el texto íntegro está en [LICENSE](LICENSE). Conforme a su
cláusula 2, esta edición está marcada como **versión alterada** del bauh
original (ver el aviso al inicio de este archivo y [CREDITS.md](CREDITS.md)).
