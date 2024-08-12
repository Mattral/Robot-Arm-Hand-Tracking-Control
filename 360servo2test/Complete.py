import cv2
from cvzone.HandTrackingModule import HandDetector
import numpy as np
import pyfirmata
import time
import threading
import speech_recognition as sr

# Initialize video capture
cap = cv2.VideoCapture(0)
cap.set(3, 1280)  # Set width
cap.set(4, 720)   # Set height

# Calculate half screen width and height
half_screen_width = int(cap.get(3) / 2)
half_screen_height = int(cap.get(4) / 2)

# Initialize hand detector
detector = HandDetector(detectionCon=0.8, maxHands=2)

# Initialize Arduino board
port = "COM6"  # Updated COM port
board = pyfirmata.Arduino(port)

# Initialize servos for robot arm (X, Y, Z)
servo_pinX = board.get_pin('d:3:s')
servo_pinY = board.get_pin('d:5:s')
servo_pinZ = board.get_pin('d:6:s')

# Initialize L298N motor driver pins
left_motor_dir1 = board.get_pin('d:7:o')
left_motor_dir2 = board.get_pin('d:8:o')
left_motor_pwm = board.get_pin('d:9:p')

right_motor_dir1 = board.get_pin('d:13:o')
right_motor_dir2 = board.get_pin('d:12:o')
right_motor_pwm = board.get_pin('d:10:p')

# Initialize variables for robot arm
minHand, maxHand = 20, 220
minDegX, maxDegX = 60, 180
minDegY, maxDegY = 40, 140
minDegZ, maxDegZ = 100, 150
servoX = 120
servoY = 120
servoZ = 120

# Initialize motor control variables
neutral_speed = 0.0
max_speed = 1.0
min_speed = 0.5

# Time tracking for movement stop
last_movement_time = time.time()

# Speech recognition setup
recognizer = sr.Recognizer()
microphone = sr.Microphone()

commands = {
    "forward": (1, 1, max_speed, max_speed),
    "go": (1, 1, max_speed, max_speed),
    "reverse": (0, 0, max_speed, max_speed),
    "back": (0, 0, max_speed, max_speed),
    "left": (0, 1, max_speed, max_speed),
    "laugh": (0, 1, max_speed, max_speed),
    "right": (1, 0, max_speed, max_speed)
}

def stop_motors():
    """Function to stop both motors."""
    left_motor_pwm.write(neutral_speed)
    right_motor_pwm.write(neutral_speed)

def move_motors(left_dir1, left_dir2, left_speed, right_dir1, right_dir2, right_speed):
    """Function to move both motors with specified directions and speeds."""
    left_motor_dir1.write(left_dir1)
    left_motor_dir2.write(left_dir2)
    left_motor_pwm.write(left_speed)
    
    right_motor_dir1.write(right_dir1)
    right_motor_dir2.write(right_dir2)
    right_motor_pwm.write(right_speed)

def speech_recognition_thread():
    """Thread function for handling speech recognition."""
    global last_movement_time
    while True:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)

        try:
            command = recognizer.recognize_google(audio).lower()
            print(f"You said: {command}")

            if command in commands:
                left_dir, right_dir, left_speed, right_speed = commands[command]
                move_motors(left_dir, not left_dir, left_speed, right_dir, not right_dir, right_speed)
                last_movement_time = time.time()
            else:
                print("Unknown command")

        except sr.UnknownValueError:
            print("Could not understand audio")
        except sr.RequestError as e:
            print(f"Could not request results; {e}")

def overlay_text(img, text):
    """Function to overlay text on the video feed."""
    cv2.putText(img, text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)

def button_click(event, x, y, flags, param):
    """Function to handle button clicks."""
    if event == cv2.EVENT_LBUTTONDOWN:
        if 50 <= x <= 250 and 50 <= y <= 100:
            print("Data Collection Button Clicked")
            # Implement data collection logic here
        elif 300 <= x <= 500 and 50 <= y <= 100:
            print("Training Button Clicked")
            # Implement training logic here
        elif 550 <= x <= 750 and 50 <= y <= 100:
            print("AI Button Clicked")
            # Implement AI logic here

# Start speech recognition thread
speech_thread = threading.Thread(target=speech_recognition_thread, daemon=True)
speech_thread.start()

cv2.namedWindow("Hand Tracking")
cv2.setMouseCallback("Hand Tracking", button_click)

while True:
    success, img = cap.read()
    hands, img = detector.findHands(img, draw=False)

    # Draw the buttons
    cv2.rectangle(img, (50, 50), (250, 100), (0, 255, 0), -1)  # Data Collection Button
    cv2.putText(img, "Data Collect", (60, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.rectangle(img, (300, 50), (500, 100), (255, 0, 0), -1)  # Training Button
    cv2.putText(img, "Train", (340, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.rectangle(img, (550, 50), (750, 100), (0, 0, 255), -1)  # AI Button
    cv2.putText(img, "AI", (620, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    if hands:
        # Identify right and left hands
        hand_r = next((h for h in hands if h['type'] == 'Right'), None)
        hand_l = next((h for h in hands if h['type'] == 'Left'), None)

        # Draw the control boxes
        cv2.rectangle(img, (0, 0), (half_screen_width, 720), (255, 0, 0), 2)
        cv2.rectangle(img, (half_screen_width, 0), (1280, 720), (0, 255, 0), 2)

        if hand_r is not None:
            lmList_r = hand_r['lmList']
            wrist_x, wrist_y = lmList_r[0][0], lmList_r[0][1]
            cv2.circle(img, (int(wrist_x), int(wrist_y - 30)), 10, (0, 255, 0), cv2.FILLED)

            x_pos = lmList_r[9][0]
            y_pos = lmList_r[9][1]

            if detector.fingersUp(hand_r) == [0, 0, 0, 0, 0]:
                stop_motors()
                last_movement_time = time.time()
            else:
                if x_pos < half_screen_width:
                    box_center_x = half_screen_width // 2
                    box_center_y = half_screen_height // 2

                    if y_pos < box_center_y - (box_center_y // 4):
                        move_motors(1, 0, max_speed, 0, 1, max_speed)
                        overlay_text(img, "forward")
                    elif y_pos > box_center_y + (box_center_y // 4):
                        move_motors(0, 1, max_speed, 1, 0, max_speed)
                        overlay_text(img, "reverse")
                    elif x_pos < box_center_x - (box_center_x // 4):
                        move_motors(0, 1, min_speed, 1, 0, max_speed)
                        overlay_text(img, "left")
                    elif x_pos > box_center_x + (box_center_x // 4):
                        move_motors(1, 0, max_speed, 0, 1, min_speed)
                        overlay_text(img, "Right")
                    else:
                        stop_motors()
                        overlay_text(img, "stopped")
                    last_movement_time = time.time()
                else:
                    stop_motors()
                    last_movement_time = time.time()

        if time.time() - last_movement_time >= 2:
            stop_motors()

        if hand_l is not None:
            lmList_l = hand_l['lmList']
            x_pos = lmList_l[9][0]
            servoX = np.interp(x_pos, [minHand, maxHand], [minDegX, maxDegX])
            servo_pinX.write(servoX)

            y_pos = lmList_l[9][1]
            servoY = np.interp(y_pos, [minHand, maxHand], [minDegY, maxDegY])
            servo_pinY.write(servoY)

            z_pos = lmList_l[12][2]
            servoZ = np.interp(z_pos, [minHand, maxHand], [minDegZ, maxDegZ])
            servo_pinZ.write(servoZ)

    cv2.imshow("Hand Tracking", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()