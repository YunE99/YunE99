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
import com.google.mlkit.vision.pose.*
import com.google.mlkit.vision.pose.accurate.AccuratePoseDetectorOptions
import kotlin.math.hypot
import kotlin.math.sqrt

class FaceAnalyzer(
    private val statusView: TextView,        // ◼ 상태 텍스트뷰
    private val overlayView: FaceOverlay,    // ◼ 얼굴 오버레이 출력 뷰
    private val previewView: PreviewView     // ◼ 카메라 프리뷰 화면
) : ImageAnalysis.Analyzer {

    // ◼ EAR 보정용 얼굴 박스 높이 이력
    private val bboxWindow = mutableListOf<Double>()
    private val bboxWindowSize = 5

    // ◼ 범위 이탈 관련 상태
    private var outOfRangeTotalTime = 0
    private var outOfRangeStart = 0L
    private var isOutOfRange = false

    // ◼ 눈 감음 상태 관리
    private var eyeCloseStart = 0L
    private var alreadyCounted = false
    private var eyeCloseAccumulated = 0
    private var eyeDrowsyCount = 0
    private var eyeDrowsyTime = 0

    // ◼ 손목 무움직임 상태 관리
    private var noMoveStartTime = 0L
    private var moveAlreadyCounted = false
    private var noMoveAccumulated = 0
    private var noMoveCount = 0
    private var noMoveTime = 0

    // ◼ 동시 발생 상태 (눈감음+무움직임)
    private var overlapStartTime = 0L
    private var overlapActive = false
    private var overlapCount = 0
    private var overlapTime = 0

    // ◼ 손목 좌표 상태
    private val movementThreshold = 30f
    private var lastLeftWrist: PointF? = null
    private var lastRightWrist: PointF? = null

    // ◼ 얼굴 랜드마크 감지기
    private val detector: FaceMeshDetector by lazy {
        val options = FaceMeshDetectorOptions.Builder()
            .setUseCase(FaceMeshDetectorOptions.FACE_MESH)
            .build()
        FaceMeshDetection.getClient(options)
    }

    // ◼ 포즈(손목) 감지기
    private val poseDetector: PoseDetector by lazy {
        val options = AccuratePoseDetectorOptions.Builder()
            .setDetectorMode(AccuratePoseDetectorOptions.STREAM_MODE)
            .build()
        PoseDetection.getClient(options)
    }

    @androidx.camera.core.ExperimentalGetImage
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
                    if (!isOutOfRange) {
                        outOfRangeStart = now
                        isOutOfRange = true
                        resetCounters()
                    }

                    val elapsedMs = now - outOfRangeStart
                    val duration2 = (elapsedMs / 1000).toInt()

                    statusView.post {
                        statusView.text = "범위 밖 (감지 실패)\n경과: ${duration2}초"
                    }

                    imageProxy.close()
                    return@addOnSuccessListener
                }
                runFullAnalysis(inputImage, meshes, now, imageProxy)
            }
            .addOnFailureListener {
                imageProxy.close()
            }
    }

    private fun runFullAnalysis(inputImage: InputImage, meshes: List<FaceMesh>, now: Long, imageProxy: ImageProxy) {
        if (isOutOfRange) {
            val elapsedMs = now - outOfRangeStart
            if (elapsedMs >= 1000) {
                outOfRangeTotalTime += (elapsedMs / 1000).toInt()
            }
            outOfRangeStart = 0L
            isOutOfRange = false
        }

        val mesh = meshes[0]
        val allPoints = mesh.allPoints.map { PointF(it.position.x, it.position.y) }
        val viewPoints = allPoints.map { translateToViewCoordinates(it, imageProxy, previewView) }
        overlayView.post { overlayView.setAllPoints(viewPoints) }

        // ◼ 자세 벗어남 판단
        val faceBoxHeight = getSmoothedBoxHeight(mesh.boundingBox.height().toDouble())
        val isOutside = viewPoints.any {
            val dx = it.x - overlayView.getGuideCenter().x
            val dy = it.y - overlayView.getGuideCenter().y
            sqrt(dx * dx + dy * dy) > overlayView.getGuideRadius()
        }
        if (faceBoxHeight < 170.0 || isOutside) {
            statusView.post { statusView.text = "자세 벗어남" }
            imageProxy.close()
            return
        }

        poseDetector.process(inputImage)
            .addOnSuccessListener { pose ->
                // ◼ 손목 좌표 계산 및 움직임 여부 판단
                val left = pose.getPoseLandmark(PoseLandmark.LEFT_WRIST)
                val right = pose.getPoseLandmark(PoseLandmark.RIGHT_WRIST)
                val lw = left?.position
                val rw = right?.position
                val lwConf = left?.inFrameLikelihood ?: 0f
                val rwConf = right?.inFrameLikelihood ?: 0f

                val moveL = if (lw != null && lwConf >= 0.7f && lastLeftWrist != null)
                    distance(lastLeftWrist!!, PointF(lw.x, lw.y)) > movementThreshold else false
                val moveR = if (rw != null && rwConf >= 0.7f && lastRightWrist != null)
                    distance(lastRightWrist!!, PointF(rw.x, rw.y)) > movementThreshold else false
                val moved = moveL || moveR

                lastLeftWrist = lw?.let { PointF(it.x, it.y) }
                lastRightWrist = rw?.let { PointF(it.x, it.y) }

                // ◼ EAR 계산
                val leftEye = getMeshPoints(mesh, listOf(33, 160, 158, 133, 153, 144))
                val rightEye = getMeshPoints(mesh, listOf(362, 385, 387, 263, 373, 380))
                val ear = (computeEAR(leftEye) + computeEAR(rightEye)) / 2.0
                val faceHeight = mesh.boundingBox.height().toFloat()
                val eyeDist = distance(leftEye[0], rightEye[3])
                val finalEAR = ((ear / faceHeight) * 100.0 + (ear / eyeDist) * 100.0) / 2.0

                var threshold = (eyeDist / faceHeight) * 0.2
                val diff = finalEAR - threshold
                threshold += when {
                    diff >= 0.35 -> 0.3
                    diff >= 0.25 -> 0.2
                    diff >= 0.15 -> 0.1
                    else -> 0.0
                }
                val isClosed = finalEAR < threshold

                // ◼ 눈 감음 판단
                if (isClosed) {
                    if (eyeCloseStart == 0L) eyeCloseStart = now
                    val elapsedMs = now - eyeCloseStart
                    if (elapsedMs >= 5000) {
                        val seconds = (elapsedMs / 1000).toInt()
                        if (seconds > eyeCloseAccumulated) {
                            eyeDrowsyTime += seconds - eyeCloseAccumulated  // ✅ 누적 증가분만 더함
                            eyeCloseAccumulated = seconds
                        }
                        if (!alreadyCounted) {
                            eyeDrowsyCount++
                            alreadyCounted = true
                        }
                    }
                } else {
                    eyeCloseStart = 0L
                    eyeCloseAccumulated = 0
                    alreadyCounted = false
                }

                // ◼ 움직임 없음 판단
                if (!moved) {
                    if (noMoveStartTime == 0L) noMoveStartTime = now
                    val elapsedMs = now - noMoveStartTime
                    if (elapsedMs >= 5000) {
                        val seconds = (elapsedMs / 1000).toInt()
                        if (seconds > noMoveAccumulated) {
                            noMoveTime += seconds - noMoveAccumulated
                            noMoveAccumulated = seconds
                        }
                        if (!moveAlreadyCounted) {
                            noMoveCount++
                            moveAlreadyCounted = true
                        }
                    }
                } else {
                    noMoveStartTime = 0L
                    noMoveAccumulated = 0
                    moveAlreadyCounted = false
                }

                // ◼ 감음 + 무움직임 동시 판단
                val bothActive = isClosed && !moved
                if (bothActive) {
                    if (overlapStartTime == 0L) {
                        overlapStartTime = now
                    } else {
                        val elapsedMs = now - overlapStartTime
                        if (elapsedMs >= 5000) {
                            val seconds = (elapsedMs / 1000).toInt()
                            if (seconds > overlapTime) {
                                overlapTime = seconds  // ✅ 항상 최신 유지시간으로 설정
                            }
                            if (!overlapActive) {
                                overlapCount++
                                overlapActive = true
                            }
                        }
                    }
                } else {
                    overlapStartTime = 0L
                    overlapActive = false
                }

                // ◼ 최종 상태 출력
                val totalCount = (eyeDrowsyCount + noMoveCount - overlapCount).coerceAtLeast(0)
                val totalTime = (eyeDrowsyTime + noMoveTime - overlapTime).coerceAtLeast(0)

                val statusText = buildString {
                    append("상태: ${if (isClosed) "눈 감김" else "눈 뜸"}")
                    append(" | : ${if (moved) "O" else "X"}\n")
                    append("총 ${totalCount}회 | ${totalTime}초\n")
                    append("범위 이탈: ${outOfRangeTotalTime}초")
                }
                statusView.post { statusView.text = statusText }
                imageProxy.close()
            }
            .addOnFailureListener {
                imageProxy.close()
            }
    }

    private fun getMeshPoints(mesh: FaceMesh, indexes: List<Int>): List<PointF> {
        return indexes.mapNotNull { idx ->
            mesh.allPoints.getOrNull(idx)?.position?.let { PointF(it.x, it.y) }
        }
    }

    private fun computeEAR(points: List<PointF>): Double {
        if (points.size < 6) return 1.0
        val vertical = (distance(points[1], points[5]) + distance(points[2], points[4])) / 2
        val horizontal = distance(points[0], points[3])
        return if (horizontal != 0f) (vertical / horizontal).toDouble() else 1.0
    }

    private fun distance(p1: PointF, p2: PointF): Float {
        return hypot(p1.x - p2.x, p1.y - p2.y)
    }

    private fun resetCounters() {
        eyeCloseStart = 0L
        alreadyCounted = false
        eyeCloseAccumulated = 0
        noMoveStartTime = 0L
        moveAlreadyCounted = false
        noMoveAccumulated = 0
        overlapStartTime = 0L
        overlapActive = false
    }

    private fun getSmoothedBoxHeight(newHeight: Double): Double {
        bboxWindow.add(newHeight)
        if (bboxWindow.size > bboxWindowSize) bboxWindow.removeAt(0)
        return bboxWindow.average()
    }

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
        val scale = minOf(viewWidth / imageWidth, viewHeight / imageHeight)
        val dx = (viewWidth - imageWidth * scale) / 2f
        val dy = (viewHeight - imageHeight * scale) / 2f
        return PointF(point.x * scale + dx + offsetX, point.y * scale + dy + offsetY)
    }
}
