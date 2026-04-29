<div align="center">

<img src="https://img.shields.io/badge/Jetson_Orin_Nano-8GB-76B900?style=for-the-badge&logo=nvidia&logoColor=white"/>
<img src="https://img.shields.io/badge/ROS2-Humble-22314E?style=for-the-badge&logo=ros&logoColor=white"/>
<img src="https://img.shields.io/badge/TensorRT-Optimized-76B900?style=for-the-badge&logo=nvidia&logoColor=white"/>
<img src="https://img.shields.io/badge/L298N-Motor_Driver-red?style=for-the-badge&logo=micro-dot-info&logoColor=white"/>
<img src="https://img.shields.io/badge/RPLiDAR-A1M8-informational?style=for-the-badge&logo=linode&logoColor=white"/>
<img src="https://img.shields.io/badge/IMX219-77_Camera-blueviolet?style=for-the-badge&logo=camera&logoColor=white"/>

<br><br>

# 🤖 PreCrash AI - Road Safety and Traffic Diagnostics Assisted by AI

## Real-World Deployment — Intelligent Edge-Based Safety System

> **Graduation Project Documentation**
> A real-time embedded system that **detects, tracks, and predicts collision risks** using multi-sensor perception and edge AI.

<br>

![Stage](https://img.shields.io/badge/Phase-2_of_2_|_Real_Deployment-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Jetson_Orin_Nano_8GB-76B900?style=flat-square)
![ROS](https://img.shields.io/badge/Middleware-ROS_2_Humble-22314E?style=flat-square)

</div>

---

## 🌍 System Overview

This project implements a **real-time road safety diagnostic system** deployed on a physical robot platform.

The system continuously:

* **Perceives the environment** using camera and LiDAR
* **Understands objects and distances** through sensor fusion
* **Tracks dynamic agents (vehicles/pedestrians)**
* **Predicts future trajectories** using deep learning
* **Evaluates collision risk** using Time-To-Collision (TTC)

Unlike reactive systems, this architecture is **predictive** — it estimates what will happen next, not just what is happening now. 

---

## 🧠 System Architecture (Layered)

The system follows a structured pipeline similar to real autonomous driving stacks:

---

### 1️⃣ Sensing Layer

Responsible for raw data acquisition:

* 📷 Camera → RGB frames
* 📡 LiDAR → Distance measurements
* 📍 GNSS/IMU → Ego-state (position, velocity)
* 🌐 V2X → External vehicle data (JSON-based messages)

---

### 2️⃣ Perception Layer

Transforms raw data into meaningful information:

* **Image Preprocessing** → resizing + normalization
* **YOLOv8 (TensorRT)** → object detection (cars, pedestrians)
* **V2X Decoder** → extracts remote vehicle states

This stage converts raw sensor streams into structured data (bounding boxes + coordinates). 

---

### 3️⃣ Fusion & Tracking Layer

This is the core intelligence bridge.

#### 🔗 Sensor Fusion

* Projects LiDAR points into the camera frame using calibration matrices
* Matches LiDAR depth with detected objects using IOU
* Computes accurate object distance

Conceptually:

* If LiDAR points fall inside a YOLO bounding box → same object
* Average depth → real-world distance

#### 🌐 V2X Integration

* Converts GPS (Lat, Long) → local (X, Y) coordinates
* Uses **Kalman Filter** to reduce noise and unify measurements

#### 🎯 Tracking

* Assigns unique IDs to objects
* Builds motion history for prediction

---

### 4️⃣ Prediction & Risk Analysis

This layer makes the system proactive:

* **LSTM Model**

  * Input: last ~10 frames of motion
  * Output: predicted trajectory (3–5 seconds ahead)

* **Risk Engine**

  * Computes **Time-To-Collision (TTC)**
  * Compares ego trajectory vs surrounding vehicles

This is where the system shifts from perception → decision intelligence. 

---

### 5️⃣ Decision & Actuation Layer

Handles real-time system behavior:

* **System Manager**

  * Adaptive frame skipping (resource optimization)
  * Task prioritization (V2X highest priority)

* **HMI**

  * Displays alerts based on risk level

* **Actuation**

  * Simulated **Autonomous Emergency Braking (AEB)**
  * Robot motion controlled via **L298N Motor Driver**

---
<div align="center">
  <img width="1076" alt="PreCrash AI System Block Diagram" src="https://github.com/user-attachments/assets/852b50db-d96f-4ef0-be14-3decc97b4877" />
  
  <br>
  
  <p>
    <b>Figure 1:</b> <i>Detailed System Block Diagram illustrating the interaction between Sensing, Perception, and Actuation layers within the PreCrash AI framework.</i>
  </p>
</div>

---

## ⚙️ Hardware Deployment

| Component          | Role                               |
| ------------------ | ---------------------------------- |
| Jetson Orin Nano   | Edge AI processing (GPU inference) |
| L298N Motor Driver | Controls motor speed & direction   |
| IMX219 Camera      | Visual perception                  |
| RPLiDAR A1M8       | Distance sensing                   |
| ESP32 / Wi-Fi      | V2X communication                  |
| Li-Po Battery      | Power system                       |

---

## ⚙️ Locomotion — L298N Integration

The robot uses a **differential drive system** controlled via the **L298N Dual H-Bridge**.

* PWM controls motor speed
* Direction controlled via IN1–IN4 logic
* ROS2 `/cmd_vel` → translated into wheel velocities

Real-world adaptation included:

* Compensating for motor non-linearity
* Handling friction and voltage drops

---

## 📡 V2X Communication (IoV Emulation)

A lightweight **Vehicle-to-Everything (V2X)** system is implemented using:

* UDP Broadcast over Wi-Fi
* JSON-based messages simulating **BSM (Basic Safety Message)**

Message structure includes:

* `senderID`
* `timestamp`
* `eventCode`
* `location`
* `priority`

This acts as a **behavioral emulation of DSRC (802.11p)** using accessible hardware. 

---

## 🧠 AI Models

### 🔍 YOLOv8 (Detection)

* Trained on ~15,000 simulated images
* Detects vehicles and pedestrians
* Optimized using **TensorRT FP16**

### 📈 LSTM (Prediction)

* Trained on ~300,000 trajectory frames
* Predicts motion sequences
* Enables early risk detection

---

## 🌉 Sim-to-Real Transition

Key engineering challenges solved:

| Simulation         | Reality              |
| ------------------ | -------------------- |
| Perfect sensors    | Noisy LiDAR + camera |
| Ideal motion       | Motor drift & delay  |
| Synchronous data   | Asynchronous streams |
| Global coordinates | Robot-centric frame  |

Solutions:

* Kalman filtering
* ROS2 message synchronization
* PWM calibration
* Sensor fusion redesign

---

## 📁 Repository Structure

```
Road-Safety-Hardware-Core/
│
├── docs/
├── firmware/   (ESP32 V2X)
├── models/     (TensorRT engines)
└── src/        (ROS2 nodes)
```

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
🔗 Simulation Repo: [carla-simulation-core](https://github.com/SadeemAlBoqami/Road-Safety-and-Traffic-Diagnostics-Assisted-by-AI-Phase2-CARLA-Simulation)

</div>
