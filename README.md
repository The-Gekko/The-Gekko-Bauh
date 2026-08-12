<div align="center">

# 🦎 bauh (Gekko Edition)

### La Interfaz Gráfica Definitiva para Administrar Aplicaciones en Arch Linux

<p align="center">
  <a href="https://github.com/The-Gekko/Bauh-Fork-The-Gekko/releases"><img src="https://img.shields.io/github/release/The-Gekko/Bauh-Fork-The-Gekko.svg?label=Release" alt="Lanzamiento"></a>
  <a href="https://aur.archlinux.org/packages/bauh"><img src="https://img.shields.io/aur/version/bauh?label=AUR" alt="AUR"></a>
  <a href="https://github.com/The-Gekko/Bauh-Fork-The-Gekko/blob/master/LICENSE"><img src="https://img.shields.io/github/license/The-Gekko/Bauh-Fork-The-Gekko?label=Licencia" alt="Licencia"></a>
</p>

<img src="pictures/gekko-bauh.png" width="320" alt="Gekko Bauh" style="border-radius: 24px;"/>

</div>

---

> **⚠️ REQUISITO IMPORTANTE: Chaotic AUR**
>
> Este fork está diseñado **exclusivamente para Arch Linux (y sus derivados como Garuda) con el repositorio Chaotic AUR habilitado**. Si no tienes Chaotic AUR configurado en tu `/etc/pacman.conf`, este fork no funcionará como se espera.

> **🏆 Fork Modernizado por thegekko**
>
> Este repositorio es un fork altamente optimizado y rediseñado del proyecto original `bauh` creado por **Vinicius Moreira**. Está **diseñado y optimizado para Arch Linux**, integrando mejoras masivas para AUR y los repositorios de **Chaotic AUR**. Incluye rendimiento superior, arquitectura moderna, el nuevo tema **Aurora** y compatibilidad total con **KDE Plasma**, **GNOME** y gestores de ventanas Wayland como **Hyprland** y **Niri**. Lee el archivo [CREDITS.md](CREDITS.md) para más información.

---

**bauh** (pronunciado _baoo_) es una interfaz gráfica para administrar tus paquetes en sistemas Arch Linux. Requiere y aprovecha al máximo los repositorios oficiales de Arch (Pacman), **AUR (Arch User Repository)** y **Chaotic AUR**.

> [!TIP]
> **🚀 Actualización v0.10.8 (Experiencia Gekko Bauh & Autenticación Modal)**
>
> ¡Bauh ha sido mejorado con el nuevo arte de **Gekko Bauh** y una interfaz de autenticación modal totalmente renovada! La ventana de contraseña ahora se mantiene al frente en todos los compositores de ventanas (`WindowStaysOnTopHint`), cuenta con enmascaramiento seguro, auto-foco y validación instantánea con `Enter` para un ingreso limpio y directo.

## ✨ Características Clave

- **Optimizado para Arch Linux**: Maneja pacman, AUR y repositorios de terceros como Chaotic AUR en un solo lugar.
- **Autenticación Modal Limpia y Directa**: Diálogo de contraseña de `root`/`sudo` emergente siempre visible al frente, con campo enmascarado y validación rápida mediante la tecla `Enter`.
- **Soporte Nativo para Solus OS (eopkg)**: ¡Nuevo! Bauh ahora detecta automáticamente si estás en Solus OS y permite gestionar los paquetes de `eopkg` nativamente.
- **Clonación de GitHub Segura**: Nuevo módulo para buscar, clonar y construir repositorios desde GitHub de forma local. ¡Viene con protección anti-scripts peligrosos!
- **Soporte Wayland Total**: Funciona impecablemente en **GNOME**, **KDE Plasma**, **Hyprland** y **Niri** (gracias a PyQt5 nativo).
- **Velocidad Increíble**: Arquitectura asíncrona ultra optimizada con interfaz sin congelamientos y renderizado silencioso de tablas.
- **Compilación Inteligente AUR**: Utiliza automáticamente todos los núcleos de tu CPU (`-j$(nproc)`) y detecta dependencias rotas o reconstrucciones necesarias.
- **Respaldo del Sistema**: Se integra con [Timeshift](https://github.com/teejee2008/timeshift) para ofrecer un proceso de respaldo simple y seguro antes de realizar un `pacman -Syu`.

## 📥 Instalación

### La Vía Oficial (Release Firmado + pipx)

Cada versión publicada en [GitHub Releases](https://github.com/The-Gekko/Bauh-Fork-The-Gekko/releases)
incluye el archivo fuente (`bauh-fork-the-gekko-<versión>.tar.zst`) y un
**manifiesto de verificación** (`bauh-fork-the-gekko-<target>.manifest.json`)
con el SHA-256 de cada archivo. La instalación aísla las dependencias en un
entorno virtual de **pipx** y crea el acceso directo del escritorio.

> [!IMPORTANT]
> Requisito: `python-pipx` (`sudo pacman -S python-pipx`). El paquete requiere
> Python 3.8 o superior.

**Desde GekkoApp (recomendado):** la opción *Tienda Bauh* de [GekkoApp](https://github.com/The-Gekko/GekkoApp)
descarga el release más reciente, verifica el manifiesto SHA-256 y ejecuta
`pipx install --force` automáticamente. Nunca clona el repositorio ni ejecuta
scripts sin verificar.

**Manual con pipx:**

```bash
# Descarga el último release y verifica su SHA-256 contra el manifiesto
pipx install --force <directorio-extraído-del-archivo-fuente>
```

### La Vía Clásica (Instalador Automatizado)

Alternativa para instalaciones locales desde el checkout:

```bash
git clone https://github.com/The-Gekko/Bauh-Fork-The-Gekko.git
cd Bauh-Fork-The-Gekko
./install.sh
```

El instalador requiere `pipx` y Python entre 3.8 y 3.12. No instala paquetes
del sistema automáticamente: en sistemas Arch puedes instalar pipx con
`sudo pacman -S python-pipx`. Usa `./install.sh --yes` para continuar sin
confirmaciones, o define `PYTHON_BIN` para elegir el intérprete usado por pipx.

## 📖 Características Detalladas (Arch/AUR)

- Resuelve conflictos y dependencias de manera automática, manejando opciones múltiples (providers) inteligentemente.
- **Soporte Completo para Chaotic AUR**: Bauh detecta y prioriza los paquetes binarios precompilados si tienes habilitado el repositorio Chaotic AUR en tu `/etc/pacman.conf`, ahorrándote horas de compilación (ej. con kernels o navegadores web pesados).
- Actualización rápida de todo el sistema y de AUR con un solo clic.
- Integración con `rebuild-detector` para saber si un paquete necesita ser compilado de nuevo tras la actualización de una librería compartida en el sistema.

### Instalación Aislada (Entorno Virtual)

Si prefieres realizar una instalación aislada manual (sin usar el script):

```bash
python3 -m venv bauh_env
bauh_env/bin/pip install bauh
bauh_env/bin/bauh
```

## 🙏 Créditos

- **Proyecto original**: [bauh](https://github.com/vinifmor/bauh) creado por **Vinicius Moreira** ([@vinifmor](https://github.com/vinifmor)) y los colaboradores del proyecto original. ¡Gracias por esta excelente base!
- **Fork modernizado**: [The-Gekko](https://github.com/The-Gekko), con optimizaciones, tema Aurora y soporte ampliado de distribuciones.
- **Arte Gekko Bauh**: La imagen de presentación (`pictures/gekko-bauh.png`) fue **creada con IA**.

## 📄 Licencia

Este software se distribuye bajo la licencia **zlib/libpng**. Por favor, revisa el archivo [LICENSE](LICENSE) y [CREDITS.md](CREDITS.md) para más detalles acerca de los términos de autoría y distribución.
