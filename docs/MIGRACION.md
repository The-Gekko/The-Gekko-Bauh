# Migración: convivencia con el bauh oficial y vuelta atrás

`gekko-bauh` deriva de [bauh](https://github.com/vinifmor/bauh) pero es un
proyecto independiente **con identidad propia en el sistema**: su ejecutable, su
lanzador, su icono y su configuración llevan su propio nombre. Eso significa que
puede instalarse junto al bauh oficial sin pisarlo, y que volver al oficial no
deja su instalación en un estado raro.

Hasta la versión `0.10.8+gekko.1` ambos compartían el nombre `bauh` y, con él,
la configuración. Si vienes de una versión anterior, lee también la sección 5.

## 1. Qué usa cada uno

| Ruta | Quién la usa | Notas |
|---|---|---|
| `~/.config/gekko-bauh/` | Solo este proyecto | Configuración general (`config.yml`) y por gem (`arch.yml`, `flatpak.yml`, `eopkg.yml`, `github.yml`, ...). |
| `~/.cache/gekko-bauh/` | Solo este proyecto | Caché de paquetes, iconos, sugerencias, temporales y logs. Se puede borrar sin perder nada. |
| `~/.local/share/gekko-bauh/` | Solo este proyecto | Temas de usuario (`themes/`) y datos compartidos. |
| `~/.config/bauh/`, `~/.cache/bauh/`, `~/.local/share/bauh/` | Solo el oficial | Este proyecto **solo las lee una vez**, para copiar tus ajustes, y nunca las modifica ni las borra. |
| `~/.local/share/pipx/venvs/gekko-bauh/` | Solo este proyecto | Entorno de pipx (la ruta exacta la da `pipx environment --value PIPX_LOCAL_VENVS`). |
| `~/.local/share/applications/gekko-bauh.desktop`, `gekko-bauh-tray.desktop` | Solo este proyecto | El oficial instala los suyos como `bauh.desktop` en `/usr/share/applications/`. |
| `~/.local/share/icons/hicolor/<N>x<N>/apps/gekko-bauh.png` | Solo este proyecto | El oficial usa `bauh.png` desde `/usr/share`. |
| `~/.config/autostart/gekko-bauh-tray.desktop` | Solo este proyecto | Si activaste el arranque de la bandeja. |
| `~/.local/share/gekko-bauh/github/repos/` | Solo este proyecto | Clones de la gem GitHub (configurable con `repos_dir` en `github.yml`). No se borran nunca, ni siquiera con `--purge`. `~/BauhRepos` es la ruta heredada. |
| `/etc/bauh/gems.forbidden` y `/etc/gekko-bauh/gems.forbidden` | Ambos | Gems prohibidas por el administrador. Se leen **las dos** y se unen las listas: la heredada, a propósito, para respetar la política que ya tuviera el sistema. |

Los ejecutables tampoco chocan: este proyecto instala `gekko-bauh`,
`gekko-bauh-tray` y `gekko-bauh-cli`, mientras que el oficial instala `bauh`,
`bauh-tray` y `bauh-cli`.

## 2. Migración automática al primer arranque

La primera vez que ejecutas `gekko-bauh`, si `~/.config/gekko-bauh` todavía no
existe y sí existe `~/.config/bauh`, se **copia** su contenido. Lo mismo con
`~/.local/share/bauh`, que guarda tus temas de usuario.

La copia es deliberadamente conservadora:

- solo actúa si el directorio de destino **no existe**, así que nunca sobrescribe
  ajustes tuyos;
- **no borra ni modifica** el directorio de origen, de modo que el bauh oficial
  sigue funcionando exactamente igual;
- **no copia la caché**, que se regenera sola y puede ocupar cientos de megabytes;
- no actúa cuando la aplicación se ejecuta como root, porque ahí las rutas son
  del sistema (`/etc`, `/var/cache`) y eso le corresponde al empaquetador.

Queda registrada en el log (`gekko-bauh --logs`).

## 3. Del bauh oficial a este proyecto

1. Cierra bauh, incluido el icono de bandeja si lo tienes activo.
2. Ejecuta el instalador:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/The-Gekko/The-Gekko-Bauh/master/install.sh | bash
   ```
3. Abre `gekko-bauh` desde el menú de aplicaciones. Tus ajustes y tus temas se
   copian solos. Arch, Flatpak y eopkg quedan activas; si en el oficial usabas
   AppImage, Web o GitHub, actívalas en
   `Ajustes → Tipos de aplicaciones`. El tema cambia a Aurora solo si no tenías
   ninguno configurado.

**No hace falta desinstalar el bauh oficial.** Los dos pueden convivir. Si aun
así prefieres quitarlo, añade `--remove-system-bauh` al instalador (usa `sudo`)
o hazlo tú con `sudo pacman -Rns bauh` o `sudo eopkg rmf -y bauh`.

## 4. Vuelta al bauh oficial

```bash
curl -fsSL https://raw.githubusercontent.com/The-Gekko/The-Gekko-Bauh/master/install.sh | bash -s -- uninstall
```

Elimina el entorno de pipx, los `.desktop` de `~/.local/share/applications/` y
los iconos, y refresca las cachés del escritorio. Si el bauh oficial estaba
instalado, sigue donde estaba y con su configuración intacta: no hay nada más
que hacer.

Para borrar además los datos de este proyecto:

```bash
curl -fsSL https://raw.githubusercontent.com/The-Gekko/The-Gekko-Bauh/master/install.sh | bash -s -- uninstall --purge
```

`--purge` borra `~/.config/gekko-bauh`, `~/.cache/gekko-bauh`,
`~/.local/share/gekko-bauh` y el directorio temporal, **conservando**
`~/.local/share/gekko-bauh/github/repos`, donde la gem GitHub clona tus
repositorios. Tampoco toca `~/.config/bauh`, que pertenece al oficial, ni
`~/BauhRepos`, ni nada que hayas compilado o instalado con la gem GitHub.

### Camino manual

1. `pipx uninstall gekko-bauh`.
2. `rm -f ~/.local/share/applications/gekko-bauh.desktop ~/.local/share/applications/gekko-bauh-tray.desktop`
   y los iconos `~/.local/share/icons/hicolor/*/apps/gekko-bauh.png`.
3. Opcional: `rm -rf ~/.config/gekko-bauh ~/.cache/gekko-bauh ~/.local/share/gekko-bauh`.
   Alternativa: `gekko-bauh --reset`, que además pide a cada gem que limpie sus
   datos; ejecútalo **antes** del paso 1.

## 5. Si vienes de una versión anterior a `0.10.8+gekko.1`

Aquellas versiones sí escribían en `~/.config/bauh`, así que ese directorio
puede contener ajustes que el bauh oficial no entiende:

| Clave | Valor que pudo quedar | Efecto en el bauh oficial |
|---|---|---|
| `ui.theme` | `aurora`, `gtk`, `matugen` | El oficial no tiene esos temas: arranca **sin hoja de estilos** (aspecto plano, botones sin iconos) y sin ningún error visible, hasta que elijas otro tema en sus ajustes. Los valores que ambos entienden son `light`, `darcula`, `default`, `knight` y `sublime`. |
| `custom_theme` | Objeto con colores y opacidad | Se ignora sin error. |
| `gems` | Lista con `eopkg`, `github`, ... | Los nombres que no conoce se ignoran, pero como la lista existe, el oficial solo activará las gems que aparezcan en ella. Pon `gems: null` para que active todas las que el sistema permita. |

El desinstalador detecta el caso del tema y **ofrece devolver `ui.theme` a
`light`**, con `--purge` y sin él. Acepta si vas a seguir usando el bauh oficial.

El instalador también migra el entorno de pipx: si encuentra uno llamado `bauh`
con la marca `.gekko-source-ref` dentro (es decir, instalado por este proyecto),
lo desinstala antes de crear `gekko-bauh`. Un entorno `bauh` que no lleve esa
marca se considera ajeno y no se toca.

## 6. Comprobar qué tienes instalado

- `command -v gekko-bauh` y `command -v bauh` indican cuál está en el `PATH`.
- `pipx list` muestra `gekko-bauh` si está instalado con el instalador.
- `pacman -Qi bauh` o `eopkg info bauh` muestran el paquete oficial del sistema.
- El diálogo **Acerca de** distingue las dos aplicaciones: esta muestra
  «bauh Gekko Edition», la versión `0.10.8+gekko.N` y enlaza a este repositorio
  y al original; el oficial muestra `bauh` y enlaza solo a `vinifmor/bauh`.
