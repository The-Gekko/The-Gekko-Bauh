# Migración: convivencia con el bauh oficial y vuelta atrás

bauh Gekko Edition y el bauh oficial (`vinifmor/bauh`, paquete `bauh` de los
repositorios o de PyPI) usan el **mismo nombre de aplicación** (`bauh`) y por
tanto **comparten** la configuración, la caché y los datos de usuario. Eso hace
que cambiar de uno a otro sea sencillo, pero también que algunos ajustes del
fork no signifiquen nada para el oficial. Esta página explica qué se comparte,
qué no, y los pasos exactos en cada dirección.

## 1. Qué se comparte y qué no

| Ruta | Quién la usa | Notas |
|---|---|---|
| `~/.config/bauh/config.yml` | Ambos | Configuración general. Ver las claves problemáticas en la sección 2. |
| `~/.config/bauh/arch.yml`, `appimage.yml`, `flatpak.yml`, `snap.yml`, `web.yml`, `debian.yml` | Ambos | Configuración por gem. |
| `~/.config/bauh/eopkg.yml`, `~/.config/bauh/github.yml` | Solo el fork | El oficial las ignora sin error. |
| `~/.cache/bauh/` | Ambos | Caché de paquetes, iconos y sugerencias. Se puede borrar sin perder nada. |
| `~/.local/share/bauh/` | Ambos | Temas de usuario (`themes/`) y datos compartidos. |
| `$XDG_RUNTIME_DIR/bauh/` | Solo el fork | Temporales y logs de la sesión; el oficial usa `/tmp/bauh@<usuario>`. Desaparecen al cerrar sesión. |
| `~/BauhRepos/` | Solo el fork | Clones de la gem GitHub (ruta configurable con `repos_dir` en `github.yml`). Nunca se borra automáticamente. |
| `~/.local/share/pipx/venvs/bauh-gekko/` | Solo el fork | Entorno de pipx del fork (la ruta exacta la da `pipx environment --value PIPX_LOCAL_VENVS`). Versiones antiguas del fork usaban `bauh`. |
| `~/.local/share/applications/bauh.desktop`, `bauh_tray.desktop` | Ambos (mismo nombre) | El instalador del fork los sobrescribe; el paquete oficial los instala en `/usr/share/applications/`. |
| `~/.local/share/icons/hicolor/<N>x<N>/apps/bauh.png` | Solo el fork | Icono Gekko; el oficial usa el suyo desde `/usr/share`. |
| `/etc/bauh/gems.forbidden` | Ambos | Gems prohibidas por el administrador. |
| `~/.config/autostart/bauh_tray.desktop` | Ambos | Si activaste el arranque de la bandeja. |

## 2. Claves de `config.yml` que el bauh oficial no entiende

| Clave | Valor típico en el fork | Efecto en el bauh oficial |
|---|---|---|
| `ui.theme` | `aurora`, `gtk`, `matugen` | El oficial no tiene esos temas: arranca **sin hoja de estilos** (aspecto Fusion plano, sin error visible) hasta que elijas otro tema en sus ajustes. Los valores compartidos son `light`, `darcula`, `default`, `knight` y `sublime`. |
| `custom_theme` (color de fondo, texto, acento, opacidad, imagen) | Objeto | Ignorado. |
| `gems` | Lista con `arch`, `flatpak`, `eopkg`, `github`, ... | Los nombres que el oficial no conoce (`eopkg`, `github`) se ignoran. **Ojo**: como la lista existe, el oficial solo activará las gems que aparezcan en ella; AppImage/Snap/Web/Debian quedarán desactivadas hasta que las marques en sus ajustes o borres la clave (`gems: null` = todas las que el sistema permita). |

En sentido contrario no hay problema: el fork entiende todas las claves del
oficial. La única diferencia al llegar desde el oficial es que las gems
heredadas están **desactivadas por defecto** en el fork; si en el oficial las
usabas, actívalas en `Ajustes → Tipos de aplicaciones`.

## 3. Del bauh oficial al fork

1. Cierra bauh (y el icono de bandeja si está activo).
2. Opcional pero recomendado: copia tu configuración
   (`cp -r ~/.config/bauh ~/.config/bauh.bak`).
3. Ejecuta el instalador:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash
   ```
   Si detecta el paquete `bauh` del sistema te avisará; para que lo
   desinstale por ti añade `--remove-system-bauh` (requiere `sudo`). También
   puedes hacerlo tú antes: `sudo pacman -Rns bauh` o `sudo eopkg remove bauh`.
   No es obligatorio desinstalarlo, pero si conviven, `bauh` en el `PATH`
   puede resolver a uno u otro según el orden de `~/.local/bin` y `/usr/bin`,
   y los dos `.desktop` se llaman igual.
4. Abre el fork. Tu configuración se conserva. Arch, Flatpak y eopkg quedan
   activas; revisa `Ajustes → Tipos de aplicaciones` y marca
   AppImage/Snap/Web/Debian si las quieres. El tema cambia a Aurora solo si no
   tenías uno configurado.

## 4. Del fork al bauh oficial (vuelta atrás)

### Camino recomendado

```bash
curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- uninstall
```

Elimina el entorno pipx (`bauh-gekko` y, si quedara, el antiguo `bauh`), los
`.desktop` de `~/.local/share/applications/` y los iconos, y refresca las
cachés. Antes de terminar **ofrece restablecer `ui.theme`** a `light` en
`config.yml` para que el oficial arranque con tema. Acepta si vas a volver al
oficial conservando la configuración.

Si además quieres empezar de cero:

```bash
curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- uninstall --purge
```

`--purge` borra `~/.config/bauh`, `~/.cache/bauh`, `~/.local/share/bauh` y
`$XDG_RUNTIME_DIR/bauh`. **No** borra `~/BauhRepos` ni nada que hayas
compilado o instalado con la gem GitHub (esos paquetes se gestionan con pacman
o con el método de build que usaste).

Después instala el oficial: `sudo pacman -S bauh` (Arch y derivados),
`pipx install bauh` (PyPI) o el método que prefieras de su
[README](https://github.com/vinifmor/bauh#installation).

### Camino manual

Si no quieres usar el instalador:

1. `pipx uninstall bauh-gekko` (y `pipx uninstall bauh` si aparece en
   `pipx list` como versión antigua del fork).
2. `rm -f ~/.local/share/applications/bauh.desktop ~/.local/share/applications/bauh_tray.desktop`
   y los iconos `~/.local/share/icons/hicolor/*/apps/bauh.png`.
3. Edita `~/.config/bauh/config.yml` y cambia `ui.theme` a `light` (o
   cualquier tema del oficial); si tenías `gems` con `eopkg`/`github`, quítalos
   o pon `gems: null`.
4. Alternativa a lo anterior: `bauh --reset` borra `~/.config/bauh`,
   `~/.cache/bauh` y los temporales, y pide a cada gem que limpie sus datos.
   Ejecútalo **con el fork todavía instalado**, antes del paso 1.
5. Instala el oficial.

## 5. Comprobar qué bauh tienes

- `bauh --help` no distingue las ediciones, pero **Acerca de** sí: el fork
  muestra «bauh Gekko Edition», la versión `0.10.8+gekko.N` y enlaza al
  repositorio del fork; el oficial muestra `bauh` y enlaza a `vinifmor/bauh`.
- `pipx list` muestra `bauh-gekko` si el fork está instalado con el instalador.
- `pacman -Qi bauh` o `eopkg info bauh` muestran el paquete oficial del
  sistema, si existe.
- `command -v bauh` indica cuál se ejecuta al escribir `bauh`
  (`~/.local/bin/bauh` = pipx; `/usr/bin/bauh` = paquete del sistema).
