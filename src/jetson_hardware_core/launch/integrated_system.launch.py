from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 1. عقدة تعريف الليدار (التعامل مع الجهاز مباشرة)
        Node(
            package='rplidar_ros',
            executable='rplidar_node',
            name='rplidar_driver',
            parameters=[{
                'serial_port': '/dev/ttyUSB0', # تأكدي من المنفذ في الجيتسون
                'serial_baudrate': 115200,
                'frame_id': 'laser',
                'angle_compensate': True,
                'scan_mode': 'Standard'
            }],
            output='screen'
        ),

        # 2. عقدة معالجة بيانات الليدار (تصفية الـ Scan)
        Node(
            package='jetson_hardware_core',
            executable='lidar_processor_node',
            name='lidar_processor_node',
            output='screen'
        ),

        # 3. عقدة الكاميرا
        Node(
            package='jetson_hardware_core',
            executable='camera_reader_node',
            name='camera_reader_node',
            output='screen'
        ),
        
        Node(
     	    package='jetson_hardware_core',
     	    executable='perception_node',
     	    name='perception_node',
     	    output='screen',
     	    parameters=[{
        	'model_engine_path': '/home/sadeem/ros2_ws/src/jetson_hardware_core/models/yolov8_n_safety.engine',
        	'conf_threshold': 0.25,
        	'iou_threshold': 0.45,
        	'input_topic': '/hardware/camera/image_raw',
        	'output_topic': '/perception/detected_objects'
        	}],
            remappings=[('/input/camera_image', '/hardware/camera/image_raw')]
            ),

        # 4. عقدة دمج البيانات (قلب النظام) مع الربط الإجباري
        Node(
            package='jetson_hardware_core',
            executable='sensor_fusion_node',
            name='sensor_fusion_node',
            output='screen',
            remappings=[
                ('/input/camera_topic', '/hardware/camera/image_raw'),
                ('/input/lidar_topic', '/hardware/lidar/processed_data')
            ]
        ),

        # 5. عقدة التنبؤ (LSTM)
        Node(
            package='jetson_hardware_core',
            executable='prediction_node',
            name='prediction_node',
            output='screen'
        ),

        # 6. عقدة تقييم الخطر (TTC)
        Node(
            package='jetson_hardware_core',
            executable='risk_assessment_node',
            name='risk_assessment_node',
            output='screen'
        ),

        # 7. عقدة القرار النهائي
        Node(
            package='jetson_hardware_core',
            executable='collision_decision_node',
            name='collision_decision_node',
            output='screen'
        ),
        
        # 8. عقدة شاشة التنبيه
        Node(
            package='jetson_hardware_core',
            executable='display_node',
            name='display_node',
            output='screen'
        ),
    ])
