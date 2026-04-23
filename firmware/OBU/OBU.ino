#include <micro_ros_arduino.h>
#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <std_msgs/msg/int32.h>
#include <esp_now.h>
#include <WiFi.h>

// تعريف الهيكل
typedef struct struct_v2x_msg {
    int device_id;
    int alert_code;
    float lat;
} struct_v2x_msg;

struct_v2x_msg incomingData;

// متغيرات ROS 2
rcl_publisher_t publisher;
std_msgs__msg__Int32 msg;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

// --- التعديل هنا: التوقيع الجديد للدالة المعتمد في إصدار 3.x ---
void OnDataRecv(const esp_now_recv_info * recv_info, const uint8_t *incoming, int len) {
    memcpy(&incomingData, incoming, sizeof(incomingData));
    
    // إرسال كود التنبيه إلى الجيتسون
    msg.data = incomingData.alert_code;
    rcl_publish(&publisher, &msg, NULL);
}

void setup() {
  set_microros_transports();
  
  WiFi.mode(WIFI_STA);
  
  if (esp_now_init() != ESP_OK) {
    return;
  }
  
  // تسجيل دالة الاستقبال
  esp_now_register_recv_cb(OnDataRecv);

  // إعداد Micro-ROS
  allocator = rcl_get_default_allocator();
  rclc_support_init(&support, 0, NULL, &allocator);
  rclc_node_init_default(&node, "v2x_bridge_node", "", &support);
  
  rclc_publisher_init_default(
    &publisher, &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
    "v2x_alerts");
}

void loop() {
  // ترك التأخير بسيطاً للسماح بمعالجة الخلفية
  delay(10);
}