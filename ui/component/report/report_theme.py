
try:
    from PySide6 import QtGui
except ImportError:
    from PyQt5 import QtGui

class ReportTheme:
    """
    Unified Color Theme for Reports (Daily, Weekly, Monthly).
    Based on 'Morandi Blue Starry' theme.
    """

    # --- Base Colors (Hex) ---
    _C_MORANDI_BLUE_LIGHT = "#A8D8EA"  # 168, 216, 234
    _C_MORANDI_BLUE_DARK  = "#7EB3E8"  # 126, 179, 232 (approx)
    _C_GOLD               = "#FFD700"  # 255, 215, 0
    _C_GOLD_LIGHT         = "#FFE033"
    _C_GOLD_DARK          = "#CCAC00"
    _C_ACCENT_LIGHT       = "#BFE6F2"
    _C_RED                = "#FF6B6B"
    _C_RED_DARK           = "#FF4444"
    _C_ORANGE             = "#FFAA00"
    _C_CYAN               = "#4ECDC4"
    _C_BLUE               = "#45B7D1"
    _C_YELLOW             = "#F9CA24"
    _C_BRIGHT_YELLOW      = "#FFEA00"  # 亮黄色 (用于时间轴高亮)
    _C_WHITE              = "#FFFFFF"
    _C_BLACK              = "#000000"

    # --- 2. 背景系统 (Background System) ---
    # [全局背景] (用于: 窗口最底层的背景)
    _CFG_BG_GLOBAL_COLOR = _C_MORANDI_BLUE_DARK 
    _CFG_BG_GLOBAL_ALPHA = 153       # 透明度 0-255 (约60% 不透明)

    # [背景板] (用于: 卡片, 列表项, 浮层, 按钮背景)
    _CFG_BG_PANEL_COLOR = _C_MORANDI_BLUE_LIGHT
    _CFG_BG_PANEL_ALPHA = 153        # 透明度 0-255 (约60% 不透明)

    # --- 3. 图表系统 (Chart System) ---
    # [柱状图] (用于: 数据条, 进度条)
    _CFG_CHART_COLOR = _C_BRIGHT_YELLOW # 使用亮黄色
    _CFG_CHART_ALPHA = 255           # 透明度 0-255 (约90% 不透明)

    # --- Semantic Colors (QColor with Alpha) ---

    @classmethod
    def color(cls, hex_code, alpha=255):
        """Helper to get QColor with alpha."""
        c = QtGui.QColor(hex_code)
        c.setAlpha(alpha)
        return c

    # Extended Palette for Daily Report
    @property
    def COLOR_PRIMARY_LIGHT(self): return self.color(self._C_GOLD_LIGHT)
    @property
    def COLOR_PRIMARY_DARK(self): return self.color(self._C_GOLD_DARK)
    @property
    def COLOR_ACCENT_LIGHT(self): return self.color(self._C_ACCENT_LIGHT)
    @property
    def COLOR_WARNING(self): return self.color(self._C_ORANGE)
    @property
    def COLOR_DANGER(self): return self.color(self._C_RED_DARK)
    
    @property
    def COLOR_TEXT_SECONDARY(self): return self.color(self._C_MORANDI_BLUE_LIGHT, 204) # 80%
    @property
    def COLOR_TEXT_MUTED(self): return self.color(self._C_MORANDI_BLUE_LIGHT, 153) # 60%
    
    @property
    def COLOR_SURFACE(self): return self.color(self._C_MORANDI_BLUE_DARK, 20) # 8%
    @property
    def COLOR_SHADOW(self): return self.color(self._C_BLACK, 25) # 0.1 approx
    @property
    def COLOR_OVERLAY(self): return self.color(self._C_MORANDI_BLUE_LIGHT, 25) # 0.1 approx

    # Backgrounds
    @property
    def COLOR_BG_CENTER(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 20)  # 8%

    @property
    def COLOR_BG_EDGE(self):
        return self.color(self._C_MORANDI_BLUE_DARK, 20)   # 8%

    @property
    def COLOR_BORDER(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 76)  # 30%

    @property
    def COLOR_INNER_SHADOW(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 12)

    # Text
    @property
    def COLOR_TEXT_TITLE(self):
        return self.color(self._C_GOLD, 255) # Gold 100%

    @property
    def COLOR_TEXT_TITLE_ALT(self):
        """Alternative title color (e.g. for Weekly report)"""
        return self.color(self._C_MORANDI_BLUE_LIGHT, 230) # 90%

    @property
    def COLOR_TEXT_SUBTITLE(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 204) # 80%

    @property
    def COLOR_TEXT_NORMAL(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 230) # 90%

    @property
    def COLOR_TEXT_DESC(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 204) # 80%

    @property
    def COLOR_TEXT_DATE(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 178) # 70%

    @property
    def COLOR_TEXT_LOCKED(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 128) # 50%
    
    @property
    def COLOR_TEXT_VALUE(self):
        return self.color(self._C_GOLD, 255)

    # Charts & Progress
    @property
    def COLOR_FILL_GOLD(self):
        return self.color(self._C_GOLD, 153)    # 60%

    @property
    def COLOR_FILL_GOLD_DIM(self):
        return self.color(self._C_GOLD, 128)    # 50%

    @property
    def COLOR_CHART_BAR(self):
        return self.color(self._CFG_CHART_COLOR, self._CFG_CHART_ALPHA)

    @property
    def COLOR_CHART_BORDER(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 102) # 40%

    @property
    def COLOR_GRID(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 38)  # 15% (Month uses 25/10%)

    # Buttons
    @property
    def COLOR_BTN_BG(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 30)  # 12%

    @property
    def COLOR_BTN_BORDER(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 76)  # 30%

    @property
    def COLOR_BTN_HOVER(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 64)  # 25%
    
    @property
    def COLOR_BTN_TEXT(self):
        return self.color(self._C_MORANDI_BLUE_LIGHT, 230) # 90%

    # Particle Colors (List of hex strings)
    @property
    def PARTICLE_COLORS(self):
        return [
            self._C_MORANDI_BLUE_LIGHT,
            self._C_GOLD,
            self._C_MORANDI_BLUE_DARK,
            self._C_RED,
            self._C_CYAN,
            self._C_BLUE,
            self._C_YELLOW
        ]

    # --- Raw Hex Access (if needed for stylesheets) ---
    @property
    def HEX_GOLD(self): return self._C_GOLD
    @property
    def HEX_BLUE_LIGHT(self): return self._C_MORANDI_BLUE_LIGHT
    
    # Singleton instance
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def draw_text_with_shadow(painter, rect, flags, text, color, shadow_color=None, offset=(1, 1)):
        """Helper to draw text with shadow."""
        if shadow_color is None:
            # Default shadow: black with 50% opacity (128)
            shadow_color = QtGui.QColor(0, 0, 0, 128)
        
        # Draw Shadow
        painter.setPen(shadow_color)
        shadow_rect = QtCore.QRectF(rect)
        shadow_rect.translate(offset[0], offset[1])
        painter.drawText(shadow_rect, flags, text)
        
        # Draw Text
        painter.setPen(color)
        painter.drawText(rect, flags, text)
        
    @staticmethod
    def draw_text_at_point_with_shadow(painter, x, y, text, color, shadow_color=None, offset=(1, 1)):
        """Helper to draw text at specific point with shadow."""
        if shadow_color is None:
            shadow_color = QtGui.QColor(0, 0, 0, 128)
            
        # Draw Shadow
        painter.setPen(shadow_color)
        painter.drawText(int(x + offset[0]), int(y + offset[1]), text)
        
        # Draw Text
        painter.setPen(color)
        painter.drawText(int(x), int(y), text)

# Global instance for easy import
theme = ReportTheme.get_instance()
