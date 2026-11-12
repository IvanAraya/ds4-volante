"""Detección de problemas de permisos sin depender de evdev.

``evdev.list_devices()`` omite en silencio los dispositivos que no se pueden
leer, así que aquí se consulta /proc/bus/input/devices para saber si el control
está conectado aunque falten permisos.
"""
import grp
import os
import pwd
import re
import shutil
from dataclasses import dataclass

PROC_DISPOSITIVOS = "/proc/bus/input/devices"
UINPUT = "/dev/uinput"
GRUPO = "input"
RUTAS_REGLAS = (
    "/etc/udev/rules.d/70-ds4-volante.rules",
    "/usr/lib/udev/rules.d/70-ds4-volante.rules",
    "/lib/udev/rules.d/70-ds4-volante.rules",
)
NOMBRE_CONTROL = "Wireless Controller"


@dataclass
class Dispositivo:
    nombre: str
    ruta: str
    identificador: str = ""

    @property
    def lectura(self):
        return os.access(self.ruta, os.R_OK)

    @property
    def escritura(self):
        return os.access(self.ruta, os.W_OK)


def analizar_proc(texto):
    """Devuelve los dispositivos de entrada descritos en /proc/bus/input/devices."""
    dispositivos = []
    for bloque in texto.split("\n\n"):
        nombre = re.search(r'^N: Name="(.*)"$', bloque, re.M)
        evento = re.search(r"^H: Handlers=.*?\b(event\d+)\b", bloque, re.M)
        ident = re.search(r"^I: (.*)$", bloque, re.M)
        if nombre and evento:
            dispositivos.append(Dispositivo(
                nombre.group(1), "/dev/input/" + evento.group(1),
                ident.group(1).strip() if ident else ""))
    return dispositivos


def controles_conectados(ruta_proc=PROC_DISPOSITIVOS):
    """Dispositivos del DualShock 4 conectados, tengan o no permisos."""
    try:
        with open(ruta_proc, encoding="utf-8", errors="replace") as f:
            texto = f.read()
    except OSError:
        return []
    return [d for d in analizar_proc(texto) if NOMBRE_CONTROL in d.nombre]


def usa_logind():
    """True si systemd-logind (o elogind) gestiona los asientos (necesario para uaccess)."""
    return os.path.isdir("/run/systemd/seats")


def reglas_instaladas():
    return any(os.path.exists(r) for r in RUTAS_REGLAS)


def en_grupo(grupo=GRUPO):
    try:
        gid = grp.getgrnam(grupo).gr_gid
    except KeyError:
        return False
    return gid in os.getgroups() or gid == os.getgid()


def grupo_en_cuenta(grupo=GRUPO):
    """True si el usuario pertenece al grupo en /etc/group (aunque la sesión aún no lo refleje)."""
    try:
        usuario = pwd.getpwuid(os.getuid()).pw_name
        g = grp.getgrnam(grupo)
    except KeyError:
        return False
    return usuario in g.gr_mem or g.gr_gid == pwd.getpwuid(os.getuid()).pw_gid


def problemas_de_acceso():
    """Lista de mensajes que explican por qué no se puede usar el control."""
    problemas = []
    if not reglas_instaladas():
        problemas.append("Las reglas udev no están instaladas: ejecuta «sudo make install» "
                         "en la carpeta del proyecto.")
    sin_acceso = [d for d in controles_conectados() if not (d.lectura and d.escritura)]
    uinput_ok = os.access(UINPUT, os.W_OK)
    if sin_acceso or not uinput_ok:
        if usa_logind():
            problemas.append("Sin permiso sobre el control o /dev/uinput: desconecta y "
                             "vuelve a conectar el control (o reinicia la sesión).")
        elif grupo_en_cuenta() and not en_grupo():
            problemas.append(f"Ya perteneces al grupo «{GRUPO}», pero tu sesión aún no lo "
                             "refleja: cierra sesión y vuelve a entrar.")
        else:
            problemas.append(f"Tu usuario debe pertenecer al grupo «{GRUPO}»: ejecuta "
                             f"«sudo usermod -aG {GRUPO} $USER» y cierra sesión.")
    return problemas


def informe():
    """Texto de diagnóstico para --diagnostico."""
    lineas = [
        f"Usuario: {pwd.getpwuid(os.getuid()).pw_name} (uid {os.getuid()})",
        f"Gestor de sesión (logind/elogind): {'sí' if usa_logind() else 'no'}",
        f"Grupo «{GRUPO}»: en la sesión {'sí' if en_grupo() else 'no'}, "
        f"en la cuenta {'sí' if grupo_en_cuenta() else 'no'}",
        f"Reglas udev instaladas: {'sí' if reglas_instaladas() else 'no'}",
        f"{UINPUT}: existe {'sí' if os.path.exists(UINPUT) else 'no'}, "
        f"escritura {'sí' if os.access(UINPUT, os.W_OK) else 'no'}",
    ]
    controles = controles_conectados()
    if controles:
        lineas.append("Control:")
        for d in controles:
            lineas.append(f"  {d.nombre} ({d.ruta}) lectura "
                          f"{'sí' if d.lectura else 'no'}, escritura "
                          f"{'sí' if d.escritura else 'no'}")
    else:
        lineas.append("Control: no conectado")
    if not shutil.which("udevadm"):
        lineas.append("Aviso: no se encontró udevadm.")
    problemas = problemas_de_acceso()
    if not controles:
        problemas.insert(0, "Conecta el control por USB o Bluetooth.")
    lineas.append("")
    lineas.extend(["Problemas encontrados:"] + [f"  - {p}" for p in problemas]
                  if problemas else ["Todo correcto."])
    return "\n".join(lineas)
