#!/usr/bin/env bash

# El script usa sintaxis exclusiva de bash ([[ ]], arrays, (( ))). Si alguien lo
# ejecuta con sh/dash, avisamos antes de que falle con errores de sintaxis.
if [ -z "${BASH_VERSION:-}" ]; then
    echo "[bauh] Este instalador necesita bash. Ejecútalo con: bash install.sh" >&2
    exit 1
fi

set -Eeuo pipefail

# ══════════════════════════════════════════════════════════════════════════════
#  Gekko Bauh — instalador / desinstalador (100% por curl, sin clonar el repo)
#
#  Instalar/actualizar:   curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash
#  Forzar reinstall:      curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- --force
#  Desinstalar:           curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- uninstall [--purge]
#
#  Requisitos: curl, pipx y Python 3.8–3.14. pipx se instala con:
#    Arch/Garuda:  sudo pacman -S python-pipx
#    Solus:        sudo eopkg install -y pipx
# ══════════════════════════════════════════════════════════════════════════════

REPO="The-Gekko/Bauh-Fork-The-Gekko"
RAW_BASE="https://raw.githubusercontent.com/$REPO"
CODELOAD_BASE="https://github.com/$REPO/archive/refs"

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
if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/setup.py" && -d "$SCRIPT_DIR/bauh" ]]; then
    LOCAL_MODE=true
fi

ASSUME_YES=false
FORCE=false
PURGE=false
ACTION="install"

usage() {
    cat <<'EOF'
Usage: install.sh [ACTION] [OPCIONES]

Ejecutado por curl (modo remoto) descarga el código fuente actual de master
desde GitHub y lo instala aislado con pipx. Desde un checkout del repo también
sirve como instalador local.

Acciones:
  install      Instala o actualiza bauh (por defecto)
  uninstall    Desinstala bauh y elimina icono y acceso directo del escritorio

Opciones:
  --yes, -y    Continúa sin confirmaciones interactivas
  --force, -f  Fuerza la reconstrucción del entorno pipx aunque ya esté instalado el mismo commit
  --purge      (con uninstall) borra también la configuración de usuario (~/.config/bauh)
  --help, -h   Muestra esta ayuda

Entorno:
  PYTHON_BIN   Intérprete Python usado por pipx (por defecto: python3)

Ejemplos:
  curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash
  curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- uninstall --purge
EOF
}

while (($#)); do
    case "$1" in
        install)
            ACTION="install" ;;
        uninstall)
            ACTION="uninstall" ;;
        --yes|-y)
            ASSUME_YES=true ;;
        --force|-f)
            FORCE=true ;;
        --purge)
            PURGE=true ;;
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

# Pregunta sí/no.
#
# IMPORTANTE: con `curl ... | bash` la entrada estándar del script ES el propio
# script, así que un `read` normal se come las siguientes líneas del código (o
# devuelve EOF y, con `set -e`, aborta la instalación en silencio). Por eso
# leemos siempre desde el terminal (/dev/tty). Si no hay terminal (CI, cron,
# systemd) la respuesta por defecto es "no", salvo que se haya pasado --yes.
ask() {
    local prompt="$1"
    local answer=""

    if [[ "$ASSUME_YES" == true ]]; then
        return 0
    fi

    if ! has_tty; then
        warning 'Sin terminal interactivo: se asume "no". Usa --yes para responder que sí automáticamente.'
        return 1
    fi

    read -r -p "$prompt" answer < /dev/tty 2>/dev/null || answer=""
    case "${answer,,}" in
        y|yes|s|si|sí) return 0 ;;
        *) return 1 ;;
    esac
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

    local pm pipx_cmd
    pm="$(detect_pkg_manager)"
    case "$pm" in
        pacman) pipx_cmd="sudo pacman -S python-pipx" ;;
        eopkg)  pipx_cmd="sudo eopkg install -y pipx" ;;
        *)      pipx_cmd="" ;;
    esac

    if [[ -z "$pipx_cmd" ]]; then
        error "No se pudo detectar el gestor de paquetes del sistema. Instala pipx manualmente y reintenta."
        exit 1
    fi

    warning 'pipx no está instalado y es obligatorio.'
    if ask "¿Instalarlo ahora con \`$pipx_cmd\`? [y/N] "; then
        info "Ejecutando: $pipx_cmd"
        eval "$pipx_cmd"
    else
        error "pipx es obligatorio. Instálalo manualmente y vuelve a ejecutar el instalador:"
        error "  $pipx_cmd"
        exit 1
    fi

    if ! command -v pipx >/dev/null 2>&1; then
        error "pipx sigue sin estar disponible tras la instalación."
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

# Versión instalada actualmente (leída del venv de pipx), vacía si no está instalada.
installed_version() {
    local py
    py="$(pipx_venv_dir)/bauh/bin/python"
    if [[ -x "$py" ]]; then
        "$py" -c 'import bauh; print(bauh.__version__)' 2>/dev/null || true
    fi
}

# Marca con el commit exacto de master que se instaló. Vive dentro del venv de
# pipx, así que `pipx uninstall` se la lleva por delante automáticamente.
ref_stamp_file() {
    printf '%s' "$(pipx_venv_dir)/bauh/.gekko-source-ref"
}

installed_ref() {
    local f
    f="$(ref_stamp_file)"
    if [[ -f "$f" ]]; then
        tr -d '[:space:]' < "$f" 2>/dev/null || true
    fi
}

save_installed_ref() {
    local f dir
    f="$(ref_stamp_file)"
    dir="$(dirname "$f")"
    [[ -d "$dir" ]] || return 0
    printf '%s\n' "$1" > "$f" 2>/dev/null || true
}

# Commit actual de master en GitHub. Identifica la fuente exacta que se va a
# instalar; __version__ no sirve para esto porque master cambia muchas veces
# sin que se suba el número de versión.
master_ref() {
    curl -fsSL -H 'Accept: application/vnd.github.sha' \
        "https://api.github.com/repos/$REPO/commits/master" 2>/dev/null \
        | tr -d '[:space:]' || true
}

pipx_bin_dir() {
    local dir
    dir="$(pipx environment --value PIPX_BIN_DIR 2>/dev/null || true)"
    printf '%s' "${dir:-$HOME/.local/bin}"
}

refresh_desktop_caches() {
    local applications_dir="$HOME/.local/share/applications"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$applications_dir" || warning 'No se pudo actualizar la base de datos de escritorio.'
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" || warning 'No se pudo actualizar la caché de iconos.'
    fi
}

# ───────────────────────────── Desinstalación ─────────────────────────────────

uninstall_main() {
    local applications_dir="$HOME/.local/share/applications"
    local icon_home="$HOME/.local/share/icons/hicolor"

    info 'Desinstalando bauh...'

    if command -v pipx >/dev/null 2>&1 && [[ -d "$(pipx_venv_dir)/bauh" ]]; then
        pipx uninstall bauh || warning 'pipx no pudo desinstalar bauh automáticamente.'
    fi

    rm -f "$applications_dir/bauh.desktop" "$applications_dir/bauh_tray.desktop"
    for size in 48x48 64x64 128x128 256x256 512x512; do
        rm -f "$icon_home/$size/apps/bauh.png"
    done

    refresh_desktop_caches

    if [[ "$PURGE" == true ]]; then
        if [[ -d "$HOME/.config/bauh" ]]; then
            rm -rf "$HOME/.config/bauh"
            info 'Configuración de usuario (~/.config/bauh) eliminada.'
        fi
    fi

    printf '%b\n' "${green}${bold}bauh fue desinstalado correctamente.${reset}"
}

# ─────────────────────────────── Instalación ──────────────────────────────────

# Ofrece desinstalar el bauh original de los repositorios para evitar conflictos.
handle_original_bauh() {
    local original_pm
    original_pm="$(detect_original_bauh)"
    [[ -n "$original_pm" ]] || return 0

    warning "Se detectó el paquete 'bauh' original instalado desde los repositorios del sistema ($original_pm)."
    warning 'Es MUY recomendable desinstalarlo antes de instalar este fork para evitar conflictos.'

    if ask '¿Deseas desinstalar el bauh original ahora? [y/N] '; then
        info "Desinstalando bauh original con $original_pm..."
        local removed=true
        if [[ "$original_pm" == "pacman" ]]; then
            sudo pacman -Rns --noconfirm bauh || removed=false
        else
            sudo eopkg remove -y bauh || removed=false
        fi
        if [[ "$removed" == true ]]; then
            info 'Bauh original desinstalado. Continuando con la instalación del fork...'
        elif [[ "$original_pm" == "pacman" ]]; then
            warning 'No se pudo desinstalar automáticamente. Hazlo manualmente con: sudo pacman -Rns bauh'
        else
            warning 'No se pudo desinstalar automáticamente. Hazlo manualmente con: sudo eopkg remove bauh'
        fi
    else
        warning 'Continuando sin desinstalar. Pueden ocurrir conflictos entre ambas versiones.'
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

install_icon_and_desktop() {
    local icon_source="$1"
    local bauh_bin="$2"
    local applications_dir="$HOME/.local/share/applications"
    local desktop_file="$applications_dir/bauh.desktop"

    info 'Instalando icono y acceso directo del escritorio...'
    for size in 48x48 64x64 128x128 256x256 512x512; do
        local icon_dir="$HOME/.local/share/icons/hicolor/$size/apps"
        mkdir -p "$icon_dir"
        install -Dm644 "$icon_source" "$icon_dir/bauh.png"
    done
    mkdir -p "$applications_dir"

    cat > "$desktop_file" <<EOF
[Desktop Entry]
Type=Application
Name=Bauh Fork The-Gekko
Comment=Manage Linux applications
Exec="$bauh_bin"
Icon=bauh
Terminal=false
Categories=System;Settings;PackageManager;
EOF

    refresh_desktop_caches
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
    local bauh_bin="$pipx_bin/bauh"

    # Resolver la fuente: checkout local o zip de master (modo curl).
    local source_spec=""
    local icon_source=""
    local tmp_dir=""
    if [[ "$LOCAL_MODE" == true ]]; then
        info "Modo local: instalando desde el checkout en $SCRIPT_DIR"
        source_spec="$SCRIPT_DIR"
        icon_source="$SCRIPT_DIR/pictures/gekko-bauh.png"
        if [[ ! -f "$icon_source" ]]; then
            icon_source="$SCRIPT_DIR/bauh/view/resources/img/gekko-bauh.png"
        fi
        if [[ ! -f "$icon_source" ]]; then
            error "No se encontró el icono de la aplicación: $icon_source"
            exit 1
        fi
    else
        # Instala siempre desde master: el último release (v0.10.7) es anterior al
        # rebrand y no incluye el icono de Gekko ni los fixes actuales.
        tmp_dir="$(mktemp -d)"
        trap 'rm -rf "${tmp_dir:-}"' EXIT
        source_spec="$CODELOAD_BASE/heads/master.zip"

        info "Descargando icono desde GitHub (master)..."
        icon_source="$tmp_dir/gekko-bauh.png"
        curl -fsSL -o "$icon_source" "$RAW_BASE/master/pictures/gekko-bauh.png" \
            || curl -fsSL -o "$icon_source" "$RAW_BASE/master/bauh/view/resources/img/gekko-bauh.png" \
            || { error 'No se pudo descargar el icono de la aplicación.'; exit 1; }
    fi

    # Aceleración: omitir el rebuild del entorno pipx solo si ya está instalado
    # exactamente el mismo commit de master. Comparar __version__ no vale: master
    # recibe decenas de commits sin cambiar el número de versión, así que el
    # instalador parecía "no hacer nada" al actualizar.
    local remote_ref=""
    local skip_build=false
    if [[ "$LOCAL_MODE" != true ]]; then
        remote_ref="$(master_ref)"
        if [[ "$FORCE" != true && -n "$remote_ref" \
              && "$remote_ref" == "$(installed_ref)" && -n "$(installed_version)" ]]; then
            skip_build=true
        fi
    fi

    if [[ "$skip_build" == true ]]; then
        info "Ya está instalado el commit actual de master (${remote_ref:0:7}, versión $(installed_version))."
        info "Omitiendo la reconstrucción del entorno pipx. Usa '--force' para reinstalar igualmente."
    else
        info "Instalando bauh con $PYTHON_BIN (Python $python_version)..."
        info "Fuente: $source_spec"
        local extra_flags=()
        # El backend de uv se niega a sobrescribir un venv que no creó en esta
        # sesión; forzamos que limpie el venv existente para reinstalar de verdad.
        # (La variable es inofensiva si pipx acaba usando el backend de pip.)
        export UV_VENV_CLEAR=1
        if ! command -v uv >/dev/null 2>&1 && pipx install --help 2>&1 | grep -q -- '--backend'; then
            extra_flags+=(--backend pip)
        fi
        pipx install --force ${extra_flags[@]+"${extra_flags[@]}"} "$source_spec"

        if [[ "$LOCAL_MODE" == true ]]; then
            # Instalación desde checkout: la marca de commit remoto ya no aplica.
            rm -f "$(ref_stamp_file)" 2>/dev/null || true
        elif [[ -n "$remote_ref" ]]; then
            save_installed_ref "$remote_ref"
        fi
    fi

    if [[ ! -x "$bauh_bin" ]]; then
        error "pipx terminó pero no se creó '$bauh_bin'. Revisa 'pipx list'."
        exit 1
    fi

    install_icon_and_desktop "$icon_source" "$bauh_bin"

    printf '%b\n' "${green}${bold}bauh fue instalado correctamente.${reset}"
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
