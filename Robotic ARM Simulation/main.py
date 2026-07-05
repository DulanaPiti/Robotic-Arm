"""
╔══════════════════════════════════════════════════════════════╗
║         NEURAL NEXUS — Industrial 6-DOF Robotic Arm HMI      ║
║         Phase 1 Prototype — Apple Light Theme + Slider UX     ║
║         Target: Raspberry Pi 5 + 10.1″ 1280×800 Touch Screen  ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import json
import time
import traceback
from typing import Optional

import numpy as np

from PyQt6.QtWidgets import (
    QLineEdit,
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QCheckBox,
    QComboBox, QFrame, QGraphicsDropShadowEffect,
    QScrollArea,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

# ── Optional dependencies ─────────────────────────────────────────────────────
try:
    import pyqtgraph.opengl as gl
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    print("[WARN] pyqtgraph / PyOpenGL not installed — 3D viewport disabled.")

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("[WARN] pyserial not installed — hardware mode unavailable.")




# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN TOKENS  — Apple Light (apple.com / SF / HIG)
# ══════════════════════════════════════════════════════════════════════════════
class T:
    # Background layers
    WINDOW    = "#F5F5F7"   # outermost chrome
    CARD      = "#FFFFFF"   # floating panel surface
    INPUT_BG  = "#F5F5F7"   # subtle recessed fill
    HOVER     = "#E8E8ED"
    PRESS     = "#D2D2D7"

    # Accent
    BLUE      = "#0071E3"
    BLUE_H    = "#0077ED"   # hover
    BLUE_P    = "#006EDB"   # pressed
    GREEN     = "#34C759"
    RED       = "#FF3B30"
    ORANGE    = "#FF9500"

    # Text — HIG label hierarchy
    INK1      = "#1D1D1F"   # primary  — 100 %
    INK2      = "#86868B"   # secondary — ~52 %
    INK3      = "#C7C7CC"   # tertiary  — ~35 %

    # Borders
    BORDER    = "#E5E5EA"   # element boundary
    SEP       = "#D2D2D7"   # section separator

    # Radius
    R_SM      = "10px"
    R_MD      = "14px"
    R_LG      = "16px"
    R_XL      = "20px"
    R_PILL    = "999px"

    # ── Apple web font stack ──────────────────────────────────────────────────
    # Priority: SF Pro → system sans → Segoe UI (Windows) → Roboto → Helvetica
    FONT      = ("San Francisco", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif")

    @staticmethod
    def ipad_shadow():
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        from PyQt6.QtGui import QColor
        fx = QGraphicsDropShadowEffect()
        fx.setBlurRadius(25)
        fx.setOffset(0, 2)
        c = QColor("#000000")
        c.setAlpha(int(0.08 * 255))
        fx.setColor(c)
        return fx

    @staticmethod
    def shadow(blur: int = 28, y: int = 6, alpha: int = 16) -> QGraphicsDropShadowEffect:
        """Ambient card shadow — super-soft, barely-there."""
        fx = QGraphicsDropShadowEffect()
        fx.setBlurRadius(blur)
        c = QColor("#000000")
        c.setAlpha(alpha)
        fx.setColor(c)
        fx.setOffset(0, y)
        return fx

    @staticmethod
    def glow(color: str = "#0071E3", blur: int = 18, alpha: int = 55) -> QGraphicsDropShadowEffect:
        fx = QGraphicsDropShadowEffect()
        fx.setBlurRadius(blur)
        c = QColor(color)
        c.setAlpha(alpha)
        fx.setColor(c)
        fx.setOffset(0, 2)
        return fx

    @staticmethod
    def best_font(size: int = 11, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
        """Return a QFont from the Apple web font priority stack."""
        for family in T.FONT:
            f = QFont(family, size, weight)
            if f.exactMatch():
                return f
        # Fallback: just ask Qt for sans-serif
        f = QFont()
        f.setStyleHint(QFont.StyleHint.SansSerif)
        f.setPointSize(size)
        f.setWeight(weight)
        return f


# ── Global QSS applied to QApplication ───────────────────────────────────────
_GLOBAL_QSS = f"""
* {{
    font-family: "San Francisco", "-apple-system", "BlinkMacSystemFont", "Segoe UI", sans-serif;
    outline: 0;
}}
QMainWindow {{ background: {T.WINDOW}; }}

/* ── Slider: groove — iOS Control Center style ── */
QSlider::groove:horizontal {{
    height: 6px;
    background: #E5E5EA;
    border-radius: 3px;
    margin: 0 6px;
}}
QSlider::sub-page:horizontal {{
    background: {T.BLUE};
    border-radius: 3px;
    height: 6px;
}}
QSlider::add-page:horizontal {{
    background: #E5E5EA;
    border-radius: 3px;
    height: 6px;
}}
QSlider::handle:horizontal {{
    width: 26px;
    height: 26px;
    margin: -10px -2px;
    border-radius: 13px;
    background: {T.CARD};
    border: 1px solid #D2D2D7;
}}
QSlider::handle:horizontal:hover {{
    border: 1.5px solid #C7C7CC;
}}
QSlider::handle:horizontal:pressed {{
    background: #F0F0F2;
    border: 1.5px solid #C7C7CC;
}}

QToolTip {{
    background: {T.CARD};
    color: {T.INK1};
    border: 1px solid {T.BORDER};
    border-radius: {T.R_SM};
    padding: 4px 10px;
    font-size: 9pt;
}}
"""

SLIDER_RANGE = (-180, 180)   # degrees, default joint angle limits

# ══════════════════════════════════════════════════════════════════════════════
#  JOINT SPACE SAFETY LIMITS — Hardware-enforced per-joint boundaries
#  Format: (min_angle, max_angle) in degrees
# ══════════════════════════════════════════════════════════════════════════════
JOINT_LIMITS = [
    (-180, 180),    # θ1  Base Yaw       — full rotation
    (-10,  150),    # θ2  Shoulder Pitch  — prevent floor collision
    (-120, 120),    # θ3  Elbow Pitch     — realistic elbow range
    (-180, 180),    # θ4  Wrist Roll      — full rotation
    (-90,   90),    # θ5  Wrist Pitch     — standard wrist flex
    (-180, 180),    # θ6  Tool Roll       — full rotation
]

# Cartesian workspace safety floor (mm)
Z_FLOOR_LIMIT = 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  PROCEDURAL GEOMETRY GENERATORS
# ══════════════════════════════════════════════════════════════════════════════

# Polished aluminum finish
_COLOR_ALUMINUM = (0.75, 0.76, 0.78, 1.0)
# Apple Blue accent for end-effector
_COLOR_APPLE_BLUE = (0.00, 0.44, 0.89, 1.0)
# Darker accent for joint spheres
_COLOR_JOINT = (0.60, 0.61, 0.63, 1.0)
_COLOR_JOINT_TIP = (0.00, 0.36, 0.73, 1.0)


def create_link_mesh(radius: float, length: float, color: tuple) -> 'gl.GLMeshItem':
    """
    Generate a polished cylinder primitive along the Z-axis.
    Base at z=0, tip at z=length.
    """
    md = gl.MeshData.cylinder(rows=12, cols=24, radius=[radius, radius], length=length)
    item = gl.GLMeshItem(
        meshdata=md,
        color=color,
        shader='shaded',
        smooth=True,
        drawFaces=True,
        drawEdges=False,
    )
    item.setGLOptions('opaque')
    return item


def create_joint_sphere(radius: float, color: tuple) -> 'gl.GLMeshItem':
    """
    Generate a sphere at a joint origin for visual articulation clarity.
    """
    md = gl.MeshData.sphere(rows=12, cols=24, radius=radius)
    item = gl.GLMeshItem(
        meshdata=md,
        color=color,
        shader='shaded',
        smooth=True,
        drawFaces=True,
        drawEdges=False,
    )
    item.setGLOptions('opaque')
    return item


# ══════════════════════════════════════════════════════════════════════════════
#  PROCEDURAL KINEMATICS CONFIG — Standard 6-DOF Sequential Chain
#  Cylinders generate along Z. Translation to next joint = Z + length.
#  Joint order: Yaw → Pitch → Pitch → Roll → Pitch → Roll
# ══════════════════════════════════════════════════════════════════════════════
ROBOT_KINEMATICS_CONFIG = [
    {
        "name": "base",
        "length": 100.0,
        "radius": 45.0,
        "rotation_axis": [0, 0, 1],   # Yaw
        "color": _COLOR_ALUMINUM,
    },
    {
        "name": "shoulder",
        "length": 350.0,
        "radius": 35.0,
        "rotation_axis": [0, 1, 0],   # Pitch
        "color": _COLOR_ALUMINUM,
    },
    {
        "name": "elbow",
        "length": 300.0,
        "radius": 25.0,
        "rotation_axis": [0, 1, 0],   # Pitch
        "color": _COLOR_ALUMINUM,
    },
    {
        "name": "wrist_roll",
        "length": 60.0,
        "radius": 20.0,
        "rotation_axis": [0, 0, 1],   # Roll
        "color": _COLOR_ALUMINUM,
    },
    {
        "name": "wrist_pitch",
        "length": 60.0,
        "radius": 18.0,
        "rotation_axis": [0, 1, 0],   # Pitch
        "color": _COLOR_ALUMINUM,
    },
    {
        "name": "end_effector",
        "length": 50.0,
        "radius": 15.0,
        "rotation_axis": [0, 0, 1],   # Roll
        "color": _COLOR_APPLE_BLUE,
    },
]


def validate_posture_safety(test_angles: list) -> bool:
    """
    Pure-math FK preview — runs the kinematic chain offline to check
    if a proposed set of joint angles causes floor collision (TCP Z < 0).

    Returns True if safe (TCP Z >= 0), False if collision.
    """
    import pyqtgraph as pg

    parent_transform = pg.Transform3D()

    for i, conf in enumerate(ROBOT_KINEMATICS_CONFIG):
        global_transform = pg.Transform3D(parent_transform)

        axis = conf['rotation_axis']
        angle = test_angles[i] if i < len(test_angles) else 0.0
        global_transform.rotate(angle, axis[0], axis[1], axis[2])

        parent_transform = pg.Transform3D(global_transform)
        parent_transform.translate(0, 0, conf['length'])

    tcp_vec = parent_transform.map(pg.Vector(0, 0, 0))
    return tcp_vec.z() >= Z_FLOOR_LIMIT




# ══════════════════════════════════════════════════════════════════════════════
#  SERIAL WORKER  (QThread — logic unchanged)
# ══════════════════════════════════════════════════════════════════════════════
class SerialWorkerSignals(QObject):
    success = pyqtSignal(str)
    error   = pyqtSignal(str)
    log     = pyqtSignal(str)


class SerialWorker(QThread):
    def __init__(self, payload: str, hardware_mode: bool,
                 port: str = "COM3", baud: int = 115200):
        super().__init__()
        self.payload       = payload
        self.hardware_mode = hardware_mode
        self.port          = port
        self.baud          = baud
        self.signals       = SerialWorkerSignals()

    def run(self) -> None:
        try:
            if self.hardware_mode and SERIAL_AVAILABLE:
                self._send_hardware()
            else:
                self._send_mock()
        except Exception as exc:
            self.signals.error.emit(f"Worker exception: {exc}\n{traceback.format_exc()}")

    def _send_hardware(self) -> None:
        self.signals.log.emit(f"[HW] Opening {self.port} @ {self.baud} baud …")
        try:
            with serial.Serial(self.port, self.baud, timeout=2) as ser:
                ser.write((self.payload + "\n").encode("utf-8"))
                self.signals.log.emit(f"[HW]  TX → {self.payload}")
                ack = ser.readline().decode("utf-8", errors="replace").strip()
                self.signals.log.emit(f"[HW]  RX ← {ack or '(no ACK)'}")
            self.signals.success.emit(self.payload)
        except serial.SerialException as exc:
            self.signals.error.emit(f"Serial error: {exc}")

    def _send_mock(self) -> None:
        self.signals.log.emit("[PC]  Simulating UART TX (50 ms delay) …")
        time.sleep(0.05)
        self.signals.log.emit(f"[PC]  TX payload → {self.payload}")
        print(f"[NEURAL NEXUS MOCK TX] {self.payload}")
        self.signals.success.emit(self.payload)


# ══════════════════════════════════════════════════════════════════════════════
#  PRIMITIVES
# ══════════════════════════════════════════════════════════════════════════════

class Card(QFrame):
    """White floating card with ambient drop shadow."""
    def __init__(self, radius: str = T.R_LG, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            Card {{
                background: {T.CARD};
                border: 1px solid #EBEBF0;
                border-radius: 18px;
            }}
        """)
        self.setGraphicsEffect(T.shadow(blur=32, y=6, alpha=13))


class SectionLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setFont(T.best_font(10, QFont.Weight.DemiBold))
        self.setStyleSheet(f"""
            QLabel {{
                color: {T.INK2};
                letter-spacing: 0.8px;
                background: transparent;
            }}
        """)
        self.setContentsMargins(2, 4, 0, 8)


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet("background: #EBEBF0; border: none;")


# ══════════════════════════════════════════════════════════════════════════════
#  AXIS CONTROL ROW  — value label + slider, all inside a white card row
# ══════════════════════════════════════════════════════════════════════════════
class AxisRow(QWidget):
    """
    One self-contained row: axis badge | large value label | unit | slider.
    The slider drives the value display; the display value is the
    single source of truth for what gets sent.
    """

    value_changed = pyqtSignal(float)   # emits the new float whenever slider moves

    def __init__(self, axis: str, accent_color: str, label: str = "",
                 limits: tuple = None, parent=None):
        super().__init__(parent)
        self.axis   = axis
        self.accent = accent_color
        self._label = label or f"{axis}-Axis"
        self._limits = limits or SLIDER_RANGE
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 8, 16, 8)
        root.setSpacing(6)
        self.setMinimumHeight(65)

        # ── Top row: badge + value + unit ──────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(14)
        top.setContentsMargins(0, 0, 0, 0)

        # Axis circle badge
        self._badge = QLabel(self.axis)
        self._badge.setFixedSize(36, 36)
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setStyleSheet(f"""
            QLabel {{
                background-color: #F5F5F7;
                border: 1px solid #E5E5EA;
                border-radius: 18px;
                font-size: 14px;
                font-weight: 600;
                color: #86868B;
            }}
        """)
        top.addWidget(self._badge)

        # Large numeric value
        self._val = QLabel("0.0")
        self._val.setMinimumWidth(110)
        self._val.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._val.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                font-weight: 700;
                color: #1D1D1F;
                background: transparent;
            }}
        """)
        top.addWidget(self._val, stretch=1)

        # Sub-label
        meta = QVBoxLayout()
        meta.setSpacing(0)
        axis_lbl = QLabel(self._label)
        axis_lbl.setFont(T.best_font(9, QFont.Weight.Medium))
        axis_lbl.setStyleSheet(f"color: {T.INK2}; background: transparent;")
        unit_lbl = QLabel("deg")
        unit_lbl.setFont(T.best_font(9))
        unit_lbl.setStyleSheet(f"color: {T.INK3}; background: transparent;")
        meta.addWidget(axis_lbl)
        meta.addWidget(unit_lbl)
        top.addLayout(meta)

        root.addLayout(top)

        # ── Slider ──────────────────────────────────────────────────────────
        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)
        slider_row.setContentsMargins(0, 0, 0, 0)

        lo_lbl = QLabel(f"{self._limits[0]}°")
        lo_lbl.setFont(T.best_font(8))
        lo_lbl.setStyleSheet(f"color: {T.INK3}; background: transparent;")
        slider_row.addWidget(lo_lbl)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(self._limits[0], self._limits[1])
        # Start at 0 if within range, otherwise at midpoint
        init_val = 0 if self._limits[0] <= 0 <= self._limits[1] else (self._limits[0] + self._limits[1]) // 2
        self.slider.setValue(init_val)
        self.slider.setFixedHeight(30)
        self.slider.valueChanged.connect(self._on_slide)
        slider_row.addWidget(self.slider, stretch=1)

        hi_lbl = QLabel(f"{self._limits[1]}°")
        hi_lbl.setFont(T.best_font(8))
        hi_lbl.setStyleSheet(f"color: {T.INK3}; background: transparent;")
        slider_row.addWidget(hi_lbl)

        root.addLayout(slider_row)

    def _on_slide(self, raw: int):
        val = float(raw)
        self._val.setText(f"{val:.1f}°")
        self.value_changed.emit(val)

    # ── public API ────────────────────────────────────────────────────────────
    def get_value(self) -> float:
        return float(self.slider.value())

    def set_value(self, v: float):
        self.slider.setValue(int(round(v)))


# ══════════════════════════════════════════════════════════════════════════════
#  SEND BUTTON
# ══════════════════════════════════════════════════════════════════════════════
class SendButton(QPushButton):
    _CFG = {
        "idle":  (T.BLUE,  T.BLUE_H,  T.BLUE_P,  "#FFFFFF", "Send Coordinates"),
        "ok":    (T.GREEN, "#2EBD50", "#28A845", "#FFFFFF", "✓  Coordinates Sent"),
        "error": (T.RED,   "#FF5247", "#E5352C", "#FFFFFF", "✕  Transmission Error"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(T.best_font(15, QFont.Weight.Bold))
        self._apply("idle")

    def _apply(self, state: str):
        bg, hv, pr, fg, txt = self._CFG[state]
        self.setText(txt)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
                letter-spacing: 0.3px;
                padding: 0 28px;
            }}
            QPushButton:hover  {{ background: {hv}; }}
            QPushButton:pressed {{ background: {pr}; }}
            QPushButton:disabled {{
                background: #E5E5EA;
                color: {T.INK3};
            }}
        """)
        glow_color = {"idle": T.BLUE, "ok": T.GREEN, "error": T.RED}[state]
        self.setGraphicsEffect(T.glow(glow_color, blur=20, alpha=50))

    def set_state(self, s: str):
        self._apply(s)


# ══════════════════════════════════════════════════════════════════════════════
#  iOS-STYLE TOGGLE SWITCH
# ══════════════════════════════════════════════════════════════════════════════
class Toggle(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QCheckBox {{ spacing: 0; background: transparent; }}
            QCheckBox::indicator {{
                width: 48px; height: 28px;
                border-radius: 14px;
                background: {T.BORDER};
                border: none;
            }}
            QCheckBox::indicator:checked   {{ background: {T.GREEN}; }}
            QCheckBox::indicator:unchecked:hover {{ border: 1.5px solid {T.BLUE}; }}
        """)


# ══════════════════════════════════════════════════════════════════════════════
#  STATUS BAR
# ══════════════════════════════════════════════════════════════════════════════
class StatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setStyleSheet(f"""
            QFrame {{
                background: {T.CARD};
                border-top: 1px solid #EBEBF0;
            }}
        """)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(8)

        self._dot = QLabel("●")
        self._dot.setFont(T.best_font(8))
        self._dot.setFixedWidth(14)
        hl.addWidget(self._dot)

        self._msg = QLabel("System ready  —  PC Test Mode")
        self._msg.setFont(T.best_font(9))
        hl.addWidget(self._msg, stretch=1)

        self._clock = QLabel("--:--:--")
        self._clock.setFont(T.best_font(9))
        self._clock.setStyleSheet(f"color: {T.INK3}; background: transparent;")
        hl.addWidget(self._clock)

        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(1000)
        self._tick()
        self.log("System ready  —  PC Test Mode", "idle")

    def _tick(self):
        from datetime import datetime
        self._clock.setText(datetime.now().strftime("%H:%M:%S"))

    def log(self, msg: str, level: str = "idle"):
        dot = {"idle": T.INK3, "info": T.BLUE, "ok": T.GREEN,
               "warn": T.ORANGE, "error": T.RED}
        txt = {"idle": T.INK2, "info": T.INK1, "ok": T.GREEN,
               "warn": T.ORANGE, "error": T.RED}
        self._dot.setStyleSheet(f"color: {dot.get(level, T.INK2)}; background: transparent;")
        self._msg.setStyleSheet(f"color: {txt.get(level, T.INK2)}; background: transparent;")
        self._msg.setText(msg)


# ══════════════════════════════════════════════════════════════════════════════
#  TELEMETRY HUD
# ══════════════════════════════════════════════════════════════════════════════
class TelemetryHUD(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.move(20, 20)
        self.setStyleSheet("""
            TelemetryHUD {
                background-color: rgba(255, 255, 255, 0.85);
                border: 1px solid rgba(0, 0, 0, 0.06);
                border-radius: 14px;
            }
        """)

        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        from PyQt6.QtGui import QColor
        fx = QGraphicsDropShadowEffect()
        fx.setBlurRadius(30)
        fx.setOffset(0, 4)
        c = QColor(0, 0, 0)
        c.setAlphaF(0.12)
        fx.setColor(c)
        self.setGraphicsEffect(fx)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        def make_header(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #86868B; letter-spacing: 1px; background: transparent;")
            lbl.setContentsMargins(0, 0, 0, 4)
            return lbl

        layout.addWidget(make_header("TCP LOCATION"))

        from PyQt6.QtWidgets import QGridLayout
        tcp_grid = QGridLayout()
        tcp_grid.setContentsMargins(0, 0, 0, 0)
        tcp_grid.setSpacing(6)
        self.tcp_labels = {}
        _tcp_colors = {"X": "#FF3B30", "Y": "#34C759", "Z": "#0071E3"}
        for i, axis in enumerate(["X", "Y", "Z"]):
            lbl = QLabel(f"{axis}")
            lbl.setFont(T.best_font(13, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {_tcp_colors[axis]}; background: transparent;")

            val = QLabel("0.0")
            val.setStyleSheet(
                "font-family: 'SF Mono', Consolas, monospace; "
                "font-size: 16px; font-weight: 700; "
                f"color: {_tcp_colors[axis]}; background: transparent;"
            )
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            unit = QLabel("mm")
            unit.setStyleSheet("font-size: 10px; color: #86868B; background: transparent;")
            unit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            tcp_grid.addWidget(lbl, i, 0)
            tcp_grid.addWidget(val, i, 1)
            tcp_grid.addWidget(unit, i, 2)
            self.tcp_labels[axis] = val

        layout.addLayout(tcp_grid)
        layout.addSpacing(6)

        # ── Visual divider ──
        sep = QFrame(self)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(0, 0, 0, 0.08); border: none;")
        layout.addWidget(sep)
        layout.addSpacing(6)

        layout.addWidget(make_header("JOINT STATES"))

        joint_grid = QGridLayout()
        joint_grid.setContentsMargins(0, 0, 0, 0)
        joint_grid.setSpacing(4)
        self.joint_labels = []
        for i in range(6):
            lbl = QLabel(f"θ{i+1}")
            lbl.setFont(T.best_font(10, QFont.Weight.DemiBold))
            lbl.setStyleSheet("color: #86868B; background: transparent;")

            val = QLabel("0.0°")
            val.setStyleSheet("font-family: 'SF Mono', Consolas, monospace; font-size: 13px; color: #1D1D1F; background: transparent;")
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            joint_grid.addWidget(lbl, i, 0)
            joint_grid.addWidget(val, i, 1)
            self.joint_labels.append(val)

        layout.addLayout(joint_grid)
        layout.addStretch()

    def update_values(self, x: float, y: float, z: float, angles: list[float]):
        self.tcp_labels["X"].setText(f"{x:.1f}")
        self.tcp_labels["Y"].setText(f"{y:.1f}")
        self.tcp_labels["Z"].setText(f"{z:.1f}")
        for i, val in enumerate(angles):
            if i < len(self.joint_labels):
                self.joint_labels[i].setText(f"{val:.1f}°")

# ══════════════════════════════════════════════════════════════════════════════
#  VIEWPORT PANEL  (Right)
# ══════════════════════════════════════════════════════════════════════════════
class ViewportPanel(QFrame):
    floor_warning = pyqtSignal(float)   # emitted when TCP Z drops below floor

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            ViewportPanel {{
                background: {T.CARD};
                border-radius: 20px;
            }}
        """)

        card_vl = QVBoxLayout(self)
        card_vl.setContentsMargins(0, 0, 0, 0)
        card_vl.setSpacing(0)

        card_vl.addWidget(self._make_header())

        if OPENGL_AVAILABLE:
            self._build_gl(card_vl)
        else:
            self._build_fallback(card_vl)

        card_vl.addWidget(self._make_footer())

    def _make_header(self) -> QFrame:
        hdr = QFrame()
        hdr.setFixedHeight(54)
        hdr.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hdr.setStyleSheet(f"""
            QFrame {{
                background: {T.CARD};
                border-bottom: 1px solid #EBEBF0;
                border-top-left-radius: 18px;
                border-top-right-radius: 18px;
            }}
        """)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(10)

        title = QLabel("3D Digital Twin")
        title.setFont(T.best_font(15, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {T.INK1}; background: transparent;")
        hl.addWidget(title)
        hl.addStretch()

        badge_text = "OpenGL Live" if OPENGL_AVAILABLE else "No renderer"
        badge = QLabel(badge_text)
        badge.setFont(T.best_font(9, QFont.Weight.DemiBold))
        badge.setStyleSheet(f"""
            QLabel {{
                color: #1D8038;
                background: #E3F5E1;
                border: none;
                border-radius: 12px;
                padding: 4px 14px;
            }}
        """)
        hl.addWidget(badge)
        return hdr

    def _build_gl(self, layout: QVBoxLayout):
        import pyqtgraph as pg

        self.gl_view = gl.GLViewWidget()
        self.gl_view.setBackgroundColor(QColor("#E8E8EC"))
        self.gl_view.setCameraPosition(distance=1800, elevation=25, azimuth=45)

        # Ground grid
        grid = gl.GLGridItem()
        grid.setSize(x=2000, y=2000, z=0)
        grid.setSpacing(x=100, y=100, z=100)
        grid.setColor(QColor(160, 160, 168, 180))
        self.gl_view.addItem(grid)

        # World origin axes
        for end, rgb in [
            ((300, 0,  0), (0.90, 0.20, 0.15)),
            ((0, 300,  0), (0.15, 0.70, 0.30)),
            ((0,  0, 300), (0.00, 0.40, 0.85)),
        ]:
            self.gl_view.addItem(gl.GLLinePlotItem(
                pos=np.array([[0, 0, 0], end], dtype=float),
                color=(*rgb, 0.8), width=2.0, antialias=True,
            ))

        # ── Procedural arm construction ──────────────────────────────────────
        self._target_angles  = [0.0] * 6
        self._current_angles = [0.0] * 6
        self._link_meshes:   list[gl.GLMeshItem] = []
        self._joint_spheres: list[gl.GLMeshItem] = []

        for i, conf in enumerate(ROBOT_KINEMATICS_CONFIG):
            # Cylinder link body
            link = create_link_mesh(conf['radius'], conf['length'], conf['color'])
            self.gl_view.addItem(link)
            self._link_meshes.append(link)

            # Sphere at the joint origin
            sphere_color = _COLOR_JOINT_TIP if i == len(ROBOT_KINEMATICS_CONFIG) - 1 else _COLOR_JOINT
            sphere = create_joint_sphere(conf['radius'] * 1.15, sphere_color)
            self.gl_view.addItem(sphere)
            self._joint_spheres.append(sphere)

        # Attempt to add a directional light (not available in all pyqtgraph versions)
        try:
            light = gl.GLLight(
                direction=(1, 1, -1),
                ambient=(0.4, 0.4, 0.4, 1),
                diffuse=(0.8, 0.8, 0.8, 1),
            )
            self.gl_view.addItem(light)
        except Exception:
            pass

        # Initial pose
        self._apply_fk()

        # Render loop — ~30 fps for smooth interpolation
        self._render_timer = QTimer(self)
        self._render_timer.timeout.connect(self._apply_fk)
        self._render_timer.start(33)

        self._angle = 45.0
        self._orbit_timer = QTimer(self)
        self._orbit_timer.timeout.connect(self._orbit_tick)

        self.hud = TelemetryHUD(self.gl_view)

        # ── Floating "Recenter View" button ───────────────────────────────────
        self._recenter_btn = QPushButton("⌖  Recenter View", self.gl_view)
        self._recenter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._recenter_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.92);
                border-radius: 14px;
                font-weight: 600;
                font-size: 12px;
                color: #1D1D1F;
                padding: 6px 14px;
                border: 1px solid rgba(0, 0, 0, 0.10);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 1.0);
                border: 1px solid rgba(0, 113, 227, 0.3);
                color: #0071E3;
            }
            QPushButton:pressed {
                background-color: rgba(240, 240, 242, 1.0);
            }
        """)
        self._recenter_btn.setFixedSize(140, 32)
        self._recenter_btn.clicked.connect(self._recenter_camera)
        # Position will be set in resizeEvent of gl_view
        self._recenter_btn.move(10, 10)  # Temporary — updated in footer area

        layout.addWidget(self.gl_view, stretch=1)

    # ── Forward Kinematics: Clean Sequential Matrix Stack ─────────────────────
    def _apply_fk(self):
        """
        Render loop using a sequential Transform3D push stack.
        Each joint: rotate → apply to mesh → translate to tip → pass to next.
        Safety is enforced proactively via validate_posture_safety() at input time.
        """
        import pyqtgraph as pg

        # Smooth interpolation toward target angles
        for i in range(6):
            diff = self._target_angles[i] - self._current_angles[i]
            self._current_angles[i] += diff * 0.15

        parent_transform = pg.Transform3D()

        for i, conf in enumerate(ROBOT_KINEMATICS_CONFIG):
            # 1. Inherit the parent's global transformation
            global_transform = pg.Transform3D(parent_transform)

            # 2. Apply the live joint angle rotation at this joint's origin
            axis = conf['rotation_axis']
            global_transform.rotate(
                self._current_angles[i], axis[0], axis[1], axis[2]
            )

            # 3. Apply this transform to the visual cylinder and joint sphere
            self._link_meshes[i].setTransform(global_transform)
            self._joint_spheres[i].setTransform(global_transform)

            # 4. Translate to the tip of this cylinder for the next joint
            parent_transform = pg.Transform3D(global_transform)
            parent_transform.translate(0, 0, conf['length'])

        # Update Telemetry HUD with the TCP (tool center point) position
        if hasattr(self, 'hud'):
            tcp_vec = parent_transform.map(pg.Vector(0, 0, 0))
            self.hud.update_values(
                tcp_vec.x(), tcp_vec.y(), tcp_vec.z(), self._current_angles
            )

    def update_joints(self, angles: list):
        """Called every time a slider moves — updates all 6 target angles."""
        if not OPENGL_AVAILABLE:
            return
        for i in range(min(len(angles), 6)):
            self._target_angles[i] = angles[i]

    def _recenter_camera(self):
        """Reset the camera to a perfect isometric viewing angle."""
        self.gl_view.setCameraPosition(distance=1800, elevation=30, azimuth=45)

    def _orbit_tick(self):
        self._angle = (self._angle + 0.3) % 360
        self.gl_view.setCameraPosition(azimuth=self._angle)

    def _build_fallback(self, layout: QVBoxLayout):
        lbl = QLabel(
            "OpenGL context unavailable.\n\n"
            "pip install pyqtgraph PyOpenGL PyOpenGL_accelerate"
        )
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(T.best_font(12))
        lbl.setStyleSheet(f"color: {T.INK2}; background: transparent;")
        layout.addWidget(lbl, stretch=1)

    def _make_footer(self) -> QFrame:
        foot = QFrame()
        foot.setFixedHeight(46)
        foot.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        foot.setStyleSheet(f"""
            QFrame {{
                background: {T.CARD};
                border-top: 1px solid #EBEBF0;
                border-bottom-left-radius: 18px;
                border-bottom-right-radius: 18px;
            }}
        """)
        hl = QHBoxLayout(foot)
        hl.setContentsMargins(20, 0, 20, 0)
        hl.setSpacing(28)

        for key, val in [("DOF", "6-Axis"), ("Payload", "5 kg"), ("Reach", "850 mm")]:
            lbl = QLabel(
                f"<span style='color:{T.INK2};font-size:9pt'>{key}</span>"
                f"&nbsp;&nbsp;"
                f"<span style='color:{T.INK1};font-weight:600;font-size:10pt'>{val}</span>"
            )
            lbl.setStyleSheet("background: transparent;")
            hl.addWidget(lbl)

        hl.addStretch()

        if OPENGL_AVAILABLE:
            self._orbit_btn = QPushButton("⟳  Orbit")
            self._orbit_btn.setFixedSize(84, 30)
            self._orbit_btn.setCheckable(True)
            self._orbit_btn.setFont(T.best_font(9))
            self._orbit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._orbit_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {T.INPUT_BG};
                    color: {T.INK2};
                    border: 1px solid {T.BORDER};
                    border-radius: {T.R_PILL};
                    padding: 0 12px;
                }}
                QPushButton:hover {{ background: {T.HOVER}; color: {T.INK1}; }}
                QPushButton:checked {{
                    background: {T.BLUE}18;
                    color: {T.BLUE};
                    border-color: {T.BLUE}55;
                }}
            """)
            self._orbit_btn.toggled.connect(
                lambda on: self._orbit_timer.start(30) if on else self._orbit_timer.stop()
            )
            hl.addWidget(self._orbit_btn)

        return foot

    def update_target(self, x: float, y: float, z: float):
        """Legacy — kept for serial send preview."""
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  LEFT CONTROL PANEL
# ══════════════════════════════════════════════════════════════════════════════
class AppleLineEdit(QLineEdit):
    def __init__(self, placeholder=""):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(T.best_font(24, QFont.Weight.Bold))
        self.setMaximumHeight(60)
        self.setStyleSheet(f"""
            QLineEdit {{
                background: #FFFFFF;
                color: #1D1D1F;
                border: 2px solid #E5E5EA;
                border-radius: 16px;
                padding: 10px 15px;
                font-size: 24px;
                font-weight: 600;
            }}
            QLineEdit:focus {{
                border: 2px solid {T.BLUE};
            }}
        """)

class ExecuteButton(QPushButton):
    _QSS_NORMAL = f"""
        QPushButton {{
            background: {T.BLUE};
            color: #FFFFFF;
            border: none;
            border-radius: 14px;
            letter-spacing: 0.5px;
        }}
        QPushButton:hover {{ background: {T.BLUE_H}; }}
        QPushButton:pressed {{ background: {T.BLUE_P}; }}
    """
    _QSS_COLLISION = f"""
        QPushButton {{
            background: {T.RED};
            color: #FFFFFF;
            border: none;
            border-radius: 14px;
            letter-spacing: 0.5px;
        }}
    """
    _QSS_WARNING = f"""
        QPushButton {{
            background: #FF9500;
            color: #FFFFFF;
            border: none;
            border-radius: 14px;
            letter-spacing: 0.5px;
        }}
    """

    def __init__(self):
        super().__init__("Execute Trajectory")
        self.setFixedHeight(54)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(T.best_font(15, QFont.Weight.DemiBold))
        self._apply_normal()

    def _apply_normal(self):
        self.setText("Execute Trajectory")
        self.setStyleSheet(self._QSS_NORMAL)
        self.setGraphicsEffect(T.glow(T.BLUE, blur=15, alpha=60))

    def flash_collision(self):
        """Flash red to indicate collision rejection, auto-revert after 1.5s."""
        self.setText("⚠  Collision Detected!")
        self.setStyleSheet(self._QSS_COLLISION)
        self.setGraphicsEffect(T.glow(T.RED, blur=15, alpha=60))
        QTimer.singleShot(1500, self._apply_normal)

    def flash_out_of_reach(self):
        """Flash red to indicate unreachable target."""
        self.setText("⚠  Out of Reach!")
        self.setStyleSheet(self._QSS_COLLISION)
        self.setGraphicsEffect(T.glow(T.RED, blur=15, alpha=60))
        QTimer.singleShot(1500, self._apply_normal)

    def flash_local_minima(self):
        """Flash orange to indicate local minima entrapment."""
        self.setText("⚠  IK Failed (Local Minima)!")
        self.setStyleSheet(self._QSS_WARNING)
        self.setGraphicsEffect(T.glow("#FF9500", blur=15, alpha=60))
        QTimer.singleShot(1500, self._apply_normal)

    def flash_too_close(self):
        """Flash orange to indicate target is within the inner deadzone."""
        self.setText("⚠  Target Too Close!")
        self.setStyleSheet(self._QSS_WARNING)
        self.setGraphicsEffect(T.glow("#FF9500", blur=15, alpha=60))
        QTimer.singleShot(1500, self._apply_normal)

class SegmentedControl(QFrame):
    toggled = pyqtSignal(int)
    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            SegmentedControl {
                background: #E5E5EA;
                border-radius: 16px;
            }
        """)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(2, 2, 2, 2)
        hl.setSpacing(0)

        self.btns = []
        for i, lbl in enumerate(labels):
            btn = QPushButton(lbl)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #86868B;
                    font-weight: 600;
                    font-size: 13px;
                    border: none;
                    border-radius: 14px;
                }
                QPushButton:checked {
                    background: #FFFFFF;
                    color: #1D1D1F;
                }
            """)
            btn.clicked.connect(lambda checked, idx=i: self._on_btn_clicked(idx))
            self.btns.append(btn)
            hl.addWidget(btn)
        
        if self.btns:
            self.btns[0].setChecked(True)
            self.btns[0].setGraphicsEffect(T.shadow(blur=8, y=2, alpha=20))

    def _on_btn_clicked(self, idx):
        for i, btn in enumerate(self.btns):
            if i == idx:
                btn.setChecked(True)
                btn.setGraphicsEffect(T.shadow(blur=8, y=2, alpha=20))
            else:
                btn.setChecked(False)
                btn.setGraphicsEffect(None)
        self.toggled.emit(idx)

class ControlPanel(QFrame):
    send_requested = pyqtSignal(float, float, float, bool, str)
    execute_requested = pyqtSignal(float, float, float, bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(440)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            ControlPanel {{
                background: {T.CARD};
                border-radius: 20px;
            }}
        """)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── App header bar ────────────────────────────────────────────────────
        root.addWidget(self._make_header())

        # ── Scrollable body with Segmented Selection ─────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
                margin: 4px 1px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 0, 0, 0.15);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0, 0, 0, 0.25);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        body = QWidget()
        body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        body.setStyleSheet("background: transparent;")

        inner = QVBoxLayout(body)
        inner.setContentsMargins(24, 20, 24, 20)
        inner.setSpacing(16)

        # iOS-Style Segmented Control
        self.segmented = SegmentedControl(["Joint Control", "Cartesian Target"])
        inner.addWidget(self.segmented)

        from PyQt6.QtWidgets import QStackedWidget
        self.stack = QStackedWidget()
        self.segmented.toggled.connect(self.stack.setCurrentIndex)
        inner.addWidget(self.stack, stretch=1)

        # ── Joint Control Card ─────────────────────────────────────────────────
        self.joint_tab = QWidget()
        joint_layout = QVBoxLayout(self.joint_tab)
        joint_layout.setContentsMargins(0, 6, 0, 0)
        joint_layout.setSpacing(2)

        self.ax1 = AxisRow("θ₁", accent_color=T.RED,    label="Base Yaw",       limits=JOINT_LIMITS[0])
        self.ax2 = AxisRow("θ₂", accent_color=T.GREEN,  label="Shoulder Pitch", limits=JOINT_LIMITS[1])
        self.ax3 = AxisRow("θ₃", accent_color=T.BLUE,   label="Elbow Pitch",    limits=JOINT_LIMITS[2])
        self.ax4 = AxisRow("θ₄", accent_color=T.ORANGE, label="Wrist Roll",     limits=JOINT_LIMITS[3])
        self.ax5 = AxisRow("θ₅", accent_color=T.GREEN,  label="Wrist Pitch",    limits=JOINT_LIMITS[4])
        self.ax6 = AxisRow("θ₆", accent_color=T.BLUE,   label="Tool Roll",      limits=JOINT_LIMITS[5])

        self.joint_axes = [self.ax1, self.ax2, self.ax3, self.ax4, self.ax5, self.ax6]

        for i, ax in enumerate(self.joint_axes):
            joint_layout.addWidget(ax)
            if i < len(self.joint_axes) - 1:
                joint_layout.addWidget(Divider())

        self.send_btn = SendButton()
        self.send_btn.clicked.connect(self._on_send)
        joint_layout.addWidget(self.send_btn)

        self.stack.addWidget(self.joint_tab)

        # ── Cartesian Control Card ─────────────────────────────────────────────
        self.cartesian_tab = QWidget()
        cartesian_layout = QVBoxLayout(self.cartesian_tab)
        cartesian_layout.setContentsMargins(0, 10, 0, 0)
        cartesian_layout.setSpacing(20)

        from PyQt6.QtWidgets import QLineEdit
        self.x_input = AppleLineEdit("X Target (mm)")
        self.y_input = AppleLineEdit("Y Target (mm)")
        self.z_input = AppleLineEdit("Z Target (mm)")

        cartesian_layout.addWidget(self.x_input)
        cartesian_layout.addWidget(self.y_input)
        cartesian_layout.addWidget(self.z_input)

        self.exec_btn = ExecuteButton()
        self.exec_btn.clicked.connect(self._on_execute_trajectory)
        cartesian_layout.addWidget(self.exec_btn)

        cartesian_layout.addStretch()

        self.stack.addWidget(self.cartesian_tab)

        # ── Serial and Global Send ────────────────────────────────────────────
        inner.addWidget(Divider())
        inner.addWidget(self._make_serial())

        scroll.setWidget(body)
        root.addWidget(scroll, stretch=1)

    # ── Header ────────────────────────────────────────────────────────────────
    @staticmethod
    def _make_header() -> QFrame:
        hdr = QFrame()
        hdr.setFixedHeight(72)
        hdr.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hdr.setStyleSheet(f"""
            QFrame {{
                background: transparent;
            }}
        """)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(22, 0, 22, 0)
        hl.setSpacing(0)

        vl = QVBoxLayout()
        vl.setSpacing(2)

        name = QLabel("Neural Nexus")
        name.setFont(T.best_font(20, QFont.Weight.Bold))
        name.setStyleSheet(f"color: {T.INK1}; background: transparent;")
        vl.addWidget(name)

        sub = QLabel("6-DOF Robotic Arm  ·  HMI Control Interface")
        sub.setFont(T.best_font(9))
        sub.setStyleSheet(f"color: {T.INK2}; background: transparent;")
        vl.addWidget(sub)

        hl.addLayout(vl)
        hl.addStretch()

        pill = QLabel("● Connected")
        pill.setFont(T.best_font(9, QFont.Weight.DemiBold))
        pill.setStyleSheet(f"""
            QLabel {{
                color: #1D8038;
                background: #E3F5E1;
                border: none;
                border-radius: 12px;
                padding: 4px 14px;
            }}
        """)
        hl.addWidget(pill)
        return hdr

    @staticmethod
    def _section(text: str) -> SectionLabel:
        return SectionLabel(text)

    # ── Serial config ─────────────────────────────────────────────────────────
    def _make_serial(self) -> QWidget:
        card = QWidget()
        vl = QVBoxLayout(card)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(16)

        # HW toggle row
        row1 = QHBoxLayout()
        row1.setSpacing(0)
        
        lbl_v = QVBoxLayout()
        lbl_v.setSpacing(2)
        hw_lbl = QLabel("Hardware Mode (UART)")
        hw_lbl.setFont(T.best_font(12, QFont.Weight.DemiBold))
        hw_lbl.setStyleSheet(f"color: {T.INK1}; background: transparent;")
        lbl_v.addWidget(hw_lbl)
        
        self.hw_hint = QLabel("PC Test Mode — no hardware required")
        self.hw_hint.setFont(T.best_font(10))
        self.hw_hint.setStyleSheet(f"color: {T.GREEN}; background: transparent;")
        lbl_v.addWidget(self.hw_hint)
        
        row1.addLayout(lbl_v)
        row1.addStretch()
        
        self.hw_toggle = Toggle()
        self.hw_toggle.toggled.connect(self._on_hw_toggle)
        row1.addWidget(self.hw_toggle)
        
        vl.addLayout(row1)

        # Port row
        self.port_row = QWidget()
        self.port_row.setStyleSheet("background: transparent;")
        pr = QHBoxLayout(self.port_row)
        pr.setContentsMargins(0, 0, 0, 0)
        pr.setSpacing(12)

        pl = QLabel("COM Port")
        pl.setFont(T.best_font(11))
        pl.setStyleSheet(f"color: {T.INK2}; background: transparent;")
        pr.addWidget(pl)

        from PyQt6.QtWidgets import QComboBox
        self.port_combo = QComboBox()
        self.port_combo.setFont(T.best_font(11))
        self.port_combo.setFixedHeight(40)
        self.port_combo.setStyleSheet(f"""
            QComboBox {{
                background: #F5F5F7;
                color: {T.INK1};
                border: 1px solid {T.SEP};
                border-radius: 8px;
                padding: 0 16px;
                min-width: 120px;
            }}
            QComboBox:focus {{ border: 1.5px solid {T.BLUE}; }}
            QComboBox::drop-down {{ border: none; width: 0px; }}
            QComboBox QAbstractItemView {{
                background: {T.CARD};
                color: {T.INK1};
                border: 1px solid {T.SEP};
                selection-background-color: {T.BLUE}22;
                selection-color: {T.BLUE};
                outline: 0;
            }}
        """)
        self._refresh_ports()
        pr.addWidget(self.port_combo, stretch=1)

        ref = QPushButton("↺")
        ref.setFixedSize(40, 40)
        ref.setFont(T.best_font(14))
        ref.setCursor(Qt.CursorShape.PointingHandCursor)
        ref.setToolTip("Refresh port list")
        ref.setStyleSheet(f"""
            QPushButton {{
                background: #F5F5F7;
                color: {T.INK2};
                border: 1px solid {T.SEP};
                border-radius: 8px;
            }}
            QPushButton:hover {{ background: {T.HOVER}; color: {T.INK1}; }}
        """)
        ref.clicked.connect(self._refresh_ports)
        pr.addWidget(ref)

        self.port_row.setVisible(False)
        vl.addWidget(self.port_row)

        baud = QLabel("115,200 baud  ·  JSON over UART  ·  8N1")
        baud.setFont(T.best_font(9))
        baud.setStyleSheet(f"color: {T.INK3}; background: transparent;")
        vl.addWidget(baud)

        return card

    # ── Handlers ──────────────────────────────────────────────────────────────
    def _on_hw_toggle(self, checked: bool):
        self.port_row.setVisible(checked)
        if checked and not SERIAL_AVAILABLE:
            self.hw_hint.setText("⚠  pyserial not installed")
            self.hw_hint.setStyleSheet(f"color: {T.RED}; background: transparent;")
        elif checked:
            self.hw_hint.setText("Hardware Mode  —  UART enabled")
            self.hw_hint.setStyleSheet(f"color: {T.ORANGE}; background: transparent;")
        else:
            self.hw_hint.setText("PC Test Mode  —  no hardware required")
            self.hw_hint.setStyleSheet(f"color: {T.GREEN}; background: transparent;")

    def _refresh_ports(self):
        self.port_combo.clear()
        if SERIAL_AVAILABLE:
            from serial.tools import list_ports
            ports = [p.device for p in list_ports.comports()]
            self.port_combo.addItems(ports if ports else ["No ports found"])
        else:
            self.port_combo.addItem("pyserial not installed")

    def _on_send(self):
        self.send_btn.setEnabled(False)
        hw   = self.hw_toggle.isChecked()
        port = self.port_combo.currentText() if hw else "COM3"
        self.send_requested.emit(
            self.ax1.get_value(),
            self.ax2.get_value(),
            self.ax3.get_value(),
            hw, port,
        )

    def _on_execute_trajectory(self):
        self.exec_btn.setEnabled(False)
        hw   = self.hw_toggle.isChecked()
        port = self.port_combo.currentText() if hw else "COM3"
        try:
            x = float(self.x_input.text() or 0.0)
            y = float(self.y_input.text() or 0.0)
            z = float(self.z_input.text() or 0.0)
        except ValueError:
            x, y, z = 0.0, 0.0, 0.0

        # ── Z-floor safety clamping ───────────────────────────────────────────
        if z < Z_FLOOR_LIMIT:
            z = Z_FLOOR_LIMIT
            self.z_input.setText(f"{z:.1f}")
            # Flash the Z input red briefly to indicate safety intervention
            self.z_input.setStyleSheet(f"""
                QLineEdit {{
                    background: #FFFFFF;
                    color: {T.RED};
                    border: 2px solid {T.RED};
                    border-radius: 16px;
                    padding: 10px 15px;
                    font-size: 24px;
                    font-weight: 600;
                }}
            """)
            # Restore normal styling after 1.5 seconds
            QTimer.singleShot(1500, lambda: self.z_input.setStyleSheet(f"""
                QLineEdit {{
                    background: #FFFFFF;
                    color: #1D1D1F;
                    border: 2px solid #E5E5EA;
                    border-radius: 16px;
                    padding: 10px 15px;
                    font-size: 24px;
                    font-weight: 600;
                }}
                QLineEdit:focus {{
                    border: 2px solid {T.BLUE};
                }}
            """))

        self.execute_requested.emit(x, y, z, hw, port)
        QTimer.singleShot(1500, lambda: self.exec_btn.setEnabled(True))

    # ── Public callbacks from main window ─────────────────────────────────────
    def on_send_success(self):
        self.send_btn.set_state("ok")
        QTimer.singleShot(2500, lambda: (
            self.send_btn.set_state("idle"),
            self.send_btn.setEnabled(True),
        ))

    def on_send_error(self):
        self.send_btn.set_state("error")
        QTimer.singleShot(3000, lambda: (
            self.send_btn.set_state("idle"),
            self.send_btn.setEnabled(True),
        ))

# (_make_box is defined above in the STL Loader section)



# ══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class NeuralNexusHMI(QMainWindow):
    def __init__(self):
        super().__init__()
        self._worker: Optional[SerialWorker] = None
        self._setup_window()
        self._build_ui()
        self.control_panel.send_requested.connect(self._on_send)
        self.control_panel.execute_requested.connect(self._on_execute)
        self._wire_sliders()
        # Connect floor warning from viewport to status bar
        self.viewport_panel.floor_warning.connect(self._on_floor_warning)

    def _setup_window(self):
        self.setWindowTitle("Neural Nexus  —  6-DOF Robotic Arm")
        self.setFixedSize(1280, 800)

        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window,        QColor(T.WINDOW))
        pal.setColor(QPalette.ColorRole.WindowText,    QColor(T.INK1))
        pal.setColor(QPalette.ColorRole.Base,          QColor(T.CARD))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor(T.INPUT_BG))
        pal.setColor(QPalette.ColorRole.Text,          QColor(T.INK1))
        pal.setColor(QPalette.ColorRole.Button,        QColor(T.INPUT_BG))
        pal.setColor(QPalette.ColorRole.ButtonText,    QColor(T.INK1))
        pal.setColor(QPalette.ColorRole.Highlight,     QColor(T.BLUE))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        self.setPalette(pal)
        self.setStyleSheet(_GLOBAL_QSS)

    def _build_ui(self):
        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        central.setStyleSheet(f"background: {T.WINDOW};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(20)

        self.control_panel  = ControlPanel()
        self.control_panel.setGraphicsEffect(T.ipad_shadow())

        self.viewport_panel = ViewportPanel()
        self.viewport_panel.setGraphicsEffect(T.ipad_shadow())

        content.addWidget(self.control_panel)
        content.addWidget(self.viewport_panel, stretch=1)

        self.status_bar = StatusBar()
        self.status_bar.setGraphicsEffect(T.ipad_shadow())
        self.status_bar.setStyleSheet(f"""
            QFrame {{
                background: {T.CARD};
                border-radius: 14px;
            }}
        """)

        root.addLayout(content, stretch=1)
        root.addWidget(self.status_bar)

    def _wire_sliders(self):
        """Connect all 6 slider value_changed → FK engine with live collision guard."""
        cp = self.control_panel
        vp = self.viewport_panel

        # Store last known safe angles for rollback
        self._last_safe_angles = [ax.get_value() for ax in cp.joint_axes]

        def _update_fk(_=None):
            proposed_angles = [ax.get_value() for ax in cp.joint_axes]

            if validate_posture_safety(proposed_angles):
                # Safe — accept and update
                self._last_safe_angles = proposed_angles[:]
                vp.update_joints(proposed_angles)
            else:
                # Collision — rollback all sliders to last safe state
                for i, ax in enumerate(cp.joint_axes):
                    ax.slider.blockSignals(True)
                    ax.slider.setValue(int(round(self._last_safe_angles[i])))
                    ax.slider.blockSignals(False)
                    ax._val.setText(f"{self._last_safe_angles[i]:.1f}°")
                vp.update_joints(self._last_safe_angles)
                self.status_bar.log(
                    "⚠  Floor collision prevented — slider reverted", "warn"
                )

        for ax in cp.joint_axes:
            ax.value_changed.connect(_update_fk)

    def _ik_objective_function(self, test_angles, target_xyz):
        """
        Calculates the Euclidean distance between the target coordinates and
        the end-effector position produced by the test angles.
        """
        import pyqtgraph as pg
        import math

        parent_transform = pg.Transform3D()

        for i, conf in enumerate(ROBOT_KINEMATICS_CONFIG):
            global_transform = pg.Transform3D(parent_transform)
            axis = conf['rotation_axis']
            angle = test_angles[i] if i < len(test_angles) else 0.0
            global_transform.rotate(angle, axis[0], axis[1], axis[2])

            parent_transform = pg.Transform3D(global_transform)
            parent_transform.translate(0, 0, conf['length'])

        tcp_vec = parent_transform.map(pg.Vector(0, 0, 0))
        tx, ty, tz = tcp_vec.x(), tcp_vec.y(), tcp_vec.z()
        return math.sqrt((tx - target_xyz[0])**2 + (ty - target_xyz[1])**2 + (tz - target_xyz[2])**2)

    def calculate_inverse_kinematics(self, x: float, y: float, z: float):
        """
        Optimization-based Inverse Kinematics solver with multi-seed fallback
        loop to prevent local minima entrapment.
        """
        import scipy.optimize
        import numpy as np

        target_xyz = np.array([x, y, z])
        current_angles = [ax.get_value() for ax in self.control_panel.joint_axes]

        # Multi-Seed initial guesses
        seed_postures = [
            current_angles,                                  # 1. Best for small movements
            [0.0, 45.0, 90.0, 0.0, 45.0, 0.0],               # 2. Neutral/Forward
            [0.0, 120.0, -120.0, 0.0, 90.0, 0.0],            # 3. Tightly Folded
            [180.0, -45.0, -90.0, 0.0, -45.0, 0.0]           # 4. Overhead/Flipped
        ]

        best_err = float('inf')
        best_angles = current_angles

        for seed in seed_postures:
            res = scipy.optimize.minimize(
                self._ik_objective_function,
                x0=seed,
                args=(target_xyz,),
                method='SLSQP',
                bounds=JOINT_LIMITS,
                tol=1e-3,
                options={'maxiter': 200, 'ftol': 1e-4}
            )
            
            err = self._ik_objective_function(res.x, target_xyz)
            
            if err < 2.0:
                # We found a valid solution, break early!
                return [float(a) for a in res.x], err
            
            # Keep track of the best one we found just in case all fail
            if err < best_err:
                best_err = err
                best_angles = res.x
                
        # If all local seeds failed, execute the global optimizer fallback
        if best_err >= 2.0:
            from scipy.optimize import differential_evolution
            global_result = differential_evolution(
                self._ik_objective_function,
                bounds=JOINT_LIMITS,
                args=(target_xyz,),
                maxiter=100,
                popsize=10,
                tol=1e-3
            )
            global_err = self._ik_objective_function(global_result.x, target_xyz)
            if global_err < best_err:
                best_err = global_err
                best_angles = global_result.x

        # Return the best one we got for the UI validation to accept or reject
        return [float(a) for a in best_angles], best_err

    def _on_floor_warning(self, tcp_z: float):
        """Handle floor collision warning from the FK engine."""
        self.status_bar.log(
            f"⚠  Floor boundary — TCP Z = {tcp_z:.1f} mm (clamped)", "warn"
        )

    def _on_execute(self, x: float, y: float, z: float, hw: bool, port: str):
        import math
        
        # 0. The Maximum Reach Sphere and Inner Deadzone (Reachability Checks)
        target_distance = math.sqrt(x**2 + y**2 + z**2)
        max_reach = sum(conf['length'] for conf in ROBOT_KINEMATICS_CONFIG)
        MIN_REACH = 250.0  # Physical constraint preventing self-collision folding

        if target_distance > max_reach:
            self.control_panel.exec_btn.flash_out_of_reach()
            self.status_bar.log(
                f"⚠  Target is physically unreachable ({target_distance:.1f} > {max_reach:.1f} mm)",
                "error"
            )
            QTimer.singleShot(1500, lambda: self.control_panel.exec_btn.setEnabled(True))
            return

        if target_distance < MIN_REACH:
            self.control_panel.exec_btn.flash_too_close()
            self.status_bar.log(
                f"⚠  Target is within Inner Deadzone ({target_distance:.1f} < {MIN_REACH:.1f} mm)",
                "error"
            )
            QTimer.singleShot(1500, lambda: self.control_panel.exec_btn.setEnabled(True))
            return

        # 1. Numerical Inverse Kinematics (optimization based)
        proposed, final_error = self.calculate_inverse_kinematics(x, y, z)

        # 2. Strict IK Validation (Error Tolerance)
        if final_error >= 2.0:
            self.control_panel.exec_btn.flash_local_minima()
            self.status_bar.log(
                f"⚠  IK Failed — trapped in local minima (Error = {final_error:.1f} mm)",
                "error"
            )
            QTimer.singleShot(1500, lambda: self.control_panel.exec_btn.setEnabled(True))
            return

        # 3. FK Guardrail — validate before committing
        if not validate_posture_safety(proposed):
            # REJECTED: collision detected
            self.control_panel.exec_btn.flash_collision()
            self.status_bar.log(
                f"⚠  IK solution rejected — TCP would collide with floor (Z < {Z_FLOOR_LIMIT})",
                "error"
            )
            QTimer.singleShot(1500, lambda: self.control_panel.exec_btn.setEnabled(True))
            return

        # 4. SAFE: Apply angles to sliders and 3D view
        self.control_panel.ax1.set_value(proposed[0])
        self.control_panel.ax2.set_value(proposed[1])
        self.control_panel.ax3.set_value(proposed[2])
        self.control_panel.ax4.set_value(proposed[3])
        self.control_panel.ax5.set_value(proposed[4])
        self.control_panel.ax6.set_value(proposed[5])

        self._last_safe_angles = proposed[:]
        self.viewport_panel.update_joints(proposed)

        payload = json.dumps({
            "target_x": round(x, 2), "target_y": round(y, 2), "target_z": round(z, 2),
            "theta1": round(proposed[0], 2), "theta2": round(proposed[1], 2), "theta3": round(proposed[2], 2)
        })
        mode = f"HW ({port})" if hw else "PC Mock"
        self.status_bar.log(f"TX [{mode}] Cartesian Target → {payload}", "info")

        self._worker = SerialWorker(payload, hw, port)
        self._worker.signals.success.connect(self._tx_ok)
        self._worker.signals.error.connect(self._tx_err)
        self._worker.start()

    def _on_send(self, x: float, y: float, z: float, hw: bool, port: str):
        payload = json.dumps({
            "theta1": round(x, 2),
            "theta2": round(y, 2),
            "theta3": round(z, 2),
        })
        mode = f"HW ({port})" if hw else "PC Mock"
        self.status_bar.log(f"TX [{mode}]  →  {payload}", "info")

        self._worker = SerialWorker(payload, hw, port)
        self._worker.signals.success.connect(self._tx_ok)
        self._worker.signals.error  .connect(self._tx_err)
        self._worker.start()

        angles = [ax.get_value() for ax in self.control_panel.joint_axes]
        self.viewport_panel.update_joints(angles)

    def _tx_ok(self, payload: str):
        self.status_bar.log(f"Transmitted  ✓  {payload}", "ok")
        self.control_panel.on_send_success()

    def _tx_err(self, msg: str):
        self.status_bar.log(f"Error  —  {msg}", "error")
        self.control_panel.on_send_error()

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.wait(2000)
        event.accept()


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Neural Nexus HMI")
    app.setOrganizationName("NeuralNexus Robotics")

    # Try the Apple font stack in priority order
    base_font = T.best_font(11)
    app.setFont(base_font)

    w = NeuralNexusHMI()
    w.show()
    w.raise_()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
