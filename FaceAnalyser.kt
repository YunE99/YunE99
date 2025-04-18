package com.ondy.studybuddy.managers

import android.annotation.SuppressLint
import android.graphics.PointF
import android.util.Log
import android.widget.TextView
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.view.PreviewView
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.facemesh.*
import kotlin.math.hypot
import kotlin.math.sqrt

class FaceAnalyzer(
    private val statusView: TextView,
    private val overlayView: FaceOverlay,
    private val previewView: PreviewView
) : ImageAnalysis.Analyzer {

//  [EAR, bounding box, 시간 측정을 위한 상태 변수들]
//  ◼ EAR
    private val earBuffer = mutableListOf<Double>()

//  ◼ Bounding obx
    private val bboxWindow = mutableListOf<Double>()
    private val bboxWindowSize = 5
//  ◼ 범위 밖 카운트
    private var outOfRangeDurationSec = 0
    private var lastOutOfRangeStart = 0L
//  ◼ 시간 및 카운트
    private var closedDurationSec = 0
    private var closedCount = 0
    private var lastClosedTime = 0L
//  ◼ 상태
    private var lastState: String = ""

//  [bounding box 높이 이동 평균 계산]
    private fun getSmoothedBoundingBoxHeight(newHeight: Double): Double {
        bboxWindow.add(newHeight)
        if (bboxWindow.size > bboxWindowSize) bboxWindow.removeAt(0)
        return bboxWindow.average()
    }

//  [이미지 좌표를 PreviewView 기준 좌표로 변환]
    private fun translateToViewCoordinates(
        point: PointF,
        imageProxy: ImageProxy,
        previewView: PreviewView,
        offsetX: Float = 0f,
        offsetY: Float = 0f
    ): PointF {
        val rotation = imageProxy.imageInfo.rotationDegrees
        val isRotated = rotation == 90 || rotation == 270
        val imageWidth = if (isRotated) imageProxy.height else imageProxy.width
        val imageHeight = if (isRotated) imageProxy.width else imageProxy.height
        val viewWidth = previewView.width.toFloat()
        val viewHeight = previewView.height.toFloat()
        val scaleX = viewWidth / imageWidth
        val scaleY = viewHeight / imageHeight
        val scale = minOf(scaleX, scaleY)
        val dx = (viewWidth - imageWidth * scale) / 2f
        val dy = (viewHeight - imageHeight * scale) / 2f
        val mappedX = point.x * scale + dx + offsetX
        val mappedY = point.y * scale + dy + offsetY
        return PointF(mappedX, mappedY)
    }

//  [FaceMeshDetector 초기화]
    private val detector: FaceMeshDetector by lazy {
        val options = FaceMeshDetectorOptions.Builder()
            .setUseCase(FaceMeshDetectorOptions.FACE_MESH)
            .build()
        FaceMeshDetection.getClient(options)
    }


//  [실시간 프레임 분석 함수]
    @SuppressLint("UnsafeOptInUsageError")
    override fun analyze(imageProxy: ImageProxy) {
        val mediaImage = imageProxy.image ?: run {
            imageProxy.close()
            return
        }
        val inputImage = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
        val now = System.currentTimeMillis()

        detector.process(inputImage)
            .addOnSuccessListener { meshes ->
                if (meshes.isEmpty()) {
                    // 얼굴 미감지 상태
                    if (lastState != "범위 밖") {
                        lastOutOfRangeStart = now
                        lastState = "범위 밖"
                    }

                    val duration = ((now - lastOutOfRangeStart) / 1000).toInt()
//                    ㆍSystem.currentTimeMillis()는 현재 시각을 밀리초(1/1000초) 단위로 반환
//                    ㆍ시간 차이를 초 단위로 보고 싶으므로 1000으로 나눔
//                    ㆍ.toInt()는 소수점 제거 → 정수 초 단위로 표현

                    statusView.post {
                        statusView.text = "범위 밖 (감지 실패)\n경과: ${duration}초"
                    }
                    return@addOnSuccessListener
                }
                // 얼굴 다시 감지됨
                if (lastState == "범위 밖" && lastOutOfRangeStart > 0) {
                    val duration = ((now - lastOutOfRangeStart) / 1000).toInt()
                    outOfRangeDurationSec += duration
                    lastOutOfRangeStart = 0L
                }

                val mesh = meshes[0]
                val allPoints = mesh.allPoints.map { point ->
                    val pos = point.position
                    PointF(pos.x, pos.y)
                }

                val transformedPoints = allPoints.map {
                    translateToViewCoordinates(it, imageProxy, previewView)
                }

                overlayView.post { overlayView.setAllPoints(transformedPoints) }

//              [bounding box 및 안내 원 기준 체크]
                val faceBoxHeight = getSmoothedBoundingBoxHeight(mesh.boundingBox.height().toDouble())
                val isOutside = transformedPoints.any {
                    val dx = it.x - overlayView.getGuideCenter().x
                    val dy = it.y - overlayView.getGuideCenter().y
                    sqrt(dx * dx + dy * dy) > overlayView.getGuideRadius()
                }

                if (faceBoxHeight < 170.0 || isOutside) {
                    lastState = "기준 미달"
                    statusView.post { statusView.text = "자세 벗어남" }
                    imageProxy.close()
                    return@addOnSuccessListener
                }

//              [EAR 변수]
                val leftEyePoints = getMeshPoints(mesh, listOf(33, 160, 158, 133, 153, 144))
                val rightEyePoints = getMeshPoints(mesh, listOf(362, 385, 387, 263, 373, 380))
                val leftEAR = computeEAR(leftEyePoints)
                val rightEAR = computeEAR(rightEyePoints)
                val ear = (leftEAR + rightEAR) / 2.0
                earBuffer.add(ear)

                // 얼굴크기, 양쪽눈 사이 거리 기반 EAR 정규화
                val faceHeight = mesh.boundingBox.height().toFloat()
                val eyeDistance = distance(leftEyePoints[0], rightEyePoints[3])
                val earByFace = (ear / faceHeight) * 100.0
                val earByEye = (ear / eyeDistance) * 100.0
                val finalEAR = (earByFace + earByEye) / 2.0  // ← 여기서 최종 EAR 사용

//                var threshold = (eyeDistance / faceHeight) * 0.3 // 임계값 카메라 아래
                var threshold = (eyeDistance / faceHeight) * 0.2 // 임계값 카메라 위

                val diff = finalEAR - threshold

                if (diff >= 0.35) {
                    threshold += 0.3  // [sy - 차이가 0.3 초과 → threshold ↑]
                } else if (diff >= 0.25) {
                    threshold += 0.2  // [sy - 차이가 0.2 초과 → threshold ↑]
                } else if (diff >= 0.15)
                    threshold += 0.1

//              [하품 변수]
//                val upperLip = getMeshPoints(mesh, listOf(13, 14, 15))
//                val lowerLip = getMeshPoints(mesh, listOf(17, 18, 87))
//                val mouthOpenRatio = computeMouthOpenRatio(upperLip, lowerLip)

//              [눈 감음 조건문]
                val isClosed = finalEAR < threshold
//                val isYawning = !isClosed && mouthOpenRatio > 0.9

                val status = when {
                    isClosed -> "눈 감김"
                    else -> "눈 뜸"
                }

                if (status != lastState) {
                    if (status == "눈 감김") lastClosedTime = now
                    else if (lastState == "눈 감김") {
                        val duration = ((now - lastClosedTime) / 1000).toInt()
                        if (duration >= 5) {
                            closedDurationSec += duration
                            closedCount++
                        }
                    }
                    lastState = status
                }

//              [상태 출력]
                if (status == "눈 감김") {
                    val duration = ((now - lastClosedTime) / 1000).toInt()

                    val previewSec = closedDurationSec + if (duration >= 5) duration else 0
                    val previewCount = closedCount + if (duration >= 5) 1 else 0

                    statusView.post {
                        statusView.text = "$status | EAR: %.2f\n th : %.2f \n ${previewCount}회 : ${previewSec}s\n${outOfRangeDurationSec}s".format(finalEAR, threshold)
                    }
                } else {
                    statusView.post {
                        statusView.text = "$status | EAR: %.2f\n th : %.2f \n ${closedCount}회 : ${closedDurationSec}s\n${outOfRangeDurationSec}s".format(finalEAR, threshold)
                    }
                }


                imageProxy.close()
            }
            .addOnFailureListener {
                Log.e("FaceAnalyzer", "감지 실패: ${it.message}")
            }
            .addOnCompleteListener {
                imageProxy.close()
            }
    }

//  [포인트 인덱스를 기반으로 실제 PointF 리스트 추출]
    private fun getMeshPoints(mesh: FaceMesh, indexes: List<Int>): List<PointF> {
        return indexes.mapNotNull { idx ->
            val point = mesh.allPoints.getOrNull(idx)
            val pos = point?.position
            if (pos != null) PointF(pos.x, pos.y) else null
        }
    }

//  [EAR(Eye Aspect Ratio) 계산]
    private fun computeEAR(points: List<PointF>): Double {
        if (points.size < 6) return 1.0
        val vertical1 = distance(points[1], points[5])
        val vertical2 = distance(points[2], points[4])
        val verticalAvg = (vertical1 + vertical2) / 2
        val horizontal = distance(points[0], points[3])
        return if (horizontal != 0f) (verticalAvg / horizontal).toDouble() else 1.0
    }

//    [입 벌림 비율 계산 (하품)]
//    private fun computeMouthOpenRatio(top: List<PointF>, bottom: List<PointF>): Double {
//        if (top.isEmpty() || bottom.isEmpty()) return 0.0
//        val topMid = top[top.size / 2]
//        val bottomMid = bottom[bottom.size / 2]
//        val left = top.first()
//        val right = top.last()
//        val vertical = distance(topMid, bottomMid)
//        val horizontal = distance(left, right)
//        return if (horizontal != 0f) (vertical / horizontal).toDouble() else 0.0
//    }

//  [두 점 사이 거리 계산]
    private fun distance(p1: PointF, p2: PointF): Float {
        return hypot(p1.x - p2.x, p1.y - p2.y)
    }
}
