# ds4-volante

Usa el acelerómetro de un control DualShock 4 (PS4) como volante en Linux: la
inclinación del control se publica como el eje `ABS_WHEEL` de un dispositivo
virtual llamado **DS4 Volante**. Los demás botones y ejes del control se
reenvían tal cual, y los gatillos digitales L2/R2 se omiten para que solo
queden los analógicos.

## Requisitos

- Linux con systemd/udev y el módulo `uinput`.
- Python 3.8 o superior, con `evdev` y `tkinter`.

| Distribución  | Paquetes                         |
|---------------|----------------------------------|
| Debian/Ubuntu | `python3-evdev python3-tk`       |
| Fedora        | `python3-evdev python3-tkinter`  |
| Arch Linux    | `python-evdev tk`                |

## Instalación

```bash
git clone https://github.com/IvanAraya/ds4-volante.git
```

```bash
cd ds4-volante
```

```bash
sudo make install
```

Después, **desconecta y vuelve a conectar el control**. La aplicación aparece
en el menú como **DS4 Volante** y también puede ejecutarse con `ds4-volante`.

`make install` copia:

| Archivo                                   | Destino                                   |
|-------------------------------------------|-------------------------------------------|
| Programa                                  | `/usr/local/bin`, `/usr/local/lib/ds4-volante` |
| Lanzador e icono                          | `/usr/local/share/applications`, `/usr/local/share/icons` |
| Página de manual (`man ds4-volante`)      | `/usr/local/share/man/man1`               |
| Reglas udev                               | `/etc/udev/rules.d/70-ds4-volante.rules`  |
| Carga de `uinput` al arrancar             | `/etc/modules-load.d/ds4-volante.conf`    |

Para desinstalar: `sudo make uninstall`.

### Actualizar desde la versión 0.1

La versión 0.1 se instalaba a mano en `~/Apps/ds4-volante` y usaba `sudo`.
Para quitarla, ejecuta como tu usuario (sin `sudo`) desde la carpeta del
proyecto:

```bash
./scripts/desinstalar-v0.1.sh
```

El script muestra lo que va a eliminar y pide confirmación. Solo borra los
archivos de esa versión (`ds4-volante.py`, `ds4-volante`, `askpass-yad`) y los
lanzadores, enlaces o scripts de tu usuario que apunten a esa carpeta. Copia la
calibración a la ubicación nueva y conserva la original. Si la carpeta antigua
es un clon de git, no borra nada dentro.

Opciones: `--simular` (muestra los cambios sin hacerlos), `--dir RUTA` (si la
instalaste en otra carpeta) y `--si` (no pide confirmación).

Los empaquetadores pueden usar `PREFIX`, `DESTDIR`, `UDEVRULESDIR` y
`MODULESLOADDIR`, por ejemplo:
`make install PREFIX=/usr DESTDIR=pkg UDEVRULESDIR=/usr/lib/udev/rules.d`.

### Permisos (sin `sudo`)

La aplicación se ejecuta como usuario normal. Las reglas udev dan acceso a
`/dev/uinput` y a los dispositivos del DualShock 4 al usuario con la sesión
activa (etiqueta `uaccess`). No es necesario ejecutarla como root.

## Uso

```bash
ds4-volante
```

Opciones: `--config RUTA` (otro archivo de configuración), `--no-iniciar`
(abre la ventana sin conectar el control), `--version` y `--help`.

En la ventana puedes ajustar el ángulo máximo, la zona muerta, el suavizado y
la inversión del giro.

### Calibración

1. Con el volante **activo**, pulsa **Calibrar**.
2. **Paso 1:** sostén el control en la posición neutral (recto).
3. **Paso 2:** gíralo a la izquierda hasta el tope que quieres usar.
4. **Paso 3:** gíralo a la derecha hasta el tope que quieres usar.

En cada paso, pulsa **Capturar** o la **Cruz (X)** del control y mantenlo
quieto mientras se mide (menos de un segundo). La pulsación de la Cruz también
llega al juego, así que conviene calibrar fuera de la partida.

Al terminar se calculan y guardan automáticamente:

- **Centro:** la posición neutral pasa a ser el valor 0 del eje.
- **Ángulo máximo:** el promedio del giro a cada lado (redondeado a 5°).
- **Dirección:** se activa o desactiva «Invertir giro» para que la izquierda
  produzca valores negativos.

**Restablecer** vuelve el centro a 0°.

### Configuración

Se guarda en `$XDG_CONFIG_HOME/ds4-volante/config.json`
(normalmente `~/.config/ds4-volante/config.json`). Si existe el archivo de la
versión 0.1 (`~/.config/ds4-volante.json`), se lee automáticamente.

## Desarrollo

```
├── src/ds4_volante/
│   ├── __main__.py     # línea de comandos
│   ├── calculo.py      # ángulo, eje y calibración (sin hardware)
│   ├── config.py       # configuración XDG
│   ├── interfaz.py     # ventana Tkinter
│   └── volante.py      # lectura evdev y dispositivo uinput
├── scripts/            # desinstalador de la versión 0.1
├── data/               # reglas udev, lanzador .desktop, icono, modules-load
├── docs/ds4-volante.1  # página de manual
├── tests/              # pruebas con pytest
├── Makefile
└── pyproject.toml
```

Ejecutar sin instalar (requiere las reglas udev para acceder al control):

```bash
make run
```

Ejecutar las pruebas:

```bash
make test
```

También puede instalarse como paquete de Python, por ejemplo con
`pipx install --system-site-packages .` (para usar el `tkinter` del sistema);
en ese caso las reglas udev se instalan aparte copiando
`data/70-ds4-volante.rules` a `/etc/udev/rules.d/`.
