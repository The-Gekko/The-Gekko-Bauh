<h1 align="center">
  <img src="https://raw.githubusercontent.com/vinifmor/bauh-files/master/pictures/logo.png" width="128"><br/>
  bauh (Arch Edition)
</h1>

<h4 align="center">La Interfaz Gráfica Definitiva para Administrar Aplicaciones en Arch Linux</h4>

<p align="center">
  <a href="https://github.com/vinifmor/bauh/releases"><img src="https://img.shields.io/github/release/vinifmor/bauh.svg?label=Release" alt="Lanzamiento"></a>
  <a href="https://aur.archlinux.org/packages/bauh"><img src="https://img.shields.io/aur/version/bauh?label=AUR" alt="AUR"></a>
  <a href="https://github.com/vinifmor/bauh/blob/master/LICENSE"><img src="https://img.shields.io/github/license/vinifmor/bauh?label=License" alt="Licencia"></a>
</p>

---

> **⚠️ REQUISITO IMPORTANTE: Chaotic AUR**  
> Este fork está diseñado **exclusivamente para Arch Linux con el repositorio Chaotic AUR habilitado**. Si no tienes Chaotic AUR configurado en tu `/etc/pacman.conf`, este fork no funcionará como se espera.
>
> **🏆 Fork Modernizado por thegekko**  
> Este repositorio es un fork altamente optimizado y rediseñado del proyecto original `bauh` creado por Vinicius Moreira. Está **diseñado y optimizado para Arch Linux**, integrando mejoras masivas para AUR y los repositorios de **Chaotic AUR**. Incluye un rendimiento superior, arquitectura moderna, el nuevo tema Aurora y compatibilidad total con **KDE Plasma**, **GNOME**, y gestores de ventanas Wayland como **Hyprland** y **Niri**. Lee el archivo [CREDITS.md](CREDITS.md) para más información.

---

**bauh** (pronunciado _baoo_), es una interfaz gráfica para administrar tus paquetes en sistemas Arch Linux. Requiere y aprovecha al máximo los repositorios oficiales de Arch (Pacman), **AUR (Arch User Repository)**, y **Chaotic AUR**.

> [!TIP]
> **🚀 Actualización v0.10.x (La Actualización Aurora y de Rendimiento)**  
> ¡Bauh ha sido completamente renovado! Cuenta con un nuevo **tema Aurora**, optimizaciones de rendimiento extremas con carga perezosa (lazy-loading), reducción drástica del consumo de CPU y soporte nativo para compilación veloz.

## ✨ Características Clave

- **Optimizado para Arch Linux**: Maneja pacman, AUR y repositorios de terceros como Chaotic AUR en un solo lugar.
- **Soporte Nativo para Solus OS (eopkg)**: ¡Nuevo! Bauh ahora detecta automáticamente si estás en Solus OS y permite gestionar los paquetes de `eopkg` nativamente.
- **Clonación de GitHub Segura**: Nuevo módulo para buscar, clonar y construir repositorios desde GitHub de forma local. ¡Viene con protección anti-scripts peligrosos!
- **Soporte Wayland Total**: Funciona impecablemente en **GNOME**, **KDE Plasma**, **Hyprland** y **Niri** (gracias a PyQt5 nativo).
- **Velocidad Increíble**: Arquitectura asíncrona ultra optimizada con interfaz sin congelamientos y renderizado silencioso de tablas.
- **Compilación Inteligente AUR**: Utiliza automáticamente todos los núcleos de tu CPU (`-j$(nproc)`) y detecta dependencias rotas o reconstrucciones necesarias.
- **Respaldo del Sistema**: Se integra con [Timeshift](https://github.com/teejee2008/timeshift) para ofrecer un proceso de respaldo simple y seguro antes de realizar un `pacman -Syu`.

---

## 📥 Instalación

### La Vía Fácil (Instalador Automatizado)

La forma más rápida y segura de instalar `bauh` en Arch Linux. Aísla de forma segura las dependencias usando `pipx` y crea un acceso directo en tu escritorio.

```bash
git clone https://github.com/The-Gekko/Bauh-Fork-The-Gekko.git
cd Bauh-Fork-The-Gekko
./install.sh
```

El instalador requiere `pipx` y Python entre 3.8 y 3.12. No instala paquetes
del sistema automaticamente: en sistemas Arch puedes instalar pipx con
`sudo pacman -S python-pipx`. Usa `./install.sh --yes` para continuar sin
confirmaciones, o define `PYTHON_BIN` para elegir el interprete usado por pipx.

---

## 📖 Características Detalladas (Arch/AUR)

- Resuelve conflictos y dependencias de manera automática, manejando opciones múltiples (providers) inteligentemente.
- **Soporte Completo para Chaotic AUR**: Bauh detecta y prioriza los paquetes binarios precompilados si tienes habilitado el repositorio Chaotic AUR en tu `/etc/pacman.conf`, ahorrándote horas de compilación (ej. con kernels o navegadores web pesados).
- Actualización rápida de todo el sistema y de AUR con un solo clic.
- Integración con `rebuild-detector` para saber si un paquete necesita ser compilado de nuevo tras la actualización de una librería compartida en el sistema.

---

### Instalación Aislada (Entorno Virtual)

Si prefieres realizar una instalación aislada manual (sin usar el script):

```bash
python3 -m venv bauh_env
bauh_env/bin/pip install bauh
bauh_env/bin/bauh
```

---

## 📄 Licencia

Este software se distribuye bajo la licencia **zlib/libpng**. Por favor, revisa el archivo [LICENSE](LICENSE) y [CREDITS.md](CREDITS.md) para más detalles acerca de los términos de autoría y distribución.
