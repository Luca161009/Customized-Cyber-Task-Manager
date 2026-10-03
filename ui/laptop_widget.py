# ui/laptop_widget.py
"""
Riquadro "showroom": modello 3D stilizzato di una workstation portatile
(ispirata a una Fujitsu Celsius, ricostruita proceduralmente e non da un
file CAD proprietario) che ruota lentamente sull'asse Y, inquadrata con
una proiezione ISOMETRICA (rotazione camera X=-35.264°, Y=45°: i tre assi
appaiono a 120° tra loro).

Rispetto alla build precedente:
- Rimossa la piattaforma circolare sotto il laptop.
- Ombreggiatura "finta" per faccia (le facce rivolte verso l'alto/luce
  sono più chiare, quelle in ombra più scure) per dare volume reale senza
  dover attivare l'illuminazione OpenGL classica.
- Proporzioni più simili a una workstation vera: base sottile, griglia di
  ventilazione laterale, touchpad, tasti distinti, bezel sottile con
  webcam, logo posteriore.
- Il widget è pensato per stare in un riquadro STRETTO e centrato (vedi
  ui/main_window.py), non a piena larghezza.
"""

import math

from OpenGL.GL import *
from OpenGL.GLU import gluPerspective
from PySide6.QtCore import QTimer
from PySide6.QtOpenGLWidgets import QOpenGLWidget

NEON = (0.0, 0.9, 1.0)
NEON_SOFT = (0.0, 0.65, 0.85)


def _shade(base_color, factor):
    return tuple(min(1.0, max(0.0, c * factor)) for c in base_color)


class LaptopShowroomWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._spin_angle = 0.0
        self._rot_speed_deg_s = 10.0  # lenta e fluida (gradi al secondo, indipendente dagli FPS)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.start(40)  # 25 FPS: fluido in modo costante, senza scatti periodici

        # Pensato per un riquadro compatto e centrato, non a piena larghezza
        self.setMinimumSize(260, 190)

    def _advance(self):
        self._spin_angle = (self._spin_angle + self._rot_speed_deg_s * 0.040) % 360.0
        self.update()

    # ------------------------------------------------------------------
    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glClearColor(0.0, 0.0, 0.0, 0.0)  # sfondo trasparente: eredita il pannello

    def resizeGL(self, w, h):
        h = max(h, 1)
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(24.0, w / h, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        glTranslatef(0.0, 0.02, -6.2)  # ancora più margine: priorità a zero tagli su qualunque angolo

        # --- Proiezione isometrica: X=-35.264°, poi Y=45° ---
        glRotatef(35.264, 1.0, 0.0, 0.0)
        glRotatef(45.0, 0.0, 1.0, 0.0)

        # --- Rotazione "showroom" continua ---
        glPushMatrix()
        glRotatef(self._spin_angle, 0.0, 1.0, 0.0)
        self._draw_laptop()
        glPopMatrix()

    # ------------------------------------------------------------------
    def _draw_quad(self, verts, color):
        glColor4f(*color, 1.0)
        glBegin(GL_QUADS)
        for v in verts:
            glVertex3f(*v)
        glEnd()

    def _draw_box_shaded(self, sx, sy, sz, base_color, edge_color=NEON, edge_alpha=0.9):
        """
        Parallelepipedo con una tinta diversa per ciascuna faccia in base
        al suo orientamento (finta illuminazione "da showroom" dall'alto).
        """
        x, y, z = sx / 2, sy / 2, sz / 2
        v = [
            (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z),
            (-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
        ]
        faces = [
            ((0, 1, 2, 3), 1.15),   # fronte
            ((5, 4, 7, 6), 0.55),   # retro
            ((4, 0, 3, 7), 0.75),   # sinistra
            ((1, 5, 6, 2), 0.85),   # destra
            ((3, 2, 6, 7), 1.35),   # sopra (più illuminata)
            ((4, 5, 1, 0), 0.45),   # sotto (in ombra)
        ]
        for face, factor in faces:
            self._draw_quad([v[i] for i in face], _shade(base_color, factor))

        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        ]
        glColor4f(*edge_color, edge_alpha)
        glLineWidth(1.3)
        glBegin(GL_LINES)
        for a, b in edges:
            glVertex3f(*v[a])
            glVertex3f(*v[b])
        glEnd()

    def _draw_laptop(self):
        base_metal = (0.16, 0.19, 0.24)
        screen_metal = (0.13, 0.16, 0.22)

        # --- Base (corpo con tastiera) ---
        glPushMatrix()
        glTranslatef(0.0, -0.40, 0.05)
        self._draw_box_shaded(1.85, 0.09, 1.20, base_metal)

        # Tasti: piccola griglia di rettangoli
        glColor4f(0.02, 0.03, 0.05, 1.0)
        rows, cols = 4, 11
        key_w, key_h = 0.135, 0.075
        gap = 0.02
        start_x = -(cols * (key_w + gap)) / 2 + key_w / 2
        start_z = -0.42
        for r in range(rows):
            for c in range(cols):
                cx = start_x + c * (key_w + gap)
                cz = start_z + r * (key_h + gap)
                glPushMatrix()
                glTranslatef(cx, 0.046, cz)
                glBegin(GL_QUADS)
                glVertex3f(-key_w / 2, 0, -key_h / 2)
                glVertex3f(key_w / 2, 0, -key_h / 2)
                glVertex3f(key_w / 2, 0, key_h / 2)
                glVertex3f(-key_w / 2, 0, key_h / 2)
                glEnd()
                glPopMatrix()

        # Touchpad
        glColor4f(*NEON_SOFT, 0.25)
        glBegin(GL_QUADS)
        glVertex3f(-0.34, 0.046, 0.30)
        glVertex3f(0.34, 0.046, 0.30)
        glVertex3f(0.34, 0.046, 0.52)
        glVertex3f(-0.34, 0.046, 0.52)
        glEnd()

        # Griglia di ventilazione laterale
        glColor4f(*NEON, 0.5)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        for i in range(6):
            zz = -0.5 + i * 0.045
            glVertex3f(0.926, -0.03, zz)
            glVertex3f(0.926, 0.03, zz)
        glEnd()
        glPopMatrix()

        # --- Schermo (inclinato, incernierato) ---
        glPushMatrix()
        glTranslatef(0.0, -0.355, -0.55)   # cerniera: bordo posteriore-alto della base
        # ANGOLO CORRETTO: a rotazione 0° lo schermo sta VERTICALE (perpendicolare
        # alla base). Valori negativi lo reclinano all'INDIETRO (lontano da chi
        # guarda) — le build precedenti (-85°/-102°) lo reclinavano quasi del
        # tutto all'indietro, un'inclinazione irrealistica. Un laptop vero, aperto
        # in posizione naturale, sta quasi verticale con solo una leggera
        # reclinazione: -12° è il valore giusto.
        glRotatef(-12.0, 1.0, 0.0, 0.0)
        # FIX: lo schermo va riposizionato lungo il SUO asse Y (l'altezza del
        # pannello), non lungo Z. Il bug precedente spostava il pannello lungo
        # lo spessore invece che lungo l'altezza: il bordo inferiore dello
        # schermo non combaciava mai con la cerniera, dando l'illusione di uno
        # schermo "staccato" dalla base, più evidente ad alcuni angoli di rotazione.
        glTranslatef(0.0, 0.48, 0.0)  # metà altezza schermo (1.02/2) con un piccolo incastro
        self._draw_box_shaded(1.85, 1.02, 0.055, screen_metal)

        # Bezel sottile + pannello acceso (leggero glow al centro)
        glColor4f(*NEON, 0.28)
        glBegin(GL_QUADS)
        glVertex3f(-0.80, -0.42, 0.031)
        glVertex3f(0.80, -0.42, 0.031)
        glVertex3f(0.80, 0.42, 0.031)
        glVertex3f(-0.80, 0.42, 0.031)
        glEnd()

        # Webcam
        glColor4f(0.05, 0.9, 1.0, 0.9)
        glBegin(GL_QUADS)
        s = 0.012
        glVertex3f(-s, 0.465, 0.033)
        glVertex3f(s, 0.465, 0.033)
        glVertex3f(s, 0.465 + s, 0.033)
        glVertex3f(-s, 0.465 + s, 0.033)
        glEnd()

        # Logo retro schermo
        glColor4f(*NEON, 0.95)
        glBegin(GL_QUADS)
        glVertex3f(-0.05, -0.05, -0.030)
        glVertex3f(0.05, -0.05, -0.030)
        glVertex3f(0.05, 0.05, -0.030)
        glVertex3f(-0.05, 0.05, -0.030)
        glEnd()
        glPopMatrix()

    # ------------------------------------------------------------------
    def load_external_model(self, path: str):
        """
        Punto di estensione per un vero modello .obj/.glb del laptop
        (utile una volta trasferita l'app sul Fujitsu Celsius reale).
        Richiede di integrare `PyWavefront` o una pipeline OpenGL
        moderna con VBO/shader.
        """
        raise NotImplementedError(
            "Caricamento modelli esterni non implementato in questa build."
        )
