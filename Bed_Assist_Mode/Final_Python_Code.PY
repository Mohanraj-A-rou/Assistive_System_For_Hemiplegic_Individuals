import cv2
import mediapipe as mp
import time
import math
import requests

# ==========================================
#        1. INITIALIZATION & SETUP
# ==========================================

# --- MediaPipe Solutions ---
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Initialize Hand Detector
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)

# --- Configuration ---
GESTURE_HOLD_TIME = 3.0   # seconds to confirm gesture

# --- ESP32 Config ---
# Your specific ESP32 IP address on the hotspot
ESP32_URL = "http://10.131.xxx.xxx" 

# --- State Variables ---
current_gesture = None
gesture_start_time = 0
confirmed_text = "Monitoring Active"
status_color = (0, 255, 0)  # Green

# --- Pushbullet Config ---
PUSHBULLET_TOKEN = "____TOKEN_____" # <-- PASTE YOUR ACTUAL TOKEN HERE
PUSHBULLET_URL = "https://api.pushbullet.com/v2/pushes"
last_sent_text = None  # Prevent duplicate alerts

# --- Camera Setup ---
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(3, 640)
cap.set(4, 480)

# ==========================================
#        2. HELPER FUNCTIONS
# ==========================================

def send_pushbullet_notification(title, body):
    """Sends an alert to your phone via Pushbullet"""
    headers = {
        "Access-Token": PUSHBULLET_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "type": "note",
        "title": title,
        "body": body
    }
    try:
        requests.post(PUSHBULLET_URL, json=data, headers=headers, timeout=5)
        print(f"Pushbullet Alert Sent: {body}")
    except Exception as e:
        print("Pushbullet Error:", e)

def trigger_esp32(endpoint):
    """Sends a request to the ESP32 (for LEDs or Buzzer)"""
    try:
        # endpoint will be "/led1", "/led2", or "/beep"
        requests.get(f"{ESP32_URL}{endpoint}", timeout=2)
        print(f"Triggered ESP32: {endpoint}")
    except Exception as e:
        print("ESP32 Connection Error:", e)

def get_fingers_status(hand, label):
    """Returns list [Thumb, Index, Middle, Ring, Pinky] (1=open, 0=closed)"""
    lm = hand.landmark
    fingers = []
    TIP_IDS = [4, 8, 12, 16, 20]

    # Thumb logic
    if label == "Left":
        fingers.append(1 if lm[4].x < lm[3].x else 0)
    else:
        fingers.append(1 if lm[4].x > lm[3].x else 0)

    # Other fingers
    for i in range(1, 5):
        fingers.append(1 if lm[TIP_IDS[i]].y < lm[TIP_IDS[i]-2].y else 0)

    return fingers

def identify_gesture(f):
    """Maps finger states to gestures"""
    # Original Gestures
    if f == [1, 0, 0, 0, 0]: return "Adjust Position"
    if f == [1, 1, 0, 0, 0]: return "Need Water/Food"
    if f == [0, 1, 0, 0, 0]: return "Restroom Request"
    if f == [0, 0, 1, 1, 1]: return "Want Medicine"
    if f == [0, 1, 1, 0, 0]: return "Call Caregiver"
    if f == [1, 1, 1, 0, 0]: return "Uncomfortable"
    
    # NEW Gestures for LEDs
    if f == [1, 1, 1, 1, 1]: return "Open Palm"
    if f == [0, 0, 0, 0, 0]: return "Closed Palm"
    
    return None

# ==========================================
#        3. MAIN LOOP
# ==========================================

print("System Starting... Press 'q' to exit.")

while True:
    success, frame = cap.read()
    if not success:
        continue

    # Flip frame horizontally for a selfie-view display
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    hand_results = hands.process(rgb)
    
    # FAILSAFE: Define variable before we ever try to use it
    seconds_left = 0 

    if hand_results.multi_hand_landmarks:
        for idx, hand_lm in enumerate(hand_results.multi_hand_landmarks):
            mp_draw.draw_landmarks(frame, hand_lm, mp_hands.HAND_CONNECTIONS)

            if hand_results.multi_handedness:
                label = hand_results.multi_handedness[idx].classification[0].label
                fingers = get_fingers_status(hand_lm, label)
                gesture = identify_gesture(fingers)

                if gesture:
                    if gesture == current_gesture:
                        hold_duration = time.time() - gesture_start_time
                        seconds_left = math.ceil(GESTURE_HOLD_TIME - hold_duration)

                        if hold_duration >= GESTURE_HOLD_TIME:
                            confirmed_text = gesture
                            status_color = (0, 255, 0)

                            if confirmed_text != last_sent_text:
                                print(f"Gesture Confirmed: {confirmed_text}")
                                
                                # 1. ALWAYS beep for ANY confirmed gesture
                                trigger_esp32("/beep")

                                # 2. Handle specific LED toggles
                                if confirmed_text == "Open Palm":
                                    trigger_esp32("/led1")
                                elif confirmed_text == "Closed Palm":
                                    trigger_esp32("/led2")
                                
                                # 3. Handle Pushbullet for original patient requests
                                else:
                                    send_pushbullet_notification(
                                        "Patient Gesture Alert",
                                        f"Patient Request: {confirmed_text}"
                                    )
                                
                                last_sent_text = confirmed_text
                        else:
                            # Display countdown timer near the hand
                            h, w, _ = frame.shape
                            cx = int(hand_lm.landmark[0].x * w)
                            cy = int(hand_lm.landmark[0].y * h)
                            cv2.putText(
                                frame,
                                f"Holding: {seconds_left}s",
                                (cx + 20, cy),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (255, 0, 0),
                                2
                            )
                    else:
                        current_gesture = gesture
                        gesture_start_time = time.time()
                        last_sent_text = None # RESETS SPAM FILTER
                else:
                    current_gesture = None
                    last_sent_text = None # RESETS SPAM FILTER
            else:
                current_gesture = None
                last_sent_text = None # RESETS SPAM FILTER
    else:
        current_gesture = None
        last_sent_text = None # RESETS SPAM FILTER

    # ==========================================
    #        4. DISPLAY
    # ==========================================

    cv2.putText(
        frame,
        f"Status: {confirmed_text}",
        (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        status_color,
        2
    )

    cv2.imshow("Patient Monitor - Gesture Based Alert", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()