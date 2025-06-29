from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import shutil, cv2, os
from datetime import datetime
import numpy as np
import tensorflow as tf

# 추가해야 할 것 
# 공부중이 아닐 때 -> 동작감지(몇분동안) -> 안움직일시 자는 것으로 판단 -> 5분마다 사진저장?
# 화면에서 벗어 날때 -> 경고
# 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 결과 이미지 저장 폴더
SAVE_DIR = "./labeling_result"
os.makedirs(SAVE_DIR, exist_ok=True)

# MoveNet Thunder 모델 로드
interpreter = tf.lite.Interpreter(model_path="movenet_thunder.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
input_size = 256  # Thunder 모델 기준

@app.get("/", response_class=HTMLResponse)
async def serve_form():
    return """
    <!DOCTYPE html>
    <html lang=\"ko\">
    <head>
      <meta charset=\"UTF-8\">
      <title>Pose 상태 분석</title>
    </head>
    <body>
      <h2>이미지 업로드 후 포즈 분석</h2>
      <form id=\"upload-form\">
        <input type=\"file\" id=\"image\" name=\"file\" accept=\"image/*\" required>
        <button type=\"submit\">업로드</button>
      </form>
      <h3>결과:</h3>
      <div id=\"result\">아직 분석 전입니다.</div>
      <script>
        const form = document.getElementById("upload-form");
        const resultDiv = document.getElementById("result");
        form.addEventListener("submit", async (e) => {
          e.preventDefault();
          const fileInput = document.getElementById("image");
          const formData = new FormData();
          formData.append("file", fileInput.files[0]);
          resultDiv.textContent = "분석 중...";
          try {
            const response = await fetch("/pose", {
              method: "POST",
              body: formData
            });
            const data = await response.json();
            resultDiv.innerHTML = `상태: ${data.status}<br><img src="${data.image_url}" width="300">`;
          } catch (error) {
            resultDiv.textContent = " 오류 발생: " + error;
          }
        });
      </script>
    </body>
    </html>
    """

@app.post("/pose")
async def analyze_pose(file: UploadFile = File(...)):
    temp_filename = "temp_input.jpg"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 원본 이미지 로드
    original_img = cv2.imread(temp_filename)
    h, w, _ = original_img.shape

    # Movenet 입력 전처리
    input_img = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
    resized_img = cv2.resize(input_img, (input_size, input_size))
    input_tensor = resized_img.astype(np.uint8)
    input_tensor = np.expand_dims(input_tensor, axis=0)

    # 모델 추론
    interpreter.set_tensor(input_details[0]['index'], input_tensor)
    interpreter.invoke()
    keypoints = interpreter.get_tensor(output_details[0]['index'])[0][0]  # (17, 3)

    # 좌표 변환 및 판법
    landmarks = []
    for kp in keypoints:
        y, x, conf = kp
        px, py = int(x * w), int(y * h)
        landmarks.append((px, py, conf))

    # 주요 관절
    nose_y = landmarks[0][1]
    left_eye_y = landmarks[1][1]
    right_eye_y = landmarks[2][1]
    left_ear_y = landmarks[3][1]
    right_ear_y = landmarks[4][1]
    left_shoulder_y = landmarks[5][1]
    right_shoulder_y = landmarks[6][1]
    avg_shoulder_y = (left_shoulder_y + right_shoulder_y) / 2

    score = 0
    if nose_y < avg_shoulder_y: score += 1
    if left_ear_y < avg_shoulder_y: score += 1
    if right_ear_y < avg_shoulder_y: score += 1
    if left_eye_y < avg_shoulder_y: score += 1
    if right_eye_y < avg_shoulder_y: score += 1

    status = "[Studying]" if score >= 3 else "[Not studying]"

    # 시각화
    colors = [(0, 0, 255), (0, 122, 255), (0, 122, 255), (0, 255, 0), (0, 255, 0), (255, 0, 255), (255, 0, 255)]
    labels = ["nose", "left_ear", "right_ear", "left_shoulder", "right_shoulder", "left_eye", "right_eye"]
    idxs = [0, 3, 4, 5, 6, 1, 2] 
    for i, idx in enumerate(idxs):
        x, y, conf = landmarks[idx]
        color = colors[i]
        label = labels[i]
        cv2.circle(original_img, (x, y), 3, color, -1)
        text = f"{label} ({conf:.2f})"
        cv2.putText(original_img, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)

    # 결과 이미지 저장
    filename =  "[UserId]" + status + datetime.now().strftime("_%Y%m%d_%H%M%S_%f")[:-3] + ".jpg"
    result_path = os.path.join(SAVE_DIR, filename)
    cv2.imwrite(result_path, original_img)
    os.remove(temp_filename)

    return JSONResponse(content={
        "status": status,
        "image_url": f"/result_image/{filename}"
    })

# 정적 파일 라우터
app.mount("/result_image", StaticFiles(directory=SAVE_DIR), name="result_image")
