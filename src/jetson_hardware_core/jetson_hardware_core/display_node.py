#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import String, Float32, Int32
import pygame
import numpy as np
import time
import threading
import os
import signal
from datetime import datetime
import math

# ══════════════════════════════════════════════════════════════
# لوحة الألوان للتصميم العصري (Pygame UI)
# ══════════════════════════════════════════════════════════════
BG         = (8, 15, 26)
PANEL      = (12, 24, 39)
PANEL_ALT  = (10, 21, 32)
BORDER     = (26, 58, 92)
TXT        = (200, 223, 240)
TXT_DIM    = (74, 122, 155)

SAFE       = (0, 200, 83)
WARN       = (255, 145, 0)
CRIT       = (255, 23, 68)
V2X_BLUE   = (0, 180, 216)

# =============================================================================
# Shared state (Thread-Safe) لتبادل البيانات بين ROS2 والشاشة
# =============================================================================
class DashState:
    def __init__(self):
        self._lock        = threading.Lock()
        self.decision     = "SAFE"
        self.danger_pct   = 0.0  # من 0.0 إلى 1.0
        self.ttc          = 99.0
        self.objects_count = 0
        self.v2x_code     = 0    # 0 = Safe, 1 = Alert

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)

    def snapshot(self):
        with self._lock:
            return (self.decision, self.danger_pct,
                    self.ttc, self.objects_count, self.v2x_code)


# =============================================================================
# ROS2 Node — يعمل في Thread منفصل ويحدث البيانات فقط
# =============================================================================
class DisplayNode(Node):
    def __init__(self, state: DashState):
        super().__init__('display_node')
        self._state = state

        self.create_subscription(String,  '/system/final_decision',
                                 lambda m: state.update(decision=m.data.upper().strip()), 10)
        self.create_subscription(Float32, '/system/danger_level',
                                 lambda m: state.update(danger_pct=float(np.clip(m.data, 0.0, 1.0))), 10)
        self.create_subscription(Float32, '/system/ttc_value',
                                 lambda m: state.update(ttc=float(m.data)), 10)
        self.create_subscription(String,  '/system/fused_objects',
                                 self._fusion_cb, 10)
        self.create_subscription(Int32, '/v2x_alerts', 
                                 lambda m: state.update(v2x_code=m.data), 10)

        self.get_logger().info("✅ ROS2 subscriptions active.")

    def _fusion_cb(self, msg):
        n = len(msg.data.strip().split('\n')) if msg.data.strip() else 0
        self._state.update(objects_count=n)


# =============================================================================
# Pygame UI — واجهة القيادة العصرية (تعمل على Main Thread)
# =============================================================================
class ModernADASUI:
    def __init__(self, state: DashState):
        self.state = state
        pygame.init()
        self.width = 1024
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("PRECRASH AI - Modern Dashboard")
        self.clock = pygame.time.Clock()
        
        # إعداد الخطوط كما طلبتِ
        self.font_xs = pygame.font.SysFont('Consolas', 11)
        self.font_sm = pygame.font.SysFont('Consolas', 14, bold=True) 
        self.font_md = pygame.font.SysFont('Consolas', 20, bold=True)
        self.font_lg = pygame.font.SysFont('Consolas', 48, bold=True)
        self.font_huge = pygame.font.SysFont('Consolas', 64, bold=True)

        self.v2x_messages = []
        self.last_v2x_code = 0
        self.add_v2x("safe", "System initialized. RSU connected.")

    def add_v2x(self, msg_type, text):
        now = datetime.now().strftime('%H:%M:%S')
        self.v2x_messages.append({"type": msg_type, "text": text, "time": now})
        if len(self.v2x_messages) > 3: 
            self.v2x_messages.pop(0)

    def draw_rect(self, color, rect, width=0, radius=6):
        pygame.draw.rect(self.screen, color, rect, width, border_radius=radius)

    def draw_text(self, text, font, color, x, y, align="left"):
        surface = font.render(str(text), True, color)
        rect = surface.get_rect()
        if align == "center": rect.center = (x, y)
        elif align == "right": rect.topright = (x, y)
        else: rect.topleft = (x, y)
        self.screen.blit(surface, rect)

    def get_status_color(self, decision, danger_pct):
        if decision == "CRITICAL" or danger_pct >= 65: return CRIT, "CRITICAL", "Immediate Action Required"
        if decision == "WARNING" or danger_pct >= 30: return WARN, "WARNING", "Monitoring Situation"
        return SAFE, "SAFE", "No Threat Detected"

    def draw_header(self):
        self.draw_rect(PANEL, (0, 0, self.width, 38), radius=0)
        pygame.draw.line(self.screen, BORDER, (0, 38), (self.width, 38))

        # العنوان المدمج
        self.draw_text("PRECRASH AI | Road Safety and Traffic Diagnostics Assisted by AI", self.font_sm, V2X_BLUE, 14, 11)

        # الوقت والتاريخ
        now = datetime.now()
        date_x = self.width - 250 
        self.draw_text("DATE", self.font_xs, TXT_DIM, date_x - 60, 5, "center")
        self.draw_text(now.strftime('%d %b %Y'), self.font_sm, TXT, date_x - 60, 18, "center")
        pygame.draw.line(self.screen, BORDER, (date_x - 15, 10), (date_x - 15, 28))
        self.draw_text("TIME", self.font_xs, TXT_DIM, date_x + 30, 5, "center")
        self.draw_text(now.strftime('%H:%M:%S'), self.font_sm, TXT, date_x + 30, 18, "center")

    def draw_panel(self, rect, title, badge_text, badge_color):
        self.draw_rect(PANEL, rect)
        self.draw_rect(BORDER, rect, width=1)
        pygame.draw.line(self.screen, BORDER, (rect[0], rect[1]+30), (rect[0]+rect[2], rect[1]+30))
        
        self.draw_text(title, self.font_sm, TXT_DIM, rect[0] + 10, rect[1] + 8) 
        
        badge_w = len(badge_text) * 7 + 10
        badge_rect = (rect[0] + rect[2] - badge_w - 10, rect[1] + 6, badge_w, 18)
        self.draw_rect(badge_color, badge_rect, width=1, radius=2)
        self.draw_text(badge_text, self.font_xs, badge_color, badge_rect[0] + badge_w//2, badge_rect[1] + 9, "center")
