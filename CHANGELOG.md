# Registro de cambios

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [0.2.0] - 2026-11-12

### Añadido
- Asistente de calibración en tres pasos (centro, izquierda y derecha).
- Reglas udev para usar la aplicación sin `sudo`.
- Instalación con `make install` (lanzador `.desktop`, icono y página de manual).
- Opciones de línea de comandos: `--config`, `--no-iniciar`, `--version`.
- Pruebas automáticas y flujo de integración continua.

### Cambiado
- El código se organiza como paquete de Python (`src/ds4_volante`).
- La configuración se guarda en `$XDG_CONFIG_HOME/ds4-volante/config.json`;
  la de la versión 0.1 se lee automáticamente.

### Eliminado
- Los lanzadores `ds4-volante` y `askpass-yad`, que usaban `sudo` y rutas fijas.

## [0.1.0]

- Primera versión.
