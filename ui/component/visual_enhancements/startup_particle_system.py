"""
启动粒子效果系统

在应用程序启动时创建庆祝性的粒子爆炸效果，包含物理模拟和渲染。
"""

import math
import random
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class Particle:
    """粒子数据类"""
    position: QtCore.QPointF
    velocity: QtCore.QPointF
    acceleration: QtCore.QPointF
    color: QtGui.QColor
    size: float
    life_time: float
    max_life: float

    @property
    def alpha(self) -> float:
        """根据生命周期计算透明度"""
        return max(0.0, 1.0 - (self.life_time / self.max_life))


class StartupParticleSystem(QtWidgets.QWidget):
    """启动粒子效果系统"""

    # 信号
    effectStarted = Signal()
    effectCompleted = Signal()

    # 粒子配置
    PARTICLE_COUNT = 50
    BURST_RADIUS = 100.0
    PARTICLE_SIZE_RANGE = (2.0, 8.0)
    LIFE_TIME_RANGE = (1.0, 3.0)
    GRAVITY = 9.8
    AIR_RESISTANCE = 0.98
    COLORS = ['#00FF88', '#FFD700', '#FF6B6B',
              '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']

    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles: List[Particle] = []
        self.is_active = False

        # 设置透明背景
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # 更新定时器
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self._update_particles)
        self.update_timer.setInterval(16)  # ~60 FPS

        # 效果持续时间定时器
        self.effect_timer = QtCore.QTimer()
        self.effect_timer.timeout.connect(self._complete_effect)
        self.effect_timer.setSingleShot(True)

    def trigger_startup_effect(self, center_point: QtCore.QPoint = None):
        """触发启动粒子效果"""
        if self.is_active:
            return

        if center_point is None:
            center_point = QtCore.QPoint(self.width() // 2, self.height() // 2)

        self.create_particle_burst(center_point, self.PARTICLE_COUNT)
        self.is_active = True
        self.update_timer.start()
        self.effect_timer.start(3000)  # 3秒后完成效果

        self.effectStarted.emit()
        self.show()

    def create_particle_burst(self, center: QtCore.QPoint, count: int = 50):
        """创建粒子爆炸效果"""
        self.particles.clear()

        for _ in range(count):
            # 随机角度和速度
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 150)

            # 初始位置（中心点附近的小范围随机）
            offset_x = random.uniform(-10, 10)
            offset_y = random.uniform(-10, 10)
            position = QtCore.QPointF(
                center.x() + offset_x, center.y() + offset_y)

            # 速度向量
            velocity = QtCore.QPointF(
                math.cos(angle) * speed,
                math.sin(angle) * speed
            )

            # 重力加速度
            acceleration = QtCore.QPointF(0, self.GRAVITY)

            # 随机颜色和大小
            color = QtGui.QColor(random.choice(self.COLORS))
            size = random.uniform(*self.PARTICLE_SIZE_RANGE)
            max_life = random.uniform(*self.LIFE_TIME_RANGE)

            particle = Particle(
                position=position,
                velocity=velocity,
                acceleration=acceleration,
                color=color,
                size=size,
                life_time=0.0,
                max_life=max_life
            )

            self.particles.append(particle)

    def _update_particles(self):
        """更新粒子状态"""
        delta_time = 0.016  # 假设60FPS

        # 更新每个粒子
        for particle in self.particles[:]:  # 创建副本以安全删除
            self.apply_physics(particle, delta_time)
            particle.life_time += delta_time

            # 移除生命周期结束的粒子
            if particle.life_time >= particle.max_life:
                self.particles.remove(particle)

        # 如果没有粒子了，停止更新
        if not self.particles:
            self._complete_effect()
        else:
            self.update()

    def apply_physics(self, particle: Particle, delta_time: float):
        """应用物理效果到粒子"""
        # 应用空气阻力
        particle.velocity.setX(particle.velocity.x() * self.AIR_RESISTANCE)
        particle.velocity.setY(particle.velocity.y() * self.AIR_RESISTANCE)

        # 应用加速度（重力）
        particle.velocity.setX(particle.velocity.x() +
                               particle.acceleration.x() * delta_time)
        particle.velocity.setY(particle.velocity.y() +
                               particle.acceleration.y() * delta_time)

        # 更新位置
        particle.position.setX(particle.position.x() +
                               particle.velocity.x() * delta_time)
        particle.position.setY(particle.position.y() +
                               particle.velocity.y() * delta_time)

    def _complete_effect(self):
        """完成粒子效果"""
        self.is_active = False
        self.update_timer.stop()
        self.effect_timer.stop()
        self.particles.clear()
        self.hide()
        self.effectCompleted.emit()

    def paintEvent(self, event):
        """渲染粒子"""
        if not self.particles:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        for particle in self.particles:
            self.render_particle(painter, particle)

    def render_particle(self, painter: QtGui.QPainter, particle: Particle):
        """渲染单个粒子"""
        # 设置颜色和透明度
        color = QtGui.QColor(particle.color)
        color.setAlphaF(particle.alpha)

        # 创建径向渐变
        gradient = QtGui.QRadialGradient(particle.position, particle.size / 2)
        gradient.setColorAt(0, color)

        # 外圈更透明
        outer_color = QtGui.QColor(color)
        outer_color.setAlphaF(color.alphaF() * 0.3)
        gradient.setColorAt(1, outer_color)

        painter.setBrush(gradient)
        painter.setPen(QtCore.Qt.NoPen)

        # 绘制粒子
        rect = QtCore.QRectF(
            particle.position.x() - particle.size / 2,
            particle.position.y() - particle.size / 2,
            particle.size,
            particle.size
        )
        painter.drawEllipse(rect)

    def resizeEvent(self, event):
        """窗口大小改变时调整粒子系统"""
        super().resizeEvent(event)
        # 如果需要，可以在这里调整粒子位置
