#!/usr/bin/env python3
"""DS4 Volante: usa la inclinación del DualShock 4 como eje de dirección."""
import json
import math
import os
import pwd
import select
import threading
import tkinter as tk

from evdev import InputDevice, UInput, AbsInfo, ecodes as e, list_devices

# Ejes del acelerómetro (según lo observado con evtest)
LADO = e.ABS_X
VERTICAL = e.ABS_Y
GATILLOS_DIGITALES = {e.BTN_TL2, e.BTN_TR2}
BOTON_CAPTURA = e.BTN_SOUTH  # Cruz (X): captura un paso durante la calibración

VALORES_INICIALES = {
    "invertir": True,
    "angulo_max": 90.0,
    "zona_muerta": 0.0,
    "suavizado": 0.4,
    "centro": 0.0,  # ángulo crudo (grados) que corresponde a la posición neutral
}


def normalizar(ang):
    """Lleva un ángulo en grados al intervalo [-180, 180)."""
    return (ang + 180.0) % 360.0 - 180.0

def carpeta_usuario():
    usuario = os.environ.get("SUDO_USER")
    if usuario:
        return pwd.getpwnam(usuario).pw_dir
    return os.path.expanduser("~")
    

CONFIG = os.path.join(carpeta_usuario(), ".config", "ds4-volante.json")

def cargar_config():
    cfg = dict(VALORES_INICIALES)
    try:
        with open(CONFIG, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def guardar_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        if "SUDO_UID" in os.environ:
            os.chown(CONFIG, int(os.environ["SUDO_UID"]), int(os.environ["SUDO_GID"]))
    except OSError:
        pass


def buscar_dispositivos():
    devs = [InputDevice(p) for p in list_devices()]
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
        raise RuntimeError(
            "No se encontró el control. Conéctalo por USB o revisa los permisos."
        )
    return principal, motion


class Volante:
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

    def _ejecutar(self):
        principal = motion = ui = None
        capturado = False
        try:
            principal, motion = buscar_dispositivos()

            caps = principal.capabilities(absinfo=True)
            caps.pop(e.EV_SYN, None)
            caps.pop(e.EV_FF, None)
            if e.EV_KEY in caps:
                caps[e.EV_KEY] = [
                    c for c in caps[e.EV_KEY] if c not in GATILLOS_DIGITALES
                ]
            caps.setdefault(e.EV_ABS, []).append(
                (e.ABS_WHEEL, AbsInfo(value=0, min=-32767, max=32767,
                                      fuzz=0, flat=0, resolution=0))
            )

            ui = UInput(caps, name="DS4 Volante")
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
                            ang = math.degrees(math.atan2(acc[LADO], acc[VERTICAL]))
                            ang = normalizar(ang - cfg["centro"])
                            if cfg["invertir"]:
                                ang = -ang
                            if abs(ang) < cfg["zona_muerta"]:
                                ang = 0.0
                            s = cfg["suavizado"]
                            filtrado = s * filtrado + (1 - s) * ang
                            valor = int(
                                max(-1.0, min(1.0, filtrado / cfg["angulo_max"])) * 32767
                            )
                            self.valor = valor
                            if valor != ultimo:
                                ui.write(e.EV_ABS, e.ABS_WHEEL, valor)
                                ui.syn()
                                ultimo = valor
            self.estado = "Detenido"
        except RuntimeError as exc:
            self.estado = str(exc)
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


def main():
    cfg = cargar_config()
    volante = Volante(cfg)

    root = tk.Tk()
    root.title("DS4 Volante")
    root.resizable(False, False)

    marco = tk.Frame(root, padx=10, pady=10)
    marco.pack()

    lbl_estado = tk.Label(marco, text="", anchor="w", width=48)
    lbl_estado.pack(fill="x")

    canvas = tk.Canvas(marco, width=300, height=24, bg="white",
                       highlightthickness=1, highlightbackground="gray")
    canvas.pack(pady=6)
    canvas.create_line(150, 0, 150, 24, fill="gray")
    barra = canvas.create_rectangle(150, 4, 150, 20, fill="steelblue", width=0)

    var_inv = tk.BooleanVar(value=cfg["invertir"])
    tk.Checkbutton(marco, text="Invertir giro", variable=var_inv).pack(anchor="w")

    var_ang = tk.DoubleVar(value=cfg["angulo_max"])
    tk.Scale(marco, label="Ángulo máximo (grados)", from_=10, to=180,
             resolution=5, orient="horizontal", length=300,
             variable=var_ang).pack()

    var_zona = tk.DoubleVar(value=cfg["zona_muerta"])
    tk.Scale(marco, label="Zona muerta (grados)", from_=0, to=15,
             resolution=0.5, orient="horizontal", length=300,
             variable=var_zona).pack()

    var_suav = tk.DoubleVar(value=cfg["suavizado"])
    tk.Scale(marco, label="Suavizado", from_=0, to=0.95,
             resolution=0.05, orient="horizontal", length=300,
             variable=var_suav).pack()

    botones = tk.Frame(marco)
    botones.pack(pady=(8, 0))
    btn_iniciar = tk.Button(botones, text="Iniciar", width=10,
                            command=volante.iniciar)
    btn_iniciar.pack(side="left", padx=4)
    btn_detener = tk.Button(botones, text="Detener", width=10,
                            command=volante.detener)
    btn_detener.pack(side="left", padx=4)

    # --- Calibración -------------------------------------------------------
    marco_cal = tk.LabelFrame(marco, text="Calibración", padx=6, pady=6)
    marco_cal.pack(fill="x", pady=(10, 0))

    lbl_cal = tk.Label(marco_cal, justify="left", anchor="w", wraplength=300)
    lbl_cal.pack(fill="x")
    botones_cal = tk.Frame(marco_cal)
    botones_cal.pack(pady=(6, 0))

    PASOS = [
        ("centro", "Paso 1/3: sostén el control en posición neutral (recto)."),
        ("izquierda", "Paso 2/3: gira el control a la izquierda hasta el tope "
                      "que quieres usar."),
        ("derecha", "Paso 3/3: gira el control a la derecha hasta el tope "
                    "que quieres usar."),
    ]
    MUESTRAS = 30  # lecturas promediadas por paso (~0,6 s)
    cal = {"paso": None, "muestras": [], "capturas": {}, "pulsaciones": 0}

    def texto_reposo():
        return (f"Centro actual: {cfg['centro']:+.1f}°. "
                "Pulsa «Calibrar» para ajustar el centro, el giro máximo "
                "y la dirección.")

    def angulo_actual_promedio(muestras):
        # Promediar las componentes evita errores al cruzar ±180°.
        lado = sum(m[0] for m in muestras) / len(muestras)
        vertical = sum(m[1] for m in muestras) / len(muestras)
        return math.degrees(math.atan2(lado, vertical))

    def mostrar_paso():
        _, texto = PASOS[cal["paso"]]
        lbl_cal.config(text=texto + "\nPulsa «Capturar» o la Cruz (X) del control.")
        btn_capturar.config(state=tk.NORMAL)

    def iniciar_calibracion():
        if not volante.activo():
            lbl_cal.config(text="Primero inicia el volante para leer el sensor.")
            return
        cal.update(paso=0, muestras=[], capturas={},
                   pulsaciones=volante.pulsaciones)
        btn_calibrar.config(state=tk.DISABLED)
        btn_cancelar.config(state=tk.NORMAL)
        btn_restablecer.config(state=tk.DISABLED)
        mostrar_paso()

    def terminar_calibracion(mensaje):
        cal.update(paso=None, muestras=[])
        btn_capturar.config(state=tk.DISABLED)
        btn_cancelar.config(state=tk.DISABLED)
        btn_calibrar.config(state=tk.NORMAL)
        btn_restablecer.config(state=tk.NORMAL)
        lbl_cal.config(text=mensaje)

    def capturar():
        if cal["paso"] is None or cal["muestras"]:
            return
        btn_capturar.config(state=tk.DISABLED)
        lbl_cal.config(text="Midiendo... no muevas el control.")
        tomar_muestra()

    def tomar_muestra():
        if cal["paso"] is None:
            return
        if not volante.activo():
            terminar_calibracion("Calibración cancelada: el volante se detuvo.")
            return
        cal["muestras"].append(volante.acc)
        if len(cal["muestras"]) < MUESTRAS:
            root.after(20, tomar_muestra)
            return
        nombre, _ = PASOS[cal["paso"]]
        cal["capturas"][nombre] = angulo_actual_promedio(cal["muestras"])
        cal["muestras"] = []
        cal["paso"] += 1
        if cal["paso"] < len(PASOS):
            mostrar_paso()
        else:
            aplicar_calibracion()

    def aplicar_calibracion():
        c = cal["capturas"]
        izq = normalizar(c["izquierda"] - c["centro"])
        der = normalizar(c["derecha"] - c["centro"])
        if abs(izq) < 5 or abs(der) < 5 or (izq > 0) == (der > 0):
            terminar_calibracion(
                "No se detectó un giro claro hacia ambos lados. "
                "Inténtalo de nuevo girando más el control."
            )
            return
        angulo = (abs(izq) + abs(der)) / 2
        angulo = max(10.0, min(180.0, round(angulo / 5) * 5))
        cfg["centro"] = round(c["centro"], 2)
        # La izquierda debe producir valores negativos en el eje.
        cfg["invertir"] = izq > 0
        cfg["angulo_max"] = angulo
        var_inv.set(cfg["invertir"])
        var_ang.set(angulo)
        guardar_config(cfg)
        terminar_calibracion(
            f"Calibración guardada. Centro: {cfg['centro']:+.1f}°, "
            f"ángulo máximo: {angulo:.0f}°, "
            f"giro {'invertido' if izq > 0 else 'normal'}."
        )

    def cancelar_calibracion():
        terminar_calibracion("Calibración cancelada. " + texto_reposo())

    def restablecer_calibracion():
        cfg["centro"] = VALORES_INICIALES["centro"]
        guardar_config(cfg)
        lbl_cal.config(text="Centro restablecido. " + texto_reposo())

    btn_calibrar = tk.Button(botones_cal, text="Calibrar", width=9,
                             command=iniciar_calibracion)
    btn_calibrar.pack(side="left", padx=2)
    btn_capturar = tk.Button(botones_cal, text="Capturar", width=9,
                             state=tk.DISABLED, command=capturar)
    btn_capturar.pack(side="left", padx=2)
    btn_cancelar = tk.Button(botones_cal, text="Cancelar", width=9,
                             state=tk.DISABLED, command=cancelar_calibracion)
    btn_cancelar.pack(side="left", padx=2)
    btn_restablecer = tk.Button(botones_cal, text="Restablecer", width=9,
                                command=restablecer_calibracion)
    btn_restablecer.pack(side="left", padx=2)
    lbl_cal.config(text=texto_reposo())

    def actualizar():
        cfg["invertir"] = var_inv.get()
        cfg["angulo_max"] = var_ang.get()
        cfg["zona_muerta"] = var_zona.get()
        cfg["suavizado"] = var_suav.get()

        lbl_estado.config(text=f"Estado: {volante.estado}")
        x = 150 + volante.valor / 32767 * 148
        canvas.coords(barra, min(150, x), 4, max(150, x), 20)

        # Permite capturar con la Cruz (X) del control durante la calibración.
        if volante.pulsaciones != cal["pulsaciones"]:
            cal["pulsaciones"] = volante.pulsaciones
            if cal["paso"] is not None and not cal["muestras"]:
                capturar()

        activo = volante.activo()
        btn_iniciar.config(state=tk.DISABLED if activo else tk.NORMAL)
        btn_detener.config(state=tk.NORMAL if activo else tk.DISABLED)
        root.after(50, actualizar)

    def cerrar():
        volante.detener(esperar=True)
        guardar_config(cfg)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", cerrar)
    volante.iniciar()
    actualizar()
    root.mainloop()


if __name__ == "__main__":
    main()
