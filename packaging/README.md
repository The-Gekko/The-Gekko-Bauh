# packaging/

Recetas de empaquetado del proyecto. Lo que hay aquí es la **fuente**: los
repositorios del AUR son otros y se actualizan copiando estos ficheros.

```
packaging/
└── aur/
    ├── gekko-bauh/       PKGBUILD + .SRCINFO del paquete estable (desde etiqueta)
    └── gekko-bauh-git/   PKGBUILD + .SRCINFO del paquete que compila master
```

- El procedimiento completo de publicación está en
  [`docs/DISTRIBUCION.md`](../docs/DISTRIBUCION.md).
- Los `.SRCINFO` se generan **siempre** con `makepkg --printsrcinfo > .SRCINFO`,
  nunca a mano.
- `tests/packaging/test_aur.py` comprueba en la suite que cada PKGBUILD y su
  `.SRCINFO` dicen lo mismo, que el `pkgver` cumple las reglas de pacman y
  corresponde a `bauh.__version__`, y que los ficheros que instala `package()`
  existen en el repositorio.
