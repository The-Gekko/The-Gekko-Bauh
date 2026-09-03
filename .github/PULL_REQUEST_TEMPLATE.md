<!--
ES: Gracias por contribuir. Rellena las secciones y marca la lista. Lee CONTRIBUTING.md.
EN: Thanks for contributing. Fill in the sections and tick the list. Read CONTRIBUTING.md.
-->

## Qué cambia / What changes

## Por qué / Why

<!-- ES: Enlaza el issue si existe (Closes #...). EN: Link the issue if any (Closes #...). -->

## Cómo se ha probado / How it was tested

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests
```

## Lista de comprobación / Checklist

- [ ] La suite completa pasa en local (`unittest discover -s tests`) y he añadido tests para lo que cambio. / Full suite passes locally and I added tests for my change.
- [ ] `ruff check bauh tests` sin errores nuevos; `shellcheck install.sh` si toqué el instalador. / No new `ruff` errors; `shellcheck` if the installer changed.
- [ ] Textos de la interfaz vía i18n, con claves en `en` y `es` (y el resto de idiomas del directorio); `tools/check_locales.py` pasa. / UI strings go through i18n with `en` and `es` keys (plus the other languages); `tools/check_locales.py` passes.
- [ ] Comentarios y docstrings en español; identificadores en inglés. / Comments and docstrings in Spanish; identifiers in English.
- [ ] Entrada en `CHANGELOG.md` si el cambio es visible para el usuario. / `CHANGELOG.md` entry if user-visible.
- [ ] Si el arreglo no es específico del fork, he abierto (o pienso abrir) el PR equivalente en vinifmor/bauh. / If the fix is not fork-specific, I opened (or will open) the equivalent PR upstream.
- [ ] No reescribo el historial de `master` ni hago push directo. / No history rewrite of `master`, no direct push.
