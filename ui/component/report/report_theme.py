try:
    from PySide6 import QtGui
except ImportError:
    from PyQt5 import QtGui

class ReportTheme:
    """
    Unified Color Theme for Reports (Daily, Weekly, Monthly).
    Based on 'Dark Fairy Forest' theme.
    Palette:
    - #547C7E (Muted Teal/Green) - Secondary / Borders
    - #50795D (Forest Green)     - Panels / Buttons
    - #2D5256 (Dark Deep Teal)   - Global Background
    - #C2E3B8 (Pale Green)       - Highlights / Light Backgrounds
    - #EBE4C3 (Beige/Cream)      - Text
    - #FBC02D (Golden Yellow)    - Accents
    """

    # --- Base Colors (Hex) ---
    _C_MORANDI_BLUE_LIGHT = "#547C7E"  # Muted Teal (Secondary/Border)
    _C_MORANDI_BLUE_DARK  = "#50795D"  # Forest Green (Primary/Panel)
    _C_GOLD               = "#EBE4C3"
    _C_GOLD_LIGHT         = "#C2E3B8"
    _C_GOLD_DARK          = "#FBC02D"
    _C_GRADIENT_START     = "#D4E0BB"
    _C_GRADIENT_END       = "#E0E1AC"
    _C_PANEL_FILL         = "#F9F5F5"
    c = "#FBC02D"
    _C_ACCENT_LIGHT       = "#C2E3B8"  # Pale Green
    _C_RED                = "#EF5350"
    _C_RED_DARK           = "#C62828"
    _C_ORANGE             = "#FB8C00"
    _C_CYAN               = "#26A69A"
    _C_BLUE               = "#42A5F5"
    _C_YELLOW             = "#FBC02D"
    _C_BRIGHT_YELLOW      = "#FFEB3B"  # Bright Yellow
    _C_WHITE              = "#FFFFFF"
    _C_BLACK              = "#000000"

    # --- 2. 背景系统 (Background System) ---
    # [全局背景] (用于: 窗口最底层的背景)
    _CFG_BG_GLOBAL_COLOR = "#2D5256" # Dark Deep Teal
    _CFG_BG_GLOBAL_ALPHA = 255       # Opaque

    # [背景板] (用于: 卡片, 列表项, 浮层, 按钮背景)
    _CFG_BG_PANEL_COLOR = "#50795D"  # Forest Green
    _CFG_BG_PANEL_ALPHA = 200        # Semi-Opaque

    @property
    def COLOR_BG_GLOBAL_COLOR(self): return self.color(self._CFG_BG_GLOBAL_COLOR)

    @property
    def COLOR_BG_PANEL(self): return self.color(self._CFG_BG_PANEL_COLOR)

    @property
    def HEX_REMINDER_GRADIENT_START(self): return self._C_GRADIENT_START

    @property
    def HEX_REMINDER_GRADIENT_END(self): return self._C_GRADIENT_END

    @property
    def HEX_REMINDER_PANEL_FILL(self): return self._C_PANEL_FILL

    # --- 3. 图表系统 (Chart System) ---
    # [柱状图] (用于: 数据条, 进度条)
    _CFG_CHART_COLOR = "#C2E3B8"     # Pale Green
    _CFG_CHART_ALPHA = 255           

    # --- Semantic Colors (QColor with Alpha) ---

    @classmethod
    def color(cls, hex_code, alpha=255):
        """Helper to get QColor with alpha."""
        c = QtGui.QColor(hex_code)
        c.setAlpha(alpha)
        return c

    # Extended Palette for Daily Report
    @property
    def COLOR_PRIMARY_LIGHT(self): return self.color(self._C_MORANDI_BLUE_LIGHT)
    @property
    def COLOR_PRIMARY_DARK(self): return self.color(self._C_MORANDI_BLUE_DARK)
    @property
    def COLOR_ACCENT_LIGHT(self): return self.color(self._C_ACCENT_LIGHT)
    @property
    def COLOR_ACCENT_DARK(self): return self.color(self._C_GOLD_DARK)
    @property
    def COLOR_WARNING(self): return self.color(self._C_ORANGE)
    @property
    def COLOR_DANGER(self): return self.color(self._C_RED_DARK)
    
    @property
    def COLOR_TEXT_SECONDARY(self): return self.color(self._C_GOLD, 200) # Beige 80%
    @property
    def COLOR_TEXT_MUTED(self): return self.color(self._C_ACCENT_LIGHT, 150) # Pale Green 60%
    
    @property
    def COLOR_SURFACE(self): return self.color(self._CFG_BG_PANEL_COLOR, 255) # Forest Green
    @property
    def COLOR_SHADOW(self): return self.color(self._C_BLACK, 60) # Dark Shadow
    @property
    def COLOR_OVERLAY(self): return self.color(self._CFG_BG_GLOBAL_COLOR, 200) # Dark Teal Overlay

    # Backgrounds
    @property
    def COLOR_BG_CENTER(self):
        return self.color(self._CFG_BG_GLOBAL_COLOR, 255)  # Dark Deep Teal

    @property
    def COLOR_BG_EDGE(self):
        return self.color("#1A3538", 255)   # Darker Teal/Black Edge

    @property
    def COLOR_BORDER(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 255) # Muted Teal Border

    @property
    def COLOR_INNER_SHADOW(self):
        return self.color(self._C_BLACK, 50)

    # Text
    @property
    def COLOR_TEXT_TITLE(self):
        return self.color(self._C_GOLD, 255) # Beige/Cream

    @property
    def COLOR_TEXT_NORMAL(self):
        return self.color("#FFFFFF", 230) # White-ish

    @property
    def COLOR_TEXT_SUBTITLE(self):
        return self.color(self._C_ACCENT_LIGHT, 200) # Pale Green

    @property
    def COLOR_TEXT_LOCKED(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 150) # Muted Teal

    @property
    def COLOR_GRID(self):
        return self.color(self._C_ACCENT_LIGHT, 30) # Faint Pale Green Grid

    @property
    def COLOR_CHART_BAR(self):
        return self.color(self._C_GOLD_DARK, 255) # Golden Yellow

    # Missing from Daily Report?
    @property
    def HEX_BLUE_LIGHT(self): return self._C_MORANDI_BLUE_LIGHT

    @staticmethod
    def draw_text_at_point_with_shadow(painter, x, y, text, color, shadow_color=None):
        if shadow_color is None:
            shadow_color = QtGui.QColor(0, 0, 0, 160)
        painter.save()
        painter.setPen(QtGui.QPen(shadow_color))
        offset = 1
        painter.drawText(x + offset, y + offset, text)
        painter.setPen(QtGui.QPen(color))
        painter.drawText(x, y, text)
        painter.restore()

# Create global instance
theme = ReportTheme()
