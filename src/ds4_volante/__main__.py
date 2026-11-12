"""Punto de entrada: ``ds4-volante`` o ``python3 -m ds4_volante``."""
import argparse
import os
import sys

from . import __version__
from .config import cargar_config, ruta_config


def analizar_argumentos(argv=None):
    parser = argparse.ArgumentParser(
        prog="ds4-volante",
        description="Usa la inclinación de un DualShock 4 como eje de dirección "
                    "(ABS_WHEEL) de un dispositivo virtual.",
    )
    parser.add_argument("-c", "--config", metavar="RUTA",
                        help=f"archivo de configuración (por defecto: {ruta_config()})")
    parser.add_argument("--no-iniciar", action="store_true",
                        help="abre la ventana sin conectar el control automáticamente")
    parser.add_argument("--diagnostico", action="store_true",
                        help="muestra el estado de permisos y del control, y termina")
    parser.add_argument("-V", "--version", action="version",
                        version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv=None):
    args = analizar_argumentos(argv)
    if args.diagnostico:
        from .diagnostico import informe
        print(informe())
        return 0
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print("ds4-volante: aviso: no es necesario ejecutarlo como root; "
              "instala las reglas udev (ver README).", file=sys.stderr)

    try:
        from .volante import Volante
    except ImportError as exc:
        sys.exit(f"ds4-volante: falta una dependencia: {exc.name} "
                 "(instala python3-evdev).")
    try:
        from .interfaz import ejecutar
    except ImportError as exc:
        sys.exit(f"ds4-volante: falta una dependencia: {exc.name} "
                 "(instala python3-tk).")

    cfg = cargar_config(args.config)
    try:
        ejecutar(cfg, Volante(cfg), args.config, iniciar=not args.no_iniciar)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # p. ej., sin servidor gráfico
        if type(exc).__name__ == "TclError":
            sys.exit(f"ds4-volante: no se pudo abrir la ventana: {exc}")
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
