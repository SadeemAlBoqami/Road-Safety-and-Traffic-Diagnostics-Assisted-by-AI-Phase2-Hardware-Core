import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32
import time

class RiskAssessmentNode(Node):
    def __init__(self):
        super().__init__('risk_assessment_node')

        # إعدادات العتبات (Thresholds)
        self.critical_ttc = 1.5  # ثانية واحدة (فرملة طارئة)
        self.warning_ttc = 3.0   # 3 ثوانٍ (تنبيه)

        # متغيرات لحساب السرعة
        self.last_dist = None
        self.last_time = None

        # الاشتراك والناشر
        self.subscription = self.create_subscription(String, '/system/fused_objects', self.fusion_callback, 10)
        self.ttc_pub = self.create_publisher(Float32, '/system/ttc_value', 10)
        self.alert_pub = self.create_publisher(String, '/system/emergency_alerts', 10)

        self.get_logger().info('✅ TTC Risk Assessment Node is Active!')

    def fusion_callback(self, msg):
        try:
            # استخراج المسافة من النص القادم من Fusion
            # "Obj:Vehicle|Dist:5.50|Angle:12.5"
            parts = msg.data.split('|')
            dist_raw = parts[1].split(':')[1]        # سيأخذ "5.50m"
            dist_clean = dist_raw.replace('m', '')   # سيحذف 'm' لتصبح "5.50"
            current_dist = float(dist_clean.strip()) # التحويل الآمن لرقم
            current_time = self.get_clock().now().nanoseconds / 1e9

            if self.last_dist is not None:
                # 1. حساب السرعة النسبية (Relative Velocity)
                dt = current_time - self.last_time
                if dt <= 0: return
                
                v_rel = (self.last_dist - current_dist) / dt

                # 2. حساب TTC فقط إذا كان الجسم يقترب (v_rel موجبة)
                if v_rel > 0.1:  # الجسم يقترب بسرعة أكثر من 0.1 م/ث
                    ttc = current_dist / v_rel
                    
                    # نشر قيمة TTC
                    ttc_msg = Float32()
                    ttc_msg.data = ttc
                    self.ttc_pub.publish(ttc_msg)

                    # 3. منطق اتخاذ القرار
                    self.evaluate_risk(ttc)
                else:
                    # الجسم يبتعد أو ثابت السرعة
                    ttc_msg = Float32()
                    ttc_msg.data = 99.0 # قيمة افتراضية تعني "لا خطر"
                    self.ttc_pub.publish(ttc_msg)

            # تحديث القيم السابقة
            self.last_dist = current_dist
            self.last_time = current_time

        except Exception as e:
            self.get_logger().error(f'Error: {e}')

    def evaluate_risk(self, ttc):
        alert_msg = String()
        if ttc <= self.critical_ttc:
            alert_msg.data = "CRITICAL: EMERGENCY BRAKE REQUIRED!"
            self.get_logger().error(alert_msg.data)
            self.alert_pub.publish(alert_msg)
        elif ttc <= self.warning_ttc:
            alert_msg.data = "WARNING: Collision Risk Ahead"
            self.get_logger().warn(alert_msg.data)
            self.alert_pub.publish(alert_msg)

def main(args=None):
    rclpy.init(args=args)
    node = RiskAssessmentNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
