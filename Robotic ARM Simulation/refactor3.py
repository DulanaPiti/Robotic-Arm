import sys
import re

with open("main.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Slider QSS Replacement
qss_old = '''/* ── Slider: groove — iOS Control Center style ── */
QSlider::groove:horizontal {
    height: 6px;
    background: #E5E5EA;
    border-radius: 3px;
    margin: 0 6px;
}
QSlider::sub-page:horizontal {
    background: {T.BLUE};
    border-radius: 3px;
    height: 6px;
}
QSlider::add-page:horizontal {
    background: #E5E5EA;
    border-radius: 3px;
    height: 6px;
}
QSlider::handle:horizontal {
    width: 26px;
    height: 26px;
    margin: -10px -2px;
    border-radius: 13px;
    background: {T.CARD};
    border: 1px solid #D2D2D7;
}'''
qss_new = '''/* ── Slider: groove — iOS Control Center style ── */
QSlider::groove:horizontal {
    height: 8px;
    background: #E5E5EA;
    border-radius: 4px;
    margin: 0 6px;
}
QSlider::sub-page:horizontal {
    background: {T.BLUE};
    border-radius: 4px;
    height: 8px;
}
QSlider::add-page:horizontal {
    background: #E5E5EA;
    border-radius: 4px;
    height: 8px;
}
QSlider::handle:horizontal {
    width: 28px;
    height: 28px;
    margin: -10px -2px;
    border-radius: 14px;
    background: {T.CARD};
    border: 1px solid #D2D2D7;
}'''
text = text.replace(qss_old, qss_new)

# 2. Add ROBOT_KINEMATICS_CONFIG
kinematics_config = '''# ══════════════════════════════════════════════════════════════════════════════
#  KINEMATICS CONFIGURATION (TUNE THESE TO ASSEMBLE STLS)
# ══════════════════════════════════════════════════════════════════════════════
ROBOT_KINEMATICS_CONFIG = [
    {
        "name": "base",
        "offset": (0.0, 0.0, 0.0),
        "local_rotation": (0.0, 1.0, 0.0, 0.0),
        "rotation_axis": (0.0, 0.0, 1.0)
    },
    {
        "name": "link1",
        "offset": (0.0, 0.0, 50.0),
        "local_rotation": (0.0, 1.0, 0.0, 0.0),
        "rotation_axis": (0.0, 1.0, 0.0)
    },
    {
        "name": "link2",
        "offset": (0.0, 0.0, 50.0),
        "local_rotation": (0.0, 1.0, 0.0, 0.0),
        "rotation_axis": (0.0, 1.0, 0.0)
    },
    {
        "name": "link3",
        "offset": (0.0, 0.0, 50.0),
        "local_rotation": (0.0, 1.0, 0.0, 0.0),
        "rotation_axis": (0.0, 0.0, 1.0)
    },
    {
        "name": "link4",
        "offset": (0.0, 0.0, 50.0),
        "local_rotation": (0.0, 1.0, 0.0, 0.0),
        "rotation_axis": (0.0, 1.0, 0.0)
    },
    {
        "name": "link5",
        "offset": (0.0, 0.0, 50.0),
        "local_rotation": (0.0, 1.0, 0.0, 0.0),
        "rotation_axis": (0.0, 0.0, 1.0)
    },
    {
        "name": "link6",
        "offset": (0.0, 0.0, 50.0),
        "local_rotation": (0.0, 1.0, 0.0, 0.0),
        "rotation_axis": (0.0, 0.0, 1.0)
    }
]

'''
# Replace old offsets
old_offsets = '''# ── Joint offsets in DISPLAY UNITS (real mm * 0.1 scale already applied) ─────
# Each tuple is the translation from the PREVIOUS joint origin to THIS one.
# Tune these to match the actual STL pivot heights once you can see them.
_JOINT_OFFSETS = [
    (0, 0,  0.0),   # base   -- world origin
    (0, 0,  8.0),   # link1  -- top of base   (~80 mm / 10)
    (0, 0, 10.0),   # link2  -- above link1   (~100 mm)
    (0, 0, 12.0),   # link3  -- above link2   (~120 mm)
    (0, 0,  8.0),   # link4  -- above link3   (~80 mm)
    (0, 0,  6.0),   # link5  -- above link4   (~60 mm)
    (0, 0,  5.0),   # link6  -- above link5   (~50 mm) end-effector
]

# Rotation axis per joint (only first 3 are slider-driven for now)
_JOINT_AXES = ["Z", "Y", "Y", "Z", "Y", "Z"]'''
text = text.replace(old_offsets, kinematics_config)

# 3. Add SegmentedControl class above ControlPanel
seg_class = '''class SegmentedControl(QFrame):
    toggled = pyqtSignal(int)
    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            SegmentedControl {
                background: #E5E5EA;
                border-radius: 9px;
            }
        """)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(2, 2, 2, 2)
        hl.setSpacing(0)

        self.btns = []
        for i, lbl in enumerate(labels):
            btn = QPushButton(lbl)
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #86868B;
                    font-weight: 600;
                    font-size: 13px;
                    border: none;
                    border-radius: 7px;
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

class ControlPanel(QFrame):'''
text = text.replace("class ControlPanel(QFrame):", seg_class)

# 4. Rewrite ViewportPanel _apply_fk
fk_old = '''    def _apply_fk(self):
        """
        Fixed-timestep rendering loop using parent-child hierarchical transformations.
        """
        import pyqtgraph as pg
        
        for i in range(len(self._target_angles)):
            diff = self._target_angles[i] - self._current_angles[i]
            self._current_angles[i] += diff * 0.15
            
        # a) Start with the world root transform
        parent_transform = pg.Transform3D()

        for i, mesh in enumerate(self._link_meshes):
            # a) Create a new transform based on the parent
            transform = pg.Transform3D(parent_transform)

            # b) Translate by the joint's offset
            dx, dy, dz = self.joint_offsets.get(i, (0.0, 0.0, 0.0))
            transform.translate(dx, dy, dz)

            # c) Apply the slider rotation
            if i > 0:
                ji = i - 1
                if ji < len(self._current_angles):
                    angle = self._current_angles[ji]
                    axis  = _JOINT_AXES[ji] if ji < len(_JOINT_AXES) else "Z"
                    
                    if axis == "Z":
                        transform.rotate(angle, 0, 0, 1)
                    elif axis == "Y":
                        transform.rotate(angle, 0, 1, 0)
                    else:
                        transform.rotate(angle, 1, 0, 0)

            # d) (Optional local mesh offset would go here if needed)

            # e) Apply to mesh
            mesh.setTransform(pg.Transform3D(transform))

            # f) Pass this transform down as the parent_transform for Joint i+1
            parent_transform = pg.Transform3D(transform)'''

fk_new = '''    def _apply_fk(self):
        """
        Fixed-timestep rendering loop using parent-child hierarchical transformations.
        """
        import pyqtgraph as pg
        
        for i in range(len(self._target_angles)):
            diff = self._target_angles[i] - self._current_angles[i]
            self._current_angles[i] += diff * 0.15
            
        parent_transform = pg.Transform3D()

        for i, mesh in enumerate(self._link_meshes):
            conf = ROBOT_KINEMATICS_CONFIG[i]
            
            # 1. Inherit parent transform
            transform = pg.Transform3D(parent_transform)

            # 2. Translate by offset
            dx, dy, dz = conf["offset"]
            transform.translate(dx, dy, dz)

            # 3. Rotate by slider angle around rotation_axis
            if i > 0:
                ji = i - 1
                if ji < len(self._current_angles):
                    angle = self._current_angles[ji]
                    rx, ry, rz = conf["rotation_axis"]
                    transform.rotate(angle, rx, ry, rz)
                    
            # 4. Store this as the new parent transform for the next link
            parent_transform = pg.Transform3D(transform)

            # 5. Apply local_rotation STRICTLY for visual alignment of this STL
            visual_transform = pg.Transform3D(transform)
            loc_angle, loc_x, loc_y, loc_z = conf["local_rotation"]
            visual_transform.rotate(loc_angle, loc_x, loc_y, loc_z)

            # 6. Apply to the GLMeshItem
            mesh.setTransform(pg.Transform3D(visual_transform))'''

if fk_old in text:
    text = text.replace(fk_old, fk_new)

# 4b. Remove self.joint_offsets from _build_gl
jo_old = '''        # Kinematic Offset Dictionary (Placeholder values for tuning)
        # These translations are applied from the parent's pivot to this link's pivot
        self.joint_offsets = {
            0: (0.0, 0.0, 0.0),    # Base origin
            1: (0.0, 0.0, 8.0),    # Link 1 relative to Base
            2: (0.0, 0.0, 10.0),   # Link 2 relative to Link 1
            3: (0.0, 12.0, 0.0),   # Link 3 relative to Link 2
            4: (0.0, 0.0, 8.0),    # Link 4 relative to Link 3
            5: (0.0, 0.0, 6.0),    # Link 5 relative to Link 4
            6: (0.0, 0.0, 5.0),    # Link 6 relative to Link 5
        }'''
text = text.replace(jo_old, "")

# 5. ControlPanel Tabs -> StackedWidget + SegmentedControl
cp_old_start = "# ── Body with Tab Selection ───────────────────────────────────────────"
cp_old_end = "# ── Serial and Global Send ────────────────────────────────────────────"
cp_old_pattern = re.compile(re.escape(cp_old_start) + r".*?" + re.escape(cp_old_end), re.DOTALL)

cp_new_tabs = '''# ── Body with Segmented Selection ─────────────────────────────────────
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
        joint_layout.setContentsMargins(0, 10, 0, 0)
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
        
        # ── Serial and Global Send ────────────────────────────────────────────'''
text = cp_old_pattern.sub(cp_new_tabs, text)

# 6. Update _make_serial representation
ser_old_start = "def _make_serial(self) -> QWidget:"
ser_old_end = "return card\n\n    # ── Handlers ──────────────────────────────────────────────────────────────"
ser_old_pattern = re.compile(re.escape(ser_old_start) + r".*?" + re.escape(ser_old_end), re.DOTALL)

ser_new = '''def _make_serial(self) -> QWidget:
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

    # ── Handlers ──────────────────────────────────────────────────────────────'''
text = ser_old_pattern.sub(ser_new, text)

# Write out the results
with open("main.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Phase 3 script complete.")
