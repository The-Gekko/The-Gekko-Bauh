# Distribución: publicar una versión de gekko-bauh

Este documento es el procedimiento completo para sacar una versión: qué se
cambia en el repositorio, qué hace solo el workflow de GitHub, qué hay que hacer
a mano en el AUR y cómo comprueba un usuario que lo que ha descargado es lo que
publicamos.

Índice:

1. [Esquema de versión](#1-esquema-de-versión)
2. [Antes de etiquetar](#2-antes-de-etiquetar)
3. [Etiquetar y empujar](#3-etiquetar-y-empujar)
4. [Qué hace el workflow de release](#4-qué-hace-el-workflow-de-release)
5. [Actualizar el paquete del AUR](#5-actualizar-el-paquete-del-aur)
6. [Verificar las sumas antes de instalar](#6-verificar-las-sumas-antes-de-instalar)
7. [PyPI: por qué no se publica](#7-pypi-por-qué-no-se-publica)
8. [Comprobaciones locales, sin red](#8-comprobaciones-locales-sin-red)

---

## 1. Esquema de versión

El mismo número aparece en tres sitios con dos grafías distintas:

| Dónde | Forma | Ejemplo |
| --- | --- | --- |
| `bauh.__version__` (`bauh/__init__.py`, primera línea) | `X.Y.Z+gekko.N` | `0.10.8+gekko.1` |
| Etiqueta git y nombre de la release | `vX.Y.Z-gekko.N` | `v0.10.8-gekko.1` |
| `pkgver` del PKGBUILD del AUR | `X.Y.Z+gekko.N` | `0.10.8+gekko.1` |

**Por qué dos grafías.** `makepkg` rechaza un `pkgver` que contenga dos puntos,
barras, **guiones** o espacios; lo comprueba
`/usr/share/makepkg/lint_pkgbuild/pkgver.sh`. El signo `+`, en cambio, sí es
válido. Y en Python `0.10.8+gekko.1` es una *local version* correcta de PEP 440,
que es justo lo que queremos decir: «la 0.10.8 del proyecto original, con los
cambios de este fork encima».

La etiqueta usa `-gekko.N` porque es la forma natural de un sufijo en git y en
SemVer, y porque así se lee de un vistazo que no es una versión del proyecto
original.

**La conversión es un único cambio de carácter**, en los dos sentidos:

```sh
# de versión de Python a pkgver:   -  →  +
# de pkgver a etiqueta:            +  →  -   (y una «v» delante)
```

En el PKGBUILD se hace en una línea, `_tag="v${pkgver/+/-}"`, y en el workflow de
release hay una comprobación que aborta si la etiqueta y `__version__` no
encajan.

**Orden con `vercmp`:** `0.10.8 < 0.10.8+gekko.1`. Quien venga del `bauh`
original nunca ve este paquete como una versión anterior.

`X.Y.Z` es siempre la versión del proyecto original de la que parte el fork;
`N` se incrementa con cada publicación propia sobre esa misma base y vuelve a
`1` cuando se integra una `X.Y.Z` nueva de aguas arriba.

---

## 2. Antes de etiquetar

Todo esto se hace en una rama y se fusiona a `master` de la forma habitual. La
etiqueta se pone **después**, sobre el commit ya fusionado.

1. **La CI de `master` tiene que estar en verde.** El workflow de release no
   repite la suite: da por bueno lo que ya validó `ci.yml`.

2. **Subir `__version__`** en la primera línea de `bauh/__init__.py`:

   ```python
   __version__ = '0.10.9+gekko.1'
   ```

   Tiene que ser la primera línea y con comillas simples: tanto el instalador
   como el `pkgver()` del paquete `-git` y el workflow la leen con una expresión
   regular sobre esa línea.

3. **Actualizar el `CHANGELOG.md`**: una sección nueva encabezada con la versión
   y la fecha, describiendo los cambios de esta publicación.

4. **Actualizar el PKGBUILD estable** `packaging/aur/gekko-bauh/PKGBUILD`:

   ```sh
   # pkgver con la grafía «+», pkgrel de vuelta a 1
   sed -i "s/^pkgver=.*/pkgver=0.10.9+gekko.1/; s/^pkgrel=.*/pkgrel=1/" \
       packaging/aur/gekko-bauh/PKGBUILD
   ```

   `pkgrel` solo sube (2, 3…) cuando cambia el empaquetado sin cambiar el
   código; al cambiar `pkgver` vuelve siempre a `1`.

   El PKGBUILD del paquete `-git` **no** se toca en cada versión: su `pkgver()`
   calcula el número en cada construcción.

5. **Regenerar los `.SRCINFO`** (hace falta `pacman`, es decir, una máquina Arch):

   ```sh
   ( cd packaging/aur/gekko-bauh     && makepkg --printsrcinfo > .SRCINFO )
   ( cd packaging/aur/gekko-bauh-git && makepkg --printsrcinfo > .SRCINFO )
   ```

6. **Pasar la suite**, que comprueba justo esa coherencia:

   ```sh
   QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests
   ```

   `tests/packaging/test_aur.py` falla si el `.SRCINFO` se quedó atrás, si el
   `pkgver` no corresponde a `bauh.__version__` o si el `package()` instala
   ficheros que ya no existen.

---

## 3. Etiquetar y empujar

Sobre el commit de `master` ya fusionado y con la CI en verde:

```sh
git tag -a v0.10.9-gekko.1 -m 'gekko-bauh 0.10.9+gekko.1'
git push origin v0.10.9-gekko.1
```

Empujar la etiqueta es lo único que dispara la publicación.

Si hay que repetir la publicación de una etiqueta que ya existe, no hace falta
borrarla: el workflow `release` se puede lanzar a mano desde la pestaña
*Actions* pasándole la etiqueta como parámetro.

---

## 4. Qué hace el workflow de release

`.github/workflows/release.yml`, disparado por cualquier etiqueta `v*`:

1. **Comprueba que la etiqueta corresponde al código.** Lee `__version__` de
   `bauh/__init__.py` y exige que la etiqueta sea esa versión con `+` cambiado
   por `-` y una `v` delante. Si no, aborta.

2. **Comprueba que el PKGBUILD va con esa versión.** Compara el `pkgver` de
   `packaging/aur/gekko-bauh/PKGBUILD` con la versión publicada. Es el despiste
   más habitual: etiquetar la versión nueva y dejarse el PKGBUILD en la anterior.

3. **Construye** el wheel y el sdist con `python -m build`.

4. **Los valida** con `twine check`.

5. **Descarga el tarball de código fuente** que GitHub genera para la etiqueta
   —el mismo que se baja el PKGBUILD del AUR— y lo guarda con el nombre exacto
   que le da `makepkg`: `gekko-bauh-<pkgver>.tar.gz`.

6. **Genera `SHA256SUMS`** con las sumas de los tres ficheros y lo comprueba
   ahí mismo con `sha256sum --check`.

7. **Publica la release** con `gh` (la CLI oficial que traen los runners) y le
   adjunta el wheel, el sdist, el tarball de código fuente y el `SHA256SUMS`.

No publica en PyPI ni sube nada al AUR: eso es el paso siguiente, y es manual.

---

## 5. Actualizar el paquete del AUR

El AUR es un repositorio git independiente; lo que hay en `packaging/aur/` es la
fuente de la que se copia. Cada paquete tiene su propio repositorio:

```sh
git clone ssh://aur@aur.archlinux.org/gekko-bauh.git      /tmp/aur-gekko-bauh
git clone ssh://aur@aur.archlinux.org/gekko-bauh-git.git  /tmp/aur-gekko-bauh-git
```

(Para poder empujar hay que tener la clave SSH pública dada de alta en la cuenta
del AUR: <https://aur.archlinux.org/account/>.)

Para el paquete estable, **después** de que la release exista:

```sh
cp packaging/aur/gekko-bauh/PKGBUILD /tmp/aur-gekko-bauh/
cd /tmp/aur-gekko-bauh

# 1. Rellenar la suma real del tarball. El PKGBUILD del repositorio lleva
#    sha256sums=('SKIP') a propósito: la suma no existe hasta que la etiqueta
#    está publicada. updpkgsums (del paquete pacman-contrib) descarga la fuente
#    y escribe la suma en el PKGBUILD.
updpkgsums

# 2. Contrastarla con la que publicó el workflow. La línea de SHA256SUMS usa
#    exactamente el mismo nombre de fichero, así que la comprobación es directa:
curl -fsSLO https://github.com/The-Gekko/Bauh-Fork-The-Gekko/releases/download/v0.10.9-gekko.1/SHA256SUMS
sha256sum --check --ignore-missing SHA256SUMS

# 3. Construir e instalar de verdad antes de subir nada.
makepkg -si

# 4. Regenerar el .SRCINFO (el AUR lo usa para indexar; sin él el paquete se
#    rechaza) y publicar.
makepkg --printsrcinfo > .SRCINFO
git add PKGBUILD .SRCINFO
git commit -m 'gekko-bauh 0.10.9+gekko.1'
git push
```

**Copia la suma de vuelta al repositorio del proyecto** si quieres que quede
registrada; si no, deja el `SKIP` y repite `updpkgsums` en la siguiente versión.

El paquete `gekko-bauh-git` solo hay que volver a subirlo cuando cambie su
receta (dependencias, `package()`…), no en cada versión: construye siempre desde
`master`.

Comprobaciones recomendadas antes de empujar al AUR, si tienes `namcap`:

```sh
namcap PKGBUILD
namcap gekko-bauh-*.pkg.tar.zst
```

---

## 6. Verificar las sumas antes de instalar

Cada release lleva un fichero `SHA256SUMS` con las sumas del wheel, del sdist y
del tarball de código fuente. Descárgalo junto con lo que te lleves y comprueba:

```sh
sha256sum --check --ignore-missing SHA256SUMS
```

`--ignore-missing` es lo que permite comprobar solo los ficheros que hayas
descargado sin que falle por los que no.

**Instalación por `curl` (`install.sh`).** El instalador no usa `SHA256SUMS`:
resuelve la referencia que le pidas contra la API de GitHub, obtiene el SHA-1
del commit exacto y descarga y guarda **ese** commit. La integridad viene del
identificador del commit y de HTTPS, no de una suma aparte. Si prefieres la
comprobación explícita, instala desde el AUR o desde la release.

**Aviso sobre los tarballs de GitHub.** Los tarballs `archive/refs/tags/...` los
regenera GitHub bajo demanda. En la práctica son estables, pero en 2023 hubo un
episodio en el que cambió su compresión y las sumas de medio mundo dejaron de
cuadrar. Publicar la suma en el `SHA256SUMS` de la release es justo lo que
permite detectarlo: si `updpkgsums` te da un valor distinto del publicado,
**no subas el paquete** y revisa qué ha pasado.

---

## 7. PyPI: por qué no se publica

El paso está escrito y comentado al final de `release.yml`, listo para
activarse, pero **no está activo**. Hay dos cosas que decidir antes:

1. **PyPI rechaza las *local versions* de PEP 440**, y `0.10.8+gekko.1` es
   exactamente eso. Publicar en PyPI obligaría a cambiar el esquema de versión
   (por ejemplo a `0.10.8.post1`) y, con él, la etiqueta y el `pkgver` del AUR.

2. **Hay que reservar el nombre `gekko-bauh` en PyPI** y dar de alta un
   publicador de confianza (OIDC) en
   <https://pypi.org/manage/account/publishing/>. Así no hay que guardar ningún
   token en el repositorio, pero el trabajo necesitaría `id-token: write` en sus
   permisos.

Mientras tanto el wheel y el sdist se publican en la release de GitHub, que es
suficiente para instalar con `pipx` o `pip` desde una URL.

---

## 8. Comprobaciones locales, sin red

Lo que se puede validar sin `makepkg`, sin red y en cualquier distribución:

```sh
# Sintaxis de los dos PKGBUILD
bash -n packaging/aur/gekko-bauh/PKGBUILD
bash -n packaging/aur/gekko-bauh-git/PKGBUILD

# Coherencia PKGBUILD ↔ .SRCINFO, versión, dependencias y ficheros instalados
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p 'test_aur.py'
```

Con `shellcheck` instalado (SC2164 se excluye porque `makepkg` ya aborta si un
`cd` falla, y SC2034/SC2154 porque las variables de `makepkg` no están definidas
en el fichero):

```sh
shellcheck --shell=bash --exclude=SC2034,SC2154,SC2164 packaging/aur/*/PKGBUILD
```

En una máquina Arch, además:

```sh
( cd packaging/aur/gekko-bauh && makepkg --printsrcinfo | diff -u .SRCINFO - )
```

---

## Apéndice: convivencia con el paquete `bauh`

Los PKGBUILD **no** declaran `conflicts=('bauh')` ni `provides=('bauh')`, y es
deliberado. Este proyecto no toca ninguno de los nombres del proyecto original:
los ejecutables son `gekko-bauh`, `gekko-bauh-tray` y `gekko-bauh-cli`; los
lanzadores, `gekko-bauh.desktop` y `gekko-bauh-tray.desktop`; el icono del tema,
`gekko-bauh`; y la configuración vive en `~/.config/gekko-bauh`.

El único punto que sí chocaría es el paquete importable, que se sigue llamando
`bauh` para poder seguir integrando las correcciones del proyecto original sin
reescribir cada `import`. Por eso `package()` **no** lo deja en `site-packages`:
lo instala en `/usr/share/gekko-bauh` y escribe tres lanzadores en `/usr/bin`
que anteponen ese directorio a `sys.path`. Así pacman no ve ni un solo fichero
compartido con el paquete `bauh` del AUR y las dos versiones se pueden tener
instaladas a la vez.

Tampoco se declara `provides=('bauh')` porque este paquete **no** es un
sustituto transparente: no aporta `/usr/bin/bauh`, así que nada que dependa de
`bauh` quedaría satisfecho con él.
