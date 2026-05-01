#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import Jetson.GPIO as GPIO

# Define L298N Pins
ENA, IN1, IN2 = 33, 11, 12
ENB, IN3, IN4 = 32, 13, 15

class MotorControlNode(Node):
    def __init__(self):
        super().__init__('motor_control_node')
        
        # GPIO Setup
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup([IN1, IN2, IN3, IN4, ENA, ENB], GPIO.OUT, initial=GPIO.LOW)
        
        # Enable Motors (Max Speed without PWM for now)
        GPIO.output(ENA, GPIO.HIGH)
        GPIO.output(ENB, GPIO.HIGH)

        # Subscribe to /cmd_vel
        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )
        self.get_logger().info("Motor Control Node Started. Listening to /cmd_vel...")

    def cmd_vel_callback(self, msg):
        linear = msg.linear.x
        angular = msg.angular.z

        # Debugging probe: Log the received signal
        self.get_logger().info(f"Signal received -> Linear: {linear}, Angular: {angular}")

        # Movement logic
        if linear > 0:
            self.get_logger().info("Action: Moving FORWARD")
            self.move_forward()
        elif linear < 0:
            self.get_logger().info("Action: Moving BACKWARD")
            self.move_backward()
        elif angular > 0:
            self.get_logger().info("Action: Turning LEFT")
            self.turn_left()
        elif angular < 0:
            self.get_logger().info("Action: Turning RIGHT")
            self.turn_right()
        else:
            self.get_logger().info("Action: STOP")
            self.stop_motors()

    def move_forward(self):
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.output(IN3, GPIO.HIGH)
        GPIO.output(IN4, GPIO.LOW)

    def move_backward(self):
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.HIGH)
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.HIGH)

    def turn_left(self):
        # Right motor forward, Left motor backward
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.HIGH)

    def turn_right(self):
        # Left motor forward, Right motor backward
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.HIGH)
        GPIO.output(IN3, GPIO.HIGH)
        GPIO.output(IN4, GPIO.LOW)

    def stop_motors(self):
        GPIO.output([IN1, IN2, IN3, IN4], GPIO.LOW)

    def cleanup(self):
        self.stop_motors()
        GPIO.cleanup()
        self.get_logger().info("Motors stopped safely. GPIO cleaned up.")

def main(args=None):
    rclpy.init(args=args)
    node = MotorControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cleanup()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
