# Créditos, procedencia y aviso de versión alterada

## Aviso de versión alterada (licencia zlib/libpng, cláusula 2)

**bauh Gekko Edition** es una **versión alterada** de
[bauh](https://github.com/vinifmor/bauh), software original de
**Vinícius Moreira** (© 2019, licencia zlib/libpng, ver [LICENSE](LICENSE)).
No es el software original ni debe presentarse como tal: lo mantiene
[The-Gekko](https://github.com/The-Gekko) en
<https://github.com/The-Gekko/Bauh-Fork-The-Gekko>, se distribuye con el
nombre `bauh-gekko` y con versiones `<versión upstream>+gekko.N`
(actualmente `0.10.8+gekko.1`). El texto de la licencia se conserva sin cambios
y sigue aplicándose a todo el código, incluido el añadido por el fork.

Los errores de esta edición se reportan en el repositorio del fork, nunca en el
del proyecto original.

## Proyecto original

**bauh** fue concebido y creado por **[Vinícius Moreira](https://github.com/vinifmor)**
como interfaz gráfica para administrar aplicaciones en Linux (AppImage, Arch /
AUR, Debian, Flatpak, Snap y Web). La inmensa mayoría del código de este
repositorio es suyo y de los colaboradores del proyecto original; sin esa base
el fork no existiría.

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

## Qué aporta el fork (The-Gekko)

Lo siguiente sí es trabajo del fork y no existe en el upstream. La lista es
deliberadamente concreta; lo que no aparece aquí (Timeshift, `rebuild-detector`,
`-j$(nproc)`, búsquedas en paralelo, gestores AppImage/Flatpak/Snap/Web/Debian)
es del proyecto original.

- **Temas**: tema Aurora (por defecto) y temas dinámicos GTK 3/4 y Matugen con
  recarga automática; botón Matugen; pestaña Personalización.
- **Gems nuevas**: eopkg (Solus) y GitHub (clonar y compilar con confirmación
  explícita del comando).
- **Gem Arch**: repositorios con guion en `get_databases`, deduplicación
  repositorio/AUR y acción «Cambiar al binario del repositorio».
- **Gems heredadas opt-in** (desactivadas por defecto).
- **Diálogo de contraseña** modal y endurecimiento de seguridad (contraseña
  por `stdin` a `sudo -S -k`, temporales bajo `$XDG_RUNTIME_DIR`, pacman sin
  shell).
- **Reorganización de la ventana principal** en `ManageWindow` + mixins, un
  único módulo de hilos (`bauh/view/qt/thread.py`) y eliminación de módulos
  fósiles; cierre bloqueado durante transacciones; `SIGINT`/`SIGTERM`;
  `sys.excepthook`.
- **Instalador `install.sh`** por `curl` con `pipx`, iconos, `.desktop`,
  migración y desinstalación con `--purge`.
- **Empaquetado**: distribución `bauh-gekko`, `pyproject.toml` con `[project]`
  completo, CI en GitHub Actions, soporte de Python 3.13 y 3.14.
- **Documentación** en español (README, CONTRIBUTING, docs/, plantillas).

Nota de atribución: el `pyproject.toml` **no** es una aportación del fork.
El upstream lo introdujo en 0.10.6 (solo con `[build-system]`); el fork lo
completa con la sección `[project]` y convierte `setup.py` en un shim.

## Arte

La imagen `pictures/gekko-bauh.png` y los iconos derivados de ella fueron
**generados con IA** para este fork. Los iconos y recursos gráficos originales
de bauh (`bauh/view/resources/img/`, `bauh/gems/*/resources/img/`) pertenecen
al proyecto original.

## Licencia

Todo el repositorio se distribuye bajo la licencia **zlib/libpng** reproducida
en [LICENSE](LICENSE). Si redistribuyes esta edición, conserva ese archivo, este
aviso de versión alterada y la atribución al autor original.
