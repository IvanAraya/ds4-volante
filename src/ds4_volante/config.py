"""Carga y guardado de la configuración según la especificación XDG."""
import json
import os
from pathlib import Path

NOMBRE_APP = "ds4-volante"

VALORES_INICIALES = {
    "invertir": True,
    "angulo_max": 90.0,
    "zona_muerta": 0.0,
    "suavizado": 0.4,
    "centro": 0.0,  # ángulo crudo (grados) que corresponde a la posición neutral
}


def carpeta_config():
    """Devuelve $XDG_CONFIG_HOME (o ~/.config si no está definido)."""
    base = os.environ.get("XDG_CONFIG_HOME")
    if not base or not os.path.isabs(base):
        base = os.path.join(os.path.expanduser("~"), ".config")
    return Path(base)


def ruta_config():
    return carpeta_config() / NOMBRE_APP / "config.json"


def ruta_config_antigua():
    """Ubicación usada por la versión 0.1 (se migra automáticamente)."""
    return carpeta_config() / f"{NOMBRE_APP}.json"


def cargar_config(ruta=None):
    """Lee la configuración; las claves ausentes toman su valor inicial."""
    cfg = dict(VALORES_INICIALES)
    candidatas = [ruta] if ruta else [ruta_config(), ruta_config_antigua()]
    for candidata in candidatas:
        try:
            with open(candidata, encoding="utf-8") as f:
                datos = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(datos, dict):
            cfg.update({k: v for k, v in datos.items() if k in VALORES_INICIALES})
            break
    return cfg


def guardar_config(cfg, ruta=None):
    """Escribe la configuración de forma atómica. Devuelve True si tuvo éxito."""
    ruta = Path(ruta) if ruta else ruta_config()
    temporal = ruta.with_name(ruta.name + ".tmp")
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
            f.write("\n")
        os.replace(temporal, ruta)
    except OSError:
        return False
    return True
