import sys

with open('main.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update font stack
text = text.replace('("San Francisco", "Segoe UI", "Roboto", "Helvetica Neue", "Arial")', '("San Francisco", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif")')
text = text.replace('font-family: "San Francisco", "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif;', 'font-family: "San Francisco", "-apple-system", "BlinkMacSystemFont", "Segoe UI", sans-serif;')

# 2. Add ipad_shadow
shadow_func = '''    @staticmethod
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
    def shadow'''
text = text.replace('    @staticmethod\n    def shadow', shadow_func)

# 3. ViewportPanel rewrite
v_old = '''class ViewportPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            ViewportPanel {{
                background: {T.WINDOW};
                border-left: 1px solid #EBEBF0;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(0)

        # White card wrapping the OpenGL widget
        self._card = QFrame()
        self._card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._card.setStyleSheet(f"""
            QFrame {{
                background: {T.CARD};
                border: 1px solid #EBEBF0;
                border-radius: 18px;
            }}
        """)
        self._card.setGraphicsEffect(T.shadow(blur=36, y=8, alpha=14))

        card_vl = QVBoxLayout(self._card)
        card_vl.setContentsMargins(0, 0, 0, 0)
        card_vl.setSpacing(0)

        card_vl.addWidget(self._make_header())

        if OPENGL_AVAILABLE:
            self._build_gl(card_vl)
        else:
            self._build_fallback(card_vl)

        card_vl.addWidget(self._make_footer())
        outer.addWidget(self._card)'''

v_new = '''class ViewportPanel(QFrame):
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

        card_vl.addWidget(self._make_footer())'''
text = text.replace(v_old, v_new)

# Viewport make_header & make_footer style fixes
vh_old = '''            QFrame {
                background: {T.CARD};
                border-bottom: 1px solid #EBEBF0;
                border-top-left-radius: 18px;
                border-top-right-radius: 18px;
            }'''
text = text.replace(vh_old, '''            QFrame {\n                background: transparent;\n            }''')

vf_old = '''            QFrame {
                background: {T.CARD};
                border-top: 1px solid #EBEBF0;
                border-bottom-left-radius: 18px;
                border-bottom-right-radius: 18px;
            }'''
text = text.replace(vf_old, '''            QFrame {\n                background: transparent;\n            }''')

# 4. _apply_fk interpolation
fk_old = '''        self._current_angles[:] = self._target_angles[:]
        
        # a) Start with the world root transform'''
fk_new = '''        for i in range(len(self._target_angles)):
            diff = self._target_angles[i] - self._current_angles[i]
            self._current_angles[i] += diff * 0.15
            
        # a) Start with the world root transform'''
text = text.replace(fk_old, fk_new)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Phase 1 done')
