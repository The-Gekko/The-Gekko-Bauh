#!/usr/bin/env bash

# El script usa sintaxis exclusiva de bash ([[ ]], arrays, (( ))). Si alguien lo
# ejecuta con sh/dash, avisamos antes de que falle con errores de sintaxis.
if [ -z "${BASH_VERSION:-}" ]; then
    echo "[bauh] Este instalador necesita bash. Ejecútalo con: bash install.sh" >&2
    exit 1
fi

set -Eeuo pipefail

# ══════════════════════════════════════════════════════════════════════════════
#  bauh Gekko Edition — instalador / desinstalador (100% por curl)
#
#  Instalar/actualizar:  curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash
#  Forzar reinstall:     ... | bash -s -- --force
#  Versión concreta:     ... | bash -s -- --ref v0.10.8-gekko.1
#  Desinstalar:          ... | bash -s -- uninstall [--purge]
#
#  Requisitos: curl, pipx y Python 3.8–3.14.
#    Arch/Garuda:  sudo pacman -S --needed python-pipx
#    Solus:        sudo eopkg install -y pipx
#
#  Las dependencias se instalan solo desde wheels precompilados. Si para tu
#  versión de Python todavía no existe wheel de PyQt5-sip o PyYAML necesitarás
#  un compilador (Arch: base-devel; Solus: system.devel) y la opción
#  --allow-build-from-source.
# ══════════════════════════════════════════════════════════════════════════════

REPO="The-Gekko/Bauh-Fork-The-Gekko"
RAW_BASE="https://raw.githubusercontent.com/$REPO"
ARCHIVE_BASE="https://github.com/$REPO/archive"
API_BASE="https://api.github.com/repos/$REPO"

# Nombre de la distribución en pipx y de los ejecutables que instala. El paquete
# importable sigue siendo «bauh», heredado del proyecto original.
PKG_NAME="gekko-bauh"

# Versiones anteriores de este instalador registraban el venv como «bauh». Se
# migra, pero solo si la marca de origen confirma que lo instalamos nosotros:
# un venv «bauh» ajeno (instalado a mano por el usuario) no se toca.
LEGACY_PKG_NAME="bauh"

# Marca con el commit exacto que se instaló. Vive dentro del venv, así que
# `pipx uninstall` se la lleva por delante y sirve además para reconocer los
# venvs creados por este instalador.
REF_STAMP_NAME=".gekko-source-ref"

# Identificadores propios del escritorio. NO se usa «bauh.desktop» ni el icono
# «bauh» para no tapar por precedencia XDG al paquete oficial si conviven.
DESKTOP_ID="gekko-bauh"
TRAY_DESKTOP_ID="gekko-bauh-tray"
ICON_NAME="gekko-bauh"
ICON_SIZES=(16 32 48 64 128 256 512)

# Dependencias que deben llegar como wheel. No se incluye el propio paquete:
# ese sí se construye desde el código fuente descargado.
WHEEL_ONLY_PACKAGES='pyqt5,pyqt5-sip,pyqt5-qt5,pyyaml,requests,colorama,python-dateutil,six,urllib3,certifi,idna,charset-normalizer'

green='\033[0;32m'
yellow='\033[0;33m'
red='\033[0;31m'
blue='\033[0;34m'
bold='\033[1m'
reset='\033[0m'

info()  { printf '%b\n' "${blue}[bauh]${reset} $*"; }
warning() { printf '%b\n' "${yellow}[bauh]${reset} $*"; }
error() { printf '%b\n' "${red}[bauh]${reset} $*" >&2; }

# --- Detección de modo: checkout local (contribuidores) o piped por curl ------
# Con `curl ... | bash` el array BASH_SOURCE queda vacío, así que SCRIPT_DIR
# queda vacío y el script entra en modo remoto.
SCRIPT_DIR=""
if [[ ${BASH_SOURCE[0]+x} ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
fi
LOCAL_MODE=false
if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/pyproject.toml" && -d "$SCRIPT_DIR/bauh" ]]; then
    LOCAL_MODE=true
fi

ASSUME_YES=false
FORCE=false
PURGE=false
REMOVE_SYSTEM_BAUH=false
INSTALL_PIPX=false
ALLOW_SOURCE_BUILD=false
AUTOSTART_TRAY=""
REQUESTED_REF="master"
ACTION="install"

usage() {
    cat <<'EOF'
Uso: install.sh [ACCIÓN] [OPCIONES]

Ejecutado por curl (modo remoto) resuelve el commit exacto de la referencia
pedida en GitHub, descarga ese commit y lo instala aislado con pipx bajo el
nombre de distribución «gekko-bauh». Desde un checkout del repositorio también
sirve como instalador local.

Acciones:
  install      Instala o actualiza bauh Gekko Edition (por defecto)
  uninstall    Desinstala bauh Gekko Edition, su icono y sus accesos directos

Opciones generales:
  --ref REF             Etiqueta, rama o SHA a instalar (por defecto: master)
  --force, -f           Reinstala aunque ya esté instalado exactamente ese commit
  --yes, -y             Responde «sí» a las preguntas SIN privilegios (nunca a las
                        que ejecutan sudo: para esas están los flags de abajo)
  --autostart           Arranca la bandeja al iniciar sesión (sin preguntar)
  --no-autostart        No configura el arranque automático de la bandeja
  --allow-build-from-source
                        Permite compilar dependencias si no hay wheel disponible
                        (requiere compilador y cabeceras de Python)
  --purge               (con uninstall) borra también configuración, caché,
                        datos compartidos y el directorio temporal
  --help, -h            Muestra esta ayuda

Opciones que ejecutan acciones con sudo (siempre explícitas):
  --remove-system-bauh  Desinstala el paquete «bauh» de los repositorios del sistema
  --install-pipx        Instala pipx con el gestor de paquetes del sistema

Entorno:
  PYTHON_BIN   Intérprete Python usado por pipx (por defecto: python3)

Ejemplos:
  curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash
  curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- --ref v0.10.8-gekko.1
  curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- uninstall --purge
EOF
}

while (($#)); do
    case "$1" in
        install)
            ACTION="install" ;;
        uninstall)
            ACTION="uninstall" ;;
        --ref)
            if [[ $# -lt 2 || -z "${2:-}" ]]; then
                error '--ref necesita un valor (etiqueta, rama o SHA).'
                exit 2
            fi
            REQUESTED_REF="$2"
            shift ;;
        --ref=*)
            REQUESTED_REF="${1#--ref=}"
            if [[ -z "$REQUESTED_REF" ]]; then
                error '--ref necesita un valor (etiqueta, rama o SHA).'
                exit 2
            fi ;;
        --yes|-y)
            ASSUME_YES=true ;;
        --force|-f)
            FORCE=true ;;
        --purge)
            PURGE=true ;;
        --remove-system-bauh)
            REMOVE_SYSTEM_BAUH=true ;;
        --install-pipx)
            INSTALL_PIPX=true ;;
        --allow-build-from-source)
            ALLOW_SOURCE_BUILD=true ;;
        --autostart)
            AUTOSTART_TRAY=true ;;
        --no-autostart)
            AUTOSTART_TRAY=false ;;
        --help|-h)
            usage
            exit 0 ;;
        *)
            error "Opción desconocida: $1"
            usage >&2
            exit 2 ;;
    esac
    shift
done

# ─────────────────────────────── Utilidades ───────────────────────────────────

# ¿Hay un terminal real al que preguntarle al usuario? No basta con `-r`:
# /dev/tty puede existir y aun así fallar al abrirse si el proceso no tiene
# terminal de control (CI, cron, systemd, contenedores).
has_tty() {
    { : < /dev/tty; } 2>/dev/null
}

# Lee una respuesta sí/no del terminal. Devuelve 0 (sí) o 1 (no).
#
# IMPORTANTE: con `curl ... | bash` la entrada estándar del script ES el propio
# script, así que un `read` normal se come las siguientes líneas del código (o
# devuelve EOF y, con `set -e`, aborta la instalación en silencio). Por eso
# leemos siempre desde el terminal (/dev/tty).
read_yes_no() {
    local prompt="$1"
    local answer=""

    read -r -p "$prompt" answer < /dev/tty 2>/dev/null || answer=""
    case "${answer,,}" in
        y|yes|s|si|sí) return 0 ;;
        *) return 1 ;;
    esac
}

# Pregunta SIN privilegios. `--yes` la responde afirmativamente; sin terminal se
# asume «no».
ask() {
    if [[ "$ASSUME_YES" == true ]]; then
        return 0
    fi

    if ! has_tty; then
        warning 'Sin terminal interactivo: se asume «no». Usa --yes para responder que sí automáticamente.'
        return 1
    fi

    read_yes_no "$1"
}

# Pregunta que desemboca en un `sudo`. A propósito NO la responde `--yes`: para
# autorizar una acción privilegiada hay que pasar su flag explícito, de modo que
# un script de CI o de cron nunca pueda desinstalar paquetes del sistema por
# arrastre (F51).
#
#   $1: prompt   $2: valor del flag explícito   $3: nombre del flag
ask_privileged() {
    local prompt="$1"
    local flag_value="$2"
    local flag_name="$3"

    if [[ "$flag_value" == true ]]; then
        return 0
    fi

    if ! has_tty; then
        warning "Sin terminal interactivo: no se ejecutará ninguna acción con sudo."
        warning "Si quieres autorizarla, vuelve a ejecutar el instalador con '$flag_name'."
        return 1
    fi

    if [[ "$ASSUME_YES" == true ]]; then
        warning "'--yes' no autoriza acciones con sudo; usa '$flag_name' para eso."
    fi

    read_yes_no "$prompt"
}

# Comprueba que `sudo` se puede usar de verdad antes de invocarlo: sin caché de
# credenciales y sin terminal, `sudo` se cuelga o falla con un error opaco.
sudo_available() {
    if ! command -v sudo >/dev/null 2>&1; then
        error "'sudo' no está instalado; ejecuta la acción manualmente como root."
        return 1
    fi

    if sudo -n true 2>/dev/null; then
        return 0
    fi

    if has_tty; then
        return 0
    fi

    error 'sudo pediría contraseña y no hay terminal interactivo donde escribirla.'
    return 1
}

detect_pkg_manager() {
    if command -v pacman >/dev/null 2>&1; then
        printf 'pacman'
    elif command -v eopkg >/dev/null 2>&1; then
        printf 'eopkg'
    fi
}

detect_original_bauh() {
    local pm pkg
    pm="$(detect_pkg_manager)"
    pkg=""
    if [[ "$pm" == "pacman" ]] && pacman -Qi bauh >/dev/null 2>&1; then
        pkg="pacman"
    elif [[ "$pm" == "eopkg" ]] && eopkg info bauh 2>/dev/null | grep -q 'Installed'; then
        pkg="eopkg"
    fi
    printf '%s' "$pkg"
}

ensure_pipx() {
    if command -v pipx >/dev/null 2>&1; then
        return 0
    fi

    local pm
    pm="$(detect_pkg_manager)"

    # Se usa un array en vez de `eval`: los argumentos nunca se reinterpretan.
    local pipx_cmd=()
    case "$pm" in
        pacman) pipx_cmd=(sudo pacman -S --needed python-pipx) ;;
        eopkg)  pipx_cmd=(sudo eopkg install -y pipx) ;;
        *)      pipx_cmd=() ;;
    esac

    if ((${#pipx_cmd[@]} == 0)); then
        error 'No se pudo detectar el gestor de paquetes del sistema. Instala pipx manualmente y reintenta.'
        exit 1
    fi

    warning 'pipx no está instalado y es obligatorio.'

    if ! ask_privileged "¿Instalarlo ahora con \`${pipx_cmd[*]}\`? [y/N] " "$INSTALL_PIPX" '--install-pipx'; then
        error 'pipx es obligatorio. Instálalo manualmente y vuelve a ejecutar el instalador:'
        error "  ${pipx_cmd[*]}"
        exit 1
    fi

    if ! sudo_available; then
        error "Instala pipx manualmente con: ${pipx_cmd[*]}"
        exit 1
    fi

    info "Ejecutando: ${pipx_cmd[*]}"
    if ! "${pipx_cmd[@]}"; then
        error "No se pudo instalar pipx con: ${pipx_cmd[*]}"
        exit 1
    fi

    if ! command -v pipx >/dev/null 2>&1; then
        error 'pipx sigue sin estar disponible tras la instalación.'
        exit 1
    fi
}

# Directorio donde pipx guarda sus venvs (no siempre es ~/.local/share/pipx).
pipx_venv_dir() {
    local dir=""
    if command -v pipx >/dev/null 2>&1; then
        dir="$(pipx environment --value PIPX_LOCAL_VENVS 2>/dev/null || true)"
    fi
    printf '%s' "${dir:-${PIPX_HOME:-$HOME/.local/share/pipx}/venvs}"
}

pipx_bin_dir() {
    local dir=""
    if command -v pipx >/dev/null 2>&1; then
        dir="$(pipx environment --value PIPX_BIN_DIR 2>/dev/null || true)"
    fi
    printf '%s' "${dir:-$HOME/.local/bin}"
}

# ¿Existe un venv de pipx con ese nombre de distribución?
pipx_has_package() {
    local venvs
    venvs="$(pipx_venv_dir)"
    [[ -d "$venvs/$1" ]]
}

# ¿Ese venv lo creó este instalador? La marca de origen solo la escribimos
# nosotros, así que distingue nuestro venv de uno homónimo instalado a mano.
pipx_venv_is_ours() {
    local venvs
    venvs="$(pipx_venv_dir)"
    [[ -f "$venvs/$1/$REF_STAMP_NAME" ]]
}

ref_stamp_file() {
    local venvs
    venvs="$(pipx_venv_dir)"
    printf '%s' "$venvs/$PKG_NAME/$REF_STAMP_NAME"
}

installed_ref() {
    local stamp
    stamp="$(ref_stamp_file)"
    if [[ -f "$stamp" ]]; then
        tr -d '[:space:]' < "$stamp" 2>/dev/null || true
    fi
}

save_installed_ref() {
    local stamp dir
    stamp="$(ref_stamp_file)"
    dir="$(dirname "$stamp")"
    [[ -d "$dir" ]] || return 0
    printf '%s\n' "$1" > "$stamp" 2>/dev/null || true
}

# Versión instalada actualmente (leída del venv de pipx), vacía si no está.
installed_version() {
    local venvs py
    venvs="$(pipx_venv_dir)"
    py="$venvs/$PKG_NAME/bin/python"
    if [[ -x "$py" ]]; then
        "$py" -c 'import bauh; print(bauh.__version__)' 2>/dev/null || true
    fi
}

# Resuelve una referencia (rama, etiqueta o SHA) al commit exacto que apunta.
# Instalar «master.zip» sin resolver antes deja la marca de origen mintiendo:
# entre la consulta y la descarga master puede haber avanzado (F04).
resolve_ref() {
    curl -fsSL -H 'Accept: application/vnd.github.sha' \
        "$API_BASE/commits/$1" 2>/dev/null \
        | tr -d '[:space:]' || true
}

refresh_desktop_caches() {
    local applications_dir="$HOME/.local/share/applications"
    local icon_home="$HOME/.local/share/icons/hicolor"

    if command -v update-desktop-database >/dev/null 2>&1 && [[ -d "$applications_dir" ]]; then
        update-desktop-database "$applications_dir" >/dev/null 2>&1 \
            || warning 'No se pudo actualizar la base de datos de escritorio.'
    fi

    # gtk-update-icon-cache falla siempre si el tema de usuario no tiene
    # index.theme, así que solo se invoca cuando ese fichero existe.
    if command -v gtk-update-icon-cache >/dev/null 2>&1 && [[ -f "$icon_home/index.theme" ]]; then
        gtk-update-icon-cache -f -t "$icon_home" >/dev/null 2>&1 \
            || warning 'No se pudo actualizar la caché de iconos.'
    fi
}

# Versiones anteriores de este instalador escribían «bauh.desktop» e iconos
# «bauh.png» en el directorio del usuario, tapando por precedencia XDG el
# lanzador del bauh oficial y cambiándole el icono (F129). Se limpian, pero solo
# si llevan nuestra marca: un bauh.desktop escrito por el usuario no se toca.
remove_legacy_launcher() {
    local applications_dir="$HOME/.local/share/applications"
    local icon_home="$HOME/.local/share/icons/hicolor"
    local legacy_desktop="$applications_dir/bauh.desktop"
    local legacy_tray="$applications_dir/bauh_tray.desktop"
    local found=false

    if [[ -f "$legacy_desktop" ]] && grep -qE 'X-Gekko-Edition=true|Name=Bauh Fork The-Gekko' "$legacy_desktop"; then
        rm -f "$legacy_desktop"
        found=true
    fi

    if [[ -f "$legacy_tray" ]] && grep -qE 'X-Gekko-Edition=true|Name=Bauh Fork The-Gekko' "$legacy_tray"; then
        rm -f "$legacy_tray"
        found=true
    fi

    if [[ "$found" == true ]]; then
        local size
        for size in "${ICON_SIZES[@]}" 1024; do
            rm -f "$icon_home/${size}x${size}/apps/bauh.png"
        done
        info 'Se retiró el lanzador antiguo que tapaba al del bauh oficial.'
    fi
}

# ───────────────────────────── Desinstalación ─────────────────────────────────

# Deja el tema en «light» si quedó en uno exclusivo del fork. El bauh oficial no
# conoce aurora/matugen/gtk: al no encontrar la hoja de estilos arranca sin QSS
# y, como los iconos de los botones vienen del QSS, la ventana aparece «rota»
# sin ningún aviso en el log (F123).
reset_fork_theme() {
    # Se revisa el directorio heredado: es el que escribían las versiones anteriores
    # de este proyecto y el que leerá el bauh oficial. El directorio propio se borra
    # entero con --purge, así que no necesita reparación.
    local config_file="$HOME/.config/$LEGACY_PKG_NAME/config.yml"
    [[ -f "$config_file" ]] || return 0

    # Solo interesa el `theme:` que cuelga del bloque `ui:` de primer nivel.
    local current_theme
    current_theme="$(awk '
        /^[^[:space:]#]/ { in_ui = ($0 ~ /^ui[[:space:]]*:/) }
        in_ui && $1 == "theme:" { print $2; exit }
    ' "$config_file" 2>/dev/null || true)"

    case "$current_theme" in
        aurora|matugen|gtk) ;;
        *) return 0 ;;
    esac

    warning "El tema '$current_theme' solo existe en bauh Gekko Edition."
    warning 'Si vuelves a instalar el bauh oficial, no encontrará esa hoja de estilos'
    warning 'y arrancará sin estilos ni iconos en los botones, y sin avisar de por qué.'

    if ! ask "¿Restablecer el tema a 'light' en $config_file? [y/N] "; then
        warning "Se deja '$current_theme'. Si el bauh oficial aparece sin estilos, edita"
        warning "  $config_file  y pon  theme: light  bajo la sección ui."
        return 0
    fi

    local tmp_config
    tmp_config="$(mktemp)"
    if awk '
        /^[^[:space:]#]/ { in_ui = ($0 ~ /^ui[[:space:]]*:/) }
        in_ui && $1 == "theme:" && !done { sub(/theme:.*/, "theme: light"); done = 1 }
        { print }
    ' "$config_file" > "$tmp_config" 2>/dev/null && [[ -s "$tmp_config" ]]; then
        cat "$tmp_config" > "$config_file"
        info "Tema restablecido a 'light'."
    else
        warning 'No se pudo reescribir la configuración; déjalo en manos de «bauh --reset».'
    fi
    rm -f "$tmp_config"
}

# Borra un venv de pipx a mano. Solo se usa si pipx no está disponible, y solo
# sobre venvs con nuestra marca de origen.
remove_venv_manually() {
    local name="$1"
    local venvs bins bin target
    venvs="$(pipx_venv_dir)"
    bins="$(pipx_bin_dir)"

    [[ -d "$venvs/$name" ]] || return 1

    # Ejecutables propios y los del nombre heredado, que instalaban versiones anteriores.
    for bin in "$PKG_NAME" "$PKG_NAME-tray" "$PKG_NAME-cli" bauh bauh-tray bauh-cli; do
        target="$bins/$bin"
        # Solo se retira el lanzador si apunta al venv que estamos borrando.
        if [[ -L "$target" ]]; then
            local dest
            dest="$(readlink -f "$target" 2>/dev/null || true)"
            [[ "$dest" == "$venvs/$name/"* ]] && rm -f "$target"
        elif [[ -f "$target" ]] && grep -q "$venvs/$name/" "$target" 2>/dev/null; then
            rm -f "$target"
        fi
    done

    rm -rf "${venvs:?}/$name"
}

purge_user_data() {
    local user_name
    user_name="$(id -un)"

    # Solo se borran las rutas propias ("$PKG_NAME"). El directorio heredado
    # "$LEGACY_PKG_NAME" pertenece ahora al proyecto original: aunque versiones
    # anteriores de este instalador lo usaran, no hay forma de distinguir sus
    # restos de una instalación oficial en uso, así que se avisa y no se toca.
    # Se cubren las rutas fijas (Path.home()/.config, .cache…) y sus variantes
    # XDG, porque conviven según la versión instalada; los duplicados no molestan.
    local paths=(
        "$HOME/.config/$PKG_NAME"
        "$HOME/.cache/$PKG_NAME"
        "$HOME/.local/share/$PKG_NAME"
        "/tmp/$PKG_NAME@$user_name"
    )
    [[ -n "${XDG_CONFIG_HOME:-}" ]] && paths+=("$XDG_CONFIG_HOME/$PKG_NAME")
    [[ -n "${XDG_CACHE_HOME:-}" ]] && paths+=("$XDG_CACHE_HOME/$PKG_NAME")
    [[ -n "${XDG_DATA_HOME:-}" ]] && paths+=("$XDG_DATA_HOME/$PKG_NAME")
    [[ -n "${XDG_RUNTIME_DIR:-}" ]] && paths+=("$XDG_RUNTIME_DIR/$PKG_NAME")

    local path
    for path in "${paths[@]}"; do
        if [[ -d "$path" ]]; then
            rm -rf "$path"
            info "Eliminado: $path"
        fi
    done

    if [[ -d "$HOME/.config/$LEGACY_PKG_NAME" ]]; then
        warning "No se ha tocado $HOME/.config/$LEGACY_PKG_NAME: ese directorio es del"
        warning 'bauh oficial. Bórralo a mano solo si no lo tienes instalado.'
    fi

    # Los repositorios clonados por la gem GitHub (~/BauhRepos por defecto)
    # pueden contener trabajo del usuario: nunca se borran sin preguntar.
    if [[ -d "$HOME/BauhRepos" ]]; then
        warning "Los repositorios clonados en $HOME/BauhRepos no se borran automáticamente."
        warning 'Revísalos y elimínalos a mano si ya no los necesitas.'
    fi
}

uninstall_main() {
    local applications_dir="$HOME/.local/share/applications"
    local icon_home="$HOME/.local/share/icons/hicolor"
    local autostart_dir="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
    local removed=false
    local pipx_missing=false
    local failed=false

    info 'Desinstalando bauh Gekko Edition...'

    if command -v pipx >/dev/null 2>&1; then
        local name
        for name in "$PKG_NAME" "$LEGACY_PKG_NAME"; do
            pipx_has_package "$name" || continue

            # El venv «bauh» solo se toca si lo creamos nosotros.
            if [[ "$name" == "$LEGACY_PKG_NAME" ]] && ! pipx_venv_is_ours "$name"; then
                warning "Se encontró un venv de pipx llamado '$name' que no instaló este script: se deja intacto."
                continue
            fi

            info "Desinstalando el paquete pipx '$name'..."
            if pipx uninstall "$name"; then
                removed=true
            else
                warning "pipx no pudo desinstalar '$name'."
                failed=true
            fi
        done
    else
        pipx_missing=true
        warning 'pipx no está disponible: se intentará limpiar el entorno a mano.'

        local name
        for name in "$PKG_NAME" "$LEGACY_PKG_NAME"; do
            pipx_has_package "$name" || continue
            if [[ "$name" == "$LEGACY_PKG_NAME" ]] && ! pipx_venv_is_ours "$name"; then
                warning "Se encontró un venv llamado '$name' que no instaló este script: se deja intacto."
                continue
            fi
            if remove_venv_manually "$name"; then
                info "Entorno '$name' eliminado a mano."
                removed=true
            fi
        done
    fi

    rm -f "$applications_dir/$DESKTOP_ID.desktop" "$applications_dir/$TRAY_DESKTOP_ID.desktop"
    rm -f "$autostart_dir/$TRAY_DESKTOP_ID.desktop"

    local size
    for size in "${ICON_SIZES[@]}"; do
        rm -f "$icon_home/${size}x${size}/apps/$ICON_NAME.png"
    done

    remove_legacy_launcher
    refresh_desktop_caches

    if [[ "$PURGE" == true ]]; then
        purge_user_data
    else
        reset_fork_theme
    fi

    # Verificación final: nada de «desinstalado correctamente» si quedan restos.
    local venvs leftovers=()
    venvs="$(pipx_venv_dir)"
    local name
    for name in "$PKG_NAME" "$LEGACY_PKG_NAME"; do
        if [[ -d "$venvs/$name" ]] && [[ "$name" == "$PKG_NAME" || -f "$venvs/$name/$REF_STAMP_NAME" ]]; then
            leftovers+=("$venvs/$name")
        fi
    done

    local resolved
    resolved="$(command -v bauh 2>/dev/null || true)"
    if [[ -n "$resolved" ]]; then
        local dest
        dest="$(readlink -f "$resolved" 2>/dev/null || printf '%s' "$resolved")"
        if [[ "$dest" == "$venvs/$PKG_NAME/"* || "$dest" == "$venvs/$LEGACY_PKG_NAME/"* ]]; then
            leftovers+=("$resolved")
        fi
    fi

    if ((${#leftovers[@]} > 0)); then
        error 'La desinstalación NO se completó. Quedan estos restos:'
        local leftover
        for leftover in "${leftovers[@]}"; do
            error "  $leftover"
        done
        error 'Elimínalos a mano o instala pipx y vuelve a ejecutar: install.sh uninstall'
        return 1
    fi

    if [[ "$removed" != true ]]; then
        warning 'No se encontró ninguna instalación de bauh Gekko Edition hecha por este script.'
        warning 'Se limpiaron de todos modos iconos y accesos directos, por si habían quedado sueltos.'
        return 1
    fi

    if [[ "$failed" == true ]]; then
        error 'Algún paso de la desinstalación falló; revisa los avisos anteriores.'
        return 1
    fi

    if [[ "$pipx_missing" == true ]]; then
        warning 'Se eliminó el entorno a mano porque pipx no estaba disponible.'
        warning 'Comprueba con «pipx list» (tras instalar pipx) que no queda nada.'
        return 1
    fi

    printf '%b\n' "${green}${bold}bauh Gekko Edition fue desinstalado correctamente.${reset}"
    return 0
}

# ─────────────────────────────── Instalación ──────────────────────────────────

# Ofrece desinstalar el bauh original de los repositorios para evitar conflictos.
# Es una acción con sudo: requiere --remove-system-bauh o una respuesta explícita
# en un terminal (F51).
handle_original_bauh() {
    local original_pm
    original_pm="$(detect_original_bauh)"
    [[ -n "$original_pm" ]] || return 0

    warning "Se detectó el paquete 'bauh' original instalado desde los repositorios del sistema ($original_pm)."
    warning 'Ambas versiones pueden convivir: este instalador usa identificadores propios'
    warning 'y no toca el lanzador ni el icono del paquete oficial.'

    if ! ask_privileged '¿Desinstalar el bauh original ahora? [y/N] ' "$REMOVE_SYSTEM_BAUH" '--remove-system-bauh'; then
        info 'Se conserva el bauh original. Continuando con la instalación del fork...'
        return 0
    fi

    local remove_cmd=()
    if [[ "$original_pm" == "pacman" ]]; then
        remove_cmd=(sudo pacman -Rns --noconfirm bauh)
    else
        remove_cmd=(sudo eopkg remove -y bauh)
    fi

    if ! sudo_available; then
        warning "Desinstálalo manualmente con: ${remove_cmd[*]}"
        return 0
    fi

    info "Desinstalando bauh original con $original_pm..."
    if "${remove_cmd[@]}"; then
        info 'Bauh original desinstalado. Continuando con la instalación del fork...'
    else
        warning "No se pudo desinstalar automáticamente. Hazlo manualmente con: ${remove_cmd[*]}"
    fi
}

check_chaotic_aur() {
    [[ -f /etc/pacman.conf ]] || return 0
    grep -qE '^\[chaotic-aur\]' /etc/pacman.conf && return 0

    warning 'El repositorio chaotic-aur no fue encontrado en /etc/pacman.conf.'
    warning 'Este fork está optimizado para sistemas Arch Linux con Chaotic AUR habilitado.'

    # Sin terminal no se puede preguntar; cancelar por defecto dejaría inservible
    # el one-liner de curl en cualquier equipo sin Chaotic AUR, así que se avisa
    # y se continúa.
    if [[ "$ASSUME_YES" != true ]] && ! has_tty; then
        warning 'Sin terminal interactivo: se continúa de todos modos (bauh funcionará, pero sin los binarios de Chaotic AUR).'
        return 0
    fi

    if ! ask '¿Continuar de todos modos? [y/N] '; then
        info 'Instalación cancelada.'
        exit 0
    fi
}

# Instala los iconos de hicolor. Cada tamaño usa su PNG propio
# (pictures/icons/gekko-bauh-<N>.png); si alguno falta se recurre al PNG grande,
# que al menos se ve, en vez de abortar.
install_icons() {
    local icons_dir="$1"
    local fallback="$2"
    local icon_home="$HOME/.local/share/icons/hicolor"
    local size source missing=0

    for size in "${ICON_SIZES[@]}"; do
        source="$icons_dir/gekko-bauh-$size.png"

        if [[ ! -f "$source" ]]; then
            source="$fallback"
            missing=$((missing + 1))
        fi

        [[ -f "$source" ]] || continue

        mkdir -p "$icon_home/${size}x${size}/apps"
        install -Dm644 "$source" "$icon_home/${size}x${size}/apps/$ICON_NAME.png"
    done

    if ((missing > 0)); then
        warning "Faltan $missing icono(s) por tamaño en pictures/icons/; se usó el PNG grande como sustituto."
    fi
}

# Escribe un .desktop a partir de la plantilla del repositorio, cambiando Exec=
# por la ruta real del binario de pipx y marcándolo como nuestro.
render_desktop() {
    local template="$1"
    local exec_path="$2"
    local dest="$3"
    local exec_value="$exec_path"

    # El campo Exec solo necesita comillas si la ruta lleva espacios.
    if [[ "$exec_path" == *[[:space:]]* ]]; then
        exec_value="\"$exec_path\""
    fi

    awk -v exec_value="$exec_value" -v icon_name="$ICON_NAME" '
        /^Exec=/ { print "Exec=" exec_value; next }
        /^Icon=/ { print "Icon=" icon_name; next }
        /^X-Gekko-Edition=/ { next }
        { print }
        END { print "X-Gekko-Edition=true" }
    ' "$template" > "$dest"
}

install_desktop_entries() {
    local desktop_dir="$1"
    local pipx_bin="$2"
    local applications_dir="$HOME/.local/share/applications"
    local autostart_dir="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

    mkdir -p "$applications_dir"

    if [[ -f "$desktop_dir/gekko-bauh.desktop" ]]; then
        render_desktop "$desktop_dir/gekko-bauh.desktop" "$pipx_bin/$PKG_NAME" "$applications_dir/$DESKTOP_ID.desktop"
    else
        warning 'No se encontró la plantilla gekko-bauh.desktop; el lanzador principal no se instalará.'
    fi

    if [[ ! -f "$desktop_dir/gekko-bauh-tray.desktop" ]]; then
        warning 'No se encontró la plantilla gekko-bauh-tray.desktop; la bandeja no tendrá lanzador.'
        return 0
    fi

    local tray_desktop="$applications_dir/$TRAY_DESKTOP_ID.desktop"
    render_desktop "$desktop_dir/gekko-bauh-tray.desktop" "$pipx_bin/$PKG_NAME-tray" "$tray_desktop"

    local enable_autostart="$AUTOSTART_TRAY"
    if [[ -z "$enable_autostart" ]]; then
        if ask '¿Arrancar la bandeja al iniciar sesión? [y/N] '; then
            enable_autostart=true
        else
            enable_autostart=false
        fi
    fi

    if [[ "$enable_autostart" == true ]]; then
        mkdir -p "$autostart_dir"
        cp "$tray_desktop" "$autostart_dir/$TRAY_DESKTOP_ID.desktop"
        info "Bandeja configurada para arrancar con la sesión ($autostart_dir/$TRAY_DESKTOP_ID.desktop)."
    else
        rm -f "$autostart_dir/$TRAY_DESKTOP_ID.desktop"
    fi
}

# Retira el venv «bauh» que dejaron versiones anteriores de este instalador. Un
# venv «bauh» ajeno (instalado por el usuario a mano) se respeta.
migrate_legacy_package() {
    pipx_has_package "$LEGACY_PKG_NAME" || return 0

    if ! pipx_venv_is_ours "$LEGACY_PKG_NAME"; then
        warning "Existe un paquete pipx llamado '$LEGACY_PKG_NAME' que no instaló este script."
        warning "No se tocará. La nueva instalación usará el nombre '$PKG_NAME'."
        return 0
    fi

    info "Se detectó una instalación anterior registrada como '$LEGACY_PKG_NAME'; se sustituye por '$PKG_NAME'."
    if ! pipx uninstall "$LEGACY_PKG_NAME"; then
        warning "No se pudo desinstalar '$LEGACY_PKG_NAME'. Hazlo con: pipx uninstall $LEGACY_PKG_NAME"
    fi
}

install_main() {
    local python_version python_supported pm
    local PYTHON_BIN="${PYTHON_BIN:-python3}"

    if ! command -v curl >/dev/null 2>&1; then
        error "'curl' es necesario y no está instalado."
        exit 1
    fi

    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
        error "El intérprete de Python '$PYTHON_BIN' no fue encontrado. Define PYTHON_BIN con un Python 3.8+."
        exit 1
    fi

    if ! python_version="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"; then
        error "No se pudo determinar la versión de '$PYTHON_BIN'."
        exit 1
    fi

    python_supported="$("$PYTHON_BIN" -c 'import sys; print((3, 8) <= sys.version_info[:2] <= (3, 14))')"
    if [[ "$python_supported" != 'True' ]]; then
        error "bauh soporta Python 3.8 a 3.14; '$PYTHON_BIN' es Python $python_version."
        exit 1
    fi

    pm="$(detect_pkg_manager)"
    [[ -n "$pm" ]] && handle_original_bauh
    check_chaotic_aur
    ensure_pipx

    local pipx_bin
    pipx_bin="$(pipx_bin_dir)"
    local bauh_bin="$pipx_bin/$PKG_NAME"

    # Resolver la fuente: checkout local o commit exacto (modo curl).
    local source_spec=""
    local icons_dir=""
    local icon_fallback=""
    local desktop_dir=""
    local resolved_ref=""
    local tmp_dir=""

    if [[ "$LOCAL_MODE" == true ]]; then
        info "Modo local: instalando desde el checkout en $SCRIPT_DIR"
        source_spec="$SCRIPT_DIR"
        icons_dir="$SCRIPT_DIR/pictures/icons"
        icon_fallback="$SCRIPT_DIR/pictures/gekko-bauh.png"
        desktop_dir="$SCRIPT_DIR/bauh/desktop"

        if [[ ! -f "$icon_fallback" ]]; then
            icon_fallback="$SCRIPT_DIR/bauh/view/resources/img/gekko-bauh.png"
        fi
    else
        # Se resuelve la referencia ANTES de descargar y se descarga ese commit
        # exacto: así lo instalado y la marca guardada son siempre lo mismo.
        info "Resolviendo '$REQUESTED_REF' en GitHub..."
        resolved_ref="$(resolve_ref "$REQUESTED_REF")"

        if [[ ! "$resolved_ref" =~ ^[0-9a-f]{40}$ ]]; then
            error "No se pudo resolver '$REQUESTED_REF' a un commit del repositorio $REPO."
            error 'Comprueba tu conexión, el límite de peticiones de la API de GitHub'
            error "y que la referencia existe. También puedes pasar un SHA con: --ref <sha>"
            exit 1
        fi

        info "Commit resuelto: $resolved_ref"
        tmp_dir="$(mktemp -d)"
        trap 'rm -rf "${tmp_dir:-}"' EXIT
        source_spec="$ARCHIVE_BASE/$resolved_ref.zip"

        icons_dir="$tmp_dir/icons"
        icon_fallback="$tmp_dir/gekko-bauh.png"
        desktop_dir="$tmp_dir/desktop"
        mkdir -p "$icons_dir" "$desktop_dir"

        info 'Descargando iconos y lanzadores del commit resuelto...'
        local size
        for size in "${ICON_SIZES[@]}"; do
            curl -fsSL -o "$icons_dir/gekko-bauh-$size.png" \
                "$RAW_BASE/$resolved_ref/pictures/icons/gekko-bauh-$size.png" 2>/dev/null \
                || rm -f "$icons_dir/gekko-bauh-$size.png"
        done

        curl -fsSL -o "$icon_fallback" "$RAW_BASE/$resolved_ref/pictures/gekko-bauh.png" 2>/dev/null \
            || curl -fsSL -o "$icon_fallback" "$RAW_BASE/$resolved_ref/bauh/view/resources/img/gekko-bauh.png" 2>/dev/null \
            || rm -f "$icon_fallback"

        local desktop_file
        for desktop_file in gekko-bauh.desktop gekko-bauh-tray.desktop; do
            curl -fsSL -o "$desktop_dir/$desktop_file" \
                "$RAW_BASE/$resolved_ref/bauh/desktop/$desktop_file" 2>/dev/null \
                || rm -f "$desktop_dir/$desktop_file"
        done
    fi

    # Aceleración: omitir el rebuild solo si ya está instalado exactamente el
    # mismo commit. Comparar __version__ no vale: master recibe decenas de
    # commits sin cambiar el número de versión.
    local skip_build=false
    if [[ "$LOCAL_MODE" != true && "$FORCE" != true && -n "$resolved_ref" ]]; then
        if [[ "$resolved_ref" == "$(installed_ref)" && -n "$(installed_version)" ]]; then
            skip_build=true
        fi
    fi

    if [[ "$skip_build" == true ]]; then
        info "Ya está instalado ese commit (${resolved_ref:0:7}, versión $(installed_version))."
        info "Omitiendo la reconstrucción del entorno pipx. Usa '--force' para reinstalar igualmente."
    else
        migrate_legacy_package

        info "Instalando $PKG_NAME con $PYTHON_BIN (Python $python_version)..."
        info "Fuente: $source_spec"

        local extra_flags=()
        # El backend de uv se niega a sobrescribir un venv que no creó en esta
        # sesión; forzamos que limpie el venv existente para reinstalar de verdad.
        # (La variable es inofensiva si pipx acaba usando el backend de pip.)
        export UV_VENV_CLEAR=1
        if ! command -v uv >/dev/null 2>&1 && pipx install --help 2>&1 | grep -q -- '--backend'; then
            extra_flags+=(--backend pip)
        fi

        # Las dependencias deben llegar como wheel: si alguna cayera a sdist, el
        # usuario vería un traceback de compilación de sip/yaml al final del
        # proceso en vez de un mensaje claro (F142). El propio paquete no está en
        # la lista: ese sí se construye desde el código descargado.
        if [[ "$ALLOW_SOURCE_BUILD" != true ]]; then
            export PIP_ONLY_BINARY="$WHEEL_ONLY_PACKAGES"
            export UV_NO_BUILD_PACKAGE="$WHEEL_ONLY_PACKAGES"
        fi

        if ! pipx install --force --python "$PYTHON_BIN" \
                ${extra_flags[@]+"${extra_flags[@]}"} "$source_spec"; then
            error 'pipx no pudo instalar bauh Gekko Edition.'
            if [[ "$ALLOW_SOURCE_BUILD" != true ]]; then
                error "Si el fallo menciona que no hay wheel para Python $python_version, tienes dos salidas:"
                error "  1) Usa otro intérprete:  PYTHON_BIN=python3.12 ...  (recomendado)"
                error '  2) Compílalas tú: instala el toolchain y repite con --allow-build-from-source'
                error '       Arch/Garuda:  sudo pacman -S --needed base-devel'
                error '       Solus:        sudo eopkg install -c system.devel python3-devel'
            fi
            exit 1
        fi

        if [[ "$LOCAL_MODE" == true ]]; then
            # Instalación desde checkout: no hay commit remoto que registrar,
            # pero sí dejamos la marca para reconocer el venv como nuestro.
            save_installed_ref "local:$SCRIPT_DIR"
        else
            save_installed_ref "$resolved_ref"
        fi
    fi

    if ! pipx_has_package "$PKG_NAME"; then
        error "pipx terminó pero no existe el entorno de '$PKG_NAME'. Revísalo con: pipx list"
        exit 1
    fi

    if [[ ! -x "$bauh_bin" ]]; then
        error "pipx terminó pero no se creó '$bauh_bin'. Revísalo con: pipx list"
        exit 1
    fi

    info 'Instalando iconos y accesos directos del escritorio...'
    install_icons "$icons_dir" "$icon_fallback"
    install_desktop_entries "$desktop_dir" "$pipx_bin"
    remove_legacy_launcher
    refresh_desktop_caches

    printf '%b\n' "${green}${bold}bauh Gekko Edition fue instalado correctamente.${reset}"
    printf 'Ejecútalo desde tu menú de aplicaciones o con: %s\n' "$bauh_bin"

    if [[ ":$PATH:" != *":$pipx_bin:"* ]]; then
        warning "'$pipx_bin' no está en tu PATH. Ejecuta 'pipx ensurepath' y abre una terminal nueva para usar 'bauh' por nombre."
    fi
}

# ─────────────────────────────────── Main ─────────────────────────────────────

if [[ "$ACTION" == "uninstall" ]]; then
    uninstall_main
else
    install_main
fi
