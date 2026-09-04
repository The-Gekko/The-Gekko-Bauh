<div align="center">

# 🦎 bauh Gekko Edition

### Gestor gráfico de aplicaciones para Arch Linux (pacman + AUR + Chaotic AUR), Flatpak y Solus (eopkg)

<p align="center">
  <a href="https://github.com/The-Gekko/The-Gekko-Bauh/releases"><img src="https://img.shields.io/github/v/tag/The-Gekko/The-Gekko-Bauh?label=%C3%9Altima%20etiqueta&sort=semver" alt="Última etiqueta"></a>
  <a href="https://github.com/The-Gekko/The-Gekko-Bauh/actions"><img src="https://img.shields.io/badge/CI-GitHub%20Actions-blue" alt="CI"></a>
  <a href="https://github.com/The-Gekko/The-Gekko-Bauh/blob/master/LICENSE"><img src="https://img.shields.io/github/license/The-Gekko/The-Gekko-Bauh?label=Licencia" alt="Licencia"></a>
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
> [aquí](https://github.com/The-Gekko/The-Gekko-Bauh/issues), nunca en el
> proyecto original. La mayor parte del código sigue siendo obra suya y de sus
> colaboradores: el crédito completo está en [CREDITS.md](CREDITS.md).
>
> Se instala como `gekko-bauh`, guarda su configuración en `~/.config/gekko-bauh` y
> convive sin interferir con una instalación del bauh oficial.
>
> **Versión en desarrollo**: `0.10.8+gekko.1` (será la etiqueta `v0.10.8-gekko.1`,
> **pendiente de publicar**), construida sobre la rama `staging` del proyecto
> original. **Último release publicado**: [`v0.10.7`](https://github.com/The-Gekko/The-Gekko-Bauh/releases/tag/v0.10.7),
> anterior al cambio de identidad: se instala como distribución `bauh`, no como
> `gekko-bauh`. Lo que hay en `master` es lo que instala `install.sh`. Detalles en
> [CHANGELOG.md](CHANGELOG.md).
>
> El repositorio se llamaba `The-Gekko/Bauh-Fork-The-Gekko`; GitHub redirige el
> nombre antiguo, pero usa siempre el actual: `The-Gekko/The-Gekko-Bauh`.

**gekko-bauh** (se pronuncia _gueko baoo_) es una interfaz gráfica en PyQt5 para
buscar, instalar, actualizar y desinstalar software en Linux. Su alcance son tres
plataformas: **Arch Linux y derivados** (pacman, AUR y cualquier repositorio
adicional de pacman, por ejemplo Chaotic AUR), **Flatpak** y **Solus (eopkg)**.
Las tres vienen activadas de fábrica. Se incluyen además tres gestores que **no
pertenecen a ninguna distribución**: AppImage, aplicaciones web y compilación
desde un repositorio de GitHub. Vienen desactivados y se activan en
`Ajustes → Tipos de aplicaciones`.

Los gestores de otras distribuciones (Debian/Ubuntu y Snap) se han **eliminado**:
este proyecto es para Arch y Solus, y arrastrar código que aquí nunca se ejecuta
solo añadía superficie que mantener y revisar.

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
  **GTK 3/4**, que toma los colores de `/etc/gtk-3.0/gtk.css`,
  `/etc/gtk-4.0/gtk.css`, `~/.config/gtk-3.0/gtk.css` y
  `~/.config/gtk-4.0/gtk.css` (`GTK_COLOR_FILES` en `bauh/stylesheet.py`), y
  **Matugen**, que lee `~/.cache/matugen/colors-gtk.css`. Ambos se recargan
  solos cuando esos archivos cambian: el vigilante de archivos solo se activa con esos dos temas
  y agrupa los cambios rápidos (debounce) para no repintar la ventana varias
  veces seguidas. Ver `Ajustes → Interfaz → Tema`.
- **Botón Matugen** en la barra superior de la ventana principal para aplicar
  el tema dinámico con un clic; su estado persiste entre sesiones.
- **Pestaña «Personalización»** en Ajustes (traducida) para color de fondo,
  texto, acento, opacidad e imagen de fondo (clave `custom_theme` de
  `~/.config/gekko-bauh/config.yml`).
- **Identidad propia**: la ventana se llama «bauh Gekko Edition», el diálogo
  «Acerca de» enlaza a este repositorio y al proyecto original, y el aviso de nueva
  versión consulta las releases de este repositorio (`bauh/view/core/update.py`).
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
  responsabilidad. Los clones se guardan por defecto en
  `~/.local/share/gekko-bauh/github/repos` (clave `repos_dir` de
  `~/.config/gekko-bauh/github.yml`); el directorio heredado `~/BauhRepos` de
  versiones anteriores se sigue reconociendo.
- **Gems universales opt-in**: AppImage, Web y GitHub vienen desactivadas. Se
  activan en `Ajustes → Tipos de aplicaciones` (o con la clave `gems` de
  `config.yml`). No dependen de ninguna distribución, así que funcionan igual en
  Arch y en Solus. Arch, Flatpak y eopkg, que son el alcance del proyecto,
  siguen activadas por defecto.
- **Sin código de otras distribuciones**: las gems de Debian/Ubuntu y Snap se
  han eliminado del árbol, junto con la acción de Arch que configuraba `snapd`.

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

- **`install.sh`**: instalador y desinstalador por `curl` basado en `pipx`, que
  funciona tanto con el backend `pip` como con el backend `uv` de pipx (ver
  [Instalación](#instalación)).
- **Identidad propia en el sistema**: distribución `gekko-bauh`, ejecutables
  `gekko-bauh`, `gekko-bauh-tray` y `gekko-bauh-cli`, configuración en
  `~/.config/gekko-bauh` y lanzador e icono propios. Nada de eso colisiona con
  una instalación del bauh oficial, y la primera ejecución copia los ajustes
  heredados de `~/.config/bauh` sin tocar el original. El paquete Python interno
  sigue llamándose `bauh` para poder integrar las correcciones del proyecto
  original. Versión PEP 440 `0.10.8+gekko.1`, `pyproject.toml` con la sección
  `[project]` completa.
- **Receta para el AUR** (`packaging/aur/`: `gekko-bauh` y `gekko-bauh-git`),
  todavía sin publicar en el AUR, y **artefacto para GekkoApp**
  (`tools/build-gekkoapp-release.sh`), que el workflow de release adjunta a
  cada etiqueta.
- **CI en GitHub Actions** (`.github/workflows/ci.yml`): la suite sin PyQt5 en
  Python 3.9, 3.12 y 3.14 y la suite completa con Qt offscreen en 3.12; `ruff`
  y `shellcheck` sobre los scripts de shell; los tests del instalador;
  construcción y comprobación del wheel; tests de integración con binarios
  simulados; y paridad de traducciones (`tools/check_locales.py`).
- Compatibilidad con **Python 3.13 y 3.14**.
- Integrado el arreglo del upstream para sesiones Wayland: define
  `QT_QPA_PLATFORM=wayland` **si no estaba ya definida** (evitaba un cierre
  inesperado al arrancar en algunos equipos).

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
- Los gestores universales, desactivados de fábrica: AppImage, aplicaciones web
  (nativefier) y compilación desde un repositorio de GitHub.

## Requisitos

- **Distribución**: Arch Linux o derivado (Garuda, EndeavourOS, Manjaro,
  CachyOS, ...) con `pacman`; o Solus con `eopkg`. En otras distribuciones bauh
  arranca, pero solo con las gems cuyas herramientas encuentre instaladas.
- **Python** 3.8 a 3.14 (3.8 «best effort»; recomendado 3.12 o superior). Es
  el rango que exige `install.sh` y que declara `pyproject.toml`
  (`requires-python = ">=3.8"`). Ver
  [Compatibilidad con Python](#compatibilidad-con-python).
- **pipx** (el instalador puede instalarlo por ti si le pasas
  `--install-pipx`). Si tu pipx usa `uv` como backend (lo elige solo cuando
  encuentra `uv` en el `PATH`), el instalador funciona igual: pasa la lista de
  dependencias «solo wheels» en el formato que espera cada backend.
- **Recomendado, no obligatorio**: un repositorio de binarios como
  [Chaotic AUR](https://aur.chaotic.cx/). Si está habilitado en
  `/etc/pacman.conf`, bauh lo trata como cualquier otro repositorio de pacman:
  prefiere su binario frente a AUR en las búsquedas y ofrece «Cambiar al
  binario del repositorio» para los paquetes que ya tengas compilados desde
  AUR. Sin él, todo funciona igual, compilando desde AUR.

## Instalación

Este README describe la instalación **de gekko-bauh por sí solo** («1x1»). Si
usas varias herramientas de The-Gekko, el Control Center
[GekkoApp](https://github.com/The-Gekko/GekkoApp) las instala y desinstala de
forma **conjunta**; ver [Desde GekkoApp](#desde-gekkoapp).

> **Elige una sola vía por proyecto; para cambiar de vía, desinstala primero
> con la misma con la que instalaste.** Mezclarlas deja restos: GekkoApp retira
> el venv pipx `gekko-bauh` que creó `install.sh` pero no sus `.desktop`,
> iconos ni autostart, e `install.sh uninstall` no conoce
> `org.thegekko.bauh.desktop` ni el estado de GekkoApp. Los paquetes del
> sistema que GekkoApp instaló con sudo (`python-pipx`/`pipx`) no se
> desinstalan.

### Por curl (recomendado)

```bash
curl -fsSL https://raw.githubusercontent.com/The-Gekko/The-Gekko-Bauh/master/install.sh | bash
```

Qué hace el instalador:

1. Comprueba `curl`, la versión de Python y `pipx`.
2. Resuelve el **commit exacto** de `master` en GitHub y descarga ese commit
   (no «lo que haya en master» en ese instante), de modo que la marca
   `.gekko-source-ref` que guarda dentro del entorno coincide siempre con el
   código instalado.
3. Instala el código en un entorno aislado de pipx llamado **`gekko-bauh`**,
   pasando `--python` con el intérprete elegido (`PYTHON_BIN`, por defecto
   `python3`). Las dependencias se instalan **solo desde wheels**
   (`PIP_ONLY_BINARY` para el backend pip, `UV_NO_BUILD_PACKAGE` para el
   backend uv); si para tu Python no hay wheel de alguna, el instalador lo
   dice y ofrece dos salidas: otro `PYTHON_BIN` o `--allow-build-from-source`.
   Si encuentra el entorno `bauh` de una versión anterior de este proyecto, lo
   **migra** a `gekko-bauh` y elimina el antiguo.
4. Instala el icono en los tamaños estándar de `hicolor` (16 a 512 px) y dos
   `.desktop` con traducciones y `StartupWMClass=gekko-bauh` en
   `~/.local/share/applications/` (aplicación y bandeja), pregunta si quieres
   que la bandeja arranque con la sesión y refresca las cachés del escritorio.

Si detecta el bauh **oficial** instalado por pacman o eopkg, avisa del
conflicto pero **no lo desinstala** a menos que se lo pidas (ver flags).
Las preguntas se leen del terminal, así que funcionan aunque el script llegue
por tubería; sin terminal (CI, cron, systemd) la respuesta por defecto es «no».

| Opción | Efecto |
|---|---|
| `--ref REF` | Rama, etiqueta o SHA a instalar en modo remoto (por defecto `master`). Desde un checkout no tiene efecto: el instalador avisa y sale con código 2. |
| `--force`, `-f` | Reconstruye el entorno pipx aunque ya esté instalado el mismo commit. |
| `--yes`, `-y` | Responde «sí» a las preguntas que **no** requieren `sudo`. Incluye la pregunta del autoarranque de la bandeja: con `--yes` y sin `--no-autostart`, la bandeja queda configurada para arrancar con la sesión. No autoriza acciones con privilegios. |
| `--autostart` | Configura el arranque automático de la bandeja sin preguntar (`~/.config/autostart/gekko-bauh-tray.desktop`). |
| `--no-autostart` | No configura el arranque automático (y retira el que hubiera). |
| `--allow-build-from-source` | Permite compilar dependencias que no tengan wheel para tu Python (necesita compilador y cabeceras: `base-devel` en Arch, `system.devel` y `python3-devel` en Solus). |
| `--purge` | Con `uninstall`: borra también configuración, caché, datos y el directorio temporal (ver [Desinstalación](#desinstalación)). |
| `--remove-system-bauh` | Autoriza desinstalar el paquete `bauh` de pacman/eopkg antes de instalar gekko-bauh. Es una acción con `sudo`. |
| `--install-pipx` | Autoriza instalar `pipx` con el gestor de paquetes del sistema si falta. Es una acción con `sudo`. |
| `PYTHON_BIN=/ruta/python3.x` | Variable de entorno: intérprete que usará pipx para crear el entorno (por defecto `python3`). |

Ejemplos:

```bash
# Reinstalar desde cero
curl -fsSL https://raw.githubusercontent.com/The-Gekko/The-Gekko-Bauh/master/install.sh | bash -s -- --force

# Instalar una rama o un commit concretos (una etiqueta también valdrá cuando exista alguna con identidad propia)
curl -fsSL https://raw.githubusercontent.com/The-Gekko/The-Gekko-Bauh/master/install.sh | bash -s -- --ref master
curl -fsSL https://raw.githubusercontent.com/The-Gekko/The-Gekko-Bauh/master/install.sh | bash -s -- --ref 49dfc5b9

# Automatizado (sin preguntas) y autorizando explícitamente las dos acciones con sudo
curl -fsSL https://raw.githubusercontent.com/The-Gekko/The-Gekko-Bauh/master/install.sh | bash -s -- --yes --no-autostart --install-pipx --remove-system-bauh
```

La lista completa y actualizada de opciones está en `install.sh --help`.

### Desde el AUR (Arch, Garuda, EndeavourOS…)

La receta está lista en [`packaging/aur/`](packaging/aur) (`gekko-bauh`,
estable desde la etiqueta, y `gekko-bauh-git`, que compila `master`), pero
**aún no está publicada en el AUR**: `paru -S gekko-bauh` o `yay -S gekko-bauh`
no encuentran nada todavía. Lo que sí puedes hacer hoy es construir el paquete
de desarrollo en local:

```bash
git clone https://github.com/The-Gekko/The-Gekko-Bauh.git
cd The-Gekko-Bauh/packaging/aur/gekko-bauh-git
makepkg -si
```

El paquete estable necesita que exista la etiqueta `v0.10.8-gekko.1` (su
`PKGBUILD` descarga el tarball de esa etiqueta y lleva `sha256sums=('SKIP')`
hasta entonces; la suma real se rellena con `updpkgsums` antes de subirlo al
AUR). El alta en el AUR y el procedimiento completo están en
[`docs/DISTRIBUCION.md`](docs/DISTRIBUCION.md).

El paquete **convive con el `bauh` original**: los ejecutables (`gekko-bauh`,
`gekko-bauh-tray`, `gekko-bauh-cli`), el icono, los lanzadores y la
configuración (`~/.config/gekko-bauh`) llevan nombres propios, y el código se
instala en `/usr/share/gekko-bauh` en vez de en `site-packages`, así que pacman
no ve ni un fichero compartido. Puedes tener los dos a la vez.

Instala además lo que vayas a usar de sus dependencias opcionales: `flatpak`,
`git` y `base-devel` (gem de GitHub y compilación de paquetes del AUR),
`timeshift` (copias de seguridad), y `python-lxml` con `python-beautifulsoup4`
(gem web).

### Desde un checkout (contribuidores)

```bash
git clone https://github.com/The-Gekko/The-Gekko-Bauh.git
cd The-Gekko-Bauh
./install.sh          # detecta el checkout local y lo instala con pipx
```

En este modo pipx no recibe el checkout tal cual, sino una **copia temporal
limpia** del árbol de trabajo (sin `build/`, `dist/`, `releases/`,
`*.egg-info`, `__pycache__`, `.git` ni entornos virtuales): setuptools
reutiliza lo que haya en `build/lib`, y un checkout con construcciones antiguas
arrastraba al venv módulos ya borrados del árbol. Tus cambios sin confirmar sí
se instalan. Desde un checkout **siempre se reconstruye** el entorno (la
comparación de commits solo existe en modo remoto) y `--ref` es un error, porque
lo que se instala es el árbol local.

### Manual con pipx o pip (avanzado)

```bash
pipx install --force "https://github.com/The-Gekko/The-Gekko-Bauh/archive/refs/heads/master.zip"
# o en un entorno virtual propio:
python3 -m venv bauh_env
bauh_env/bin/pip install "https://github.com/The-Gekko/The-Gekko-Bauh/archive/refs/heads/master.zip"
bauh_env/bin/gekko-bauh
```

Así no se instalan ni el icono ni los `.desktop`, y `pipx` no deja la marca
`.gekko-source-ref` que usan `install.sh uninstall` y la plantilla de issues.

> [!WARNING]
> `pip install bauh` o `pacman -S bauh` **no** instalan este proyecto: instalan el
> bauh original (PyPI / repositorios), sin el tema Aurora, las gems eopkg y
> GitHub, ni los cambios de la gem Arch.

### Desde GekkoApp

[GekkoApp](https://github.com/The-Gekko/GekkoApp) (el Control Center de
The-Gekko, en Rust + Tauri) instala gekko-bauh **desde un release verificado**,
no ejecutando `install.sh`:

1. Resuelve el último release de `The-Gekko/The-Gekko-Bauh` y descarga el
   manifiesto `bauh-fork-the-gekko-x86_64-unknown-linux-gnu.manifest.json` y
   el artefacto `bauh-fork-the-gekko-<X.Y.Z.gekko.N>.tar.zst` que lo acompaña
   (el `+` de la versión va como `.` en el nombre del archivo; hoy,
   `bauh-fork-the-gekko-0.10.7.tar.zst`).
2. Comprueba el **tamaño y el SHA-256** del artefacto contra el manifiesto.
3. Si el paquete `bauh` de pacman está instalado, pide confirmación y lo
   desinstala; después instala `python-pipx` (Arch) o `pipx` (Solus) si falta.
4. Ejecuta `pipx install --force` sobre el árbol verificado y materializa el
   lanzador con id `org.thegekko.bauh` y su icono `hicolor` de 512 px.

Hoy el último release es `v0.10.7`, anterior al cambio de identidad, así que
GekkoApp instala por ahora la distribución `bauh`. Cuando se publique
`v0.10.8-gekko.1`, el mismo flujo instalará `gekko-bauh` con sus tres
ejecutables y las dos entradas de menú (`org.thegekko.bauh` y
`org.thegekko.bauh.tray`); ese release lo genera `release.yml` con
`tools/build-gekkoapp-release.sh` (ver [`docs/DISTRIBUCION.md`](docs/DISTRIBUCION.md)),
y la aceptación de etiquetas con guion (`v0.10.8-gekko.1`) forma parte de la
versión 1.2.0 de GekkoApp, en preparación. **Orden de publicación
recomendado**: primero GekkoApp 1.2.0 y después `v0.10.8-gekko.1`, porque
GekkoApp 1.1.0 (la publicada) rechaza la etiqueta con guion.

Lo que instala GekkoApp se **desinstala desde el propio Control Center**, no con
`install.sh uninstall`. Esta vía es la conjunta; la de este README, la 1x1.
Elige una sola vía por proyecto; para cambiar de vía, desinstala primero con la
misma con la que instalaste: GekkoApp retira el venv pipx `gekko-bauh` que creó
`install.sh` pero no sus `.desktop`, iconos ni autostart, e `install.sh
uninstall` no conoce `org.thegekko.bauh.desktop` ni el estado de GekkoApp. Los
paquetes del sistema que GekkoApp instaló con sudo (`python-pipx`/`pipx`) no se
desinstalan.

## Actualización

**Por curl**: vuelve a ejecutar el comando de instalación. El instalador compara
el commit instalado (`.gekko-source-ref`) con el commit actual de `master` y
solo reconstruye el entorno si hay cambios; por eso actualizar es rápido y no
depende de que cambie el número de versión. Usa `--force` para reconstruir de
todos modos.

**Desde un checkout**: `./install.sh` reconstruye siempre el entorno. La
comparación de commits solo aplica al modo remoto.

Desde la propia aplicación, el aviso de «nueva versión disponible» consulta
las releases de este repositorio (`bauh/view/core/update.py`).

### Verificar las descargas (SHA256)

A partir del próximo release (el primero con identidad propia), `release.yml`
publicará un fichero `SHA256SUMS` con las sumas del wheel, del sdist, del
tarball de código fuente de la etiqueta y de los dos ficheros que consume
GekkoApp. **`v0.10.7` no lo tiene.** Descárgalo junto a lo que te lleves y
comprueba antes de instalar:

```bash
sha256sum --check --ignore-missing SHA256SUMS
```

`--ignore-missing` hace que se comprueben solo los ficheros que hayas
descargado, sin fallar por los que no.

**Nombres con `+`.** GitHub renombra los assets de una release cuyo nombre lleva
caracteres especiales y cambia el `+` por `.`: el wheel
`gekko_bauh-0.10.8+gekko.1-py3-none-any.whl` se descarga como
`gekko_bauh-0.10.8.gekko.1-py3-none-any.whl`. Por eso `SHA256SUMS` lleva dos
líneas para cada fichero con `+` (nombre original y nombre publicado) y la
comprobación anterior funciona con cualquiera de los dos. El artefacto de
GekkoApp ya se genera sin `+` (`bauh-fork-the-gekko-X.Y.Z.gekko.N.tar.zst`).

La instalación **por curl no usa ese fichero**: `install.sh` resuelve la
referencia que le pidas contra la API de GitHub, obtiene el SHA-1 del commit
exacto y descarga e instala ese commit, dejando la marca dentro del entorno de
pipx. La integridad viene ahí del identificador del commit y de HTTPS. El
`PKGBUILD` estable lleva `sha256sums=('SKIP')` hasta que exista la etiqueta;
GekkoApp, por su parte, verifica el SHA-256 que declara el manifiesto del
release.

Los detalles están en
[`docs/DISTRIBUCION.md`](docs/DISTRIBUCION.md#6-verificar-las-sumas-antes-de-instalar).

## Desinstalación

```bash
curl -fsSL https://raw.githubusercontent.com/The-Gekko/The-Gekko-Bauh/master/install.sh | bash -s -- uninstall
```

Elimina el entorno pipx (`gekko-bauh`, y `bauh` si quedara de una versión
anterior), los `.desktop` (aplicación, bandeja y autoarranque) y los iconos, y
refresca las cachés del escritorio. **No toca** tu configuración. Si no había
ninguna instalación hecha por `install.sh`, limpia igualmente iconos y accesos
directos sueltos, lo avisa y termina con código de salida **1**.

Para borrar **también** los datos de usuario:

```bash
curl -fsSL https://raw.githubusercontent.com/The-Gekko/The-Gekko-Bauh/master/install.sh | bash -s -- uninstall --purge
```

`--purge` elimina `~/.config/gekko-bauh`, `~/.cache/gekko-bauh`,
`~/.local/share/gekko-bauh` y el directorio temporal de la sesión (y sus
variantes `XDG_*` si apuntan a otro sitio, sin repetir rutas), **conservando
`~/.local/share/gekko-bauh/github/repos`**, donde la gem GitHub clona tus
repositorios: pueden contener trabajo sin publicar, así que no se borran nunca
automáticamente (ni ese directorio ni el heredado `~/BauhRepos`). Con `--purge`
y sin instalación previa, la purga se hace de todos modos y el comando termina
con **0** (avisando de que no había nada instalado).

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
  paralelo. Las gems AppImage, Web y GitHub quedan desactivadas hasta que las
  marques en `Ajustes → Tipos de aplicaciones`. Si en el oficial usabas Snap o
  Debian, aquí no existen: este proyecto solo cubre Arch y Solus.
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
y en X11. Al arrancar en una sesión Wayland (`XDG_SESSION_TYPE=wayland`) define
`QT_QPA_PLATFORM=wayland` **si no estaba ya definida** (arreglo integrado desde
el upstream; un valor previo, por ejemplo `offscreen` en los tests o `xcb` si
prefieres XWayland, se respeta).

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
| `~/.local/share/gekko-bauh/` | Datos compartidos, temas de usuario (`themes/`) y clones de la gem GitHub (`github/repos/`). |
| `~/.cache/gekko-bauh/tmp` | Archivos temporales de la sesión, con permisos `0700`. No se usa `$XDG_RUNTIME_DIR` porque es un tmpfs pequeño (10 % de la RAM). |
| `~/.cache/gekko-bauh/logs` | Logs de la sesión (`gekko-bauh --logs` los muestra además en el terminal). |
| `/etc/bauh/gems.forbidden`, `/etc/gekko-bauh/gems.forbidden` | Gems que el administrador prohíbe cargar (una por línea). Se leen las dos rutas y se unen: la heredada respeta una política que el sistema ya tuviera puesta. |

Argumentos útiles: `gekko-bauh --logs` (logs en el terminal), `gekko-bauh --settings`
(abre directamente los ajustes), `gekko-bauh --offline`, `gekko-bauh --reset` (borra
configuración, caché y temporales), `gekko-bauh --version`,
`gekko-bauh-cli updates [--format json]`.

## Cómo ejecutar los tests

La suite usa `unittest` (sin pytest). **Necesita un entorno virtual con
`requirements-dev.txt`**: sin `pyyaml` y `colorama`, 24 módulos de test fallan
al importarse y la suite termina en error aunque el código esté bien. Los tests
de la interfaz necesitan además PyQt5 (`requirements.txt`) y una plataforma Qt
sin pantalla; si PyQt5 no está instalado se omiten solos.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -t .
```

Además de los tests unitarios, `tests/integration/` ejecuta las gems contra
**binarios `pacman`, `eopkg` y `flatpak` simulados en el `PATH`**: comprueban los
argumentos que llegan de verdad al proceso y el análisis de salidas reales, algo
que un test que parchea `subprocess` no puede ver. El instalador tiene sus
propios **26 casos** en bash, con `pipx`, `uv`, `curl` y `sudo` simulados:
`bash tests/installer/run_tests.sh`.

Lint: `.venv/bin/ruff check bauh tests tools` y
`shellcheck install.sh tests/installer/run_tests.sh tools/build-gekkoapp-release.sh`.
Paridad de traducciones: `python3 tools/check_locales.py`. El detalle está en
[docs/TESTS.md](docs/TESTS.md) y en [CONTRIBUTING.md](CONTRIBUTING.md).

## Sincronización con upstream

Este proyecto sigue a `vinifmor/bauh` (`master` y `staging`) mediante **merges** (no
rebase) sobre `master`, registra la base upstream de cada versión en el
`CHANGELOG.md` y numera sus versiones como `<versión upstream>+gekko.N`. La
política completa (remotes, cadencia, cómo se resuelven los conflictos en los
archivos que este proyecto reestructuró y cómo devolver arreglos al proyecto
original) está
en [docs/SINCRONIZACION_UPSTREAM.md](docs/SINCRONIZACION_UPSTREAM.md).

## Compatibilidad con Python

- **Rango admitido**: 3.8 a 3.14, el mismo en `install.sh` (rechaza cualquier
  otro intérprete) y en `pyproject.toml` (`requires-python = ">=3.8"`,
  clasificadores de 3.8 a 3.14). Para desarrollar se pide 3.9 o superior
  (ver [CONTRIBUTING.md](CONTRIBUTING.md)).
- **Probado en CI**: 3.9, 3.12 y 3.14 (3.10, 3.11 y 3.13 funcionan pero no se
  prueban en cada cambio).
- **3.8, «best effort»**: el código sigue declarando `>=3.8` y no se ha roto a
  propósito, pero Python 3.8 está fuera de soporte desde octubre de 2024 y las
  versiones actuales de `PyQt5-sip`, `requests` y `urllib3` ya no lo admiten.
  Se retirará en una versión futura; ninguna de las distribuciones a las que va
  dirigido el proyecto (Arch y derivados, Solus) lo incluye.

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
