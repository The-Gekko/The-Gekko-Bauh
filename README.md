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

### La Vía Rápida (curl, recomendada)

Instala la versión actual de **master** con un solo comando. No necesitas
clonar el repositorio ni guardar ningún script en tu equipo:

```bash
curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash
```

El instalador descarga el código fuente, lo instala aislado en un entorno de
**pipx**, crea el icono y el acceso directo del escritorio, y refresca las
cachés del sistema.

- **Actualizar**: vuelve a ejecutar el mismo comando. Si ya tienes la versión
  actual instalada, **omite la reconstrucción** del entorno para que sea rápido.
- **Forzar reinstalación** (p. ej. si cambió el código sin subir la versión):

  ```bash
  curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- --force
  ```

- **Sin confirmaciones** (scripts/automatización): añade `--yes`:
  `curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- --yes`

> [!IMPORTANT]
> Requiere **pipx** y Python entre **3.8 y 3.14**. Instala pipx según tu
> distribución (el instalador detecta la tuya y puede instalarlo por ti):
>
> - **Arch / Garuda**: `sudo pacman -S python-pipx`
> - **Solus**: `sudo eopkg install -y pipx`

### Desde GekkoApp

La opción *Tienda Bauh* de [GekkoApp](https://github.com/The-Gekko/GekkoApp)
instala bauh automáticamente. Nunca clona el repositorio ni ejecuta scripts sin
verificar.

### Instalación Manual con pipx (avanzado)

```bash
# Aislado en un entorno virtual propio
python3 -m venv bauh_env
bauh_env/bin/pip install bauh
bauh_env/bin/bauh
```

### Para Contribuidores (desde el checkout)

```bash
git clone https://github.com/The-Gekko/Bauh-Fork-The-Gekko.git
cd Bauh-Fork-The-Gekko
./install.sh          # instala desde el checkout local (usa ./install.sh --yes para automatizar)
```

## 🗑️ Desinstalación

Igual de simple que la instalación, también por curl:

```bash
curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- uninstall
```

Elimina la aplicación (entorno pipx, icono y acceso directo del escritorio) y
refresca las cachés del sistema.

Para borrar **también** la configuración de usuario (no se toca por defecto):

```bash
curl -fsSL https://raw.githubusercontent.com/The-Gekko/Bauh-Fork-The-Gekko/master/install.sh | bash -s -- uninstall --purge
```

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
