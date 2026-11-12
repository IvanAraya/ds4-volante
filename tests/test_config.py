import json

import pytest

from ds4_volante import config


@pytest.fixture(autouse=True)
def xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path


def test_ruta_sigue_xdg(xdg):
    assert config.ruta_config() == xdg / "ds4-volante" / "config.json"


def test_xdg_relativo_se_ignora(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", "relativo")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config.ruta_config() == tmp_path / ".config" / "ds4-volante" / "config.json"


def test_valores_iniciales_sin_archivo():
    assert config.cargar_config() == config.VALORES_INICIALES


def test_guardar_y_cargar():
    cfg = dict(config.VALORES_INICIALES, centro=12.5)
    assert config.guardar_config(cfg)
    assert config.cargar_config()["centro"] == 12.5
    assert not list(config.ruta_config().parent.glob("*.tmp"))


def test_migra_configuracion_antigua(xdg):
    (xdg / "ds4-volante.json").write_text(json.dumps({"angulo_max": 45}))
    assert config.cargar_config()["angulo_max"] == 45


def test_ignora_claves_desconocidas_y_json_invalido(xdg):
    ruta = config.ruta_config()
    ruta.parent.mkdir(parents=True)
    ruta.write_text(json.dumps({"suavizado": 0.1, "otra": 1}))
    cfg = config.cargar_config()
    assert cfg["suavizado"] == 0.1 and "otra" not in cfg
    ruta.write_text("{roto")
    assert config.cargar_config() == config.VALORES_INICIALES
