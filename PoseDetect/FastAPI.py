from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def 

























# from fastapi import FastAPI, UploadFile, File
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# import cv2
# import mediapipe as mp
# import numpy as np
# import time
# from PIL import Image
# import io

# # FastAPI 앱 초기화
# app = FastAPI()

# # CORS 설정
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # 세션 유사 변수 (단일 사용자 기준)
# user_session = {
#     "last_focused_time": time.time(),
#     "focus_status": "Focused"
# }

# # MediaPipe 모듈 import 및 객체 생성
# # mp_drawing = mp.solutions.drawing_utils
# # mp_face = mp.solutions.face_detection
# mp_holistic = mp.solutions.holistic

# # # Drawing 스타일 객체 저장 (필요 시 사용)
# # red_spec = mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=2)

# # # 얼굴 탐지 모델 초기화 (필요 시 사용)
# # face_detector = mp_face.FaceDetection(min_detection_confidence=0.2)

# # 기본 임계값 설정
# focus_threshold = 5
# valHead = 0.06
# valLeft = 0.4
# valRight = 0.6

# # 자세 판별 함수
# def detect_posture(pose_landmarks, face_landmarks) -> str:
#     global valHead, valLeft, valRight

#     nose = pose_landmarks[0]
    
#     left_shoulder = pose_landmarks[11]
#     right_shoulder = pose_landmarks[12]

#     if nose.y > left_shoulder.y and nose.y > right_shoulder.y:
#         return "Face Down"

#     if face_landmarks is None:
#         return "Face Down"
#     else:
#         left_eye_center = face_landmarks[468]
#         left_eye_left = face_landmarks[33]
#         left_eye_right = face_landmarks[133]
#         left_eye_above = face_landmarks[159]

#         if left_eye_above.y > left_eye_center.y:
#             return "Sleep"

#     return "Focused"

# # 자세 감지 API
# @app.post("/detect_pose/")
# async def detect_pose(file: UploadFile = File(...)):
#     global valHead, valLeft, valRight, user_session

#     try:
#         contents = await file.read()
#         image = Image.open(io.BytesIO(contents))
#         frame = np.array(image)

#         if frame.shape[-1] == 4:
#             frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)

#         with mp_holistic.Holistic(static_image_mode=False, refine_face_landmarks=True) as holistic:
#             rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#             results = holistic.process(rgb_frame)

#             if results.pose_landmarks:
#                 pose_landmarks = results.pose_landmarks.landmark
#                 face_landmarks = results.face_landmarks.landmark if results.face_landmarks else None
#                 posture = detect_posture(pose_landmarks, face_landmarks)
#             else:
#                 posture = "Not in the Seat"

#         current_time = time.time()
#         last_focused_time = user_session.get("last_focused_time", current_time)
#         focus_status = user_session.get("focus_status", "Focused")

#         if posture == "Focused":
#             last_focused_time = current_time
#             focus_status = "Focused"
#         else:
#             elapsed_time = current_time - last_focused_time
#             if elapsed_time > focus_threshold:
#                 focus_status = "Not Focused"

#         user_session["last_focused_time"] = last_focused_time
#         user_session["focus_status"] = focus_status

#         return JSONResponse({
#             "posture": posture,
#             "head": valHead,
#             "left": valLeft,
#             "right": valRight
#         })

#     except Exception as e:
#         return JSONResponse(status_code=400, content={"error": str(e)})

# # 값 업데이트용 모델
# class ThresholdValues(BaseModel):
#     valHead: float = 0
#     valLeft: float = 0
#     valRight: float = 0

# # 임계값 업데이트 API
# @app.post("/update_values/")
# async def update_values(values: ThresholdValues):
#     global valHead, valLeft, valRight

#     try:
#         if values.valHead > 0:
#             valHead = values.valHead * 0.01
#         if values.valLeft > 0:
#             valLeft = values.valLeft * 0.01
#         if values.valRight > 0:
#             valRight = values.valRight * 0.01

#         print("F Head:", valHead)
#         print("F Left:", valLeft)
#         print("F Right:", valRight)

#         return JSONResponse({"message": "Values updated successfully"})

#     except Exception as e:
#         return JSONResponse(status_code=400, content={"error2": str(e)})
