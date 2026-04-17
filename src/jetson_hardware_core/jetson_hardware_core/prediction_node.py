import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32
import numpy as np
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
from collections import deque

class PredictionNode(Node):
    def __init__(self):
        super().__init__('prediction_node')
        
        # 1. إعدادات المسارات والنموذج
        self.engine_path = '/home/sadeem/ros2_ws/src/jetson_hardware_core/models/lstm_model_v4.engine'
        self.sequence_length = 50
        self.num_features = 6
        
        # ذاكرة مؤقتة لآخر 50 إطاراً
        self.data_buffer = deque(maxlen=self.sequence_length)
        
        # 2. تهيئة TensorRT (نسخة 10.x)
        self.logger = trt.Logger(trt.Logger.INFO)
        self.load_engine()
        self.allocate_buffers()

        # 3. الاشتراكات والناشرون
        self.subscription = self.create_subscription(String, '/system/fused_objects', self.fusion_callback, 10)
        self.danger_pub = self.create_publisher(Float32, '/system/danger_level', 10)

        self.get_logger().info('✅ Prediction Node (LSTM Engine v10) is Active!')

    def load_engine(self):
        """تحميل المحرك وفك تسلسله"""
        with open(self.engine_path, "rb") as f:
            runtime = trt.Runtime(self.logger)
            self.engine = runtime.deserialize_cuda_engine(f.read())
        
        # تغيير الاسم من context إلى trt_context لتجنب تعارض ROS 2
        self.trt_context = self.engine.create_execution_context()

    def allocate_buffers(self):
        """تخصيص الذاكرة باستخدام الأسماء (TensorRT 10 API)"""
        # الحصول على أسماء المدخلات والمخرجات
        self.input_name = self.engine.get_tensor_name(0)
        self.output_name = self.engine.get_tensor_name(1)

        # الحصول على الأبعاد (الحل للخطأ AttributeError)
        input_shape = self.engine.get_tensor_shape(self.input_name)
        output_shape = self.engine.get_tensor_shape(self.output_name)

        # حجز مساحة الذاكرة
        self.h_input = cuda.pagelocked_empty(trt.volume(input_shape), dtype=np.float32)
        self.h_output = cuda.pagelocked_empty(trt.volume(output_shape), dtype=np.float32)
        self.d_input = cuda.mem_alloc(self.h_input.nbytes)
        self.d_output = cuda.mem_alloc(self.h_output.nbytes)
        self.stream = cuda.Stream()

    def fusion_callback(self, msg):
        """استقبال البيانات وتغذية الـ Buffer"""
        try:
            parts = msg.data.split('|')
            dist = float(parts[1].split(':')[1])
            angle = float(parts[2].split(':')[1])
            
            # تمثيل البيانات (6 خصائص كما تدرب النموذج)
            current_frame = [0.0, 0.0, 0.0, 0.0, dist, angle]
            self.data_buffer.append(current_frame)
            
            if len(self.data_buffer) == self.sequence_length:
                self.infer()
        except:
            pass

    def infer(self):
        """عملية التنبؤ باستخدام Async V3 API"""
        input_data = np.array(self.data_buffer, dtype=np.float32).flatten()
        np.copyto(self.h_input, input_data)

        # نقل البيانات للـ GPU
        cuda.memcpy_htod_async(self.d_input, self.h_input, self.stream)

        # ربط الذاكرة بأسماء التنسورات
        self.trt_context.set_tensor_address(self.input_name, int(self.d_input))
        self.trt_context.set_tensor_address(self.output_name, int(self.d_output))

        # تنفيذ الحسابات (Async V3 هو المعيار الجديد)
        self.trt_context.execute_async_v3(stream_handle=self.stream.handle)

        # إعادة النتيجة
        cuda.memcpy_dtoh_async(self.h_output, self.d_output, self.stream)
        self.stream.synchronize()

        collision_prob = float(self.h_output[0])
        
        # نشر الاحتمالية
        msg = Float32()
        msg.data = collision_prob
        self.danger_pub.publish(msg)

        if collision_prob > 0.75:
            self.get_logger().warn(f'🚨 HIGH RISK DETECTED: {collision_prob:.2f}')

def main(args=None):
    rclpy.init(args=args)
    node = PredictionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
