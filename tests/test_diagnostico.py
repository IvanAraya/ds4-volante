import pytest

from ds4_volante import diagnostico

# Extracto de /proc/bus/input/devices con un DualShock 4 por USB.
PROC = """\
I: Bus=0011 Vendor=0001 Product=0001 Version=ab41
N: Name="AT Translated Set 2 keyboard"
H: Handlers=sysrq kbd leds event3

I: Bus=0003 Vendor=054c Product=05c4 Version=8111
N: Name="Sony Computer Entertainment Wireless Controller"
H: Handlers=event11 js0

I: Bus=0003 Vendor=054c Product=05c4 Version=8111
N: Name="Sony Computer Entertainment Wireless Controller Motion Sensors"
H: Handlers=event12

I: Bus=0003 Vendor=054c Product=05c4 Version=8111
N: Name="Sony Computer Entertainment Wireless Controller Touchpad"
H: Handlers=mouse1 event13

I: Bus=0019 Vendor=0000 Product=0001 Version=0000
N: Name="Power Button"
H: Handlers=kbd
"""


def test_analizar_proc():
    dispositivos = diagnostico.analizar_proc(PROC)
    assert [d.ruta for d in dispositivos] == [
        "/dev/input/event3", "/dev/input/event11",
        "/dev/input/event12", "/dev/input/event13",
    ]
    assert dispositivos[2].nombre.endswith("Motion Sensors")
    assert "Vendor=054c" in dispositivos[1].identificador


def test_controles_conectados(tmp_path):
    proc = tmp_path / "devices"
    proc.write_text(PROC)
    nombres = [d.nombre for d in diagnostico.controles_conectados(str(proc))]
    assert len(nombres) == 3
    assert all("Wireless Controller" in n for n in nombres)


def test_controles_conectados_sin_proc(tmp_path):
    assert diagnostico.controles_conectados(str(tmp_path / "no-existe")) == []


@pytest.fixture
def entorno(monkeypatch):
    """Simula un sistema; cada prueba ajusta los valores que necesita."""
    estado = {"reglas": True, "logind": False, "grupo_sesion": False,
              "grupo_cuenta": False, "acceso": False}
    monkeypatch.setattr(diagnostico, "reglas_instaladas", lambda: estado["reglas"])
    monkeypatch.setattr(diagnostico, "usa_logind", lambda: estado["logind"])
    monkeypatch.setattr(diagnostico, "en_grupo", lambda g="input": estado["grupo_sesion"])
    monkeypatch.setattr(diagnostico, "grupo_en_cuenta",
                        lambda g="input": estado["grupo_cuenta"])
    monkeypatch.setattr(diagnostico.os, "access", lambda ruta, modo: estado["acceso"])
    monkeypatch.setattr(diagnostico, "controles_conectados",
                        lambda: diagnostico.analizar_proc(PROC)[1:])
    return estado


def test_sin_reglas_y_sin_logind(entorno):
    # Caso real: reglas sin instalar, sistema sin systemd y usuario fuera de «input».
    entorno["reglas"] = False
    texto = " ".join(diagnostico.problemas_de_acceso())
    assert "sudo make install" in texto
    assert "usermod -aG input" in texto


def test_grupo_pendiente_de_nueva_sesion(entorno):
    entorno["grupo_cuenta"] = True
    (problema,) = diagnostico.problemas_de_acceso()
    assert "cierra sesión" in problema and "usermod" not in problema


def test_con_logind_sugiere_reconectar(entorno):
    entorno["logind"] = True
    (problema,) = diagnostico.problemas_de_acceso()
    assert "vuelve a conectar" in problema


def test_todo_correcto(entorno):
    entorno["acceso"] = True
    assert diagnostico.problemas_de_acceso() == []
    assert "Todo correcto." in diagnostico.informe()
