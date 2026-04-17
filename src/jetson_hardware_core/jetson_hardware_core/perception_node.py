#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String  # أضفنا هذا لاستيراد نوع الرسالة النصية
from cv_bridge import CvBridge
import cv2
import numpy as np
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

class JetsonPerceptionNode(Node):
    def __init__(self):
        super().__init__('perception_node')
        self.bridge = CvBridge()
        self.trt_logger = trt.Logger(trt.Logger.INFO)
        
        # 1. إعداد المحرك (تأكدي من صحة المسار)
        engine_path = "/home/sadeem/ros2_ws/src/system_core/system_core/best.engine"
        with open(engine_path, "rb") as f:
            runtime = trt.Runtime(self.trt_logger)
            self.engine = runtime.deserialize_cuda_engine(f.read())
        
        self.trt_context = self.engine.create_execution_context()
        self.classes = ['Vehicle', 'Pedestrian'] 
        
        # 2. تخصيص الذاكرة (كما هي)
        self.inputs, self.outputs, self.allocations = [], [], []
        self.stream = cuda.Stream()
        for i in range(self.engine.num_io_tensors):
            name = self.engine.get_tensor_name(i)
            dtype = trt.nptype(self.engine.get_tensor_dtype(name))
            shape = self.engine.get_tensor_shape(name)
            size = trt.volume(shape)
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            self.allocations.append(int(device_mem))
            if self.engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT:
                self.inputs.append({'host': host_mem, 'device': device_mem, 'name': name, 'shape': shape})
            else:
                self.outputs.append({'host': host_mem, 'device': device_mem, 'name': name, 'shape': shape})

        # 3. الناشرون والمشتركون
        self.subscription = self.create_subscription(Image, '/hardware/camera/image_raw', self.image_callback, 10)
        
        # ناشر الصورة (للعرض البشري HMI)
        self.image_pub = self.create_publisher(Image, '/perception/image_with_bboxes', 10)
        
        # ناشر البيانات الرقمية (لعقدة الدمج Fusion Node)
        self.detection_pub = self.create_publisher(String, '/perception/detections', 10)
        
        self.get_logger().info("🚀 Perception System: Visual & Data Output is Ready!")

    def preprocess(self, image):
        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (640, 640))
        img = img.transpose((2, 0, 1)).astype(np.float32)
        img /= 255.0
        return np.ascontiguousarray(img)

    def postprocess(self, output, orig_shape):
        output = output.reshape(self.outputs[0]['shape']).squeeze().transpose()
        boxes, confs, class_ids = [], [], []
        h_orig, w_orig = orig_shape[:2]
        x_factor, y_factor = w_orig / 640, h_orig / 640

        for row in output:
            score = np.max(row[4:])
            if score > 0.5:
                class_id = np.argmax(row[4:])
                cx, cy, w, h = row[:4]
                left = int((cx - w/2) * x_factor)
                top = int((cy - h/2) * y_factor)
                width = int(w * x_factor)
                height = int(h * y_factor)
                boxes.append([left, top, width, height])
                confs.append(float(score))
                class_ids.append(class_id)

        indices = cv2.dnn.NMSBoxes(boxes, confs, 0.5, 0.45)
        return [(boxes[i], confs[i], class_ids[i]) for i in indices]

    def image_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            input_data = self.preprocess(frame)
            
            # تنفيذ الاستنتاج
            np.copyto(self.inputs[0]['host'], input_data.ravel())
            cuda.memcpy_htod_async(self.inputs[0]['device'], self.inputs[0]['host'], self.stream)
            for inp in self.inputs: self.trt_context.set_tensor_address(inp['name'], inp['device'])
            for out in self.outputs: self.trt_context.set_tensor_address(out['name'], out['device'])
            self.trt_context.execute_async_v3(stream_handle=self.stream.handle)
            cuda.memcpy_dtoh_async(self.outputs[0]['host'], self.outputs[0]['device'], self.stream)
            self.stream.synchronize()

            detections = self.postprocess(self.outputs[0]['host'], frame.shape)
            
            # --- الجزء الجديد: تجهيز ونشر البيانات الرقمية ---
            detection_strings = []
            for (box, conf, cls_id) in detections:
                x, y, w, h = box
                # نحسب مركز المربع (Center X) لأنه الأهم لربطه بزاوية الليدار
                center_x = x + (w / 2)
                
                # نجهز نص يحتوي على: الفئة، المركز، العرض، الارتفاع
                detection_info = f"{self.classes[cls_id]},{center_x},{y},{w},{h}"
                detection_strings.append(detection_info)

                # الرسم (للعرض فقط)
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, self.classes[cls_id], (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # دمج كل الكائنات المكتشفة في رسالة واحدة تفصل بينها فاصلة منقوطة (;)
            data_msg = String()
            data_msg.data = ";".join(detection_strings)
            self.detection_pub.publish(data_msg)
            # -----------------------------------------------

            self.image_pub.publish(self.bridge.cv2_to_imgmsg(frame, encoding="bgr8"))
            
        except Exception as e:
            self.get_logger().error(f"Error: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = JetsonPerceptionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__': main()
