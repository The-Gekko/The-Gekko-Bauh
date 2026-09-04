# Créditos, procedencia y aviso de versión alterada

## Aviso de versión alterada (licencia zlib/libpng, cláusula 2)

**gekko-bauh** («bauh Gekko Edition») es una **versión alterada** de
[bauh](https://github.com/vinifmor/bauh), software original de
**Vinícius Moreira** (© 2019, licencia zlib/libpng, ver [LICENSE](LICENSE)).
No es el software original ni debe presentarse como tal: lo mantiene
[The-Gekko](https://github.com/The-Gekko) en
<https://github.com/The-Gekko/The-Gekko-Bauh>, se distribuye con el nombre
`gekko-bauh` y con versiones `<versión de origen>+gekko.N` (actualmente
`0.10.8+gekko.1`). El texto de la licencia se conserva sin cambios y sigue
aplicándose a todo el código, incluido el añadido aquí.

El proyecto se desarrolla de forma independiente, con su propio rumbo, sus
propias versiones y su propia identidad en el sistema (ejecutable `gekko-bauh`,
configuración en `~/.config/gekko-bauh`), de modo que puede instalarse junto al
bauh oficial sin interferir con él. Esa independencia no reduce la deuda con el
proyecto del que parte: la inmensa mayoría del código sigue siendo suyo.

Los errores de esta edición se reportan en este repositorio, nunca en el del
proyecto original.

## Proyecto original

**bauh** fue concebido y creado por **[Vinícius Moreira](https://github.com/vinifmor)**
como interfaz gráfica para administrar aplicaciones en Linux (AppImage, Arch /
AUR, Debian, Flatpak, Snap y Web). La inmensa mayoría del código de este
repositorio es suyo y de los colaboradores del proyecto original; sin esa base
este proyecto no existiría.

### Colaboradores del upstream cuyo trabajo incluye esta versión

Cambios publicados en `vinifmor/bauh` después de la versión 0.10.7 e integrados
en `0.10.8+gekko.1` (ver la sección «Contributions (upstream)» de
[CHANGELOG.md](CHANGELOG.md)):

| Colaborador | Aportación |
|---|---|
| [vinifmor](https://github.com/vinifmor) | Mantenimiento, 0.10.8 en `staging`, arreglo `fix-qt-wayland-crash`. |
| [albanobattistella](https://github.com/albanobattistella) | Traducciones al italiano. |
| [KoromeloDev](https://github.com/KoromeloDev) | Traducciones al ruso. |
| [antipeth](https://github.com/antipeth) | Traducción al chino simplificado. |
| [Boria138](https://github.com/Boria138) | Detección de sistemas basados en Arch mediante `/etc/os-release`. |
| [EGYT5453](https://github.com/EGYT5453) | Limpieza de espacios en las traducciones inglesas. |
| [NoobKozlegeny](https://github.com/NoobKozlegeny) | Arch: marcar/desmarcar todas las dependencias opcionales de una vez. |

Las versiones anteriores a 0.10.7 incluyen a muchos más colaboradores; sus
nombres están en el historial del upstream y en las secciones antiguas de
`CHANGELOG.md`.

## Qué aporta este proyecto (The-Gekko)

Lo siguiente sí es trabajo de este proyecto y no existe en el original. La lista es
deliberadamente concreta; lo que no aparece aquí (Timeshift, `rebuild-detector`,
`-j$(nproc)`, búsquedas en paralelo, los gestores de Flatpak, AppImage, Snap,
Web y Debian)
es del proyecto original.

- **Temas**: tema Aurora (por defecto) y temas dinámicos GTK 3/4 y Matugen con
  recarga automática; botón Matugen; pestaña Personalización.
- **Gems nuevas**: eopkg (Solus) y GitHub (clonar y compilar con confirmación
  explícita del comando).
- **Gem Arch**: repositorios con guion en `get_databases`, deduplicación
  repositorio/AUR y acción «Cambiar al binario del repositorio».
- **Alcance acotado**: Arch/AUR/Chaotic AUR, Flatpak y Solus (eopkg) activas por
  defecto; AppImage, Web y GitHub quedan como opcionales. Los gestores de Debian
  y Snap, que pertenecen a otras distribuciones, se han eliminado.
- **Diálogo de contraseña** modal y endurecimiento de seguridad (contraseña
  por `stdin` a `sudo -S -k`, temporales privados `0700` bajo
  `~/.cache/gekko-bauh/tmp` con dueño y enlaces comprobados, pacman sin shell).
- **Reorganización de la ventana principal** en `ManageWindow` + mixins, un
  único módulo de hilos (`bauh/view/qt/thread.py`) y eliminación de módulos
  fósiles; cierre bloqueado durante transacciones; `SIGINT`/`SIGTERM`;
  `sys.excepthook`.
- **Instalador `install.sh`** por `curl` con `pipx`, iconos, `.desktop`,
  migración y desinstalación con `--purge`.
- **Identidad e empaquetado**: nombre propio `gekko-bauh` (ejecutable, lanzador,
  icono y configuración), con migración automática desde `~/.config/bauh`;
  `pyproject.toml` con `[project]`
  completo, CI en GitHub Actions, soporte de Python 3.13 y 3.14.
- **Documentación** en español (README, CONTRIBUTING, docs/, plantillas).

Nota de atribución: el `pyproject.toml` **no** es una aportación de este proyecto.
El proyecto original lo introdujo en 0.10.6 (solo con `[build-system]`); aquí se
completa con la sección `[project]` y se eliminan `setup.py` y `setup.cfg`.

## Arte

La imagen `pictures/gekko-bauh.png` y los iconos derivados de ella fueron
**generados con IA** para este proyecto. Los iconos y recursos gráficos originales
de bauh (`bauh/view/resources/img/`, `bauh/gems/*/resources/img/`) pertenecen
al proyecto original.

## Licencia

Todo el repositorio se distribuye bajo la licencia **zlib/libpng** reproducida
en [LICENSE](LICENSE). Si redistribuyes esta edición, conserva ese archivo, este
aviso de versión alterada y la atribución al autor original.
