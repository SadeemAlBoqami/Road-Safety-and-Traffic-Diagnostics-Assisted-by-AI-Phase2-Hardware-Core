import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from visualization_msgs.msg import Marker, MarkerArray
import numpy as np

class LidarProcessorNode(Node):
    def __init__(self):
        super().__init__('lidar_processor_node')
        
        self.subscription = self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.marker_pub = self.create_publisher(MarkerArray, '/detected_clusters_markers', 10)
        
        # معاملات التجميع
        self.cluster_threshold = 0.2  # المسافة القصوى بين نقطتين لاعتبارهما نفس الجسم (20 سم)
        self.min_points = 3           # أقل عدد نقاط لتشكيل جسم

        self.get_logger().info("✅ Lidar Processor Node (Clustering) is Active!")

    def scan_callback(self, msg):
        ranges = np.array(msg.ranges)
        angles = np.linspace(msg.angle_min, msg.angle_max, len(ranges))
        
        # 1. تحويل الإحداثيات لـ Cartesian
        # نستبعد القراءات الخاطئة أو البعيدة جداً
        valid = (ranges > msg.range_min) & (ranges < msg.range_max)
        x = ranges[valid] * np.cos(angles[valid])
        y = ranges[valid] * np.sin(angles[valid])
        points = np.stack((x, y), axis=1)

        if len(points) == 0: return

        # 2. خوارزمية التجميع البسيطة
        clusters = []
        if len(points) > 0:
            current_cluster = [points[0]]
            for i in range(1, len(points)):
                dist = np.linalg.norm(points[i] - points[i-1])
                if dist < self.cluster_threshold:
                    current_cluster.append(points[i])
                else:
                    if len(current_cluster) >= self.min_points:
                        clusters.append(np.array(current_cluster))
                    current_cluster = [points[i]]
            # إضافة آخر مجموعة
            if len(current_cluster) >= self.min_points:
                clusters.append(np.array(current_cluster))

        self.publish_markers(clusters)

    def publish_markers(self, clusters):
        # وظيفة هذه الدالة هي عرض "دوائر" في RViz تمثل الأجسام المكتشفة
        marker_array = MarkerArray()
        for i, cluster in enumerate(clusters):
            center = np.mean(cluster, axis=0)
            marker = Marker()
            marker.header.frame_id = "laser"
            marker.id = i
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            marker.pose.position.x = float(center[0])
            marker.pose.position.y = float(center[1])
            marker.scale.x = 0.2
            marker.scale.y = 0.2
            marker.scale.z = 0.2
            marker.color.a = 1.0
            marker.color.g = 1.0  # لون أخضر للأجسام المكتشفة
            marker_array.markers.append(marker)
        
        self.marker_pub.publish(marker_array)

def main(args=None):
    rclpy.init(args=args)
    node = LidarProcessorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
