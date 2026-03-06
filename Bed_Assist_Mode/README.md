## Bed_Assist_Mode

- The bed-assist mode supports the user during rest by enabling easy communication, smart environmental control, and continuous health monitoring.
- This mode mainly focuses on allowing the user to express their needs, control home appliances, and ensure safety through both automatic and manual emergency alert mechanisms.
- A laptop is used as the camera module with OpenCV and MediaPipe for real-time gesture recognition. An ESP32 microcontroller acts as the central controller and IoT interface, and local Wi-Fi is used to send notifications to the caregiver.
- The MAX30102 sensor is integrated to monitor heart rate and oxygen saturation levels, and an FSR sensor is used for fall and stroke detection based on pressure variations. An emergency physical push button is included for manual alert triggering.
- For demonstrating IoT-based control, an LED and a fan are used as representative appliances. This prototype validates the practical feasibility of the proposed bed-assist mode in terms of gesture-based control, health monitoring, and reliable alert communication
