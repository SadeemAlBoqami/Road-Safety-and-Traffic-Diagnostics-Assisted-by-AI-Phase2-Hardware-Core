#include <esp_now.h>
#include <WiFi.h>
#include <Wire.h> 
#include <LiquidCrystal_I2C.h>

// إعداد الشاشة: العنوان الغالب هو 0x27 وحجمها 16x2
LiquidCrystal_I2C lcd(0x27, 16, 2);

const int BUTTON_PIN = 4;

typedef struct struct_v2x_msg {
    int device_id;
    int alert_code;
    float lat;
} struct_v2x_msg;

struct_v2x_msg myData;
uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// دالة لتحويل الكود الرقمي إلى نص للـ LCD
String getScenarioName(int code) {
  switch (code) {
    case 1: return "ACCIDENT";
    case 2: return "TRAFFIC JAM";
    case 3: return "GREEN LIGHT";
    case 4: return "RED LIGHT";
    case 5: return "ROAD WORKS";
    default: return "UNKNOWN";
  }
}

void setup() {
  Serial.begin(115200);
  
  // تهيئة الشاشة
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("V2X RSU READY");
  
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  
  WiFi.mode(WIFI_STA);
  esp_now_init();
  
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  esp_now_add_peer(&peerInfo);

  randomSeed(analogRead(0));
}

void loop() {
  if (digitalRead(BUTTON_PIN) == LOW) {
    myData.device_id = 101;
    myData.alert_code = random(1, 6); 
    myData.lat = 21.27;

    esp_now_send(broadcastAddress, (uint8_t *) &myData, sizeof(myData));
    
    // تحديث الشاشة بالسيناريو الجديد
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("V2X SENDING...");
    lcd.setCursor(0, 1);
    lcd.print(getScenarioName(myData.alert_code));

    Serial.print("Triggered Scenario: ");
    Serial.println(getScenarioName(myData.alert_code));

    delay(500); 
  }
}