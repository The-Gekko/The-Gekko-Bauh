#!/usr/bin/env python3
"""Comprueba la paridad de los ficheros de traducción de bauh Gekko Edition.

Cada directorio de locales contiene un fichero por idioma («en», «es», «pt»…)
con líneas «clave=valor». El idioma «en» es la referencia: cualquier otro idioma
que no defina una de sus claves deja al usuario viendo texto en inglés (o la
clave cruda) en mitad de la interfaz.

Este script recorre bauh/view/resources/locale y el directorio de locales de
cada gem, compara las claves de cada idioma con las de «en» y termina con código
de salida 1 si falta alguna. Está pensado para ejecutarse en CI, pero también es
útil en local antes de abrir un pull request.

Uso:
    python3 tools/check_locales.py            # falla si faltan claves
    python3 tools/check_locales.py --report   # informe completo, sin fallar
    python3 tools/check_locales.py --root .   # raíz alternativa del repositorio
"""

import argparse
import os
import sys
from typing import Dict, List, Set, Tuple

# Idioma de referencia con el que se comparan todos los demás.
REFERENCE_LANGUAGE = 'en'

# Ficheros que viven junto a los locales pero no son traducciones.
IGNORED_FILENAMES = {'__init__.py'}


def find_locale_dirs(root: str) -> List[str]:
    """Devuelve todos los directorios de locales del proyecto, ordenados.

    Un directorio cuenta como conjunto de traducciones si contiene un fichero
    llamado exactamente «en». Esta regla, además de los locales principales y los
    de cada gem, recoge los subconjuntos «locale/about» y «locale/tray», que se
    cargan por separado (bauh/view/qt/about.py) y son fáciles de olvidar.
    """
    locale_dirs = []

    for current_dir, subdirs, filenames in os.walk(os.path.join(root, 'bauh')):
        # No descender en cachés de bytecode: no contienen traducciones.
        subdirs[:] = [d for d in subdirs if d != '__pycache__']

        if REFERENCE_LANGUAGE in filenames and os.path.isfile(os.path.join(current_dir, REFERENCE_LANGUAGE)):
            locale_dirs.append(current_dir)

    return sorted(locale_dirs)


def read_locale_keys(file_path: str) -> Tuple[Set[str], List[str], List[str]]:
    """Lee un fichero de traducción y devuelve (claves, errores, avisos).

    Replica el análisis de bauh.view.util.translation.get_locale_keys: se ignoran
    las líneas en blanco y se parte por el primer '=' encontrado.

    Son errores las líneas que ese analizador no puede convertir en una entrada
    (sin «=» o con clave vacía). Las claves repetidas son solo un aviso: no rompen
    nada porque gana la última, pero casi siempre señalan una traducción perdida.
    """
    keys: Set[str] = set()
    errors: List[str] = []
    warnings: List[str] = []

    with open(file_path, 'r', encoding='utf-8') as file_handle:
        for number, line in enumerate(file_handle, start=1):
            stripped = line.strip()

            if not stripped:
                continue

            if '=' not in stripped:
                errors.append(f'{file_path}:{number}: línea sin «=»: {stripped!r}')
                continue

            key = stripped.split('=', 1)[0].strip()

            if not key:
                errors.append(f'{file_path}:{number}: clave vacía')
                continue

            if key in keys:
                warnings.append(f'{file_path}:{number}: clave duplicada: {key}')

            keys.add(key)

    return keys, errors, warnings


def list_languages(locale_dir: str) -> List[str]:
    """Idiomas disponibles en un directorio de locales, ordenados."""
    languages = []

    for name in os.listdir(locale_dir):
        if name in IGNORED_FILENAMES:
            continue

        if os.path.isfile(os.path.join(locale_dir, name)):
            languages.append(name)

    return sorted(languages)


class DirReport:
    """Resultado de comparar un directorio de locales con el idioma de referencia."""

    def __init__(self) -> None:
        self.missing: Dict[str, Set[str]] = {}
        self.extras: List[str] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []


def check_locale_dir(locale_dir: str, root: str, required_languages: Set[str] = frozenset()) -> DirReport:
    """Compara todos los idiomas de un directorio con el de referencia.

    ``required_languages`` son idiomas que deben existir aunque el directorio no los tenga:
    sin ellos, un fichero de idioma entero ausente pasaba inadvertido, porque la lista de
    idiomas se derivaba de los ficheros presentes. Es justo el caso más probable y más grave:
    añadir una gem nueva traducida solo a «en» y «es».
    """
    relative_dir = os.path.relpath(locale_dir, root)
    reference_path = os.path.join(locale_dir, REFERENCE_LANGUAGE)
    report = DirReport()

    if not os.path.isfile(reference_path):
        report.errors.append(f'{relative_dir}: no existe el idioma de referencia «{REFERENCE_LANGUAGE}»')
        return report

    reference_keys, errors, warnings = read_locale_keys(reference_path)
    report.errors.extend(errors)
    report.warnings.extend(warnings)

    for language in sorted(set(list_languages(locale_dir)) | set(required_languages)):
        if language == REFERENCE_LANGUAGE:
            continue

        language_path = os.path.join(locale_dir, language)

        if not os.path.isfile(language_path):
            report.missing[language] = set(reference_keys)
            report.errors.append(f'{relative_dir}: falta el fichero del idioma «{language}»')
            continue

        language_keys, errors, warnings = read_locale_keys(language_path)
        report.errors.extend(errors)
        report.warnings.extend(warnings)

        absent = reference_keys - language_keys
        if absent:
            report.missing[language] = absent

        surplus = language_keys - reference_keys
        if surplus:
            report.extras.append(f'{relative_dir}/{language}: {len(surplus)} clave(s) que «en» no define: '
                                 + ', '.join(sorted(surplus)[:10]))

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description='Comprueba la paridad de los ficheros de traducción.')
    parser.add_argument('--root', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        help='raíz del repositorio (por defecto: la del propio script)')
    parser.add_argument('--report', action='store_true',
                        help='muestra el informe completo y termina con éxito aunque falten claves')
    parser.add_argument('--languages', default='',
                        help='lista separada por comas de idiomas a exigir (por defecto: todos los presentes)')
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    # Idiomas cuyas claves ausentes hacen fallar la comprobación. Vacío = todos.
    blocking_languages = {lang.strip() for lang in args.languages.split(',') if lang.strip()}
    locale_dirs = find_locale_dirs(root)

    if not locale_dirs:
        print(f'ERROR: no se encontró ningún directorio de locales bajo {root}', file=sys.stderr)
        return 1

    # Un idioma presente en cualquier directorio debe existir en todos: si no, un fichero de
    # idioma entero ausente no se comparaba con nada y pasaba inadvertido. Es el caso más
    # probable al añadir una gem nueva: traducirla solo a «en» y «es».
    required_languages = set(blocking_languages)

    for locale_dir in locale_dirs:
        required_languages.update(list_languages(locale_dir))

    total_missing = 0
    total_errors = 0
    total_warnings = 0
    reported_extras: List[str] = []

    for locale_dir in locale_dirs:
        relative_dir = os.path.relpath(locale_dir, root)
        report = check_locale_dir(locale_dir, root, required_languages)
        reported_extras.extend(report.extras)

        for message in report.errors:
            total_errors += 1
            print(f'ERROR  {message}')

        for message in report.warnings:
            total_warnings += 1
            print(f'AVISO  {message}')

        # Si se acotó la comprobación a unos idiomas, el resto solo informa.
        blocking = {lang: keys for lang, keys in report.missing.items()
                    if not blocking_languages or lang in blocking_languages}

        if not report.missing:
            print(f'OK     {relative_dir}: todos los idiomas cubren las claves de «{REFERENCE_LANGUAGE}»')
            continue

        for language in sorted(report.missing):
            absent = sorted(report.missing[language])

            if language in blocking:
                total_missing += len(absent)
                label = 'FALTAN'
            else:
                label = 'INFO  '

            shown = absent if args.report else absent[:10]
            suffix = '' if len(shown) == len(absent) else f' … (+{len(absent) - len(shown)} más)'
            print(f'{label} {relative_dir}/{language}: {len(absent)} clave(s): ' + ', '.join(shown) + suffix)

    if args.report:
        for extra in reported_extras:
            print(f'EXTRA  {extra}')

    print()
    print(f'Directorios revisados: {len(locale_dirs)}')
    print(f'Claves ausentes (bloqueantes): {total_missing}')
    print(f'Errores de formato: {total_errors}')
    print(f'Avisos: {total_warnings}')

    if args.report:
        # En modo informe nunca se falla: sirve para ver el estado sin bloquear.
        return 0

    if total_missing or total_errors:
        print()
        print('Añade las claves que faltan a los ficheros de locale indicados '
              '(mínimo «en» y «es»; el resto de idiomas existentes también).', file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
