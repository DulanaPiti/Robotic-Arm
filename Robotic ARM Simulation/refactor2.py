import sys
import re

with open("main.py", "r", encoding="utf-8") as f:
    text = f.read()

# Replace ControlPanel
cp_old_start = "class ControlPanel(QFrame):"
cp_old_end = "# (_make_box is defined above in the STL Loader section)"
cp_old_pattern = re.compile(re.escape(cp_old_start) + r".*?" + re.escape(cp_old_end), re.DOTALL)

cp_new = '''class AppleLineEdit(QLineEdit):
    def __init__(self, placeholder=""):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(T.best_font(28, QFont.Weight.Bold))
        self.setFixedHeight(72)
        self.setStyleSheet(f"""
            QLineEdit {{
                background: #FFFFFF;
                color: #1D1D1F;
                border: 2px solid #E5E5EA;
                border-radius: 16px;
                padding: 4px;
            }}
            QLineEdit:focus {{
                border: 2px solid {T.BLUE};
            }}
        """)

class ExecuteButton(QPushButton):
    def __init__(self):
        super().__init__("Execute Trajectory")
        self.setFixedHeight(54)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(T.best_font(15, QFont.Weight.DemiBold))
        self.setStyleSheet(f"""
            QPushButton {{
                background: {T.BLUE};
                color: #FFFFFF;
                border: none;
                border-radius: 14px;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{ background: {T.BLUE_H}; }}
            QPushButton:pressed {{ background: {T.BLUE_P}; }}
        """)
        self.setGraphicsEffect(T.glow(T.BLUE, blur=15, alpha=60))

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

        # ── Body with Tab Selection ───────────────────────────────────────────
        body = QWidget()
        body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        body.setStyleSheet("background: transparent;")
        
        inner = QVBoxLayout(body)
        inner.setContentsMargins(20, 20, 20, 20)
        inner.setSpacing(16)
        
        # iOS-Style Tab Widget
        from PyQt6.QtWidgets import QTabWidget
        self.tabs = QTabWidget()
        self.tabs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: {T.INPUT_BG};
                color: {T.INK2};
                padding: 10px 0px;
                width: 190px;
                font-family: "{T.FONT[0]}", -apple-system, sans-serif;
                font-weight: 600;
                font-size: 13px;
                border-radius: 12px;
                margin-right: 8px;
                margin-bottom: 12px;
            }}
            QTabBar::tab:selected {{
                background: {T.BLUE};
                color: #FFFFFF;
            }}
        """)
        
        # ── Joint Control Tab ─────────────────────────────────────────────────
        self.joint_tab = QWidget()
        joint_layout = QVBoxLayout(self.joint_tab)
        joint_layout.setContentsMargins(0, 0, 0, 0)
        joint_layout.setSpacing(12)
        
        self.axX = AxisRow("θ₁", accent_color=T.RED,    label="Base Rotation")
        self.axY = AxisRow("θ₂", accent_color=T.GREEN,  label="Shoulder Pitch")
        self.axZ = AxisRow("θ₃", accent_color=T.BLUE,   label="Elbow Pitch")

        joint_layout.addWidget(self.axX)
        joint_layout.addWidget(Divider())
        joint_layout.addWidget(self.axY)
        joint_layout.addWidget(Divider())
        joint_layout.addWidget(self.axZ)
        joint_layout.addStretch()

        self.send_btn = SendButton()
        self.send_btn.clicked.connect(self._on_send)
        joint_layout.addWidget(self.send_btn)

        self.tabs.addTab(self.joint_tab, "Joint Control")
        
        # ── Cartesian Control Tab ─────────────────────────────────────────────
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
        
        self.tabs.addTab(self.cartesian_tab, "Cartesian Target")
        
        inner.addWidget(self.tabs, stretch=1)
        
        # ── Serial and Global Send ────────────────────────────────────────────
        inner.addWidget(Divider())
        inner.addWidget(self._make_serial())
        
        root.addWidget(body, stretch=1)

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
        vl.setSpacing(12)

        # HW toggle
        row1 = QHBoxLayout()
        row1.setSpacing(0)
        hw_lbl = QLabel("Hardware Mode  (UART)")
        hw_lbl.setFont(T.best_font(11))
        hw_lbl.setStyleSheet(f"color: {T.INK1}; background: transparent;")
        row1.addWidget(hw_lbl, stretch=1)
        self.hw_toggle = Toggle()
        self.hw_toggle.toggled.connect(self._on_hw_toggle)
        row1.addWidget(self.hw_toggle)
        vl.addLayout(row1)

        self.hw_hint = QLabel("PC Test Mode  —  no hardware required")
        self.hw_hint.setFont(T.best_font(9))
        self.hw_hint.setStyleSheet(f"color: {T.GREEN}; background: transparent;")
        vl.addWidget(self.hw_hint)

        # Port row
        self.port_row = QWidget()
        self.port_row.setStyleSheet("background: transparent;")
        pr = QHBoxLayout(self.port_row)
        pr.setContentsMargins(0, 0, 0, 0)
        pr.setSpacing(8)

        pl = QLabel("COM Port")
        pl.setFont(T.best_font(10))
        pl.setStyleSheet(f"color: {T.INK2}; background: transparent;")
        pr.addWidget(pl)

        from PyQt6.QtWidgets import QComboBox
        self.port_combo = QComboBox()
        self.port_combo.setFont(T.best_font(10))
        self.port_combo.setFixedHeight(36)
        self.port_combo.setStyleSheet(f"""
            QComboBox {{
                background: {T.INPUT_BG};
                color: {T.INK1};
                border: 1px solid {T.BORDER};
                border-radius: {T.R_SM};
                padding: 0 12px;
                min-width: 110px;
            }}
            QComboBox:focus {{ border: 1.5px solid {T.BLUE}; }}
            QComboBox::drop-down {{ border: none; width: 22px; }}
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
        ref.setFixedSize(36, 36)
        ref.setFont(T.best_font(13))
        ref.setCursor(Qt.CursorShape.PointingHandCursor)
        ref.setToolTip("Refresh port list")
        ref.setStyleSheet(f"""
            QPushButton {{
                background: {T.INPUT_BG};
                color: {T.INK2};
                border: 1px solid {T.BORDER};
                border-radius: {T.R_SM};
            }}
            QPushButton:hover {{ background: {T.HOVER}; color: {T.INK1}; }}
        """)
        ref.clicked.connect(self._refresh_ports)
        pr.addWidget(ref)

        self.port_row.setVisible(False)
        vl.addWidget(self.port_row)

        baud = QLabel("115,200 baud  ·  JSON over UART  ·  8N1")
        baud.setFont(T.best_font(8))
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
            self.axX.get_value(),
            self.axY.get_value(),
            self.axZ.get_value(),
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
'''

text = cp_old_pattern.sub(cp_new, text)

# Now replace NeuralNexusHMI
n_old_start = "class NeuralNexusHMI(QMainWindow):"
n_old_end = "if __name__ == \"__main__\":"
n_old_pattern = re.compile(re.escape(n_old_start) + r".*?" + re.escape(n_old_end), re.DOTALL)

n_new = '''class NeuralNexusHMI(QMainWindow):
    def __init__(self):
        super().__init__()
        self._worker: Optional[SerialWorker] = None
        self._setup_window()
        self._build_ui()
        self.control_panel.send_requested.connect(self._on_send)
        self.control_panel.execute_requested.connect(self._on_execute)
        self._wire_sliders()

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
        """Connect slider value_changed → FK engine for real-time preview."""
        cp = self.control_panel
        vp = self.viewport_panel

        def _update_fk(_=None):
            vp.update_joints(
                cp.axX.get_value(),
                cp.axY.get_value(),
                cp.axZ.get_value(),
            )

        cp.axX.value_changed.connect(_update_fk)
        cp.axY.value_changed.connect(_update_fk)
        cp.axZ.value_changed.connect(_update_fk)

    def calculate_inverse_kinematics(self, x: float, y: float, z: float):
        """
        Dummy inverse kinematics implementation.
        Maps Target XYZ straight to theta1, theta2, theta3 (-180 to 180 bounded).
        """
        def bound(v):
            val = float(v) % 360
            if val > 180: val -= 360
            elif val < -180: val += 360
            return float(val)
        return bound(x), bound(y), bound(z)

    def _on_execute(self, x: float, y: float, z: float, hw: bool, port: str):
        # 1. Dummy Inverse Kinematics
        t1, t2, t3 = self.calculate_inverse_kinematics(x, y, z)
        
        # 2. Update existing UI Sliders to match new angles
        self.control_panel.axX.set_value(t1)
        self.control_panel.axY.set_value(t2)
        self.control_panel.axZ.set_value(t3)
        
        # 3. Animate 3D view smoothly
        self.viewport_panel.update_joints(t1, t2, t3)
        
        payload = json.dumps({
            "target_x": round(x, 2), "target_y": round(y, 2), "target_z": round(z, 2),
            "theta1": round(t1, 2), "theta2": round(t2, 2), "theta3": round(t3, 2)
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

        self.viewport_panel.update_joints(x, y, z)

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


if __name__ == "__main__":
'''

text = n_old_pattern.sub(n_new, text)

# add QLineEdit import natively
text = text.replace('from PyQt6.QtWidgets import (', 'from PyQt6.QtWidgets import (\n    QLineEdit,')

with open("main.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Phase 2 done")
