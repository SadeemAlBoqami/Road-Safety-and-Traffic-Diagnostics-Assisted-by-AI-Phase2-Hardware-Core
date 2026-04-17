import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, String

class CollisionDecisionNode(Node):
    def __init__(self):
        super().__init__('collision_decision_node')
        
        # إعدادات العتبات المعتمدة (NHTSA/Euro NCAP Standards)
        self.ttc_warning_threshold = 4.0  # ثوانٍ
        self.ttc_critical_threshold = 2.0 # ثوانٍ
        self.lstm_warning_threshold = 0.5 # احتمالية 50%
        self.lstm_critical_threshold = 0.8 # احتمالية 80%

        # تخزين آخر النتائج المستلمة
        self.current_lstm_prob = 0.0
        self.current_ttc_value = 99.0  # قيمة افتراضية تعني "آمن"

        # الاشتراكات (Subscribers)
        self.create_subscription(Float32, '/system/danger_level', self.lstm_callback, 10)
        self.create_subscription(Float32, '/system/ttc_value', self.ttc_callback, 10)
        
        # الناشر النهائي (Publisher)
        # هذا التوبيك هو ما سيتم مراقبته على اللابتوب لاتخاذ فعل
        self.decision_pub = self.create_publisher(String, '/system/final_decision', 10)

        self.get_logger().info('✅ Collision Decision Node is operational with 4s/2s logic.')

    def lstm_callback(self, msg):
        self.current_lstm_prob = msg.data
        self.process_final_decision()

    def ttc_callback(self, msg):
        self.current_ttc_value = msg.data
        self.process_final_decision()

    def process_final_decision(self):
        """
        تطبيق منطق الاندماج لاتخاذ القرار النهائي:
        - الحالة الحرجة (Critical): إذا كان TTC أقل من ثانيتين أو LSTM يتوقع خطراً عالياً جداً.
        - حالة التحذير (Warning): إذا كان TTC أقل من 4 ثوانٍ أو LSTM يكتشف نمطاً مقلقاً.
        """
        final_msg = String()
        
        # 1. حالة التنبيه الحرج (Critical Alert)
        if self.current_ttc_value < self.ttc_critical_threshold or \
           self.current_lstm_prob >= self.lstm_critical_threshold:
            final_msg.data = "CRITICAL: EMERGENCY BRAKE REQUIRED"
            self.get_logger().error(f"🚨 {final_msg.data} (TTC: {self.current_ttc_value:.2f}s, AI: {self.current_lstm_prob:.2f})")
        
        # 2. حالة التحذير (Warning)
        elif self.current_ttc_value < self.ttc_warning_threshold or \
             self.current_lstm_prob >= self.lstm_warning_threshold:
            final_msg.data = "WARNING: REDUCE SPEED"
            self.get_logger().warn(f"⚠️ {final_msg.data} (TTC: {self.current_ttc_value:.2f}s, AI: {self.current_lstm_prob:.2f})")
        
        # 3. الحالة الآمنة (Safe Status)
        else:
            final_msg.data = "STATUS: SAFE"
            # لا نطبع رسائل الـ SAFE بكثرة لتقليل الضوضاء في التيرمينال

        self.decision_pub.publish(final_msg)

def main(args=None):
    rclpy.init(args=args)
    node = CollisionDecisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
