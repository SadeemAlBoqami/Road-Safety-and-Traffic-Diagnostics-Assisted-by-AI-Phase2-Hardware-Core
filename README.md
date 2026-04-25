<div align="center">

<img src="https://img.shields.io/badge/Jetson_Orin_Nano-8GB-76B900?style=for-the-badge&logo=nvidia&logoColor=white"/>
<img src="https://img.shields.io/badge/ROS2-Humble-22314E?style=for-the-badge&logo=ros&logoColor=white"/>
<img src="https://img.shields.io/badge/TensorRT-Optimized-76B900?style=for-the-badge&logo=nvidia&logoColor=white"/>
<img src="https://img.shields.io/badge/RPLiDAR-A1M8-informational?style=for-the-badge&logo=linode&logoColor=white"/>
<img src="https://img.shields.io/badge/IMX219-77_Camera-blueviolet?style=for-the-badge&logo=github&logoColor=white"/>

<br><br>

# 🤖 PreCrash AI - Road Safety and Traffic Diagnostics Assisted by AI
## Hardware Deployment — Jetson-Based Mobile Robot

> **Graduation Project Documentation**  
> This repository documents the real-world deployment phase of our Sim-to-Real pipeline.  
> It contains all code running on the physical robot: motor control, sensing, sensor fusion, and model inference.

<br>

![Stage](https://img.shields.io/badge/Phase-2_of_2_|_Real_Deployment-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Jetson_Orin_Nano_8GB-76B900?style=flat-square)
![ROS](https://img.shields.io/badge/Middleware-ROS_2_Humble-22314E?style=flat-square)

</div>


---


## 📌 What This Repository Documents

This repository is a **technical record** of the hardware deployment work completed during Phase 2 of the graduation project. It contains all code that runs on the physical robot:

- ✅ Motor control via Waveshare Motor Driver HAT (I2C / PCA9685 + TB6612FNG)
- ✅ Camera stream acquisition from IMX219-77 (CSI interface)
- ✅ LiDAR data acquisition from RPLiDAR A1M8 (USB / serial)
- ✅ Sensor fusion node merging camera and LiDAR data
- ✅ Model inference pipeline (YOLOv8 + LSTM) running on Jetson Orin Nano

> This code was written specifically for our robot's hardware configuration. It is not a general library.

---

## 🔩 Hardware Platform

| Component | Part | Interface |
|-----------|------|-----------|
| **Compute** | NVIDIA Jetson Orin Nano Dev Kit (8GB) | — |
| **Chassis** | 4WD Aluminum Robot Chassis Kit | — |
| **Motor Controller** | Waveshare Motor Driver HAT (PCA9685 + TB6612FNG) | I2C |
| **Camera** | IMX219-77 Camera Module | CSI-2 |
| **LiDAR** | RPLiDAR A1M8 | USB |
| **Wi-Fi** | Intel AX210 M.2 Card | M.2 (PCIe) |
| **Storage** | MicroSD 128GB A2 | — |
| **Display** | 7" HDMI Capacitive Touch Screen | DP → HDMI |
| **Battery** | 3S Li-Po 11.1V ≥ 2200mAh (XT60) | — |
| **Buck Converter** | LM2596 (11.1V → 5V) | — |

---

## 📁 Repository Structure

```
Road-Safety-Hardware-Core/
│
├── 📂 docs/                        # Project documentation & charts
├── 📂 firmware/                    # ESP32 firmware code
│   ├── 📂 OBU/                     # V2X vehicle receiver
│   └── 📂 RSU/                     # V2X infrastructure transmitter
│
├── 📂 models/                      # Optimized AI weights 
│   ├── 🧠 best.engine              # YOLOv8 detection engine 
│   └── 📈 lstm_model_v4.engine     # LSTM prediction engine 
│
└── 📂 src/                         # ROS 2 workspace 
    │
    ├── 📦 jetson_hardware_core/    # Core AI logic 
    │   ├── 📂 launch/              # System launch scripts
    │   └── 📂 jetson_hardware_core/# ROS 2 nodes 
    │       ├── camera_reader.py    # Camera acquisition 
    │       ├── perception_node.py  # YOLOv8 inference 
    │       ├── lidar_processor.py  # LiDAR processing 
    │       ├── sensor_fusion.py    # Multi-modal fusion
    │       ├── prediction_node.py  # LSTM trajectory prediction 
    │       ├── risk_assessment.py  # Risk/TTC scoring
    │       ├── collision_decision.py # Safety arbitration
    │       └── display_node.py     # HMI dashboard UI
    │
    └── 📦 v2x_diagnostics/         # V2X communication bridge
        └── v2x_manager.py          # V2X message decoding
```

---

## ⚙️ Motor Control — Waveshare HAT

### What the Code Does

`motor_driver.py` implements low-level I2C communication with the **Waveshare Motor Driver HAT**, which uses a **PCA9685** PWM controller paired with **TB6612FNG** H-bridge drivers. It exposes a simple speed/direction API used by the ROS 2 control node.

### I2C Configuration

```
Jetson 40-pin Header  →  Waveshare HAT
─────────────────────────────────────
Pin 3  (SDA, I2C1)   →  SDA
Pin 5  (SCL, I2C1)   →  SCL
Pin 4  (5V)          →  VCC
Pin 6  (GND)         →  GND

PCA9685 I2C Address: 0x40 (default, no address jumpers changed)
PWM Frequency:       100 Hz (set in driver initialization)
```

### Motor Channel Mapping

```
PCA9685 Channels → TB6612FNG → Motors
──────────────────────────────────────
Ch 0, 1, 2   →  Motor A (Front-Left)
Ch 3, 4, 5   →  Motor B (Front-Right)
Ch 6, 7, 8   →  Motor C (Rear-Left)
Ch 9, 10, 11 →  Motor D (Rear-Right)
```

### `cmd_vel_subscriber.py`

Subscribes to `/cmd_vel` (ROS 2 `geometry_msgs/Twist`) and converts linear/angular velocity commands into differential PWM values for the four motors:

```
linear.x  →  base forward/backward speed (applied equally to all motors)
angular.z →  left/right differential (subtracted from left, added to right)
```

### `safety_stop.py`

Subscribes to `/risk_prediction`. When `risk_level > 0.75`, it immediately sets all motor PWM to zero and publishes a `/safety_event` message. Normal operation resumes only when risk drops below threshold.

---

## 📷 Camera — IMX219-77

### What the Code Does

`camera_node.py` captures frames from the **IMX219-77** via the Jetson's **CSI-2** interface using GStreamer, converts them to ROS 2 `sensor_msgs/Image` messages, and publishes them on `/camera/image_raw`.

### Capture Pipeline (GStreamer)

```
nvarguscamerasrc  →  nvvidconv  →  video/x-raw (BGR, 800×600)  →  appsink
```

GStreamer is used rather than standard `cv2.VideoCapture()` to access the Jetson's hardware ISP, which handles noise reduction and white balance for the IMX219 sensor.

### Published Topic

```
/camera/image_raw    [sensor_msgs/Image]
  encoding: bgr8
  width:    800
  height:   600
  frame_id: camera_link
```

---

## 📡 LiDAR — RPLiDAR A1M8

### What the Code Does

`lidar_node.py` communicates with the **RPLiDAR A1M8** over USB serial (`/dev/ttyUSB0`) using the RPLiDAR Python SDK, and publishes 360° scan data as a ROS 2 `sensor_msgs/LaserScan` message.

### Sensor Specifications (as used)

| Parameter | Value |
|-----------|-------|
| Scan rate | 10 Hz |
| Angular resolution | ~1° |
| Range | 0.15 m – 12 m |
| Output | 2D planar scan (single horizontal plane) |

### Published Topic

```
/scan    [sensor_msgs/LaserScan]
  frame_id:    laser_link
  angle_min:   -π
  angle_max:    π
  range_min:    0.15
  range_max:   12.0
```

> **Important:** The RPLiDAR A1M8 produces a **2D scan only** — no elevation data. This is a known difference from the 3D LiDAR used in CARLA simulation. The sensor fusion node handles this discrepancy (see below).

---

## 🔀 Sensor Fusion

### What the Code Does

`fusion_node.py` aligns **camera detections** (bounding boxes from YOLOv8) with **LiDAR scan data** to associate each detected object with an estimated range. The output is a list of tracked objects with both visual class labels and estimated distances.

### Fusion Logic

1. Subscribe to `/detections` (bounding boxes) and `/scan` (LiDAR ranges)
2. For each bounding box, compute the angular sector it occupies in the camera frame
3. Map that angular sector to the LiDAR's scan angle using the known extrinsic offset between camera and LiDAR mounts
4. Extract the minimum range within that angular sector as the object's distance estimate
5. Publish enriched object list to `/fused_objects`

### Coordinate Alignment

All transforms follow **ROS REP 103** conventions (X forward, Y left, Z up, units in meters). The static transform between `camera_link` and `laser_link` is defined based on physical mount measurements on the robot chassis.

### Known Limitation

Because the RPLiDAR A1M8 scans a single horizontal plane, objects that are taller or shorter than the scan height (e.g., a pedestrian's torso visible in camera but legs occluded) may produce no corresponding LiDAR return. In these cases, the fusion node falls back to camera-only detection without a range estimate.

---

## 🧠 Model Inference on Jetson

### YOLOv8 — `yolo_node.py`

Runs the **TensorRT-optimized YOLOv8** engine on every incoming camera frame. The `.engine` file was compiled on the Jetson itself from the ONNX weights exported in the simulation phase (TensorRT engines are device-specific).

```
Input:   /camera/image_raw   [800×600 BGR]
           │
         Resize + normalize → (640×640, float32, normalized)
           │
         TensorRT Engine (FP16)
           │
         NMS post-processing
           │
Output:  /detections   [vision_msgs/Detection2DArray]
```

**Achieved inference time:** *(to be filled)*

### LSTM — `lstm_node.py`

For each tracked object published in `/fused_objects`, the LSTM node maintains a **rolling buffer of 10 kinematic states** (x, y, vx, vy, heading, speed). Once the buffer is full, it runs inference and predicts the next 5 positions.

```
Buffer (10 frames × 6 features)
           │
         LSTM (2 layers, hidden=128)
           │
         5 predicted (x, y) positions
           │
Output:  /risk_prediction   [custom_msgs/RiskLevel]
           risk_level:  0.0 – 1.0
           predicted_ttc: seconds
```

Risk level is computed from the predicted trajectory's closest approach distance to the robot's projected path.

### `alert_node.py`

Subscribes to `/risk_prediction` and triggers alerts based on threshold:

| Risk Level | Action |
|------------|--------|
| < 0.4 | No action |
| 0.4 – 0.74 | Warning displayed on screen |
| ≥ 0.75 | Visual + audio alert; safety stop triggered |

---

## 🔗 ROS 2 System Overview

```
RQT RQT RQT RQT RQT RQT RQT RQT
RQT RQT RQT RQT RQT RQT RQT RQT
RQT RQT RQT RQT RQT RQT RQT RQT
RQT RQT RQT RQT RQT RQT RQT RQT 
```

---

## ⚡ Power Architecture

```
3S Li-Po (11.1V, XT60)
         │
         └──── XT60 Parallel Splitter
                       │
                       ├──── Waveshare Motor Driver HAT  ← 11.1V direct
                       │     (TB6612FNG handles motor voltage directly)
                       │
                       └──── LM2596 Buck Converter  (set to 8.0V)
                                       │
                             Jetson Orin Nano (5V / 4A input)
```

> The LM2596 output voltage was set and verified with a multimeter before first connection to the Jetson. The Jetson Orin Nano requires a stable **5V ± 0.25V** input; operation outside this range risks permanent damage to the SoM.

---

## 🌉 Sim-to-Real Adaptations

Differences between the CARLA simulation environment and the physical robot required the following adaptations in this codebase:

| Sim Assumption | Real Condition | Adaptation in This Repo |
|----------------|---------------|------------------------|
| 3D LiDAR (32-channel) | RPLiDAR A1M8 (2D, single plane) | Fusion node uses angular sector matching instead of 3D projection |
| Noiseless camera | IMX219 with real-world noise + lighting variation | GStreamer ISP pipeline used; no additional filtering added |
| Synchronous simulator tick | Asynchronous real-world sensor streams | ROS 2 message timestamps used for synchronization |
| CARLA world coordinates (absolute) | Robot-centric relative coordinates | REP 103 TF tree used; all positions relative to `base_link` |
| Infinite battery / compute | 11.1V Li-Po + Jetson Orin Nano constraints | TensorRT FP16 used; non-essential logging disabled at runtime |

---

## 📚 References

- **[8]** S. Macenski et al., "Robot Operating System 2," *Science Robotics*, 2022.
- **[9]** "REP 103 — Standard Units of Measure and Coordinate Conventions," ROS.org.
- **[10]** "NVIDIA JetPack Software Stack," NVIDIA Developer.
- **[14]** "Jetson Orin Nano Developer Kit Carrier Board Specification," NVIDIA.
- **[13]** I. Uprety, "Large Scale Learning on Tiny Devices," M.S. thesis, Washington State Univ., 2025.
- **[22]** M. Capra et al., "Hardware and Software Optimizations for Accelerating DNNs," *arXiv*, 2020.

---

<div align="center">

**Phase 2 of 2 — Hardware Deployment**  
🔗 Simulation Repo: [carla-simulation-pipeline](https://github.com/SadeemAlBoqami/Road-Safety-and-Traffic-Diagnostics-Assisted-by-AI-Phase2-CARLA-Simulation)

</div>
