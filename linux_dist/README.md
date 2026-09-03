# linux_dist — canales de distribución

## Estado: la receta de AppImage NO está soportada

El contenido de `linux_dist/appimage/` (`AppImageBuilder.yml`, `Dockerfile`,
`build.sh`) es material heredado del proyecto original y **no se mantiene en
bauh Gekko Edition**. No lo ejecutes esperando obtener un AppImage de este fork.

### Por qué no se ha adaptado

Se optó por marcarla como no soportada en lugar de actualizarla porque, tal y
como está, la receta no construye este fork sino el proyecto original, y
arreglarla a medias produciría algo peor: un AppImage con el nombre del fork y
el código de otro. Los puntos concretos:

1. **Descarga el código equivocado.** `AppImageBuilder.yml` obtiene el tarball
   de `github.com/vinifmor/bauh`, no el de este repositorio. Lo que empaqueta es
   el bauh original.
2. **Se auto-actualiza contra el upstream.** `update-information` apunta a
   `gh-releases-zsync|vinifmor|bauh|latest|…`, así que cualquier AppImage
   generado se actualizaría solo con las publicaciones del proyecto original,
   sustituyendo el fork por el upstream sin avisar.
3. **Borra ficheros de empaquetado que ya no existen.** La receta ejecuta
   `rm setup.cfg setup.py requirements.txt` para «quitar los ficheros de
   instalación obsoletos». En este fork los metadatos viven en la tabla
   `[project]` de `pyproject.toml` y `setup.py`/`setup.cfg` ya no existen: ese
   paso o falla o deja el árbol sin nada que instalar.
4. **Runtime congelado.** Fija Debian bullseye y rutas literales de
   `python3.9`, fuera del rango 3.8–3.14 que el fork declara y prueba en CI.
5. **No entra en el alcance del proyecto.** bauh Gekko Edition da soporte a Arch
   Linux con Chaotic AUR y AUR, a Flatpak y a Solus con eopkg, y se distribuye
   por un único canal: `install.sh` + pipx. Mantener y probar una segunda vía de
   empaquetado no aporta nada a ese alcance.

Para evitar sorpresas, `build.sh` aborta salvo que se le pase explícitamente la
variable de entorno `BAUH_APPIMAGE_UNSUPPORTED_OK=1`, y `AppImageBuilder.yml`
lleva el aviso en su cabecera.

### Si algún día se quiere revivir

Como mínimo habría que:

- cambiar `wget …/vinifmor/bauh/archive/…` por el archivo de este repositorio y
  fijar el commit o la etiqueta exactos (`v0.10.8-gekko.1`, por ejemplo);
- cambiar `update-information` a `gh-releases-zsync|The-Gekko|Bauh-Fork-The-Gekko|latest|…`
  y publicar el `.zsync` junto a la release;
- eliminar el paso `rm setup.cfg setup.py requirements.txt` (ya no aplica) y
  construir directamente con `python3 -m build --wheel`, que lee `pyproject.toml`;
- subir la base a Debian bookworm (o posterior) y sustituir las rutas
  `python3.9` por la versión real del runtime elegido;
- actualizar `app_info` (`id`, `name`, `icon`) a los identificadores del fork:
  `gekko-bauh` y el icono `gekko-bauh`;
- añadir un job de CI que la construya, porque una receta de empaquetado que
  nadie ejecuta vuelve a romperse en cuestión de semanas.

## Canal soportado

La instalación oficial es `install.sh`, que resuelve el commit exacto en GitHub
y lo instala aislado con **pipx** bajo el nombre de distribución `gekko-bauh`.
Consulta el README del repositorio para las instrucciones de uso.
