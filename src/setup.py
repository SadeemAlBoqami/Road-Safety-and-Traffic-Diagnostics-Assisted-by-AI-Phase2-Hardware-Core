import os
from glob import glob
from setuptools import setup

package_name = 'jetson_hardware_core'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # سطر ملفات الـ launch
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='sadeem',
    maintainer_email='sadeem@todo.todo',
    description='Integrated Hardware Core for Jetson AI Robot',
    license='TODO: License declaration',
    # tests_require=['pytest'],
    
   entry_points={
        'console_scripts': [
            # الطرف الأيسر هو الاسم الذي يناديه ملف الـ Launch
            'camera_reader_node = jetson_hardware_core.camera_reader_node:main',
            'sensor_fusion_node  = jetson_hardware_core.sensor_fusion_node:main',
            'perception_node = jetson_hardware_core.perception_node:main',
            'lidar_processor_node = jetson_hardware_core.lidar_processor_node:main',
            'prediction_node = jetson_hardware_core.prediction_node:main',
            'risk_assessment_node = jetson_hardware_core.risk_assessment_node:main',
            'collision_decision_node = jetson_hardware_core.collision_decision_node:main',
        ],
    },
)
