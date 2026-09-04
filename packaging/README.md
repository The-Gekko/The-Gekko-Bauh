# packaging/

Recetas de empaquetado del proyecto. Lo que hay aquí es la **fuente**: los
repositorios del AUR son otros y se actualizan copiando estos ficheros.

```
packaging/
└── aur/
    ├── gekko-bauh/       PKGBUILD + .SRCINFO del paquete estable (desde etiqueta)
    └── gekko-bauh-git/   PKGBUILD + .SRCINFO del paquete que compila master
```

**Estado: la receta está lista, pero AÚN NO publicada en el AUR.** No existe
`aur.archlinux.org/packages/gekko-bauh` ni `gekko-bauh-git`. El paquete estable
además necesita la etiqueta `v0.10.8-gekko.1`, que todavía no se ha publicado
(el único release es `v0.10.7`, anterior al cambio de identidad), y por eso
lleva `sha256sums=('SKIP')`: la suma real se rellena con `updpkgsums` justo
antes de subirlo. Lo que sí se puede hacer hoy es construir `gekko-bauh-git` en
local:

```sh
cd packaging/aur/gekko-bauh-git && makepkg -si
```

- El procedimiento completo de publicación (etiqueta, workflow de release,
  alta en el AUR) está en [`docs/DISTRIBUCION.md`](../docs/DISTRIBUCION.md).
- Los `.SRCINFO` se generan **siempre** con `makepkg --printsrcinfo > .SRCINFO`,
  nunca a mano.
- Los dos PKGBUILD apuntan al repositorio `The-Gekko/The-Gekko-Bauh`. El
  tarball de una etiqueta se extrae en `The-Gekko-Bauh-<etiqueta sin la v>`,
  que es lo que calcula `_srcdir` en el paquete estable.
- `tests/packaging/test_aur.py` comprueba en la suite que cada PKGBUILD y su
  `.SRCINFO` dicen lo mismo, que el `pkgver` cumple las reglas de pacman y
  corresponde a `bauh.__version__`, que los ficheros que instala `package()`
  existen en el repositorio y que `release.yml` publica también el artefacto
  de GekkoApp.
- Los ficheros que consume [GekkoApp](https://github.com/The-Gekko/GekkoApp)
  no viven aquí: los genera `tools/build-gekkoapp-release.sh` y los adjunta a
  cada release el workflow `release.yml`.
