#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ASSUME_YES=false

green='\033[0;32m'
yellow='\033[0;33m'
red='\033[0;31m'
blue='\033[0;34m'
bold='\033[1m'
reset='\033[0m'

info() {
    printf '%b\n' "${blue}[bauh]${reset} $*"
}

warning() {
    printf '%b\n' "${yellow}[bauh]${reset} $*"
}

error() {
    printf '%b\n' "${red}[bauh]${reset} $*" >&2
}

usage() {
    cat <<'EOF'
Usage: ./install.sh [--yes] [--help]

Installs the current checkout with pipx and creates a user desktop entry.

Environment variables:
  PYTHON_BIN  Python interpreter to create the pipx environment (default: python3)

Options:
  --yes       Continue without interactive confirmations.
  --help       Show this help message.
EOF
}

while (($#)); do
    case "$1" in
        --yes|-y)
            ASSUME_YES=true
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            usage >&2
            exit 2
            ;;
    esac
    shift
done

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    error "Python interpreter '$PYTHON_BIN' was not found. Set PYTHON_BIN to a Python 3.8+ interpreter."
    exit 1
fi

if ! python_version="$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"; then
    error "Could not determine the version of '$PYTHON_BIN'."
    exit 1
fi

python_supported="$($PYTHON_BIN -c 'import sys; print((3, 8) <= sys.version_info[:2] <= (3, 14))')"

if [[ "$python_supported" != 'True' ]]; then
    error "bauh supports Python versions 3.8 through 3.14; '$PYTHON_BIN' is Python $python_version."
    exit 1
fi

if ! command -v pipx >/dev/null 2>&1; then
    error "pipx is required but was not found. Install it with your distribution package manager and run this script again."
    error "On Arch-based systems: sudo pacman -S python-pipx"
    exit 1
fi

# --- Detect and offer to remove the original bauh installed from repos ---
original_bauh_found=false
original_bauh_pkg=""

if command -v pacman >/dev/null 2>&1 && pacman -Qi bauh >/dev/null 2>&1; then
    original_bauh_found=true
    original_bauh_pkg="pacman"
elif command -v eopkg >/dev/null 2>&1 && eopkg info bauh 2>/dev/null | grep -q 'Installed'; then
    original_bauh_found=true
    original_bauh_pkg="eopkg"
fi

if [[ "$original_bauh_found" == true ]]; then
    warning "Se detectó el paquete 'bauh' original instalado desde los repositorios del sistema ($original_bauh_pkg)."
    warning "Es MUY recomendable desinstalarlo antes de instalar este fork para evitar conflictos."

    if [[ "$ASSUME_YES" != true ]]; then
        read -r -p '¿Deseas desinstalar el bauh original ahora? [y/N] ' answer
        if [[ "$answer" =~ ^[Yy]$ ]]; then
            if [[ "$original_bauh_pkg" == "pacman" ]]; then
                info "Desinstalando bauh original con pacman..."
                sudo pacman -Rns --noconfirm bauh || warning "No se pudo desinstalar automáticamente. Hazlo manualmente con: sudo pacman -Rns bauh"
            elif [[ "$original_bauh_pkg" == "eopkg" ]]; then
                info "Desinstalando bauh original con eopkg..."
                sudo eopkg remove -y bauh || warning "No se pudo desinstalar automáticamente. Hazlo manualmente con: sudo eopkg remove bauh"
            fi
            info "Bauh original desinstalado. Continuando con la instalación del fork..."
        else
            warning "Continuando sin desinstalar. Pueden ocurrir conflictos entre ambas versiones."
        fi
    fi
fi

if [[ -f /etc/pacman.conf ]] && ! grep -qE '^\[chaotic-aur\]' /etc/pacman.conf; then
    warning "The chaotic-aur repository was not found in /etc/pacman.conf."
    warning "This fork is optimized for Arch Linux systems that enable Chaotic AUR."

    if [[ "$ASSUME_YES" != true ]]; then
        read -r -p 'Continue anyway? [y/N] ' answer
        if [[ ! "$answer" =~ ^[Yy]$ ]]; then
            info 'Installation cancelled.'
            exit 0
        fi
    fi
fi

pipx_bin_dir="$(pipx environment --value PIPX_BIN_DIR 2>/dev/null || true)"
if [[ -z "$pipx_bin_dir" ]]; then
    pipx_bin_dir="$HOME/.local/bin"
fi

info "Installing bauh with $PYTHON_BIN (Python $python_version)..."
extra_flags=()
if ! command -v uv >/dev/null 2>&1; then
    extra_flags+=(--backend pip)
fi
pipx install --force "${extra_flags[@]}" "$SCRIPT_DIR"

bauh_bin="$pipx_bin_dir/bauh"
if [[ ! -x "$bauh_bin" ]]; then
    error "pipx completed but '$bauh_bin' was not created. Check 'pipx list' for details."
    exit 1
fi

icon_source_png="$SCRIPT_DIR/pictures/gekko-bauh.png"

if [[ ! -f "$icon_source_png" ]]; then
    icon_source_png="$SCRIPT_DIR/bauh/view/resources/img/gekko-bauh.png"
fi

if [[ ! -f "$icon_source_png" ]]; then
    error "Application icon was not found: $icon_source_png"
    exit 1
fi

applications_dir="$HOME/.local/share/applications"
desktop_file="$applications_dir/bauh.desktop"

info 'Installing icon and desktop entry...'
for size in 48x48 64x64 128x128 256x256 512x512; do
    icon_dir="$HOME/.local/share/icons/hicolor/$size/apps"
    mkdir -p "$icon_dir"
    install -Dm644 "$icon_source_png" "$icon_dir/bauh.png"
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

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$applications_dir" || warning 'Could not update the desktop database.'
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons" || warning 'Could not update the icon cache.'
fi

printf '%b\n' "${green}${bold}bauh was installed successfully.${reset}"
printf 'Run it from your application menu or with: %s\n' "$bauh_bin"

if [[ ":$PATH:" != *":$pipx_bin_dir:"* ]]; then
    warning "'$pipx_bin_dir' is not in PATH. Run 'pipx ensurepath' and open a new terminal to use 'bauh' by name."
fi
