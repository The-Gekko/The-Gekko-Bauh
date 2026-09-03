# Política de sincronización con el upstream (vinifmor/bauh)

Este fork vive de seguir de cerca a [vinifmor/bauh](https://github.com/vinifmor/bauh).
Esta página define cómo se integra su trabajo, cómo se resuelven los conflictos
en las partes que el fork ha reestructurado y cómo se numeran las versiones.
Es la única fuente de verdad sobre este tema; si algo cambia, se cambia aquí.

## 1. Remotes y ramas

| Nombre | URL | Uso |
|---|---|---|
| `origin` | `https://github.com/The-Gekko/Bauh-Fork-The-Gekko.git` | El fork. Rama publicada: `master`. |
| `upstream` | `https://github.com/vinifmor/bauh.git` | El proyecto original. Se vigilan `master` (releases), `staging` (siguiente versión) y las ramas `fix-*`. |

```bash
git remote add upstream https://github.com/vinifmor/bauh.git   # una sola vez
git fetch upstream --tags
```

## 2. Base upstream registrada

Cada versión del fork declara en `CHANGELOG.md` su **base upstream**: la rama y
el commit de `vinifmor/bauh` sobre los que está construida, más las ramas
adicionales que se hayan integrado. Ejemplo (0.10.8+gekko.1):
`staging@3a38a666` + `fix-qt-wayland-crash`. Los merges de sincronización
llevan en su mensaje el commit exacto que integran, de modo que
`git log --merges --grep='upstream'` reconstruye el historial completo.

## 3. Procedimiento de sincronización

Siempre **merge**, nunca rebase de `master`: `master` está publicada,
`install.sh` la instala por commit y reescribir su historial rompería la
detección de actualizaciones de todos los usuarios.

```bash
git fetch upstream --tags
git switch -c sync/upstream-$(date +%Y%m%d) master
git merge --no-ff upstream/staging      # o upstream/master, o upstream/fix-xxx
# resolver conflictos (sección 4)
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests
.venv/bin/ruff check bauh tests && shellcheck install.sh && python3 tools/check_locales.py
git commit   # mensaje: "merge: integrar upstream/staging@<sha corto> (<resumen>)"
```

Después se abre un pull request `sync/upstream-...` → `master` titulado
`sync: upstream/staging@<sha>`; se integra con la CI en verde y **sin
squash** (para conservar los commits y la autoría del upstream).

Cadencia: al menos una vez por trimestre y, además, ante cualquier release o
commit relevante en `upstream/master` (suscríbete a las releases del upstream
en GitHub). Las ramas `fix-*` del upstream se integran en cuanto resuelvan un
problema que afecte al fork, sin esperar a `staging`.

## 4. Resolución de conflictos en archivos reestructurados por el fork

El fork ha movido o reescrito algunos archivos que el upstream sigue tocando.
Regla general: **el cambio del upstream se porta al lugar nuevo**; nunca se
resucita el archivo antiguo para «que aplique el parche».

| Si el upstream cambia... | En el fork vive en... | Cómo se resuelve |
|---|---|---|
| `bauh/view/qt/window.py` (la `ManageWindow` monolítica) | `bauh/view/qt/window/manage_window.py` y `bauh/view/qt/window/mixins/{ui,actions,filters}.py` | Git lo marcará como «borrado por nosotros / modificado por ellos». Se acepta el borrado y se aplica el cambio a mano en el mixin correspondiente (UI → `ui.py`, acciones/diálogos → `actions.py`, filtros → `filters.py`). |
| `bauh/view/qt/thread.py` | `bauh/view/qt/thread.py` (único módulo de hilos) | Merge normal. Si el upstream añade una clase nueva, se añade aquí y se exporta con el mismo nombre. |
| `bauh/view/qt/components.py` | `bauh/view/qt/components/*.py` | Aceptar el borrado y portar el cambio al módulo del componente. |
| `bauh/view/qt/root.py` (`RootDialog`) | Mismo archivo, reescrito | Mantener la firma `ask_password(..., parent=...)` y la entrega de la contraseña por `stdin`; portar solo la lógica. |
| `bauh/context.py`, `bauh/stylesheet.py` | Mismos archivos | Mantener `set_theme(theme_key, app, logger, app_config=None)` y el vigilante de temas; portar el cambio. |
| `bauh/gems/arch/pacman.py`, `controller.py` | Mismos archivos | Merge normal. Cuidado con `get_databases` (regex con guion), la deduplicación en `search()` y la acción de cambio a binario. |
| `setup.py`, `setup.cfg`, `pyproject.toml`, `requirements.txt` | Solo `pyproject.toml` (`[project]`) | Este proyecto borró `setup.py` y `setup.cfg`: acepta el borrado en el conflicto y porta a `pyproject.toml` las dependencias y clasificadores nuevos. |
| `bauh/__init__.py` (`__version__`) | Mismo archivo | Conservar siempre la versión del fork (sección 5). |
| `CHANGELOG.md` | Mismo archivo | La sección del fork queda arriba; las del upstream se conservan literalmente debajo de la nota «Las entradas siguientes proceden del upstream». |
| `README.md`, `CONTRIBUTING.md`, plantillas de `.github/` | Reescritos en español | Se descarta el texto del upstream; si trae información nueva (requisitos, dependencias) se incorpora redactada. |
| `bauh/view/resources/locale/*`, `bauh/gems/*/resources/locale/*` | Mismos archivos | Merge normal; después `python3 tools/check_locales.py`. Las claves nuevas del fork nunca colisionan si llevan prefijo propio (`gekko.`, `eopkg.`, `github.`). |
| `bauh/desktop/gekko-bauh.desktop`, `gekko-bauh-tray.desktop`, `linux_dist/` | Archivos propios | Merge normal; conservar `StartupWMClass=gekko-bauh` y el nombre visible. Renombrar los del upstream, no añadirlos. |
| `install.sh` | Solo existe en el fork | Sin conflicto posible. |

Tras cualquier merge con conflictos se ejecuta la suite completa con PyQt5 (los
conflictos en la capa Qt no se detectan sin ella) y se arranca la aplicación
al menos una vez (`gekko-bauh --logs`).

## 5. Esquema de versiones

- `bauh/__init__.py`: `__version__ = '<versión upstream>+gekko.N'`
  (PEP 440 con etiqueta local). Ejemplo: `0.10.8+gekko.1`.
- Etiqueta git: `v<versión upstream>-gekko.N` (PEP 440 no permite `+` en los
  nombres de etiqueta habituales de GitHub). Ejemplo: `v0.10.8-gekko.1`.
- `<versión upstream>` es la versión del upstream en la que se basa el fork,
  **publicada o no**: mientras el upstream tenga 0.10.8 solo en `staging`, el
  fork ya usa `0.10.8+gekko.N` porque incluye ese código.
- `N` empieza en 1 y sube con cada release del fork sobre la misma base.
  **Se reinicia a 1** cuando se integra una versión nueva del upstream.
- `pip`/`pipx` ordenan correctamente `0.10.8 < 0.10.8+gekko.1 < 0.10.9`, así
  que el fork siempre «gana» a la misma versión del upstream y siempre
  «pierde» frente a la siguiente, que es lo deseado.

## 6. Cuando el upstream publique 0.10.8, 0.10.9, ...

1. `git fetch upstream --tags` y merge de `upstream/master` en `master`
   siguiendo la sección 3.
2. Si la versión publicada coincide con la base actual (por ejemplo 0.10.8 ya
   estaba en `staging`): revisar el diff entre `staging` integrado y la
   etiqueta, actualizar la «base upstream» del `CHANGELOG.md`, subir `N`
   (`0.10.8+gekko.2`) y etiquetar.
3. Si es una versión nueva (0.10.9): tras el merge, cambiar `__version__` a
   `0.10.9+gekko.1`, abrir una sección `## [0.10.9+gekko.1]` en
   `CHANGELOG.md` con la base upstream y las contribuciones integradas
   (copiar la lista de `### Contributions` del upstream con enlaces a los
   autores), etiquetar `v0.10.9-gekko.1` y publicar la release en GitHub
   (wheel + sdist + `sha256` generados por la CI).
4. Comprobar que `install.sh` instala la versión nueva en un equipo limpio y
   que la migración de configuración descrita en `docs/MIGRACION.md` sigue
   siendo cierta.

## 7. Devolver arreglos al upstream

Toda corrección que **no** sea específica del fork (un fallo de la gem Arch,
una traducción, un crash de la interfaz, un problema de empaquetado que también
tenga el upstream) se envía al upstream:

1. Crear la rama desde `upstream/staging`, no desde `master` del fork:
   `git switch -c fix/<tema> upstream/staging`.
2. Aplicar solo el arreglo (sin tema Aurora, sin `install.sh`, sin cambios de
   identidad), con mensaje de commit y descripción del pull request **en
   inglés**, siguiendo el estilo del upstream.
3. Abrir el pull request contra `vinifmor/bauh:staging` y enlazarlo desde el
   issue o commit del fork.
4. Cuando el upstream lo integre, entrará de vuelta en el fork con la siguiente
   sincronización; mientras tanto el fork puede llevar el mismo commit
   (cherry-pick) para no esperar.

Lo que **no** se envía al upstream: tema Aurora y temas dinámicos, gems eopkg
y GitHub, `install.sh`, cambios de nombre/URL, gems opt-in y cualquier
decisión de producto propia del fork.
