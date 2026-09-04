---
name: Reporte de error / Bug report
about: Algo no funciona en bauh Gekko Edition / Something is broken in bauh Gekko Edition
title: ''
labels: bug
assignees: ''

---

<!--
ES: Este repositorio es un fork de vinifmor/bauh. Si el mismo error ocurre con el
    bauh oficial, repórtalo también allí (https://github.com/vinifmor/bauh/issues)
    y enlaza ambos issues. Las sugerencias de nuevas AppImages para la base de
    datos van al upstream, no aquí.
EN: This repository is a fork of vinifmor/bauh. If the same bug happens with the
    official bauh, please report it there too (https://github.com/vinifmor/bauh/issues)
    and link both issues. AppImage database suggestions belong to the upstream.
-->

## Antes de abrir el issue / Before opening the issue

- [ ] **ES**: He actualizado a la versión actual de `master` y el error sigue ocurriendo.
      **EN**: I updated to the current `master` and the bug still happens.
      ```bash
      curl -fsSL https://raw.githubusercontent.com/The-Gekko/The-Gekko-Bauh/master/install.sh | bash -s -- --force
      ```
- [ ] **ES**: He buscado issues abiertos y cerrados con el mismo problema.
      **EN**: I searched open and closed issues for the same problem.

## Descripción / Description

<!-- ES: Qué ocurre, de forma clara y concisa. EN: What happens, clearly and concisely. -->

## Pasos para reproducir / Steps to reproduce

1.
2.
3.

## Comportamiento esperado / Expected behavior

## Comportamiento real / Actual behavior

<!-- ES: Capturas de pantalla si ayudan. EN: Screenshots if they help. -->

## Entorno / Environment

<!-- ES: Pega la salida de estos comandos. EN: Paste the output of these commands. -->

```bash
# Versión y commit instalados / Installed version and commit
pipx list | grep -i bauh
cat "$(pipx environment --value PIPX_LOCAL_VENVS)/gekko-bauh/.gekko-source-ref"
python3 --version

# Distribución y sesión gráfica / Distro and graphical session
cat /etc/os-release | grep -E '^(NAME|VERSION_ID)='
echo "$XDG_CURRENT_DESKTOP / $XDG_SESSION_TYPE"
```

- **Distribución / Distro**:
- **Entorno de escritorio o compositor / Desktop environment or compositor** (KDE, GNOME, Hyprland, Niri, ...):
- **Sesión / Session**: Wayland | X11
- **Método de instalación / Install method**: `install.sh` | pipx manual | venv | otro
- **Gems activas / Enabled gems** (`Ajustes → Tipos de aplicaciones`): arch, eopkg, github, ...
- **Tema / Theme** (`ui.theme` en `~/.config/gekko-bauh/config.yml`):

## Logs

<!--
ES: Ejecuta la aplicación desde un terminal con `gekko-bauh --logs`, reproduce el
    error y pega aquí la salida completa (o adjúntala como archivo). Revisa que no
    contenga contraseñas ni datos personales.
EN: Run the application from a terminal with `gekko-bauh --logs`, reproduce the bug
    and paste the full output here (or attach it as a file). Make sure it contains
    no passwords or personal data.
-->

```text

```

## Información adicional / Additional context

<!--
ES: ¿Ocurre también con el bauh oficial? ¿Tienes repositorios adicionales de
    pacman (p. ej. chaotic-aur)? ¿Empezó tras una actualización concreta?
EN: Does it happen with the official bauh too? Any extra pacman repositories
    (e.g. chaotic-aur)? Did it start after a specific update?
-->
