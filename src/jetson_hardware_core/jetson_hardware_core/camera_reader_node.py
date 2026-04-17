#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class CameraReaderNode(Node):
    def __init__(self):
        super().__init__('camera_reader_node')
        
        # Publisher for the raw image
        self.publisher_ = self.create_publisher(Image, '/hardware/camera/image_raw', 10)
        self.bridge = CvBridge()
        
        # GStreamer pipeline optimized for IMX219 CSI Camera on NVIDIA Jetson
        gstreamer_pipeline = (
            "nvarguscamerasrc sensor-id=0 ! "
            "video/x-raw(memory:NVMM), width=1280, height=720, format=(string)NV12, framerate=30/1 ! "
            "nvvidconv flip-method=0 ! "
            "video/x-raw, width=1280, height=720, format=(string)BGRx ! "
            "videoconvert ! "
            "video/x-raw, format=(string)BGR ! appsink drop=true sync=false"
        )
        
        self.get_logger().info("Initializing CSI Camera (IMX219) using GStreamer...")
        self.cap = cv2.VideoCapture(gstreamer_pipeline, cv2.CAP_GSTREAMER)
        
        if not self.cap.isOpened():
            self.get_logger().error("Failed to open CSI Camera! Please check the ribbon cable connection and sensor-id.")
        else:
            self.get_logger().info("CSI Camera successfully opened.")
            self.get_logger().info("Publishing to topic: /hardware/camera/image_raw at ~30 FPS")
            
            # Timer to fetch and publish frames at 30 FPS
            self.timer = self.create_timer(1.0 / 30.0, self.timer_callback)

    def timer_callback(self):
        ret, frame = self.cap.read()
        if ret:
            # Convert OpenCV frame to ROS 2 Image message and publish
            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            self.publisher_.publish(msg)
        else:
            # Throttled warning so it doesn't flood the terminal if the camera drops
            self.get_logger().warn("Failed to capture frame from camera.", throttle_duration_sec=2.0)

    def destroy_node(self):
        # Safely release the camera resource when shutting down
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
            self.get_logger().info("Camera resource released.")
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = CameraReaderNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("KeyboardInterrupt received. Shutting down Camera Reader Node...")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
