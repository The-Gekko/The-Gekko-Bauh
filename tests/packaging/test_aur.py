"""Comprobaciones de los paquetes del AUR (packaging/aur).

Todo se hace con Python puro: ni makepkg ni red. La idea es cazar en la suite los
despistes que en el AUR solo se ven cuando alguien intenta construir el paquete:

  * un .SRCINFO que se quedó atrás respecto a su PKGBUILD;
  * un pkgver que pacman rechazaría;
  * un pkgver que no corresponde a la versión que declara el código;
  * un package() que instala ficheros que ya no existen en el repositorio.
"""

import os
import re
import shlex
import unittest
from pathlib import Path

import bauh

RAIZ = Path(__file__).resolve().parents[2]
DIR_AUR = RAIZ / 'packaging' / 'aur'

# Nombres de los dos paquetes: el estable y el que compila desde la rama principal.
PAQUETE_ESTABLE = 'gekko-bauh'
PAQUETE_GIT = 'gekko-bauh-git'

# Tamaños de icono que espera package(). Coinciden con pictures/icons/.
TAMANOS_ICONO = (16, 32, 48, 64, 128, 256, 512)

# Caracteres que makepkg prohíbe en pkgver. Es literalmente la comprobación de
# /usr/share/makepkg/lint_pkgbuild/pkgver.sh: «dos puntos, barras, guiones o
# espacios». El signo «+» sí está permitido, y de ahí el esquema «0.10.8+gekko.N».
CARACTERES_PROHIBIDOS_EN_PKGVER = ':/- \t'

MOTIVO_SIN_IDENTIDAD = (
    'el árbol de trabajo todavía no incluye la identidad «gekko-bauh» '
    '(bauh.__app_name__ != "gekko-bauh"), así que no hay con qué contrastar '
    'la versión ni los ficheros que instala el paquete'
)


def identidad_disponible() -> bool:
    """Indica si el árbol ya lleva la identidad propia del proyecto."""
    return getattr(bauh, '__app_name__', 'bauh') == 'gekko-bauh'


def version_a_pkgver(version: str) -> str:
    """Convierte una versión de Python en el pkgver equivalente de pacman.

    Es la conversión documentada en packaging/aur/gekko-bauh/PKGBUILD: el guion
    está prohibido en pkgver, así que se sustituye por «+», que sí es válido y
    además es una «local version» correcta de PEP 440.
    """
    return version.replace('-', '+')


def pkgver_a_etiqueta(pkgver: str) -> str:
    """Convierte un pkgver en la etiqueta git equivalente (la conversión inversa)."""
    return 'v' + pkgver.replace('+', '-')


def _expandir(texto: str, variables: dict) -> str:
    """Expande las variables de un valor de PKGBUILD.

    Solo admite las formas que usan estos PKGBUILD: «$var», «${var}»,
    «${var/a/b}» y «${var#prefijo}». Cualquier otra construcción lanza una
    excepción a propósito: es preferible que el test se rompa de forma ruidosa a
    que compare valores expandidos a medias.
    """
    patron = re.compile(r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)')

    def reemplazo(coincidencia: 're.Match') -> str:
        contenido = coincidencia.group(1)
        if contenido is None:
            return variables.get(coincidencia.group(2), '')

        if '/' in contenido:
            nombre, buscado, sustituto = contenido.split('/', 2)
            return variables.get(nombre, '').replace(buscado, sustituto, 1)

        if '#' in contenido:
            nombre, prefijo = contenido.split('#', 1)
            valor = variables.get(nombre, '')
            return valor[len(prefijo):] if valor.startswith(prefijo) else valor

        if '%' in contenido:
            nombre, sufijo = contenido.split('%', 1)
            valor = variables.get(nombre, '')
            return valor[:-len(sufijo)] if sufijo and valor.endswith(sufijo) else valor

        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', contenido):
            raise ValueError(f'expansión de bash no soportada por el test: ${{{contenido}}}')

        return variables.get(contenido, '')

    return patron.sub(reemplazo, texto)


def _sin_comentario(linea: str) -> str:
    """Recorta el comentario de una línea de bash respetando las comillas.

    Hace falta porque los comentarios de estos PKGBUILD llevan paréntesis y
    porque la fuente del paquete -git termina en «#branch=master» dentro de unas
    comillas dobles: ni un «)» de un comentario debe cerrar un array, ni ese
    «#branch» debe tomarse por un comentario.
    """
    comilla = ''

    for posicion, caracter in enumerate(linea):
        if comilla:
            if caracter == comilla:
                comilla = ''
        elif caracter in '"\'':
            comilla = caracter
        elif caracter == '#':
            return linea[:posicion]

    return linea


def leer_pkgbuild(ruta: Path) -> dict:
    """Devuelve las asignaciones de nivel superior de un PKGBUILD ya expandidas.

    Los escalares se devuelven como cadena y los arrays como lista de cadenas.
    Se deja de leer en la primera función, que es donde acaban las asignaciones
    en estos PKGBUILD: así no se cuelan las variables locales de build()
    o package().
    """
    variables: dict = {}
    lineas = [_sin_comentario(linea) for linea in ruta.read_text(encoding='utf-8').splitlines()]
    indice = 0

    inicio_funcion = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*\(\)\s*\{')
    asignacion = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$')

    while indice < len(lineas):
        linea = lineas[indice]

        if inicio_funcion.match(linea):
            break

        coincidencia = asignacion.match(linea)
        if not coincidencia:
            indice += 1
            continue

        nombre, resto = coincidencia.group(1), coincidencia.group(2)

        if resto.startswith('('):
            cuerpo = resto[1:]
            while ')' not in cuerpo:
                indice += 1
                if indice >= len(lineas):
                    raise ValueError(f'array «{nombre}» sin cerrar en {ruta}')
                cuerpo += '\n' + lineas[indice]
            cuerpo = cuerpo[:cuerpo.rindex(')')]
            valores = [_expandir(pieza, variables) for pieza in shlex.split(cuerpo, comments=True)]
            variables[nombre] = valores
        else:
            piezas = shlex.split(resto, comments=True)
            variables[nombre] = _expandir(piezas[0], variables) if piezas else ''

        indice += 1

    return variables


def leer_srcinfo(ruta: Path) -> dict:
    """Devuelve el contenido de un .SRCINFO como {clave: [valores]}."""
    datos: dict = {}

    for linea in ruta.read_text(encoding='utf-8').splitlines():
        linea = linea.strip()
        if not linea or linea.startswith('#') or '=' not in linea:
            continue
        clave, _, valor = linea.partition('=')
        datos.setdefault(clave.strip(), []).append(valor.strip())

    return datos


def cuerpo_de_funcion(ruta: Path, nombre: str) -> str:
    """Devuelve el cuerpo de una función del PKGBUILD, con las continuaciones unidas."""
    texto = ruta.read_text(encoding='utf-8')
    inicio = texto.index(f'{nombre}() {{')
    profundidad = 0
    fin = inicio

    for posicion in range(inicio, len(texto)):
        if texto[posicion] == '{':
            profundidad += 1
        elif texto[posicion] == '}':
            profundidad -= 1
            if profundidad == 0:
                fin = posicion
                break

    return texto[inicio:fin].replace('\\\n', ' ')


def ficheros_que_instala(ruta: Path) -> list:
    """Rutas del código fuente que copia el package() de un PKGBUILD.

    Se leen de las órdenes «install -Dm644 ORIGEN DESTINO» y se expande el
    tamaño del bucle de iconos.
    """
    cuerpo = cuerpo_de_funcion(ruta, 'package')
    origenes = []

    for orden in re.findall(r'^\s*install -Dm644 .*$', cuerpo, re.MULTILINE):
        piezas = shlex.split(orden)
        origen = piezas[2]

        if '$_size' in origen or '${_size}' in origen:
            for tamano in TAMANOS_ICONO:
                origenes.append(origen.replace('${_size}', str(tamano)).replace('$_size', str(tamano)))
        else:
            origenes.append(origen)

    return origenes


class LecturaDePkgbuildTest(unittest.TestCase):
    """El parser de PKGBUILD del propio test tiene que hacer lo que dice."""

    def test_expande_las_formas_de_bash_que_usan_los_pkgbuild(self):
        variables = {'pkgver': '0.10.8+gekko.1', '_gh_repo': 'The-Gekko-Bauh'}

        self.assertEqual('v0.10.8-gekko.1', _expandir('v${pkgver/+/-}', variables))
        self.assertEqual('0.10.8-gekko.1', _expandir('${_tag#v}', {'_tag': 'v0.10.8-gekko.1'}))
        self.assertEqual('The-Gekko-Bauh-1', _expandir('$_gh_repo-1', variables))

    def test_rechaza_las_expansiones_que_no_entiende(self):
        with self.assertRaises(ValueError):
            _expandir('${var:-por defecto}', {})


class CoherenciaPkgbuildSrcinfoTest(unittest.TestCase):
    """El .SRCINFO se genera con «makepkg --printsrcinfo» y se sube junto al
    PKGBUILD; si uno de los dos se queda atrás, el AUR muestra datos falsos."""

    def _comprobar_par(self, paquete: str):
        directorio = DIR_AUR / paquete
        pkgbuild = leer_pkgbuild(directorio / 'PKGBUILD')
        srcinfo = leer_srcinfo(directorio / '.SRCINFO')

        self.assertEqual([paquete], srcinfo['pkgbase'], f'{paquete}: pkgbase del .SRCINFO')
        self.assertEqual([paquete], srcinfo['pkgname'], f'{paquete}: pkgname del .SRCINFO')
        self.assertEqual(paquete, pkgbuild['pkgname'], f'{paquete}: pkgname del PKGBUILD')

        for clave in ('pkgver', 'pkgrel', 'pkgdesc', 'url'):
            self.assertEqual([pkgbuild[clave]], srcinfo[clave],
                             f'{paquete}: «{clave}» distinto entre PKGBUILD y .SRCINFO')

        for clave in ('arch', 'license', 'depends', 'makedepends', 'optdepends', 'options',
                      'source', 'sha256sums'):
            self.assertEqual(pkgbuild[clave], srcinfo[clave],
                             f'{paquete}: «{clave}» distinto entre PKGBUILD y .SRCINFO')

        for clave in ('provides', 'conflicts'):
            self.assertEqual(pkgbuild.get(clave, []), srcinfo.get(clave, []),
                             f'{paquete}: «{clave}» distinto entre PKGBUILD y .SRCINFO')

    def test_el_paquete_estable_y_su_srcinfo_coinciden(self):
        self._comprobar_par(PAQUETE_ESTABLE)

    def test_el_paquete_git_y_su_srcinfo_coinciden(self):
        self._comprobar_par(PAQUETE_GIT)

    def test_los_dos_paquetes_declaran_las_mismas_dependencias(self):
        estable = leer_pkgbuild(DIR_AUR / PAQUETE_ESTABLE / 'PKGBUILD')
        variante_git = leer_pkgbuild(DIR_AUR / PAQUETE_GIT / 'PKGBUILD')

        self.assertEqual(estable['depends'], variante_git['depends'])
        self.assertEqual(estable['optdepends'], variante_git['optdepends'])
        # La única diferencia esperada en makedepends es «git», que hace falta
        # para descargar la rama.
        self.assertEqual(['git'] + estable['makedepends'], variante_git['makedepends'])


class DependenciasTest(unittest.TestCase):

    def setUp(self):
        self.pkgbuild = leer_pkgbuild(DIR_AUR / PAQUETE_ESTABLE / 'PKGBUILD')

    def test_declara_las_dependencias_de_ejecucion(self):
        # Nombres tal y como se llaman los paquetes en Arch.
        esperadas = {'python', 'python-pyqt5', 'python-requests', 'python-yaml',
                     'python-colorama', 'python-dateutil'}
        self.assertLessEqual(esperadas, set(self.pkgbuild['depends']))

    def test_declara_el_flujo_pep_517_en_makedepends(self):
        esperadas = {'python-build', 'python-installer', 'python-setuptools', 'python-wheel'}
        self.assertEqual(esperadas, set(self.pkgbuild['makedepends']))

    def test_lo_opcional_esta_en_optdepends_y_va_explicado(self):
        opcionales = {entrada.split(':', 1)[0]: entrada.split(':', 1)[1].strip()
                      for entrada in self.pkgbuild['optdepends']}

        for nombre in ('flatpak', 'git', 'base-devel', 'timeshift', 'python-lxml',
                       'python-beautifulsoup4'):
            self.assertIn(nombre, opcionales, f'falta «{nombre}» en optdepends')
            self.assertTrue(opcionales[nombre], f'«{nombre}» está en optdepends sin explicación')

    def test_ninguna_dependencia_opcional_esta_tambien_como_obligatoria(self):
        obligatorias = set(self.pkgbuild['depends'])
        opcionales = {entrada.split(':', 1)[0] for entrada in self.pkgbuild['optdepends']}
        self.assertEqual(set(), obligatorias & opcionales)


class VersionTest(unittest.TestCase):

    def test_los_pkgver_cumplen_las_reglas_de_pacman(self):
        for paquete in (PAQUETE_ESTABLE, PAQUETE_GIT):
            with self.subTest(paquete=paquete):
                pkgver = leer_pkgbuild(DIR_AUR / paquete / 'PKGBUILD')['pkgver']

                self.assertTrue(pkgver, 'pkgver no puede estar vacío')
                for caracter in CARACTERES_PROHIBIDOS_EN_PKGVER:
                    self.assertNotIn(caracter, pkgver,
                                     f'makepkg rechaza «{caracter!r}» en pkgver')
                self.assertTrue(pkgver.isascii(), 'pkgver solo admite caracteres ASCII')

    def test_la_etiqueta_del_paquete_estable_se_deriva_del_pkgver(self):
        """El PKGBUILD reconstruye la etiqueta con ${pkgver/+/-}: aquí se comprueba
        que la fuente que descarga es exactamente la de esa etiqueta."""
        pkgbuild = leer_pkgbuild(DIR_AUR / PAQUETE_ESTABLE / 'PKGBUILD')
        etiqueta = pkgver_a_etiqueta(pkgbuild['pkgver'])

        self.assertEqual(etiqueta, pkgbuild['_tag'])
        self.assertEqual(1, len(pkgbuild['source']))
        self.assertTrue(pkgbuild['source'][0].endswith(f'/{etiqueta}.tar.gz'),
                        f'la fuente no apunta a la etiqueta {etiqueta}: {pkgbuild["source"][0]}')

    @unittest.skipUnless(identidad_disponible(), MOTIVO_SIN_IDENTIDAD)
    def test_el_pkgver_corresponde_a_la_version_del_codigo(self):
        pkgbuild = leer_pkgbuild(DIR_AUR / PAQUETE_ESTABLE / 'PKGBUILD')
        self.assertEqual(version_a_pkgver(bauh.__version__), pkgbuild['pkgver'])

    @unittest.skipUnless(identidad_disponible(), MOTIVO_SIN_IDENTIDAD)
    def test_la_variante_git_parte_de_la_version_del_codigo(self):
        """El pkgver del PKGBUILD -git es un marcador que pkgver() recalcula, pero
        su parte de versión tiene que ser la del código."""
        pkgver = leer_pkgbuild(DIR_AUR / PAQUETE_GIT / 'PKGBUILD')['pkgver']
        self.assertTrue(pkgver.startswith(version_a_pkgver(bauh.__version__) + '.r'),
                        f'{pkgver} no empieza por la versión del código con el sufijo «.r»')


class ConvivenciaConBauhTest(unittest.TestCase):
    """Este proyecto está pensado para convivir con el paquete «bauh» del AUR."""

    def test_ningun_paquete_declara_conflicto_ni_sustitucion_de_bauh(self):
        for paquete in (PAQUETE_ESTABLE, PAQUETE_GIT):
            with self.subTest(paquete=paquete):
                pkgbuild = leer_pkgbuild(DIR_AUR / paquete / 'PKGBUILD')

                for clave in ('conflicts', 'provides', 'replaces'):
                    nombres = [entrada.split('=', 1)[0] for entrada in pkgbuild.get(clave, [])]
                    self.assertNotIn('bauh', nombres,
                                     f'{paquete}: «{clave}» no debe mencionar a «bauh»')

    def test_el_paquete_importable_no_va_a_site_packages(self):
        """El paquete importable se sigue llamando «bauh», así que instalarlo en
        site-packages chocaría fichero a fichero con el paquete «bauh» del AUR.
        Por eso package() lo reubica y escribe sus propios lanzadores."""
        for paquete in (PAQUETE_ESTABLE, PAQUETE_GIT):
            with self.subTest(paquete=paquete):
                cuerpo = cuerpo_de_funcion(DIR_AUR / paquete / 'PKGBUILD', 'package')

                self.assertIn('--destdir="$_stage"', cuerpo,
                              'el wheel debe instalarse primero en una raíz intermedia')
                self.assertIn('/usr/share/', cuerpo)
                self.assertNotIn('--destdir="$pkgdir"', cuerpo,
                                 'instalar directo en $pkgdir dejaría el paquete en site-packages')

    def test_la_variante_git_si_sustituye_al_paquete_estable(self):
        pkgbuild = leer_pkgbuild(DIR_AUR / PAQUETE_GIT / 'PKGBUILD')

        self.assertEqual([f'{PAQUETE_ESTABLE}={pkgbuild["pkgver"]}'], pkgbuild['provides'])
        self.assertEqual([PAQUETE_ESTABLE], pkgbuild['conflicts'])


class FuenteTest(unittest.TestCase):

    def test_la_variante_git_compila_desde_la_rama_principal(self):
        pkgbuild = leer_pkgbuild(DIR_AUR / PAQUETE_GIT / 'PKGBUILD')
        fuente = pkgbuild['source'][0]

        self.assertIn('git+https://', fuente)
        self.assertTrue(fuente.endswith('#branch=master'), f'fuente inesperada: {fuente}')
        self.assertEqual(['SKIP'], pkgbuild['sha256sums'],
                         'en una fuente VCS la suma correcta es SKIP')
        self.assertIn('git', pkgbuild['makedepends'])
        self.assertIn('pkgver()', (DIR_AUR / PAQUETE_GIT / 'PKGBUILD').read_text(encoding='utf-8'),
                      'un paquete -git necesita una función pkgver()')

    def test_el_paquete_estable_documenta_como_rellenar_la_suma(self):
        """Mientras la suma sea el marcador SKIP, el PKGBUILD tiene que decir en
        claro cómo se sustituye; si ya lleva una suma real, tiene que ser un
        SHA-256 bien formado."""
        directorio = DIR_AUR / PAQUETE_ESTABLE
        pkgbuild = leer_pkgbuild(directorio / 'PKGBUILD')
        texto = (directorio / 'PKGBUILD').read_text(encoding='utf-8')

        self.assertEqual(1, len(pkgbuild['sha256sums']))
        suma = pkgbuild['sha256sums'][0]

        if suma == 'SKIP':
            self.assertIn('updpkgsums', texto,
                          'con la suma en SKIP hay que explicar cómo se calcula la real')
        else:
            self.assertRegex(suma, r'^[0-9a-f]{64}$')


class FicherosInstaladosTest(unittest.TestCase):

    def test_package_instala_licencia_lanzadores_e_iconos(self):
        for paquete in (PAQUETE_ESTABLE, PAQUETE_GIT):
            with self.subTest(paquete=paquete):
                instalados = ficheros_que_instala(DIR_AUR / paquete / 'PKGBUILD')

                self.assertIn('LICENSE', instalados,
                              'la licencia zlib es «custom:» y hay que instalarla')
                self.assertIn('bauh/desktop/gekko-bauh.desktop', instalados)
                self.assertIn('bauh/desktop/gekko-bauh-tray.desktop', instalados)

                iconos = [ruta for ruta in instalados if ruta.startswith('pictures/icons/')]
                self.assertEqual(len(TAMANOS_ICONO), len(iconos),
                                 'debe instalarse un icono por cada tamaño disponible')

    @unittest.skipUnless(identidad_disponible(), MOTIVO_SIN_IDENTIDAD)
    def test_todo_lo_que_instala_package_existe_en_el_repositorio(self):
        for paquete in (PAQUETE_ESTABLE, PAQUETE_GIT):
            for relativa in ficheros_que_instala(DIR_AUR / paquete / 'PKGBUILD'):
                with self.subTest(paquete=paquete, fichero=relativa):
                    self.assertTrue((RAIZ / relativa).is_file(),
                                    f'{paquete}: package() instala «{relativa}», que no existe')

    @unittest.skipUnless(identidad_disponible(), MOTIVO_SIN_IDENTIDAD)
    def test_estan_todos_los_iconos_por_tamano(self):
        for tamano in TAMANOS_ICONO:
            with self.subTest(tamano=tamano):
                self.assertTrue((RAIZ / 'pictures' / 'icons' / f'gekko-bauh-{tamano}.png').is_file())


class ArchivosDelPaqueteTest(unittest.TestCase):

    def test_cada_paquete_tiene_pkgbuild_y_srcinfo(self):
        for paquete in (PAQUETE_ESTABLE, PAQUETE_GIT):
            with self.subTest(paquete=paquete):
                self.assertTrue((DIR_AUR / paquete / 'PKGBUILD').is_file())
                self.assertTrue((DIR_AUR / paquete / '.SRCINFO').is_file())

    def test_el_paquete_es_independiente_de_la_arquitectura(self):
        for paquete in (PAQUETE_ESTABLE, PAQUETE_GIT):
            with self.subTest(paquete=paquete):
                pkgbuild = leer_pkgbuild(DIR_AUR / paquete / 'PKGBUILD')
                self.assertEqual(['any'], pkgbuild['arch'])
                self.assertEqual(['custom:zlib'], pkgbuild['license'])

    def test_los_pkgbuild_son_bash_valido(self):
        """Sin makepkg no se puede construir, pero sí comprobar la sintaxis."""
        import subprocess

        for paquete in (PAQUETE_ESTABLE, PAQUETE_GIT):
            with self.subTest(paquete=paquete):
                ruta = DIR_AUR / paquete / 'PKGBUILD'
                proceso = subprocess.run(['bash', '-n', str(ruta)],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(0, proceso.returncode,
                                 f'{paquete}: {proceso.stderr.decode("utf-8", "replace")}')

    def test_la_documentacion_de_distribucion_existe(self):
        documento = RAIZ / 'docs' / 'DISTRIBUCION.md'
        self.assertTrue(documento.is_file(), 'falta docs/DISTRIBUCION.md')

        texto = documento.read_text(encoding='utf-8')
        for referencia in ('updpkgsums', 'SHA256SUMS', '.SRCINFO', 'sha256sum'):
            self.assertIn(referencia, texto,
                          f'docs/DISTRIBUCION.md debería explicar «{referencia}»')


class WorkflowDeReleaseTest(unittest.TestCase):

    RUTA = Path('.github') / 'workflows' / 'release.yml'

    def setUp(self):
        ruta = RAIZ / self.RUTA
        if not ruta.is_file():
            self.skipTest(f'no existe {self.RUTA}')
        self.texto = ruta.read_text(encoding='utf-8')

    def test_se_dispara_con_las_etiquetas_de_version(self):
        self.assertIn("- 'v*'", self.texto)

    def test_construye_valida_y_publica_las_sumas(self):
        for orden in ('python -m build', 'twine check', 'sha256sum', 'SHA256SUMS'):
            self.assertIn(orden, self.texto, f'el workflow debería ejecutar «{orden}»')

    def test_la_publicacion_en_pypi_esta_desactivada(self):
        """El frente deja el paso preparado pero comentado: la decisión es del dueño."""
        activo = [linea for linea in self.texto.splitlines()
                  if 'pypi-publish' in linea and not linea.lstrip().startswith('#')]
        self.assertEqual([], activo, 'el paso de PyPI debe seguir comentado')
        self.assertIn('pypi-publish', self.texto, 'el paso de PyPI debe quedar documentado')

    def test_comprueba_que_la_etiqueta_corresponde_al_codigo(self):
        self.assertIn('__version__', self.texto)
        self.assertIn('packaging/aur/gekko-bauh/PKGBUILD', self.texto,
                      'el workflow debería avisar si el PKGBUILD se quedó en la versión anterior')

    def test_genera_y_publica_el_artefacto_de_gekkoapp(self):
        """GekkoApp instala gekko-bauh desde el .tar.zst y el manifiesto que
        genera tools/build-gekkoapp-release.sh: la release tiene que llevarlos."""
        self.assertIn('tools/build-gekkoapp-release.sh', self.texto)
        self.assertIn('bauh-fork-the-gekko-x86_64-unknown-linux-gnu.manifest.json', self.texto)
        self.assertIn('*.tar.zst *.manifest.json', self.texto,
                      'SHA256SUMS debe cubrir también los ficheros de GekkoApp')
        self.assertTrue((RAIZ / 'tools' / 'build-gekkoapp-release.sh').is_file())

    def test_las_sumas_cubren_los_nombres_renombrados_por_github(self):
        # GitHub sustituye el «+» de los assets por «.»: SHA256SUMS lleva las dos grafías.
        self.assertIn('${nombre//+/.}', self.texto)
        self.assertIn('--ignore-missing', self.texto)


if __name__ == '__main__':
    os.chdir(RAIZ)
    unittest.main()
