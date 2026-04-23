#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32

class V2XScenarioManager(Node):
    def __init__(self):
        super().__init__('v2x_scenario_manager')
        
        # إنشاء الاشتراك في موضوع التنبيهات القادم من الـ ESP32
        self.subscription = self.create_subscription(
            Int32,
            'v2x_alerts',
            self.listener_callback,
            10)
            
        self.get_logger().info('=========================================')
        self.get_logger().info('V2X Diagnostics Manager has been started')
        self.get_logger().info('Waiting for V2X Alert from RSU...')
        self.get_logger().info('=========================================')

    def listener_callback(self, msg):
        scenario = msg.data
        
        # تحليل السيناريو بناءً على القيمة المستلمة عشوائياً من الـ RSU
        if scenario == 1:
            self.get_logger().error('🚨 [CRITICAL] SCENARIO 1: ACCIDENT DETECTED! Sending Stop Command to Motors.')
            # هنا سيتم لاحقاً استدعاء دالة التوقف في حزمة jetson_hardware_core
            
        elif scenario == 2:
            self.get_logger().warning('⚠️ [WARNING] SCENARIO 2: HEAVY TRAFFIC AHEAD! Reducing speed by 50%.')
            
        elif scenario == 3:
            self.get_logger().info('🟢 [STATUS] SCENARIO 3: SMART LIGHT IS GREEN. Proceeding normally.')
            
        elif scenario == 4:
            self.get_logger().info('🔴 [STATUS] SCENARIO 4: SMART LIGHT IS RED. Waiting at the line.')
            
        elif scenario == 5:
            self.get_logger().warning('🚧 [CAUTION] SCENARIO 5: ROAD WORKS AHEAD. Transitioning to safe lane.')
            
        else:
            self.get_logger().info(f'🔎 [INFO] Received unknown V2X code: {scenario}')

def main(args=None):
    rclpy.init(args=args)
    
    # إنشاء الكائن (Node)
    v2x_node = V2XScenarioManager()
    
    try:
        # إبقاء العقدة تعمل لاستقبال البيانات
        rclpy.spin(v2x_node)
    except KeyboardInterrupt:
        v2x_node.get_logger().info('V2X Manager shutting down...')
    finally:
        # تنظيف الذاكرة عند الإغلاق
        v2x_node.destroy_node()
        rclpy.shutdown()

# --- السطر الحاسم الذي يضمن تشغيل الكود ---
if __name__ == '__main__':
    main()
