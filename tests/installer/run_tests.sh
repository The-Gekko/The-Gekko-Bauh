#!/usr/bin/env bash
#
# Tests de install.sh.
#
# Cada caso ejecuta el instalador real en un HOME temporal, con `pipx`, `uv`,
# `sudo`, `pacman`, `curl` e `id` falsos delante del PATH. Los falsos registran
# sus argumentos en un fichero de log, de modo que se puede comprobar tanto lo
# que el instalador crea en disco como los comandos que decide ejecutar (o no
# ejecutar).
#
# El `uv` falso hace que pipx elija (como el real cuando encuentra uv) el
# backend uv, y el `pipx` falso reproduce la comprobación de uv sobre
# UV_NO_BUILD_PACKAGE: con una lista separada por comas aborta, igual que uv al
# crear el venv. Así todos los casos de instalación pasan por el backend que
# rompía el instalador en cualquier host con uv.
#
# Todo lo que se escribe queda dentro del directorio temporal: el `id` falso
# devuelve un usuario ficticio para que el directorio temporal que borra --purge
# sea /tmp/gekko-bauh@bauh-installer-test y nunca el del usuario real.
#
# Uso:  bash tests/installer/run_tests.sh
# Salida: 0 si todos los casos pasan, 1 si falla alguno.

set -uo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$TESTS_DIR/../.." && pwd)"
INSTALLER="$REPO_ROOT/install.sh"

FAKE_USER='bauh-installer-test'
FAKE_TEMP_DIR="/tmp/gekko-bauh@$FAKE_USER"

if [[ ! -f "$INSTALLER" ]]; then
    echo "No se encontró el instalador en $INSTALLER" >&2
    exit 1
fi

# `setsid` deja al proceso sin terminal de control, así que has_tty() devuelve
# falso de forma determinista: sin esto, ejecutar los tests desde una consola
# haría que el instalador se quedase esperando una respuesta en /dev/tty.
RUNNER=()
if command -v setsid >/dev/null 2>&1; then
    RUNNER=(setsid -w)
else
    echo "AVISO: no hay 'setsid'; si ejecutas esto desde un terminal los tests pueden bloquearse." >&2
fi

TOTAL=0
FAILED=0
CURRENT_CASE=''
SANDBOX=''

# ───────────────────────────── Utilidades de test ─────────────────────────────

pass() { printf '  ok    %s\n' "$1"; }

fail() {
    FAILED=$((FAILED + 1))
    printf '  FALLO %s\n' "$1" >&2
}

start_case() {
    CURRENT_CASE="$1"
    TOTAL=$((TOTAL + 1))
    printf '\n[%02d] %s\n' "$TOTAL" "$CURRENT_CASE"
    make_sandbox
}

assert_status() {
    local expected="$1" actual="$2" what="$3"
    if [[ "$expected" == "$actual" ]]; then
        pass "$what (salida $actual)"
    else
        fail "$what: se esperaba salida $expected y fue $actual"
    fi
}

assert_file() {
    if [[ -f "$1" ]]; then
        pass "existe ${1#"$SANDBOX"/}"
    else
        fail "debería existir: ${1#"$SANDBOX"/}"
    fi
}

assert_no_file() {
    if [[ ! -e "$1" ]]; then
        pass "no existe ${1#"$SANDBOX"/}"
    else
        fail "NO debería existir: ${1#"$SANDBOX"/}"
    fi
}

assert_dir() {
    if [[ -d "$1" ]]; then
        pass "existe el directorio ${1#"$SANDBOX"/}"
    else
        fail "debería existir el directorio: ${1#"$SANDBOX"/}"
    fi
}

assert_no_dir() {
    if [[ ! -d "$1" ]]; then
        pass "no existe el directorio ${1#"$SANDBOX"/}"
    else
        fail "NO debería existir el directorio: ${1#"$SANDBOX"/}"
    fi
}

assert_contains() {
    local file="$1" needle="$2"
    if [[ -f "$file" ]] && grep -qF -- "$needle" "$file"; then
        pass "«$needle» en ${file#"$SANDBOX"/}"
    else
        fail "«$needle» NO está en ${file#"$SANDBOX"/}"
    fi
}

assert_not_contains() {
    local file="$1" needle="$2"
    if [[ ! -f "$file" ]] || ! grep -qF -- "$needle" "$file"; then
        pass "«$needle» ausente de ${file#"$SANDBOX"/}"
    else
        fail "«$needle» NO debería estar en ${file#"$SANDBOX"/}"
    fi
}

# ────────────────────────────── Entorno simulado ──────────────────────────────

make_sandbox() {
    SANDBOX="$(mktemp -d)"
    export SANDBOX
    export HOME="$SANDBOX/home"
    export XDG_CONFIG_HOME="$HOME/.config"
    export XDG_CACHE_HOME="$HOME/.cache"
    export FAKE_BIN="$SANDBOX/bin"
    export FAKE_LOG="$SANDBOX/commands.log"
    export VENVS_DIR="$HOME/.local/share/pipx/venvs"
    export BIN_DIR="$HOME/.local/bin"
    export OUTPUT="$SANDBOX/output.txt"

    # Comportamiento configurable de los falsos, por defecto el más neutro.
    export FAKE_PACMAN_HAS_BAUH=0     # 1 => `pacman -Qi bauh` tiene éxito
    export FAKE_CURL_MODE='real'      # real | fail-api | resolve
    export FAKE_CURL_SHA='0123456789abcdef0123456789abcdef01234567'

    mkdir -p "$FAKE_BIN" "$HOME" "$VENVS_DIR" "$BIN_DIR"
    : > "$FAKE_LOG"

    write_fake_pipx
    write_fake_uv
    write_fake_sudo
    write_fake_pacman
    write_fake_id
    write_fake_curl

    export PATH="$FAKE_BIN:$PATH"
}

cleanup_sandbox() {
    [[ -n "$SANDBOX" && -d "$SANDBOX" ]] && rm -rf "$SANDBOX"
    rm -rf "$FAKE_TEMP_DIR"
}

write_fake_pipx() {
    cat > "$FAKE_BIN/pipx" <<'FAKE'
#!/usr/bin/env bash
set -u
printf 'pipx %s\n' "$*" >> "$FAKE_LOG"

venvs="$VENVS_DIR"
bins="$BIN_DIR"

case "${1:-}" in
    environment)
        case "${3:-}" in
            PIPX_LOCAL_VENVS) printf '%s\n' "$venvs" ;;
            PIPX_BIN_DIR)     printf '%s\n' "$bins" ;;
            *)                printf '\n' ;;
        esac
        exit 0 ;;
    install)
        # `pipx install --help` se usa para detectar si existe --backend.
        for arg in "$@"; do
            if [[ "$arg" == '--help' ]]; then
                echo '  --backend {pip,uv}'
                exit 0
            fi
        done
        # Backend: uv si hay un `uv` en el PATH y no se pidió --backend pip, como
        # hace pipx de verdad (resolve_backend_name: cli > metadata > env > auto).
        backend='pip'
        command -v uv >/dev/null 2>&1 && backend='uv'
        prev=''
        for arg in "$@"; do
            [[ "$prev" == '--backend' ]] && backend="$arg"
            prev="$arg"
        done
        printf 'pipx-backend %s\n' "$backend" >> "$FAKE_LOG"
        printf 'env UV_NO_BUILD_PACKAGE=%s\n' "${UV_NO_BUILD_PACKAGE-<sin definir>}" >> "$FAKE_LOG"
        printf 'env PIP_ONLY_BINARY=%s\n' "${PIP_ONLY_BINARY-<sin definir>}" >> "$FAKE_LOG"

        # uv rechaza la variable con comas al crear el venv (mensaje literal de uv 0.12).
        if [[ "$backend" == 'uv' && "${UV_NO_BUILD_PACKAGE:-}" == *,* ]]; then
            echo "error: Failed to parse environment variable \`UV_NO_BUILD_PACKAGE\` with invalid value \`$UV_NO_BUILD_PACKAGE\`: Not a valid package or extra name" >&2
            exit 2
        fi

        # La fuente es el último argumento. Si es un directorio, se guarda su
        # árbol para poder comprobar qué llega de verdad a pipx.
        source="${*: -1}"
        printf 'pipx-source %s\n' "$source" >> "$FAKE_LOG"
        if [[ -d "$source" ]]; then
            (cd "$source" && find . -mindepth 1 | sed 's|^\./||' | LC_ALL=C sort) > "$SANDBOX/pipx-source-tree.txt"
        fi

        mkdir -p "$venvs/gekko-bauh/bin" "$bins"
        cat > "$venvs/gekko-bauh/bin/python" <<'PYFAKE'
#!/usr/bin/env bash
echo '0.10.8+gekko.1'
PYFAKE
        chmod +x "$venvs/gekko-bauh/bin/python"
        for launcher in gekko-bauh gekko-bauh-tray gekko-bauh-cli; do
            printf '#!/bin/sh\n# %s/gekko-bauh/bin/python\n' "$venvs" > "$bins/$launcher"
            chmod +x "$bins/$launcher"
        done
        exit 0 ;;
    uninstall)
        name="${2:-}"
        rm -rf "${venvs:?}/$name"
        for launcher in gekko-bauh gekko-bauh-tray gekko-bauh-cli; do
            rm -f "$bins/$launcher"
        done
        exit 0 ;;
    list)
        ls -1 "$venvs" 2>/dev/null || true
        exit 0 ;;
esac
exit 0
FAKE
    chmod +x "$FAKE_BIN/pipx"
}

# Basta con que exista: install.sh solo hace `command -v uv` para decidir si
# pipx va a usar el backend uv.
write_fake_uv() {
    cat > "$FAKE_BIN/uv" <<'FAKE'
#!/usr/bin/env bash
echo 'uv 0.0.0 (falso para los tests del instalador)'
exit 0
FAKE
    chmod +x "$FAKE_BIN/uv"
}

write_fake_sudo() {
    cat > "$FAKE_BIN/sudo" <<'FAKE'
#!/usr/bin/env bash
set -u
# `sudo -n true` es la comprobación de credenciales: se acepta sin registrarla.
if [[ "${1:-}" == '-n' && "${2:-}" == 'true' ]]; then
    exit 0
fi
printf 'sudo %s\n' "$*" >> "$FAKE_LOG"
exit 0
FAKE
    chmod +x "$FAKE_BIN/sudo"
}

write_fake_pacman() {
    cat > "$FAKE_BIN/pacman" <<'FAKE'
#!/usr/bin/env bash
set -u
printf 'pacman %s\n' "$*" >> "$FAKE_LOG"
if [[ "${1:-}" == '-Qi' && "${2:-}" == 'bauh' ]]; then
    [[ "${FAKE_PACMAN_HAS_BAUH:-0}" == '1' ]] && exit 0
    exit 1
fi
exit 0
FAKE
    chmod +x "$FAKE_BIN/pacman"
}

write_fake_id() {
    cat > "$FAKE_BIN/id" <<'FAKE'
#!/usr/bin/env bash
set -u
if [[ "${1:-}" == '-un' ]]; then
    printf '%s\n' "${FAKE_USER_NAME:-bauh-installer-test}"
    exit 0
fi
exec /usr/bin/id "$@"
FAKE
    chmod +x "$FAKE_BIN/id"
}

write_fake_curl() {
    cat > "$FAKE_BIN/curl" <<'FAKE'
#!/usr/bin/env bash
set -u
printf 'curl %s\n' "$*" >> "$FAKE_LOG"

url="${*: -1}"
out=''
prev=''
for arg in "$@"; do
    [[ "$prev" == '-o' ]] && out="$arg"
    prev="$arg"
done

case "${FAKE_CURL_MODE:-real}" in
    fail-api)
        # Ninguna descarga funciona: simula quedarse sin red o sin cuota de API.
        exit 22 ;;
    resolve)
        if [[ "$url" == *'api.github.com'* ]]; then
            printf '%s\n' "$FAKE_CURL_SHA"
            exit 0
        fi
        # El resto de descargas (iconos, .desktop) falla a propósito para
        # comprobar que el instalador sigue adelante con sus alternativas.
        exit 22 ;;
    icons-fallback)
        # La API resuelve y el PNG grande llega, pero los iconos por tamaño no
        # existen todavía en ese commit: el instalador debe recurrir al grande.
        if [[ "$url" == *'api.github.com'* ]]; then
            printf '%s\n' "$FAKE_CURL_SHA"
            exit 0
        fi
        if [[ "$url" == *'/pictures/icons/'* ]]; then
            exit 22
        fi
        if [[ "$url" == *'gekko-bauh.png' || "$url" == *'.desktop' ]]; then
            [[ -n "$out" ]] && printf 'contenido\n' > "$out"
            exit 0
        fi
        exit 22 ;;
esac

# Modo 'real': no se sale a la red en los tests; se responde vacío.
[[ -n "$out" ]] && : > "$out"
exit 0
FAKE
    chmod +x "$FAKE_BIN/curl"
}

# Ejecuta el instalador en modo local (checkout) y guarda la salida.
run_installer_local() {
    "${RUNNER[@]}" bash "$INSTALLER" "$@" > "$OUTPUT" 2>&1 < /dev/null
}

# Ejecuta una copia del instalador colocada en otro checkout (ver
# test_local_install_uses_a_clean_copy).
run_installer_from() {
    local installer="$1"
    shift
    "${RUNNER[@]}" bash "$installer" "$@" > "$OUTPUT" 2>&1 < /dev/null
}

# Ejecuta el instalador en modo remoto: al leer el script por la entrada
# estándar, BASH_SOURCE queda vacío, igual que con `curl ... | bash`.
run_installer_remote() {
    "${RUNNER[@]}" bash -s -- "$@" > "$OUTPUT" 2>&1 < "$INSTALLER"
}

# ─────────────────────────────────── Casos ────────────────────────────────────

test_local_install() {
    start_case 'instalación local: entornos, iconos y lanzadores propios'

    run_installer_local --yes --no-autostart
    assert_status 0 "$?" 'el instalador termina bien'

    assert_contains "$FAKE_LOG" 'pipx install --force --python python3'

    # Se instala desde una copia limpia del checkout, nunca desde el checkout mismo.
    assert_contains "$FAKE_LOG" 'pipx-source '
    assert_not_contains "$FAKE_LOG" "pipx-source $REPO_ROOT"
    assert_contains "$SANDBOX/pipx-source-tree.txt" 'bauh/__init__.py'
    assert_contains "$SANDBOX/pipx-source-tree.txt" 'pyproject.toml'
    assert_contains "$VENVS_DIR/gekko-bauh/.gekko-source-ref" "local:$REPO_ROOT"

    local apps="$HOME/.local/share/applications"
    assert_file "$apps/gekko-bauh.desktop"
    assert_file "$apps/gekko-bauh-tray.desktop"

    # No se escribe bauh.desktop: taparía por precedencia XDG al bauh oficial.
    assert_no_file "$apps/bauh.desktop"
    assert_no_file "$apps/bauh_tray.desktop"

    assert_contains "$apps/gekko-bauh.desktop" "Exec=$BIN_DIR/gekko-bauh"
    assert_contains "$apps/gekko-bauh.desktop" 'Icon=gekko-bauh'
    assert_contains "$apps/gekko-bauh.desktop" 'X-Gekko-Edition=true'
    assert_contains "$apps/gekko-bauh.desktop" 'Name=bauh Gekko Edition'
    assert_contains "$apps/gekko-bauh.desktop" 'StartupWMClass=gekko-bauh'
    assert_contains "$apps/gekko-bauh.desktop" 'Name[es]='
    assert_contains "$apps/gekko-bauh.desktop" 'Comment[es]='
    assert_contains "$apps/gekko-bauh.desktop" 'Keywords='
    assert_contains "$apps/gekko-bauh-tray.desktop" "Exec=$BIN_DIR/gekko-bauh-tray"

    local icons="$HOME/.local/share/icons/hicolor"
    local size
    for size in 16 32 48 64 128 256 512; do
        assert_file "$icons/${size}x${size}/apps/gekko-bauh.png"
        assert_no_file "$icons/${size}x${size}/apps/bauh.png"
    done

    # Marca de origen: identifica el venv como creado por este instalador.
    assert_file "$VENVS_DIR/gekko-bauh/.gekko-source-ref"
    assert_contains "$VENVS_DIR/gekko-bauh/.gekko-source-ref" 'local:'

    # --no-autostart no debe dejar entrada de arranque automático.
    assert_no_file "$XDG_CONFIG_HOME/autostart/gekko-bauh-tray.desktop"

    cleanup_sandbox
}

test_autostart() {
    start_case '--autostart deja la bandeja en el arranque de sesión'

    run_installer_local --yes --autostart
    assert_status 0 "$?" 'el instalador termina bien'
    assert_file "$XDG_CONFIG_HOME/autostart/gekko-bauh-tray.desktop"
    assert_contains "$XDG_CONFIG_HOME/autostart/gekko-bauh-tray.desktop" "Exec=$BIN_DIR/gekko-bauh-tray"

    cleanup_sandbox
}

test_legacy_migration() {
    start_case 'migración: se retira el venv «bauh» y el lanzador que tapaba al oficial'

    # Instalación anterior de este mismo instalador.
    mkdir -p "$VENVS_DIR/bauh/bin" "$HOME/.local/share/applications"
    echo 'abc123' > "$VENVS_DIR/bauh/.gekko-source-ref"
    printf '[Desktop Entry]\nName=Bauh Fork The-Gekko\nExec=/x/bauh\nIcon=bauh\n' \
        > "$HOME/.local/share/applications/bauh.desktop"
    mkdir -p "$HOME/.local/share/icons/hicolor/64x64/apps"
    : > "$HOME/.local/share/icons/hicolor/64x64/apps/bauh.png"

    run_installer_local --yes --no-autostart
    assert_status 0 "$?" 'el instalador termina bien'

    assert_contains "$FAKE_LOG" 'pipx uninstall bauh'
    assert_no_dir "$VENVS_DIR/bauh"
    assert_no_file "$HOME/.local/share/applications/bauh.desktop"
    assert_no_file "$HOME/.local/share/icons/hicolor/64x64/apps/bauh.png"
    assert_file "$HOME/.local/share/applications/gekko-bauh.desktop"

    cleanup_sandbox
}

test_foreign_venv_untouched() {
    start_case 'un venv «bauh» ajeno no se desinstala'

    # Sin marca de origen: no lo instalamos nosotros.
    mkdir -p "$VENVS_DIR/bauh/bin"

    run_installer_local --yes --no-autostart
    assert_status 0 "$?" 'el instalador termina bien'

    assert_not_contains "$FAKE_LOG" 'pipx uninstall bauh'
    assert_dir "$VENVS_DIR/bauh"
    assert_contains "$OUTPUT" 'no instaló este script'

    cleanup_sandbox
}

test_yes_does_not_authorize_sudo() {
    start_case '--yes NO autoriza desinstalar el bauh del sistema'

    export FAKE_PACMAN_HAS_BAUH=1

    run_installer_local --yes --no-autostart
    assert_status 0 "$?" 'el instalador termina bien'

    assert_not_contains "$FAKE_LOG" 'pacman -Rns'
    assert_contains "$OUTPUT" '--remove-system-bauh'
    assert_contains "$OUTPUT" 'Se conserva el bauh original'

    cleanup_sandbox
}

test_remove_system_bauh_flag() {
    start_case '--remove-system-bauh sí ejecuta la desinstalación con sudo'

    export FAKE_PACMAN_HAS_BAUH=1

    run_installer_local --yes --no-autostart --remove-system-bauh
    assert_status 0 "$?" 'el instalador termina bien'

    assert_contains "$FAKE_LOG" 'sudo pacman -Rns --noconfirm bauh'

    cleanup_sandbox
}

test_remote_ref_unresolvable() {
    start_case 'modo remoto: si no se resuelve la referencia, se aborta'

    export FAKE_CURL_MODE='fail-api'

    run_installer_remote --yes --no-autostart --ref master
    assert_status 1 "$?" 'el instalador aborta'

    assert_contains "$OUTPUT" 'No se pudo resolver'
    assert_not_contains "$FAKE_LOG" 'pipx install'

    cleanup_sandbox
}

test_remote_installs_resolved_commit() {
    start_case 'modo remoto: se instala el commit resuelto y esa misma marca se guarda'

    export FAKE_CURL_MODE='resolve'

    run_installer_remote --yes --no-autostart --ref master
    assert_status 0 "$?" 'el instalador termina bien'

    # Se descarga exactamente el SHA resuelto, no «heads/master.zip».
    assert_contains "$FAKE_LOG" "archive/$FAKE_CURL_SHA.zip"
    assert_not_contains "$FAKE_LOG" 'heads/master.zip'

    # La marca guardada es el mismo SHA que se instaló.
    assert_file "$VENVS_DIR/gekko-bauh/.gekko-source-ref"
    assert_contains "$VENVS_DIR/gekko-bauh/.gekko-source-ref" "$FAKE_CURL_SHA"

    cleanup_sandbox
}

test_uninstall_without_installation() {
    start_case 'uninstall sin nada instalado NO declara éxito'

    run_installer_local uninstall
    assert_status 1 "$?" 'el desinstalador señala que no había nada'

    assert_contains "$OUTPUT" 'No se encontró ninguna instalación'
    assert_not_contains "$OUTPUT" 'desinstalado correctamente'

    cleanup_sandbox
}

test_uninstall_purge_without_installation() {
    start_case 'uninstall --purge sin nada instalado purga los datos y termina con 0'

    mkdir -p "$HOME/.config/gekko-bauh" "$HOME/.cache/gekko-bauh"
    : > "$HOME/.config/gekko-bauh/config.yml"
    : > "$HOME/.cache/gekko-bauh/marca"

    run_installer_local uninstall --purge --yes
    assert_status 0 "$?" 'la purga sin instalación previa no es un error'

    assert_contains "$OUTPUT" 'No se encontró ninguna instalación'
    assert_contains "$OUTPUT" 'se termina sin error'
    assert_not_contains "$OUTPUT" 'desinstalado correctamente'
    assert_no_dir "$HOME/.config/gekko-bauh"
    assert_no_dir "$HOME/.cache/gekko-bauh"

    cleanup_sandbox
}

test_uninstall_after_install() {
    start_case 'uninstall tras instalar: limpia entorno, iconos y lanzadores'

    run_installer_local --yes --no-autostart
    assert_status 0 "$?" 'la instalación previa termina bien'

    run_installer_local uninstall --yes
    assert_status 0 "$?" 'el desinstalador termina bien'

    assert_contains "$OUTPUT" 'desinstalado correctamente'
    assert_no_dir "$VENVS_DIR/gekko-bauh"
    assert_no_file "$HOME/.local/share/applications/gekko-bauh.desktop"
    assert_no_file "$HOME/.local/share/applications/gekko-bauh-tray.desktop"
    assert_no_file "$HOME/.local/share/icons/hicolor/256x256/apps/gekko-bauh.png"

    cleanup_sandbox
}

test_uninstall_purge() {
    start_case 'uninstall --purge borra config, caché, datos y temporal'

    run_installer_local --yes --no-autostart
    assert_status 0 "$?" 'la instalación previa termina bien'

    mkdir -p "$HOME/.config/gekko-bauh" "$HOME/.cache/gekko-bauh" \
             "$HOME/.local/share/gekko-bauh" "$FAKE_TEMP_DIR"
    printf 'ui:\n  theme: light\n' > "$HOME/.config/gekko-bauh/config.yml"
    : > "$HOME/.cache/gekko-bauh/marca"
    : > "$HOME/.local/share/gekko-bauh/marca"
    : > "$FAKE_TEMP_DIR/marca"

    # Datos del bauh oficial: --purge no debe tocarlos.
    mkdir -p "$HOME/.config/bauh"
    printf 'ui:\n  theme: darcula\n' > "$HOME/.config/bauh/config.yml"

    run_installer_local uninstall --purge --yes
    assert_status 0 "$?" 'el desinstalador termina bien'

    assert_no_dir "$HOME/.config/gekko-bauh"
    assert_no_dir "$HOME/.cache/gekko-bauh"
    assert_no_dir "$HOME/.local/share/gekko-bauh"
    assert_no_dir "$FAKE_TEMP_DIR"

    # El directorio heredado pertenece ahora al proyecto original.
    assert_dir "$HOME/.config/bauh"
    assert_contains "$HOME/.config/bauh/config.yml" 'theme: darcula'
    assert_contains "$SANDBOX/output.txt" 'No se ha tocado'

    cleanup_sandbox
}

test_uninstall_resets_fork_theme() {
    start_case 'uninstall sin --purge devuelve el tema del fork a «light»'

    run_installer_local --yes --no-autostart
    assert_status 0 "$?" 'la instalación previa termina bien'

    mkdir -p "$HOME/.config/bauh"
    # `custom_theme.theme` es de otra sección: no debe tocarse.
    printf 'ui:\n  theme: aurora\n  system_theme: false\ncustom_theme:\n  theme: aurora\n' \
        > "$HOME/.config/bauh/config.yml"

    run_installer_local uninstall --yes
    assert_status 0 "$?" 'el desinstalador termina bien'

    assert_contains "$HOME/.config/bauh/config.yml" 'theme: light'
    assert_contains "$HOME/.config/bauh/config.yml" 'system_theme: false'
    # La clave de la sección custom_theme sigue intacta.
    assert_contains "$HOME/.config/bauh/config.yml" 'custom_theme:'
    if [[ "$(grep -c 'theme: aurora' "$HOME/.config/bauh/config.yml")" == '1' ]]; then
        pass 'solo se reescribió el tema de la sección ui'
    else
        fail 'se reescribieron temas fuera de la sección ui'
    fi

    cleanup_sandbox
}

test_theme_untouched_when_standard() {
    start_case 'uninstall no toca un tema estándar del bauh oficial'

    run_installer_local --yes --no-autostart
    assert_status 0 "$?" 'la instalación previa termina bien'

    mkdir -p "$HOME/.config/bauh"
    printf 'ui:\n  theme: darcula\n' > "$HOME/.config/bauh/config.yml"

    run_installer_local uninstall --yes
    assert_status 0 "$?" 'el desinstalador termina bien'

    assert_contains "$HOME/.config/bauh/config.yml" 'theme: darcula'

    cleanup_sandbox
}

test_help_and_bad_option() {
    start_case 'ayuda y opciones inválidas'

    run_installer_local --help
    assert_status 0 "$?" '--help termina bien'
    assert_contains "$OUTPUT" '--remove-system-bauh'
    assert_contains "$OUTPUT" '--ref'

    run_installer_local --opcion-inexistente
    assert_status 2 "$?" 'una opción desconocida sale con 2'

    run_installer_local --ref
    assert_status 2 "$?" '--ref sin valor sale con 2'

    cleanup_sandbox
}

test_remote_skips_rebuild_when_same_commit() {
    start_case 'modo remoto: reinstalar el mismo commit omite la reconstrucción'

    export FAKE_CURL_MODE='resolve'

    run_installer_remote --yes --no-autostart
    assert_status 0 "$?" 'la primera instalación termina bien'
    assert_contains "$FAKE_LOG" 'pipx install'
    assert_contains "$VENVS_DIR/gekko-bauh/.gekko-source-ref" "$FAKE_CURL_SHA"

    # A partir de aquí solo interesa lo que haga la segunda ejecución.
    : > "$FAKE_LOG"

    run_installer_remote --yes --no-autostart
    assert_status 0 "$?" 'la segunda instalación termina bien'
    assert_not_contains "$FAKE_LOG" 'pipx install --force'
    assert_contains "$OUTPUT" 'Omitiendo la reconstrucción'

    cleanup_sandbox
}

test_remote_force_rebuilds() {
    start_case 'modo remoto: --force reconstruye aunque el commit coincida'

    export FAKE_CURL_MODE='resolve'

    run_installer_remote --yes --no-autostart
    assert_status 0 "$?" 'la primera instalación termina bien'

    : > "$FAKE_LOG"

    run_installer_remote --yes --no-autostart --force
    assert_status 0 "$?" 'la reinstalación forzada termina bien'
    assert_contains "$FAKE_LOG" 'pipx install --force'

    cleanup_sandbox
}

test_remote_ref_is_honoured() {
    start_case 'modo remoto: --ref consulta la referencia pedida'

    export FAKE_CURL_MODE='resolve'

    run_installer_remote --yes --no-autostart --ref v0.10.8-gekko.1
    assert_status 0 "$?" 'el instalador termina bien'

    # La referencia pedida debe llegar tal cual a la API y el commit resuelto
    # debe ser el que se descarga e instala.
    assert_contains "$FAKE_LOG" 'commits/v0.10.8-gekko.1'
    assert_contains "$FAKE_LOG" "archive/$FAKE_CURL_SHA.zip"
    assert_contains "$VENVS_DIR/gekko-bauh/.gekko-source-ref" "$FAKE_CURL_SHA"

    cleanup_sandbox
}

test_remote_icon_fallback() {
    start_case 'modo remoto: sin iconos por tamaño se recurre al PNG grande'

    export FAKE_CURL_MODE='icons-fallback'

    run_installer_remote --yes --no-autostart
    assert_status 0 "$?" 'el instalador termina bien'

    # Aunque los iconos por tamaño no existan en ese commit, deben quedar
    # instalados todos los tamaños a partir del PNG grande.
    local icons="$HOME/.local/share/icons/hicolor"
    local size
    for size in 16 48 256 512; do
        assert_file "$icons/${size}x${size}/apps/gekko-bauh.png"
    done

    assert_file "$HOME/.local/share/applications/gekko-bauh.desktop"

    cleanup_sandbox
}

# ──────────────────────────────────── Main ────────────────────────────────────

echo "Instalador bajo prueba: $INSTALLER"

test_purge_also_resets_fork_theme() {
    start_case 'uninstall --purge también devuelve el tema del fork a «light»'

    run_installer_local --yes --no-autostart
    assert_status 0 "$?" 'la instalación previa termina bien'

    mkdir -p "$HOME/.config/bauh"
    printf 'ui:\n  theme: aurora\n' > "$HOME/.config/bauh/config.yml"

    run_installer_local uninstall --purge --yes
    assert_status 0 "$?" 'el desinstalador termina bien'

    # reset_fork_theme opera sobre ~/.config/bauh, que la purga no toca: dejar el tema
    # propio ahí haría arrancar al bauh oficial sin hoja de estilos y sin ningún error
    assert_contains "$HOME/.config/bauh/config.yml" 'theme: light'

    cleanup_sandbox
}

test_purge_keeps_github_clones() {
    start_case 'uninstall --purge conserva los clones de la gem GitHub'

    run_installer_local --yes --no-autostart
    assert_status 0 "$?" 'la instalación previa termina bien'

    local repos="$HOME/.local/share/gekko-bauh/github/repos"
    mkdir -p "$repos/mi-usuario/mi-proyecto/.git" \
             "$HOME/.local/share/gekko-bauh/themes"
    : > "$repos/mi-usuario/mi-proyecto/trabajo-sin-publicar.txt"
    : > "$HOME/.local/share/gekko-bauh/themes/mio.qss"
    : > "$HOME/.local/share/gekko-bauh/github/cache.yml"

    run_installer_local uninstall --purge --yes
    assert_status 0 "$?" 'el desinstalador termina bien'

    # el trabajo local del usuario no se borra ni con --purge
    if [[ -f "$repos/mi-usuario/mi-proyecto/trabajo-sin-publicar.txt" ]]; then
        pass 'los clones de la gem GitHub siguen ahí'
    else
        fail 'se borraron los clones de la gem GitHub'
    fi

    assert_no_file "$HOME/.local/share/gekko-bauh/themes/mio.qss"
    assert_no_file "$HOME/.local/share/gekko-bauh/github/cache.yml"
    assert_contains "$SANDBOX/output.txt" 'no se han borrado'

    cleanup_sandbox
}

test_foreign_bauh_binary_is_not_a_leftover() {
    start_case 'uninstall no da por fallida la desinstalación por el bauh oficial'

    run_installer_local --yes --no-autostart
    assert_status 0 "$?" 'la instalación previa termina bien'

    # venv «bauh» ajeno: sin nuestra marca de origen y con su propio ejecutable en el PATH
    local venvs="$HOME/.local/share/pipx/venvs"
    mkdir -p "$venvs/bauh/bin"
    printf '#!/bin/sh\necho bauh oficial\n' > "$HOME/.local/bin/bauh"
    chmod +x "$HOME/.local/bin/bauh"
    ln -sf "$HOME/.local/bin/bauh" "$venvs/bauh/bin/bauh"

    run_installer_local uninstall --yes
    assert_status 0 "$?" 'el desinstalador termina bien pese al bauh ajeno'

    assert_not_contains "$SANDBOX/output.txt" 'La desinstalación NO se completó'
    assert_contains "$SANDBOX/output.txt" 'se deja intacto'

    if [[ -x "$HOME/.local/bin/bauh" ]]; then
        pass 'el ejecutable del bauh oficial sigue intacto'
    else
        fail 'se borró el ejecutable del bauh oficial'
    fi

    cleanup_sandbox
}

test_uv_backend_gets_a_space_separated_list() {
    start_case 'backend uv: UV_NO_BUILD_PACKAGE va separada por espacios y PIP_ONLY_BINARY por comas'

    run_installer_local --yes --no-autostart
    assert_status 0 "$?" 'el instalador termina bien con el backend uv'

    # Con el `uv` falso en el PATH, install.sh no debe forzar --backend pip.
    assert_contains "$FAKE_LOG" 'pipx-backend uv'
    assert_not_contains "$FAKE_LOG" '--backend pip'

    # uv espera una lista separada por espacios; con comas aborta al crear el venv.
    assert_contains "$FAKE_LOG" 'env UV_NO_BUILD_PACKAGE=pyqt5 pyqt5-sip pyqt5-qt5 pyyaml requests colorama python-dateutil six urllib3 certifi idna charset-normalizer'
    assert_not_contains "$OUTPUT" 'Not a valid package or extra name'
    # pip sí usa comas.
    assert_contains "$FAKE_LOG" 'env PIP_ONLY_BINARY=pyqt5,pyqt5-sip,pyqt5-qt5,pyyaml,requests,colorama,python-dateutil,six,urllib3,certifi,idna,charset-normalizer'

    cleanup_sandbox
}

test_allow_build_from_source_unsets_the_wheel_only_lists() {
    start_case '--allow-build-from-source no restringe a wheels'

    run_installer_local --yes --no-autostart --allow-build-from-source
    assert_status 0 "$?" 'el instalador termina bien'

    assert_contains "$FAKE_LOG" 'env UV_NO_BUILD_PACKAGE=<sin definir>'
    assert_contains "$FAKE_LOG" 'env PIP_ONLY_BINARY=<sin definir>'

    cleanup_sandbox
}

test_ref_is_an_error_in_local_mode() {
    start_case 'modo local: --ref no se ignora en silencio, sale con 2'

    run_installer_local --yes --no-autostart --ref v0.10.7
    assert_status 2 "$?" '--ref desde un checkout sale con 2'

    assert_contains "$OUTPUT" "no tiene efecto desde un checkout"
    assert_contains "$OUTPUT" 'v0.10.7'
    assert_not_contains "$FAKE_LOG" 'pipx install'
    assert_no_file "$HOME/.local/share/applications/gekko-bauh.desktop"

    # La forma --ref=valor se trata igual.
    run_installer_local --yes --no-autostart --ref=master
    assert_status 2 "$?" '--ref=master desde un checkout sale con 2'

    cleanup_sandbox
}

test_local_install_uses_a_clean_copy() {
    start_case 'modo local: pipx recibe una copia sin build/, dist/, egg-info, __pycache__ ni .git'

    # Un checkout de mentira con restos de construcciones antiguas: build/lib
    # conserva gems ya borradas del árbol (debian, snap) y paquetes espurios.
    local checkout="$SANDBOX/checkout"
    mkdir -p "$checkout/bauh/desktop" "$checkout/bauh/__pycache__" \
             "$checkout/build/lib/bauh/gems/debian" "$checkout/build/lib/bauh/gems/snap" \
             "$checkout/build/lib/tools" "$checkout/build/lib/build" \
             "$checkout/dist" "$checkout/gekko_bauh.egg-info" "$checkout/.git" \
             "$checkout/.venv/bin" "$checkout/tools"
    cp "$INSTALLER" "$checkout/install.sh"
    cp "$REPO_ROOT/pyproject.toml" "$checkout/pyproject.toml"
    cp "$REPO_ROOT/bauh/__init__.py" "$checkout/bauh/__init__.py"
    cp "$REPO_ROOT"/bauh/desktop/gekko-bauh.desktop "$REPO_ROOT"/bauh/desktop/gekko-bauh-tray.desktop "$checkout/bauh/desktop/"
    : > "$checkout/bauh/__pycache__/__init__.cpython-312.pyc"
    : > "$checkout/build/lib/bauh/gems/debian/__init__.py"
    : > "$checkout/build/lib/bauh/gems/snap/__init__.py"
    : > "$checkout/build/lib/tools/check_locales.py"
    : > "$checkout/build/lib/build/__init__.py"
    : > "$checkout/dist/gekko_bauh-0.0.0-py3-none-any.whl"
    : > "$checkout/gekko_bauh.egg-info/PKG-INFO"
    : > "$checkout/.git/HEAD"
    : > "$checkout/.venv/bin/python"
    : > "$checkout/tools/check_locales.py"

    run_installer_from "$checkout/install.sh" --yes --no-autostart
    assert_status 0 "$?" 'el instalador termina bien'

    local tree="$SANDBOX/pipx-source-tree.txt"
    assert_file "$tree"
    assert_not_contains "$FAKE_LOG" "pipx-source $checkout"

    # Lo que sí tiene que llegar.
    assert_contains "$tree" 'pyproject.toml'
    assert_contains "$tree" 'bauh/__init__.py'
    assert_contains "$tree" 'bauh/desktop/gekko-bauh.desktop'
    assert_contains "$tree" 'tools/check_locales.py'

    # Lo que no.
    assert_not_contains "$tree" 'build/'
    assert_not_contains "$tree" 'gems/debian'
    assert_not_contains "$tree" 'gems/snap'
    assert_not_contains "$tree" 'dist/'
    assert_not_contains "$tree" 'egg-info'
    assert_not_contains "$tree" '__pycache__'
    assert_not_contains "$tree" '.pyc'
    assert_not_contains "$tree" '.git'
    assert_not_contains "$tree" '.venv'

    # La copia temporal se retira al terminar y la marca apunta al checkout real.
    local source_dir
    source_dir="$(sed -n 's/^pipx-source //p' "$FAKE_LOG" | tail -n1)"
    if [[ -n "$source_dir" && ! -e "$source_dir" ]]; then
        pass "la copia temporal ${source_dir#"$SANDBOX"/} se borró al terminar"
    else
        fail "la copia temporal sigue existiendo: $source_dir"
    fi
    assert_contains "$VENVS_DIR/gekko-bauh/.gekko-source-ref" "local:$checkout"

    # El checkout original no se toca.
    assert_file "$checkout/build/lib/bauh/gems/debian/__init__.py"

    cleanup_sandbox
}

test_purge_does_not_repeat_paths_when_xdg_equals_the_defaults() {
    start_case 'uninstall --purge no repite rutas cuando XDG_DATA_HOME es ~/.local/share'

    # XDG_CONFIG_HOME y XDG_CACHE_HOME ya valen lo mismo que las rutas fijas en
    # el sandbox; se añade XDG_DATA_HOME para cubrir las tres.
    export XDG_DATA_HOME="$HOME/.local/share/"

    run_installer_local --yes --no-autostart
    assert_status 0 "$?" 'la instalación previa termina bien'

    local repos="$HOME/.local/share/gekko-bauh/github/repos"
    mkdir -p "$repos/usuario/proyecto" "$HOME/.config/gekko-bauh" "$HOME/.cache/gekko-bauh"
    : > "$repos/usuario/proyecto/trabajo.txt"
    : > "$HOME/.config/gekko-bauh/config.yml"
    : > "$HOME/.cache/gekko-bauh/marca"

    run_installer_local uninstall --purge --yes
    assert_status 0 "$?" 'el desinstalador termina bien'

    local warnings deletions
    warnings="$(grep -c 'no se han borrado' "$OUTPUT")"
    deletions="$(grep -c "Eliminado: $HOME/.local/share/gekko-bauh" "$OUTPUT")"
    if [[ "$warnings" == '1' ]]; then
        pass 'el aviso de los clones conservados aparece una sola vez'
    else
        fail "el aviso de los clones conservados aparece $warnings veces"
    fi
    if [[ "$deletions" == '1' ]]; then
        pass 'la ruta de datos se trata una sola vez'
    else
        fail "la ruta de datos se trató $deletions veces"
    fi
    if [[ "$(grep -c 'Eliminado: ' "$OUTPUT")" == '3' ]]; then
        pass 'se eliminan exactamente config, caché y datos (sin duplicados)'
    else
        fail "líneas «Eliminado:» inesperadas: $(grep -c 'Eliminado: ' "$OUTPUT")"
    fi
    assert_file "$repos/usuario/proyecto/trabajo.txt"

    unset XDG_DATA_HOME
    cleanup_sandbox
}

test_local_install
test_uv_backend_gets_a_space_separated_list
test_allow_build_from_source_unsets_the_wheel_only_lists
test_ref_is_an_error_in_local_mode
test_local_install_uses_a_clean_copy
test_purge_does_not_repeat_paths_when_xdg_equals_the_defaults
test_autostart
test_legacy_migration
test_foreign_venv_untouched
test_yes_does_not_authorize_sudo
test_remove_system_bauh_flag
test_remote_ref_unresolvable
test_remote_installs_resolved_commit
test_uninstall_without_installation
test_uninstall_purge_without_installation
test_uninstall_after_install
test_uninstall_purge
test_purge_also_resets_fork_theme
test_purge_keeps_github_clones
test_foreign_bauh_binary_is_not_a_leftover
test_uninstall_resets_fork_theme
test_theme_untouched_when_standard
test_help_and_bad_option
test_remote_skips_rebuild_when_same_commit
test_remote_force_rebuilds
test_remote_ref_is_honoured
test_remote_icon_fallback

echo
if ((FAILED > 0)); then
    printf 'RESULTADO: %d comprobación(es) fallida(s) en %d casos.\n' "$FAILED" "$TOTAL" >&2
    exit 1
fi

printf 'RESULTADO: %d casos, todas las comprobaciones pasaron.\n' "$TOTAL"
exit 0
