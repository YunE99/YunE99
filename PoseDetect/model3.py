import cv2
import numpy as np
import tensorflow as tf
from datetime import datetime
import os
import time
import requests, base64


# 저장 경로 설정
SAVE_DIR = "./labeling_result"
os.makedirs(SAVE_DIR, exist_ok=True)

# 전역변수
last_status = None
status_start_time = None
prev_landmarks = None  #  이전 관절 위치 저장용 변수 추가
movement_start_time = None

# 비디오 
video_path = r"C:\Users\User\Desktop\PoseDetect\studying2.mp4"
# video_path = r"C:\Users\User\Desktop\PoseDetect\sleep1.mp4"
# video_path = r"C:\Users\User\Desktop\PoseDetect\stop1.mp4"
# video_path = r"C:\Users\User\Desktop\PoseDetect\noNpeople.mp4"

# MoveNet Thunder 모델 로드
interpreter = tf.lite.Interpreter(model_path="movenet_thunder.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
input_size = 256

# 자세 판단 함수
def classify_posture(landmarks):
    global prev_landmarks, movement_start_time  # ✅ 전역 변수 사용

    # 3차 판단: 어깨, 팔, 손꿈치 인식률 낮으면 사람 없음으로 간주
    low_conf_count = 0
    for i in [5, 6, 7, 8, 9, 10]:
        if landmarks[i][2] < 0.35:
            low_conf_count += 1

    if low_conf_count >= 4:
        return "[Non People]"


    nose_y = landmarks[0][1]
    left_eye_y = landmarks[1][1]
    right_eye_y = landmarks[2][1]
    left_ear_y = landmarks[3][1]
    right_ear_y = landmarks[4][1]
    left_shoulder_y = landmarks[5][1]
    right_shoulder_y = landmarks[6][1]
    avg_shoulder_y = (left_shoulder_y + right_shoulder_y) / 2

    #  1차 판단: 얼굴 위치 기준
    score = 0
    if nose_y < avg_shoulder_y: score += 1
    if left_ear_y < avg_shoulder_y: score += 1
    if right_ear_y < avg_shoulder_y: score += 1
    if left_eye_y < avg_shoulder_y: score += 1
    if right_eye_y < avg_shoulder_y: score += 1

    status = "[Studying]" if score >= 3 else "[Not Studying]"

    #  2차 판단: 움직임이 거의 없으면 Not Studying으로 덮어쓰기 (5분 이상 정지 시)
    if prev_landmarks:
        movement = 0
        for i in [7, 8, 9, 10]:
            dx = abs(landmarks[i][0] - prev_landmarks[i][0])
            dy = abs(landmarks[i][1] - prev_landmarks[i][1])
            movement += dx + dy

        if movement < 20:
            if movement_start_time is None:
                movement_start_time = time.time()
            elif time.time() - movement_start_time >= 5:
                status = "[Not Studying]"
        else:
            movement_start_time = None  # 움직임이 있으면 초기화

    prev_landmarks = landmarks  # 항상 갱신
    return status

# MoveNet 추론 함수
def run_movenet(frame):
    h, w = frame.shape[:2]
    img = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (input_size, input_size))
    input_tensor = img.astype(np.uint8)
    input_tensor = np.expand_dims(input_tensor, axis=0)

    interpreter.set_tensor(input_details[0]['index'], input_tensor)
    interpreter.invoke()
    keypoints = interpreter.get_tensor(output_details[0]['index'])[0][0]

    landmarks = []
    for kp in keypoints:
        y, x, conf = kp
        px, py = int(x * w), int(y * h)
        landmarks.append((px, py, conf))

    return landmarks

# 시각화 함수
def draw_keypoints(frame, landmarks):
    KEYPOINT_NAMES = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle"
    ]
    idxs = [0,1,2,3,4,5,6,7,8,9,10]

    for i, idx in enumerate(idxs):
        x, y, conf = landmarks[idx]
        color = (0, 255, 0) if conf > 0.3 else (128, 128, 128)
        cv2.circle(frame, (x, y), 4, color, -1)
        label = f"{KEYPOINT_NAMES[i]} ({conf:.2f})"
        cv2.putText(frame, label, (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

# 영상 입력 (캠일 땐 0)
cap = cv2.VideoCapture(video_path)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    target_width = 1280
    h, w = frame.shape[:2]
    aspect_ratio = h / w
    new_height = int(target_width * aspect_ratio)
    frame = cv2.resize(frame, (target_width, new_height))

    landmarks = run_movenet(frame)
    status = classify_posture(landmarks)
    draw_keypoints(frame, landmarks)

    # 상태 변화 감지 → 타이머 초기화
    if status != last_status:
        last_status = status
        status_start_time = time.time()

    elapsed_time = time.time() - status_start_time if status_start_time else 0

    # 상태 출력
    cv2.putText(frame, status, (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # 상태가 지속되었을 경우 서버 전송
    if status in ["[Not Studying]", "[Non People]"] and elapsed_time >= 5: # 위에서 상태판단 후 지속여부 확인 -> 저장시간(상태판단 + 지속시간)
        filename = f"[userid]{status}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}.jpg"

        # 이미지 base64 인코딩
        _, buffer = cv2.imencode(".jpg", frame)
        image_base64 = base64.b64encode(buffer).decode('utf-8')

        payload = {
            "user_id": "[userid]",
            "status": status,
            "timestamp": datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3],
            "image_base64": image_base64
        }

        try:
            response = requests.post("http://localhost:8000/receive_status", json=payload)
            print("JSON 전송 완료:", response.status_code, response.json())
        except Exception as e:
            print("전송 실패:", e)

        status_start_time = time.time()  # 중복 방지용 초기화

    cv2.imshow("Pose Detection", frame)

    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()