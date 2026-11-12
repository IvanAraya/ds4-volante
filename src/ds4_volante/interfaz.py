"""Ventana principal (Tkinter) con ajustes y asistente de calibración."""
import tkinter as tk

from . import calculo
from .config import VALORES_INICIALES, guardar_config

ANCHO = 300
PASOS = [
    ("centro", "Paso 1/3: sostén el control en posición neutral (recto)."),
    ("izquierda", "Paso 2/3: gira el control a la izquierda hasta el tope "
                  "que quieres usar."),
    ("derecha", "Paso 3/3: gira el control a la derecha hasta el tope "
                "que quieres usar."),
]
MUESTRAS = 30  # lecturas promediadas por paso (~0,6 s)


class Ventana:
    def __init__(self, root, cfg, volante, ruta_config=None):
        self.root = root
        self.cfg = cfg
        self.volante = volante
        self.ruta_config = ruta_config
        self.cal = {"paso": None, "muestras": [], "capturas": {}, "pulsaciones": 0}

        root.title("DS4 Volante")
        root.resizable(False, False)
        marco = tk.Frame(root, padx=10, pady=10)
        marco.pack()
        self._crear_ajustes(marco)
        self._crear_calibracion(marco)
        root.protocol("WM_DELETE_WINDOW", self.cerrar)

    # --- Construcción -----------------------------------------------------
    def _crear_ajustes(self, marco):
        cfg = self.cfg
        self.lbl_estado = tk.Label(marco, text="", anchor="w", justify="left",
                                   wraplength=ANCHO)
        self.lbl_estado.pack(fill="x")

        self.canvas = tk.Canvas(marco, width=ANCHO, height=24, bg="white",
                                highlightthickness=1, highlightbackground="gray")
        self.canvas.pack(pady=6)
        mitad = ANCHO // 2
        self.canvas.create_line(mitad, 0, mitad, 24, fill="gray")
        self.barra = self.canvas.create_rectangle(mitad, 4, mitad, 20,
                                                  fill="steelblue", width=0)

        self.var_inv = tk.BooleanVar(value=cfg["invertir"])
        tk.Checkbutton(marco, text="Invertir giro",
                       variable=self.var_inv).pack(anchor="w")

        self.var_ang = tk.DoubleVar(value=cfg["angulo_max"])
        tk.Scale(marco, label="Ángulo máximo (grados)", from_=10, to=180,
                 resolution=5, orient="horizontal", length=ANCHO,
                 variable=self.var_ang).pack()

        self.var_zona = tk.DoubleVar(value=cfg["zona_muerta"])
        tk.Scale(marco, label="Zona muerta (grados)", from_=0, to=15,
                 resolution=0.5, orient="horizontal", length=ANCHO,
                 variable=self.var_zona).pack()

        self.var_suav = tk.DoubleVar(value=cfg["suavizado"])
        tk.Scale(marco, label="Suavizado", from_=0, to=0.95,
                 resolution=0.05, orient="horizontal", length=ANCHO,
                 variable=self.var_suav).pack()

        botones = tk.Frame(marco)
        botones.pack(pady=(8, 0))
        self.btn_iniciar = tk.Button(botones, text="Iniciar", width=10,
                                     command=self.volante.iniciar)
        self.btn_iniciar.pack(side="left", padx=4)
        self.btn_detener = tk.Button(botones, text="Detener", width=10,
                                     command=self.volante.detener)
        self.btn_detener.pack(side="left", padx=4)

    def _crear_calibracion(self, marco):
        marco_cal = tk.LabelFrame(marco, text="Calibración", padx=6, pady=6)
        marco_cal.pack(fill="x", pady=(10, 0))

        self.lbl_cal = tk.Label(marco_cal, justify="left", anchor="w",
                                wraplength=ANCHO)
        self.lbl_cal.pack(fill="x")
        botones = tk.Frame(marco_cal)
        botones.pack(pady=(6, 0))

        def boton(texto, comando, estado=tk.NORMAL):
            b = tk.Button(botones, text=texto, width=9, state=estado,
                          command=comando)
            b.pack(side="left", padx=2)
            return b

        self.btn_calibrar = boton("Calibrar", self.iniciar_calibracion)
        self.btn_capturar = boton("Capturar", self.capturar, tk.DISABLED)
        self.btn_cancelar = boton("Cancelar", self.cancelar_calibracion, tk.DISABLED)
        self.btn_restablecer = boton("Restablecer", self.restablecer_calibracion)
        self.lbl_cal.config(text=self._texto_reposo())

    # --- Calibración ------------------------------------------------------
    def _texto_reposo(self):
        return (f"Centro actual: {self.cfg['centro']:+.1f}°. "
                "Pulsa «Calibrar» para ajustar el centro, el giro máximo "
                "y la dirección.")

    def _mostrar_paso(self):
        _, texto = PASOS[self.cal["paso"]]
        self.lbl_cal.config(
            text=texto + "\nPulsa «Capturar» o la Cruz (X) del control.")
        self.btn_capturar.config(state=tk.NORMAL)

    def iniciar_calibracion(self):
        if not self.volante.activo():
            self.lbl_cal.config(text="Primero inicia el volante para leer el sensor.")
            return
        self.cal.update(paso=0, muestras=[], capturas={},
                        pulsaciones=self.volante.pulsaciones)
        self.btn_calibrar.config(state=tk.DISABLED)
        self.btn_cancelar.config(state=tk.NORMAL)
        self.btn_restablecer.config(state=tk.DISABLED)
        self._mostrar_paso()

    def _terminar_calibracion(self, mensaje):
        self.cal.update(paso=None, muestras=[])
        self.btn_capturar.config(state=tk.DISABLED)
        self.btn_cancelar.config(state=tk.DISABLED)
        self.btn_calibrar.config(state=tk.NORMAL)
        self.btn_restablecer.config(state=tk.NORMAL)
        self.lbl_cal.config(text=mensaje)

    def capturar(self):
        if self.cal["paso"] is None or self.cal["muestras"]:
            return
        self.btn_capturar.config(state=tk.DISABLED)
        self.lbl_cal.config(text="Midiendo... no muevas el control.")
        self._tomar_muestra()

    def _tomar_muestra(self):
        cal = self.cal
        if cal["paso"] is None:
            return
        if not self.volante.activo():
            self._terminar_calibracion("Calibración cancelada: el volante se detuvo.")
            return
        cal["muestras"].append(self.volante.acc)
        if len(cal["muestras"]) < MUESTRAS:
            self.root.after(20, self._tomar_muestra)
            return
        nombre, _ = PASOS[cal["paso"]]
        cal["capturas"][nombre] = calculo.angulo_promedio(cal["muestras"])
        cal["muestras"] = []
        cal["paso"] += 1
        if cal["paso"] < len(PASOS):
            self._mostrar_paso()
        else:
            self._aplicar_calibracion()

    def _aplicar_calibracion(self):
        c = self.cal["capturas"]
        try:
            resultado = calculo.calcular_calibracion(
                c["centro"], c["izquierda"], c["derecha"])
        except calculo.CalibracionInvalida as exc:
            self._terminar_calibracion(
                f"{exc} Inténtalo de nuevo girando más el control.")
            return
        self.cfg.update(resultado)
        self.var_inv.set(resultado["invertir"])
        self.var_ang.set(resultado["angulo_max"])
        self._guardar()
        self._terminar_calibracion(
            f"Calibración guardada. Centro: {resultado['centro']:+.1f}°, "
            f"ángulo máximo: {resultado['angulo_max']:.0f}°, "
            f"giro {'invertido' if resultado['invertir'] else 'normal'}."
        )

    def cancelar_calibracion(self):
        self._terminar_calibracion("Calibración cancelada. " + self._texto_reposo())

    def restablecer_calibracion(self):
        self.cfg["centro"] = VALORES_INICIALES["centro"]
        self._guardar()
        self.lbl_cal.config(text="Centro restablecido. " + self._texto_reposo())

    # --- Ciclo de la aplicación -------------------------------------------
    def _guardar(self):
        if not guardar_config(self.cfg, self.ruta_config):
            self.lbl_cal.config(text="No se pudo guardar la configuración.")

    def actualizar(self):
        cfg = self.cfg
        cfg["invertir"] = self.var_inv.get()
        cfg["angulo_max"] = self.var_ang.get()
        cfg["zona_muerta"] = self.var_zona.get()
        cfg["suavizado"] = self.var_suav.get()

        self.lbl_estado.config(text=f"Estado: {self.volante.estado}")
        mitad = ANCHO // 2
        x = mitad + self.volante.valor / calculo.EJE_MAX * (mitad - 2)
        self.canvas.coords(self.barra, min(mitad, x), 4, max(mitad, x), 20)

        # Permite capturar con la Cruz (X) del control durante la calibración.
        if self.volante.pulsaciones != self.cal["pulsaciones"]:
            self.cal["pulsaciones"] = self.volante.pulsaciones
            if self.cal["paso"] is not None and not self.cal["muestras"]:
                self.capturar()

        activo = self.volante.activo()
        self.btn_iniciar.config(state=tk.DISABLED if activo else tk.NORMAL)
        self.btn_detener.config(state=tk.NORMAL if activo else tk.DISABLED)
        self.root.after(50, self.actualizar)

    def cerrar(self):
        self.volante.detener(esperar=True)
        guardar_config(self.cfg, self.ruta_config)
        self.root.destroy()


def ejecutar(cfg, volante, ruta_config=None, iniciar=True):
    root = tk.Tk(className="ds4-volante")
    ventana = Ventana(root, cfg, volante, ruta_config)
    if iniciar:
        volante.iniciar()
    ventana.actualizar()
    root.mainloop()
