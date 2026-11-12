"""Lectura del DualShock 4 y publicación del eje virtual mediante uinput."""
import select
import threading

from evdev import AbsInfo, InputDevice, UInput, ecodes as e, list_devices
from evdev.uinput import UInputError

from . import calculo

# Ejes del acelerómetro (según lo observado con evtest)
LADO = e.ABS_X
VERTICAL = e.ABS_Y
GATILLOS_DIGITALES = {e.BTN_TL2, e.BTN_TR2}
BOTON_CAPTURA = e.BTN_SOUTH  # Cruz (X): captura un paso durante la calibración
NOMBRE_VIRTUAL = "DS4 Volante"

AYUDA_PERMISOS = (
    "Instala las reglas udev (ver README) y vuelve a conectar el control."
)


def buscar_dispositivos():
    """Devuelve (principal, sensores) del primer DualShock 4 encontrado."""
    devs = []
    sin_acceso = False
    for ruta in list_devices():
        try:
            devs.append(InputDevice(ruta))
        except PermissionError:
            sin_acceso = True
        except OSError:
            pass
    motion = next(
        (d for d in devs if "Wireless Controller Motion Sensors" in d.name), None
    )
    principal = next(
        (
            d for d in devs
            if "Wireless Controller" in d.name
            and "Motion" not in d.name
            and "Touchpad" not in d.name
        ),
        None,
    )
    for d in devs:
        if d is not principal and d is not motion:
            d.close()
    if principal is None or motion is None:
        for d in (principal, motion):
            if d:
                d.close()
        mensaje = "No se encontró el control. Conéctalo por USB o Bluetooth."
        if sin_acceso:
            mensaje += " Algunos dispositivos no son accesibles: " + AYUDA_PERMISOS
        raise RuntimeError(mensaje)
    return principal, motion


class Volante:
    """Hilo que reenvía el control y añade el eje ABS_WHEEL a partir de la inclinación."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.valor = 0
        self.estado = "Detenido"
        self.acc = (0, 1)  # última lectura cruda del acelerómetro (lado, vertical)
        self.pulsaciones = 0  # veces que se ha pulsado BOTON_CAPTURA
        self._parar = threading.Event()
        self._hilo = None

    def activo(self):
        return self._hilo is not None and self._hilo.is_alive()

    def iniciar(self):
        if self.activo():
            return
        self._parar.clear()
        self.estado = "Buscando el control..."
        self._hilo = threading.Thread(target=self._ejecutar, daemon=True)
        self._hilo.start()

    def detener(self, esperar=False):
        self._parar.set()
        if esperar and self._hilo:
            self._hilo.join(timeout=2)

    def _crear_virtual(self, principal):
        caps = principal.capabilities(absinfo=True)
        caps.pop(e.EV_SYN, None)
        caps.pop(e.EV_FF, None)
        if e.EV_KEY in caps:
            caps[e.EV_KEY] = [c for c in caps[e.EV_KEY] if c not in GATILLOS_DIGITALES]
        caps.setdefault(e.EV_ABS, []).append(
            (e.ABS_WHEEL, AbsInfo(value=0, min=-calculo.EJE_MAX, max=calculo.EJE_MAX,
                                  fuzz=0, flat=0, resolution=0))
        )
        return UInput(caps, name=NOMBRE_VIRTUAL)

    def _ejecutar(self):
        principal = motion = ui = None
        capturado = False
        try:
            principal, motion = buscar_dispositivos()
            ui = self._crear_virtual(principal)
            principal.grab()
            capturado = True
            self.estado = "Activo"

            acc = {LADO: 0, VERTICAL: 1}
            filtrado = 0.0
            ultimo = None
            fuentes = {principal.fd: principal, motion.fd: motion}

            while not self._parar.is_set():
                listos, _, _ = select.select(fuentes, [], [], 0.2)
                for fd in listos:
                    dev = fuentes[fd]
                    for ev in dev.read():
                        if dev is principal:
                            if ev.type == e.EV_KEY and ev.code in GATILLOS_DIGITALES:
                                continue
                            if (ev.type == e.EV_KEY and ev.code == BOTON_CAPTURA
                                    and ev.value == 1):
                                self.pulsaciones += 1
                            ui.write_event(ev)
                        elif ev.type == e.EV_ABS and ev.code in acc:
                            acc[ev.code] = ev.value
                        elif ev.type == e.EV_SYN:
                            cfg = self.cfg
                            self.acc = (acc[LADO], acc[VERTICAL])
                            ang = calculo.angulo_corregido(*self.acc, cfg)
                            filtrado = calculo.suavizar(filtrado, ang, cfg["suavizado"])
                            valor = calculo.valor_eje(filtrado, cfg["angulo_max"])
                            self.valor = valor
                            if valor != ultimo:
                                ui.write(e.EV_ABS, e.ABS_WHEEL, valor)
                                ui.syn()
                                ultimo = valor
            self.estado = "Detenido"
        except RuntimeError as exc:
            self.estado = str(exc)
        except (PermissionError, UInputError):
            self.estado = "Sin permiso para usar el control o /dev/uinput. " + AYUDA_PERMISOS
        except OSError as exc:
            self.estado = f"Control desconectado o sin acceso ({exc.strerror or exc})"
        except Exception as exc:  # p. ej., error al crear el dispositivo virtual
            self.estado = f"Error: {exc}"
        finally:
            if capturado:
                try:
                    principal.ungrab()
                except OSError:
                    pass
            if ui:
                ui.close()
            for d in (principal, motion):
                if d:
                    try:
                        d.close()
                    except OSError:
                        pass
            self.valor = 0
