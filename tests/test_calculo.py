import math

import pytest

from ds4_volante import calculo
from ds4_volante.config import VALORES_INICIALES


def acc(grados, magnitud=8000):
    r = math.radians(grados)
    return (magnitud * math.sin(r), magnitud * math.cos(r))


@pytest.mark.parametrize("entrada, esperado", [
    (0, 0), (179, 179), (180, -180), (-180, -180), (190, -170), (-190, 170), (720, 0),
])
def test_normalizar(entrada, esperado):
    assert calculo.normalizar(entrada) == pytest.approx(esperado)


def test_angulo_promedio_cruza_180_sin_errores():
    # Promediar 170° y -170° debe dar ~180°, no 0°.
    ang = calculo.angulo_promedio([acc(170), acc(-170)])
    assert abs(calculo.normalizar(ang)) == pytest.approx(180)


def test_angulo_promedio_sin_muestras():
    with pytest.raises(ValueError):
        calculo.angulo_promedio([])


def test_angulo_corregido_aplica_centro_inversion_y_zona_muerta():
    cfg = dict(VALORES_INICIALES, centro=10.0, invertir=True, zona_muerta=2.0)
    assert calculo.angulo_corregido(*acc(40), cfg) == pytest.approx(-30)
    assert calculo.angulo_corregido(*acc(11), cfg) == 0.0
    cfg["invertir"] = False
    assert calculo.angulo_corregido(*acc(40), cfg) == pytest.approx(30)


def test_valor_eje_limita_al_rango():
    assert calculo.valor_eje(0, 90) == 0
    assert calculo.valor_eje(45, 90) == calculo.EJE_MAX // 2
    assert calculo.valor_eje(200, 90) == calculo.EJE_MAX
    assert calculo.valor_eje(-200, 90) == -calculo.EJE_MAX


def test_suavizar():
    assert calculo.suavizar(10, 20, 0) == 20
    assert calculo.suavizar(10, 20, 0.5) == 15


def test_calcular_calibracion():
    r = calculo.calcular_calibracion(8.0, 78.0, -52.0)
    assert r == {"centro": 8.0, "angulo_max": 65.0, "invertir": True}


def test_calcular_calibracion_sin_inversion():
    r = calculo.calcular_calibracion(0.0, -40.0, 40.0)
    assert r["invertir"] is False
    assert r["angulo_max"] == 40.0


def test_calcular_calibracion_alrededor_de_180():
    # Control casi boca abajo: el giro cruza ±180°.
    r = calculo.calcular_calibracion(175.0, -145.0, 135.0)
    assert r["angulo_max"] == 40.0
    assert r["invertir"] is True


@pytest.mark.parametrize("izq, der", [(2.0, -40.0), (30.0, 40.0), (-30.0, -40.0)])
def test_calcular_calibracion_invalida(izq, der):
    with pytest.raises(calculo.CalibracionInvalida):
        calculo.calcular_calibracion(0.0, izq, der)
