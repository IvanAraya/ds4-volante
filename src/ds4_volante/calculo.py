"""Cálculos puros (sin hardware): ángulo, eje y calibración."""
import math

EJE_MAX = 32767


def normalizar(ang):
    """Lleva un ángulo en grados al intervalo [-180, 180)."""
    return (ang + 180.0) % 360.0 - 180.0


def angulo_crudo(lado, vertical):
    """Inclinación lateral en grados a partir de dos ejes del acelerómetro."""
    return math.degrees(math.atan2(lado, vertical))


def angulo_promedio(muestras):
    """Ángulo medio de varias lecturas (lado, vertical).

    Se promedian las componentes y no los ángulos, para evitar errores
    al cruzar ±180°.
    """
    if not muestras:
        raise ValueError("Se necesita al menos una muestra")
    lado = sum(m[0] for m in muestras) / len(muestras)
    vertical = sum(m[1] for m in muestras) / len(muestras)
    return angulo_crudo(lado, vertical)


def angulo_corregido(lado, vertical, cfg):
    """Ángulo relativo al centro calibrado, con inversión y zona muerta."""
    ang = normalizar(angulo_crudo(lado, vertical) - cfg["centro"])
    if cfg["invertir"]:
        ang = -ang
    if abs(ang) < cfg["zona_muerta"]:
        ang = 0.0
    return ang


def suavizar(anterior, nuevo, factor):
    """Filtro exponencial: factor 0 = sin suavizado, cercano a 1 = muy suave."""
    return factor * anterior + (1 - factor) * nuevo


def valor_eje(angulo, angulo_max):
    """Convierte un ángulo en un valor entero del eje [-EJE_MAX, EJE_MAX]."""
    proporcion = max(-1.0, min(1.0, angulo / angulo_max))
    return int(proporcion * EJE_MAX)


class CalibracionInvalida(ValueError):
    pass


def calcular_calibracion(centro, izquierda, derecha, giro_minimo=5.0):
    """Calcula centro, ángulo máximo e inversión a partir de tres capturas.

    Los argumentos son ángulos crudos en grados. Devuelve un diccionario con
    las claves de configuración "centro", "angulo_max" e "invertir".
    """
    izq = normalizar(izquierda - centro)
    der = normalizar(derecha - centro)
    if abs(izq) < giro_minimo or abs(der) < giro_minimo or (izq > 0) == (der > 0):
        raise CalibracionInvalida(
            "No se detectó un giro claro hacia ambos lados."
        )
    angulo = (abs(izq) + abs(der)) / 2
    angulo = max(10.0, min(180.0, round(angulo / 5) * 5))
    return {
        "centro": round(centro, 2),
        "angulo_max": float(angulo),
        # La izquierda debe producir valores negativos en el eje.
        "invertir": izq > 0,
    }
