# ds4-volante

Usa el acelerómetro de un control DualShock 4 (PS4) como volante: la
inclinación del control se publica como el eje `ABS_WHEEL` de un dispositivo
virtual llamado **DS4 Volante**. Los demás botones y ejes del control se
reenvían tal cual.

## Requisitos

- Linux con el módulo `uinput`.
- Python 3 con `python-evdev` y `tkinter`.
- Permisos de lectura sobre `/dev/input/*` y de escritura sobre `/dev/uinput`
  (el lanzador `ds4-volante` usa `sudo`).

## Uso

```bash
./ds4-volante
```

En la ventana puedes ajustar el ángulo máximo, la zona muerta, el suavizado y
la inversión del giro.

## Calibración

1. Con el volante **activo**, pulsa **Calibrar**.
2. **Paso 1:** sostén el control en la posición neutral (recto).
3. **Paso 2:** gíralo a la izquierda hasta el tope que quieres usar.
4. **Paso 3:** gíralo a la derecha hasta el tope que quieres usar.

En cada paso, pulsa **Capturar** o la **Cruz (X)** del control y mantenlo
quieto mientras se mide (menos de un segundo).

Al terminar se calculan y guardan automáticamente:

- **Centro:** la posición neutral pasa a ser el valor 0 del eje.
- **Ángulo máximo:** el promedio del giro a cada lado (redondeado a 5°).
- **Dirección:** se activa o desactiva «Invertir giro» para que la izquierda
  produzca valores negativos.

**Restablecer** vuelve el centro a 0°. La configuración se guarda en
`~/.config/ds4-volante.json`.
