import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import math
import time

# 모델 및 비디오 경로
MODEL_PATH = 'face_landmarker.task'
video_path = r"C:\Users\User\Desktop\PoseDetect\sleep1.mp4"

# 옵션 설정
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=False,
    output_facial_transformation_matrixes=False,
    num_faces=1,
    running_mode=vision.RunningMode.VIDEO
)

# FaceLandmarker 초기화
face_landmarker = vision.FaceLandmarker.create_from_options(options)

# 비디오 열기
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("비디오를 열 수 없습니다.")
    exit()

# 거리 계산 함수
def get_distance(p1, p2, width, height):
    x1, y1 = int(p1.x * width), int(p1.y * height)
    x2, y2 = int(p2.x * width), int(p2.y * height)
    return math.hypot(x2 - x1, y2 - y1)

# 초기 변수
sleep_start_frame = None
sleep_threshold_sec = 5
timestamp = 0
prev_status = "None"

fps = cap.get(cv2.CAP_PROP_FPS)
frame_index_at_change = 0

# 메인 루프
while cap.isOpened():
    start_time = time.time()  #  프레임 처리 시작 시간

    ret, frame = cap.read()
    if not ret:
        print("영상 끝까지 처리 완료.")
        break

    frame = cv2.resize(frame, (640, 480))
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    result = face_landmarker.detect_for_video(mp_image, timestamp)

    # 현재 프레임 위치 기준 영상 시간 계산
    frame_index = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    elapsed_time = (frame_index - frame_index_at_change) / fps

    logic_status = ""
    status = "No face"
    color = (255, 255, 255)

    if result.face_landmarks:
        for landmark in result.face_landmarks:
            h, w = frame.shape[:2]

            left_top = landmark[159]
            left_bottom = landmark[145]
            right_top = landmark[386]
            right_bottom = landmark[374]

            left_eye_gap = get_distance(left_top, left_bottom, w, h)
            right_eye_gap = get_distance(right_top, right_bottom, w, h)
            threshold = 5

            if left_eye_gap < threshold and right_eye_gap < threshold:
                if sleep_start_frame is None:
                    sleep_start_frame = frame_index
                elapsed_frame = frame_index - sleep_start_frame
                elapsed_sec = elapsed_frame / fps

                if elapsed_sec >= sleep_threshold_sec:
                    logic_status = "Sleeping"
                    status = f"Sleeping ({elapsed_time:.1f}s)"
                    color = (0, 0, 255)
                else:
                    logic_status = "Close eyes"
                    status = f"Close eyes ({elapsed_time:.1f}s)"
                    color = (0, 255, 255)
            else:
                sleep_start_frame = None
                logic_status = "Awake"
                status = f"Awake ({elapsed_time:.1f}s)"
                color = (0, 255, 0)

            # 상태 변경 시 프레임 기준 초기화
            if logic_status != prev_status:
                frame_index_at_change = frame_index
                prev_status = logic_status

            # 랜드마크 시각화
            for lm in landmark:
                x_px = int(lm.x * w)
                y_px = int(lm.y * h)
                cv2.circle(frame, (x_px, y_px), 1, (0, 255, 0), -1)

    # 상태 텍스트 출력
    cv2.putText(frame, status, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    cv2.imshow("Face Landmarker", frame)

    timestamp += int(1000 / fps)

    # 프레임 처리 시간 기반 waitTime 자동 계산
    elapsed = time.time() - start_time
    frame_duration = 1.0 / fps
    delay = max(int((frame_duration - elapsed) * 1000), 1)  # 최소 1ms

    if cv2.waitKey(delay) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
