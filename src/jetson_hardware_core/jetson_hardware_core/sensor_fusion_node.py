#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from visualization_msgs.msg import MarkerArray
import math
import time

class SensorFusionNode(Node):
    def __init__(self):
        super().__init__('sensor_fusion_node')
        
        # 1. الإعدادات الهندسية (Camera Extrinsics & Intrinsics)
        self.declare_parameter('fov_h', 79.3)  # من مواصفات IMX219-77
        self.declare_parameter('img_w', 640)
        self.FOV_H = self.get_parameter('fov_h').value
        self.IMG_W = self.get_parameter('img_w').value
        
        # 2. المشتركون (Subscribers)
        # استقبال إحداثيات الكاميرا: "Class,CenterX,Y,W,H"
        self.cam_sub = self.create_subscription(String, '/perception/detections', self.process_fusion, 10)
        # استقبال الأجسام المكتشفة من الليدار
        self.lidar_sub = self.create_subscription(MarkerArray, '/detected_clusters_markers', self.update_lidar_data, 10)
        
        # 3. الناشر (Publisher) لنتائج الدمج النهائية
        self.fusion_pub = self.create_publisher(String, '/system/fused_objects', 10)

        self.latest_lidar_objects = []
        self.get_logger().info("✅ Sensor Fusion Node: Academic Framework Active.")

    def update_lidar_data(self, msg):
        """تحديث مخزن بيانات الليدار وتحويلها لإحداثيات قطبية"""
        self.latest_lidar_objects = []
        for marker in msg.markers:
            x, y = marker.pose.position.x, marker.pose.position.y
            distance = math.sqrt(x**2 + y**2)
            # الزاوية بالدرجات (atan2 يعطي النتائج من -180 إلى 180)
            angle = math.degrees(math.atan2(y, x))
            self.latest_lidar_objects.append({'dist': distance, 'angle': angle, 'ts': time.time()})

    def process_fusion(self, msg):
        """الخوارزمية المركزية للمطابقة (Data Association)"""
        if not msg.data or not self.latest_lidar_objects:
            return

        cam_detections = msg.data.split(';')
        fused_results = []

        for det in cam_detections:
            data = det.split(',')
            if len(data) < 2: continue
            
            obj_class = data[0]
            center_x = float(data[1])
            
            # أ- التحويل من بكسل إلى زاوية (Mapping Function)
            # المبدأ: الخطية في توزيع البكسلات بالنسبة للزاوية
            angle_cam = ( (center_x / self.IMG_W) - 0.5 ) * self.FOV_H
            
            # ب- خوارزمية البحث عن الجار الأقرب (Nearest Neighbor Gating)
            best_match = None
            min_diff = 5.0  # Threshold: 5 degrees
            
            for obj in self.latest_lidar_objects:
                # تصحيح إشارة زاوية الليدار لتتطابق مع اتجاه الكاميرا
                # غالباً الليدار يحسب لليسار موجب والكاميرا لليمن موجب، لذا نعكس أحدهما
                diff = abs(angle_cam - (-obj['angle']))
                
                if diff < min_diff:
                    min_diff = diff
                    best_match = obj

            # ج- تجميع البيانات المصادق عليها
            if best_match:
                result = f"Obj:{obj_class}|Dist:{best_match['dist']:.2f}m|Angle:{angle_cam:.1f}"
                fused_results.append(result)
                self.get_logger().info(f"🎯 Fused: {result}")

        # نشر النتيجة النهائية
        if fused_results:
            output = String()
            output.data = ";".join(fused_results)
            self.fusion_pub.publish(output)

def main(args=None):
    rclpy.init(args=args)
    node = SensorFusionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

