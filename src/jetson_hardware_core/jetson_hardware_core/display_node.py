import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import String, Float32, Int32  # أضيفي Int32
import cv2
import numpy as np
import time
import threading
import os
import signal
from datetime import datetime


# =============================================================================
# IntegratedDisplayNode — Road Safety AI Dashboard
# Target : 7-inch 1024×600 on Jetson Orin Nano
#
# Threading architecture (سبب هذا التصميم):
# ─────────────────────────────────────────
# cv2.imshow / cv2.waitKey / cv2.setMouseCallback يجب أن تعمل على
# MAIN THREAD دائماً في Linux/X11 — هذا شرط من OpenCV وليس خياراً.
# rclpy.spin() يحتل الـ main thread بالكامل، لذلك الحل الصحيح هو:
#   • ROS2 callbacks → thread منفصل (MultiThreadedExecutor)
#   • OpenCV render loop → main thread
# التواصل بينهما عبر threading.Event للإغلاق وshared state للبيانات.
# =============================================================================

CANVAS_W = 1024
CANVAS_H = 600
WIN_NAME  = "ROAD SAFETY AI"

# ── Palette (BGR) ─────────────────────────────────────────────────────────────
BG       = (40,  22,  10)
PANEL_BG = (53,  30,  14)
BORDER   = (95,  58,  30)
ACCENT   = (217, 163,  91)
WHITE    = (235, 235, 235)
DIM      = (110,  88,  50)

SAFE_FG  = (80,  210,  55)
SAFE_BG  = (12,   42,   8)
WARN_FG  = (50,  160, 245)
WARN_BG  = (12,   30,   0)
CRIT_FG  = (45,   45, 210)
CRIT_BG  = (12,    8,  38)

BAR_SAFE = (65,  170,  45)
BAR_WARN = (35,  130, 210)
BAR_CRIT = (25,   25, 190)

FT_MONO = cv2.FONT_HERSHEY_DUPLEX
FT_SANS = cv2.FONT_HERSHEY_SIMPLEX

# ── Close button coords (في Header، يسار الساعة بمسافة كافية) ────────────────
BTN_W  = 48
BTN_H  = 28
BTN_X1 = CANVAS_W - BTN_W - 8
BTN_Y1 = 4
BTN_X2 = BTN_X1 + BTN_W
BTN_Y2 = BTN_Y1 + BTN_H


# =============================================================================
# Shared state (thread-safe بـ Lock)
# =============================================================================
class DashState:
    def __init__(self):
        self._lock        = threading.Lock()
        self.decision     = "STANDBY"
        self.danger_pct   = 0.0
        self.ttc          = 0.0
        self.objects_count = 0
        self.v2x_code = 0  # 0 تعني لا يوجد تنبيه

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)

    def snapshot(self):
        with self._lock:
            return (self.decision, self.danger_pct,
                    self.ttc, self.objects_count)


# =============================================================================
# ROS2 Node — runs on a separate thread, writes to DashState only
# =============================================================================
class DisplayNode(Node):
    def __init__(self, state: DashState):
        super().__init__('display_node')
        self._state = state

        self.create_subscription(String,  '/system/final_decision',
                                 lambda m: state.update(decision=m.data.upper().strip()), 10)
        self.create_subscription(Float32, '/system/danger_level',
                                 lambda m: state.update(danger_pct=float(np.clip(m.data, 0, 1))), 10)
        self.create_subscription(Float32, '/system/ttc_value',
                                 lambda m: state.update(ttc=float(m.data)), 10)
        self.create_subscription(String,  '/system/fused_objects',
                                 self._fusion_cb, 10)

        self.get_logger().info("ROS2 subscriptions active.")
        
        self.create_subscription(Int32, '/v2x_alerts', 
                         lambda m: state.update(v2x_code=m.data), 10)

    def _fusion_cb(self, msg):
        n = len(msg.data.strip().split('\n')) if msg.data.strip() else 0
        self._state.update(objects_count=n)


# =============================================================================
# Drawing helpers (standalone functions — no class needed)
# =============================================================================
def _panel(f, x, y, w, h, bg, border=None, r=6):
    pts = np.array([
        [x+r, y], [x+w-r, y],
        [x+w, y+r], [x+w, y+h-r],
        [x+w-r, y+h], [x+r, y+h],
        [x, y+h-r], [x, y+r]
    ], dtype=np.int32)
    cv2.fillPoly(f, [pts], bg)
    for cx, cy in [(x+r,y+r),(x+w-r,y+r),(x+r,y+h-r),(x+w-r,y+h-r)]:
        cv2.circle(f, (cx, cy), r, bg, -1)
    if border:
        cv2.polylines(f, [pts], True, border, 1, cv2.LINE_AA)


def _put(f, text, x, y, scale, color, font=FT_SANS, thick=1):
    cv2.putText(f, text, (max(2, x), y), font, scale, color, thick, cv2.LINE_AA)


def _centered(f, text, cx, y, scale, color, font=FT_SANS, thick=1):
    (tw, _), _ = cv2.getTextSize(text, font, scale, thick)
    _put(f, text, cx - tw // 2, y, scale, color, font, thick)


def _fit_text(text, max_w, font, max_scale=1.6, min_scale=0.4, thick=2):
    lo, hi = min_scale, max_scale
    for _ in range(12):
        mid = (lo + hi) / 2
        (tw, _), _ = cv2.getTextSize(text, font, mid, thick)
        lo, hi = (mid, hi) if tw <= max_w else (lo, mid)
    return lo


def _danger_bar(f, x, y, w, h, pct, bar_color):
    cv2.rectangle(f, (x, y), (x+w, y+h), PANEL_BG, -1)
    cv2.rectangle(f, (x, y), (x+w, y+h), BORDER, 1)
    fw = max(0, int(pct * w) - 2)
    if fw > 0:
        cv2.rectangle(f, (x+1, y+1), (x+1+fw, y+h-1), bar_color, -1)
    for thr in [0.30, 0.65]:
        tx = x + int(thr * w)
        cv2.line(f, (tx, y), (tx, y+h), BORDER, 1)
    for frac, lbl in [(0.0,"0"),(0.30,"30"),(0.65,"65"),(1.0,"100%")]:
        lx = x + int(frac * w)
        (lw, _), _ = cv2.getTextSize(lbl, FT_SANS, 0.32, 1)
        lx = max(x, min(lx - lw//2, x + w - lw))
        cv2.putText(f, lbl, (lx, y+h+13), FT_SANS, 0.32, DIM, 1, cv2.LINE_AA)


def _status_colors(decision, danger_pct):
    if "CRITICAL" in decision or danger_pct > 0.65:
        return CRIT_FG, CRIT_BG, BAR_CRIT
    if "WARNING" in decision or danger_pct > 0.30:
        return WARN_FG, WARN_BG, BAR_WARN
    return SAFE_FG, SAFE_BG, BAR_SAFE


# =============================================================================
# render_frame — builds one complete frame from current state snapshot
# =============================================================================
def render_frame(decision, danger_pct, ttc, objects_count, btn_hover):
    W, H = CANVAS_W, CANVAS_H
    f = np.full((H, W, 3), BG, dtype=np.uint8)

    fg, st_bg, bar_clr = _status_colors(decision, danger_pct)
    M, GAP = 12, 8

    # ── HEADER ────────────────────────────────────────────────────────────────
    HDR = 36
    cv2.rectangle(f, (0, 0), (W, HDR), PANEL_BG, -1)
    cv2.line(f, (0, HDR), (W, HDR), BORDER, 1)

    _put(f, "TAIF UNIVERSITY   |   ROAD SAFETY AI", M, 24, 0.42, ACCENT)

    # الساعة — توضع يسار زر الإغلاق بمسافة 8px
    ts = datetime.now().strftime("%H:%M:%S")
    (tsw, _), _ = cv2.getTextSize(ts, FT_SANS, 0.42, 1)
    ts_x = BTN_X1 - tsw - 14
    _put(f, ts, ts_x, 24, 0.42, DIM)

    # ── CLOSE BUTTON ──────────────────────────────────────────────────────────
    btn_bg  = (70, 35, 35) if btn_hover else (55, 25, 25)
    btn_brd = (90, 65, 210) if btn_hover else (70, 50, 180)
    cv2.rectangle(f, (BTN_X1, BTN_Y1), (BTN_X2, BTN_Y2), btn_bg, -1)
    cv2.rectangle(f, (BTN_X1, BTN_Y1), (BTN_X2, BTN_Y2), btn_brd,
                  2 if btn_hover else 1)
    pad     = 8
    x_color = (110, 110, 255) if btn_hover else (80, 80, 210)
    cv2.line(f, (BTN_X1+pad, BTN_Y1+pad), (BTN_X2-pad, BTN_Y2-pad), x_color, 2, cv2.LINE_AA)
    cv2.line(f, (BTN_X2-pad, BTN_Y1+pad), (BTN_X1+pad, BTN_Y2-pad), x_color, 2, cv2.LINE_AA)

    # ── ROW 1: STATUS + TTC ───────────────────────────────────────────────────
    TOP  = HDR + M
    MID  = W // 2
    R1_H = 220

    # Panel A — STATUS
    aX, aY, aW, aH = M, TOP, MID - M - GAP, R1_H
    _panel(f, aX, aY, aW, aH, st_bg, fg, r=8)
    _put(f, "SYSTEM STATUS", aX+10, aY+22, 0.52, fg)
    cv2.line(f, (aX+8, aY+31), (aX+aW-8, aY+31), BORDER, 1)

    d_text  = decision if decision else "STANDBY"
    d_scale = _fit_text(d_text, aW - 28, FT_MONO, max_scale=1.5, thick=3)
    _centered(f, d_text, aX + aW//2, aY + 135, d_scale, fg, FT_MONO, thick=3)

    sublabels = {
        "SAFE":     "NO THREAT DETECTED",
        "WARNING":  "MONITOR SITUATION",
        "CRITICAL": "IMMEDIATE ACTION",
        "STANDBY":  "AWAITING INPUT",
        "WAITING":  "AWAITING INPUT",
    }
    _centered(f, sublabels.get(d_text, ""), aX + aW//2, aY + 165, 0.36, fg)

    # Panel B — TTC
    bX = MID + GAP
    bW = W - bX - M
    _panel(f, bX, TOP, bW, R1_H, PANEL_BG, BORDER, r=8)
    _put(f, "TIME TO COLLISION", bX+10, TOP+22, 0.52, ACCENT)
    cv2.line(f, (bX+8, TOP+31), (bX+bW-8, TOP+31), BORDER, 1)

    ttc_str   = f"{ttc:05.2f}"
    ttc_scale = _fit_text(ttc_str, bW - 60, FT_MONO, max_scale=2.0, thick=3)
    ttc_color = fg if danger_pct > 0.30 else WHITE
    (tw, _), _ = cv2.getTextSize(ttc_str, FT_MONO, ttc_scale, 3)
    (uw, _), _ = cv2.getTextSize(" sec",  FT_SANS, 0.50, 1)
    sx = bX + (bW - tw - uw) // 2
    cv2.putText(f, ttc_str, (sx,    TOP+130), FT_MONO, ttc_scale, ttc_color, 3, cv2.LINE_AA)
    cv2.putText(f, " sec",  (sx+tw, TOP+130), FT_SANS, 0.50,      ACCENT,    1, cv2.LINE_AA)

    if ttc <= 0:      q = "NO DATA"
    elif ttc < 2.0:   q = "CRITICAL RANGE"
    elif ttc < 4.0:   q = "WARNING RANGE"
    else:             q = "SAFE DISTANCE"
    _centered(f, q, bX + bW//2, TOP + 165, 0.36, fg)

    # ── ROW 2: DANGER BAR ─────────────────────────────────────────────────────
    R2_Y = TOP + R1_H + GAP
    R2_H = 72
    _panel(f, M, R2_Y, W-2*M, R2_H, PANEL_BG, BORDER, r=6)
    _put(f, "AI DANGER LEVEL", M+10, R2_Y+22, 0.52, ACCENT)

    pct_str = f"{int(danger_pct*100):3d}%"
    (pw, _), _ = cv2.getTextSize(pct_str, FT_MONO, 0.72, 2)
    cv2.putText(f, pct_str, (W-M-pw-10, R2_Y+22), FT_MONO, 0.72, fg, 2, cv2.LINE_AA)
    _danger_bar(f, M+10, R2_Y+28, W-2*M-20, 20, danger_pct, bar_clr)

    # ── ROW 3: FOOTER TILES ───────────────────────────────────────────────────
    R3_Y  = R2_Y + R2_H + GAP + 14
    R3_H  = H - R3_Y - M
    tw_   = (W - 2*M - GAP*3) // 4
    tiles = [
        ("OBJECTS",  str(objects_count), WHITE),
        ("SENSOR",   "CAM+LiDAR",        ACCENT),
        ("MODEL",    "YOLOv8+LSTM",       ACCENT),
        ("GPU",      "ORIN  OK",          SAFE_FG),
    ]
    for i, (lbl, val, vc) in enumerate(tiles):
        tx = M + i * (tw_ + GAP)
        _panel(f, tx, R3_Y, tw_, R3_H, PANEL_BG, BORDER, r=5)
        _centered(f, lbl, tx + tw_//2, R3_Y + 22, 0.48, DIM)
        vs = _fit_text(val, tw_ - 16, FT_MONO, max_scale=0.70, min_scale=0.28, thick=1)
        _centered(f, val, tx + tw_//2, R3_Y + R3_H - 10, vs, vc, FT_MONO, thick=1)

    # أضيفي هذا المنطق قبل إرجاع الفريم (return f)
    if v2x_code == 1:
        cv2.rectangle(f, (0, 0), (CANVAS_W, 40), (0, 0, 200), -1)
        _centered(f, "V2X ALERT: ACCIDENT AHEAD!", CANVAS_W//2, 30, 0.7, WHITE, thick=2)

    return f


# =============================================================================
# main — OpenCV render loop على MAIN THREAD، ROS2 على thread منفصل
# =============================================================================
def main(args=None):
    rclpy.init(args=args)

    state     = DashState()
    node      = DisplayNode(state)
    executor  = MultiThreadedExecutor()
    executor.add_node(node)

    # ROS2 يعمل في background thread
    ros_thread = threading.Thread(target=executor.spin, daemon=True)
    ros_thread.start()

    # ── OpenCV window setup (main thread) ────────────────────────────────────
    cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN_NAME, CANVAS_W, CANVAS_H)
    cv2.setWindowProperty(WIN_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    btn_hover = False

    def mouse_cb(event, x, y, flags, param):
        nonlocal btn_hover
        inside = (BTN_X1 <= x <= BTN_X2 and BTN_Y1 <= y <= BTN_Y2)
        if event == cv2.EVENT_MOUSEMOVE:
            btn_hover = inside
        elif event == cv2.EVENT_LBUTTONDOWN and inside:
            # إرسال SIGINT للعملية نفسها — يُحاكي Ctrl+C ويُفعّل finally
            os.kill(os.getpid(), signal.SIGINT)

    cv2.setMouseCallback(WIN_NAME, mouse_cb)

    # ── Render loop ───────────────────────────────────────────────────────────
    try:
        while rclpy.ok():
            decision, danger_pct, ttc, objects_count = state.snapshot()
            frame = render_frame(decision, danger_pct, ttc, objects_count, btn_hover)
            cv2.imshow(WIN_NAME, frame)

            # waitKey(33) = ~30fps cap — يستقبل keyboard input بشكل موثوق
            # على main thread بدون تداخل مع ROS2
            key = cv2.waitKey(33) & 0xFF
            if key in (27, ord('q'), ord('Q')):
                node.get_logger().info("Keyboard exit.")
                break

    except KeyboardInterrupt:
        pass

    finally:
        node.get_logger().info("Shutting down display node.")
        cv2.destroyAllWindows()
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
