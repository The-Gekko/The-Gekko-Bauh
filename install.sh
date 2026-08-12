#!/usr/bin/env bash

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
  --force, -f  Fuerza la reconstrucción del entorno pipx aunque la versión ya esté instalada
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

    if [[ -n "$pipx_cmd" ]]; then
        if [[ "$ASSUME_YES" == true ]]; then
            info "pipx no está instalado. Ejecutando: $pipx_cmd"
            eval "$pipx_cmd"
        else
            read -r -p 'pipx no está instalado. ¿Instalarlo ahora con sudo? [y/N] ' answer
            if [[ "$answer" =~ ^[Yy]$ ]]; then
                info "Ejecutando: $pipx_cmd"
                eval "$pipx_cmd"
            else
                error "pipx es obligatorio. Instálalo manualmente y vuelve a ejecutar el instalador:"
                error "  $pipx_cmd"
                exit 1
            fi
        fi
    else
        error "No se pudo detectar el gestor de paquetes del sistema. Instala pipx manualmente y reintenta."
        exit 1
    fi

    if ! command -v pipx >/dev/null 2>&1; then
        error "pipx sigue sin estar disponible tras la instalación."
        exit 1
    fi
}

# Versión instalada actualmente (leída del venv de pipx), vacía si no está instalada.
installed_version() {
    local py="$HOME/.local/share/pipx/venvs/bauh/bin/python"
    if [[ -x "$py" ]]; then
        "$py" -c 'import bauh; print(bauh.__version__)' 2>/dev/null || true
    fi
}

# Versión actual en master (para omitir el rebuild si ya está instalada la misma).
master_version() {
    curl -fsSL "$RAW_BASE/master/bauh/__init__.py" 2>/dev/null \
        | grep -m1 '__version__' \
        | sed -E "s/.*__version__ *= *['\"]([^'\"]+)['\"].*/\1/" || true
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

    if command -v pipx >/dev/null 2>&1 && [[ -d "$HOME/.local/share/pipx/venvs/bauh" ]]; then
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
    local original original_pm
    original="$(detect_original_bauh)"
    [[ -n "$original" ]] || return 0
    original_pm="$original"

    warning "Se detectó el paquete 'bauh' original instalado desde los repositorios del sistema ($original_pm)."
    warning 'Es MUY recomendable desinstalarlo antes de instalar este fork para evitar conflictos.'

    if [[ "$ASSUME_YES" == true ]]; then
        info "Desinstalando bauh original con $original_pm..."
        if [[ "$original_pm" == "pacman" ]]; then
            sudo pacman -Rns --noconfirm bauh \
                || warning 'No se pudo desinstalar automáticamente. Hazlo manualmente con: sudo pacman -Rns bauh'
        else
            sudo eopkg remove -y bauh \
                || warning 'No se pudo desinstalar automáticamente. Hazlo manualmente con: sudo eopkg remove bauh'
        fi
        info 'Bauh original desinstalado.'
    else
        read -r -p '¿Deseas desinstalar el bauh original ahora? [y/N] ' answer
        if [[ "$answer" =~ ^[Yy]$ ]]; then
            info "Desinstalando bauh original con $original_pm..."
            if [[ "$original_pm" == "pacman" ]]; then
                sudo pacman -Rns --noconfirm bauh \
                    || warning 'No se pudo desinstalar automáticamente. Hazlo manualmente con: sudo pacman -Rns bauh'
            else
                sudo eopkg remove -y bauh \
                    || warning 'No se pudo desinstalar automáticamente. Hazlo manualmente con: sudo eopkg remove bauh'
            fi
            info 'Bauh original desinstalado. Continuando con la instalación del fork...'
        else
            warning 'Continuando sin desinstalar. Pueden ocurrir conflictos entre ambas versiones.'
        fi
    fi
}

check_chaotic_aur() {
    if [[ -f /etc/pacman.conf ]] && ! grep -qE '^\[chaotic-aur\]' /etc/pacman.conf; then
        warning 'El repositorio chaotic-aur no fue encontrado en /etc/pacman.conf.'
        warning 'Este fork está optimizado para sistemas Arch Linux con Chaotic AUR habilitado.'

        if [[ "$ASSUME_YES" != true ]]; then
            read -r -p '¿Continuar de todos modos? [y/N] ' answer
            if [[ ! "$answer" =~ ^[Yy]$ ]]; then
                info 'Instalación cancelada.'
                exit 0
            fi
        fi
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
    local ref=""
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
        ref="master"
        tmp_dir="$(mktemp -d)"
        trap 'rm -rf "${tmp_dir:-}"' EXIT
        source_spec="$CODELOAD_BASE/heads/master.zip"

        info "Descargando icono desde GitHub (master)..."
        icon_source="$tmp_dir/gekko-bauh.png"
        curl -fsSL -o "$icon_source" "$RAW_BASE/master/pictures/gekko-bauh.png" \
            || curl -fsSL -o "$icon_source" "$RAW_BASE/master/bauh/view/resources/img/gekko-bauh.png" \
            || { error 'No se pudo descargar el icono de la aplicación.'; exit 1; }
    fi

    # Aceleración: omitir el rebuild del entorno pipx si ya está la misma versión.
    local installed=""
    local remote=""
    if [[ "$LOCAL_MODE" != true ]]; then
        remote="$(master_version)"
    fi
    installed="$(installed_version || true)"

    if [[ "$FORCE" != true && -n "$installed" && -n "$remote" && "$installed" == "$remote" ]]; then
        info "Ya está instalada la versión $installed (actual en master)."
        info "Omitiendo la reconstrucción del entorno pipx. Usa '--force' para reinstalarla igualmente."
    else
        info "Instalando bauh con $PYTHON_BIN (Python $python_version)..."
        info "Fuente: $source_spec"
        local extra_flags=()
        if command -v uv >/dev/null 2>&1; then
            # El backend de uv se niega a sobrescribir un venv que no creó en esta
            # sesión; forzamos que limpie el venv existente para reinstalar de verdad.
            export UV_VENV_CLEAR=1
        else
            extra_flags+=(--backend pip)
        fi
        pipx install --force "${extra_flags[@]}" "$source_spec"
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
