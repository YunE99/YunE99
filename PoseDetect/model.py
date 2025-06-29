from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil, cv2, os
from datetime import datetime
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모델 초기화
model_path = "pose_landmarker.task"
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    output_segmentation_masks=False,
    num_poses=1
)
pose_landmarker = vision.PoseLandmarker.create_from_options(options)

# HTML UI
@app.get("/", response_class=HTMLResponse)
async def serve_form():
    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
      <meta charset="UTF-8">
      <title>Pose 상태 분석</title>
    </head>
    <body>
      <h2>이미지 업로드 후 포즈 분석</h2>
      <form id="upload-form">
        <input type="file" id="image" name="file" accept="image/*" required>
        <button type="submit">업로드</button>
      </form>
      <h3>결과:</h3>
      <div id="result">아직 분석 전입니다.</div>

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

# 포즈 분석 API
@app.post("/pose")
async def analyze_pose(file: UploadFile = File(...)):
    # 임시 파일 저장
    temp_filename = "temp_input.jpg"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 이미지 로드
    mp_image = mp.Image.create_from_file(temp_filename)
    original_img = cv2.imread(temp_filename)
    h, w, _ = original_img.shape

    result = pose_landmarker.detect(mp_image)

    status = None
    result_filename = None

    if result.pose_landmarks:
        lm = result.pose_landmarks[0]

        nose = lm[0].y
        left_ear = lm[7].y
        right_ear = lm[8].y
        left_shoulder = lm[11].y
        right_shoulder = lm[12].y
        avg_shoulder = (left_shoulder + right_shoulder) / 2
        left_elbow = lm[13].y
        right_elbow = lm[14].y

        score = 0
        if nose < avg_shoulder: score += 1
        if left_ear < avg_shoulder: score += 1
        if right_ear < avg_shoulder: score += 1

        if score >= 2:  # 2개 이상이면 학습중
            status = "학습중"
        else:
            status = "학습안함"




        # 랜드마크 시각화
        for idx, color, label in [
            (0, (0, 0, 255), "nose"),
            (7, (0, 122, 255), "left_ear"),
            (8, (0, 122, 255), "right_ear"),
            (11, (122, 255, 0), "left_shoulder"),
            (12, (122, 255, 0), "right_shoulder"),
            (13, (0, 255, 120), "left_elbow"),
            (14, (0, 255, 120), "right_elbow")
        ]:
            x, y = int(lm[idx].x * w), int(lm[idx].y * h)
            cv2.circle(original_img, (x, y), 2, color, -1)
            cv2.putText(original_img, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # 학습안함일 때만 이미지 저장
        # if status == "학습안함":
        now = datetime.now()
        result_filename = now.strftime("result_%Y%m%d_%H%M%S_%f")[:-3] + ".jpg"  # 밀리초까지
        cv2.imwrite(result_filename, original_img)

    else:
        status = "포즈 감지 실패"

    # 원본 삭제
    os.remove(temp_filename)

    return JSONResponse(content={
        "status": status,
        "image_url": f"/result_image/{result_filename}" if result_filename else ""
    })

# 저장된 이미지 정적 라우터
from fastapi.staticfiles import StaticFiles
app.mount("/result_image", StaticFiles(directory="."), name="result_image")
