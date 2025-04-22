// ✅ 수정 적용된 전체 코드 (눈 감음 / 무움직임 모두 같은 방식으로 작동)
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
    private val statusView: TextView,
    private val overlayView: FaceOverlay,
    private val previewView: PreviewView
) : ImageAnalysis.Analyzer {

    private val bboxWindow = mutableListOf<Double>()
    private val bboxWindowSize = 5

    private var outOfRangeTime = 0
    private var outOfRangeStart = 0L

    private var eyeCloseStart = 0L
    private var alreadyCounted = false
    private var prevState: String = ""

    // ✅ 눈 감음 상태 관련
    private var eyeCloseAccumulated = 0
    private var eyeDrowsyCount = 0
    private var eyeDrowsyTime = 0

    // ✅ 움직임 없음 관련
    private var noMoveStartTime = 0L
    private var moveAlreadyCounted = false
    private var noMoveAccumulated = 0
    private var noMoveCount = 0
    private var noMoveTime = 0

    private val movementThreshold = 30f
    private var lastLeftWrist: PointF? = null
    private var lastRightWrist: PointF? = null
    private var isMoving = false
    private var nowMove = false

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

    private val detector: FaceMeshDetector by lazy {
        val options = FaceMeshDetectorOptions.Builder()
            .setUseCase(FaceMeshDetectorOptions.FACE_MESH)
            .build()
        FaceMeshDetection.getClient(options)
    }

    private val poseDetector: PoseDetector by lazy {
        val options = AccuratePoseDetectorOptions.Builder()
            .setDetectorMode(AccuratePoseDetectorOptions.STREAM_MODE)
            .build()
        PoseDetection.getClient(options)
    }

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
                    if (prevState != "범위 밖") {
                        outOfRangeStart = now
                        prevState = "범위 밖"
                    }
                    val duration = ((now - outOfRangeStart) / 1000).toInt()
                    statusView.post { statusView.text = "범위 밖 (감지 실패)\n경과: ${duration}초" }
                    imageProxy.close()
                    return@addOnSuccessListener
                }

                val mesh = meshes[0]
                val allPoints = mesh.allPoints.map { PointF(it.position.x, it.position.y) }
                val viewPoints = allPoints.map { translateToViewCoordinates(it, imageProxy, previewView) }
                overlayView.post { overlayView.setAllPoints(viewPoints) }

                val faceBoxHeight = getSmoothedBoxHeight(mesh.boundingBox.height().toDouble())
                val isOutside = viewPoints.any {
                    val dx = it.x - overlayView.getGuideCenter().x
                    val dy = it.y - overlayView.getGuideCenter().y
                    sqrt(dx * dx + dy * dy) > overlayView.getGuideRadius()
                }
                if (faceBoxHeight < 170.0 || isOutside) {
                    prevState = "기준 미달"
                    statusView.post { statusView.text = "자세 벗어남" }
                    imageProxy.close()
                    return@addOnSuccessListener
                }

                poseDetector.process(inputImage)
                    .addOnSuccessListener { pose ->
                        val leftLandmark = pose.getPoseLandmark(PoseLandmark.LEFT_WRIST)
                        val rightLandmark = pose.getPoseLandmark(PoseLandmark.RIGHT_WRIST)
                        val lw = leftLandmark?.position
                        val rw = rightLandmark?.position
                        val lwConf = leftLandmark?.inFrameLikelihood ?: 0f
                        val rwConf = rightLandmark?.inFrameLikelihood ?: 0f

                        if (lw == null || rw == null) {
                            imageProxy.close()
                            return@addOnSuccessListener
                        }

                        val mappedLW = translateToViewCoordinates(PointF(lw.x, lw.y), imageProxy, previewView)
                        val mappedRW = translateToViewCoordinates(PointF(rw.x, rw.y), imageProxy, previewView)
                        overlayView.setWristPoints(left = mappedLW, right = mappedRW, leftConf = lwConf, rightConf = rwConf)

                        val moveL = if (lwConf >= 0.7f && lastLeftWrist != null) distance(lastLeftWrist!!, PointF(lw.x, lw.y)) > movementThreshold else false
                        val moveR = if (rwConf >= 0.7f && lastRightWrist != null) distance(lastRightWrist!!, PointF(rw.x, rw.y)) > movementThreshold else false
                        lastLeftWrist = PointF(lw.x, lw.y)
                        lastRightWrist = PointF(rw.x, rw.y)

                        val moved = moveL || moveR

                        if (moved) {
                            nowMove = true
                            isMoving = true
                            noMoveStartTime = 0L
                            noMoveAccumulated = 0
                            moveAlreadyCounted = false
                        } else {
                            if (noMoveStartTime == 0L) noMoveStartTime = now

                            val totalDuration = ((now - noMoveStartTime) / 1000).toInt()

                            if (totalDuration >= 5) {
                                val effectiveDuration = totalDuration - 5 // 5초 넘은 시점부터 누적
                                val delta = effectiveDuration - noMoveAccumulated
                                if (delta > 0) noMoveTime += delta
                                noMoveAccumulated = effectiveDuration

                                if (!moveAlreadyCounted) {
                                    noMoveCount++
                                    moveAlreadyCounted = true
                                }

                                isMoving = false
                            }
                        }

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
                        val state = if (isClosed) "눈 감김" else "눈 뜸"

                        if (isClosed) {
                            if (prevState != "눈 감김") {
                                eyeCloseStart = now
                                eyeCloseAccumulated = 0
                                alreadyCounted = false
                            }

                            val totalDuration = ((now - eyeCloseStart) / 1000).toInt()

                            if (totalDuration >= 5) {
                                val effectiveDuration = totalDuration - 5
                                val delta = effectiveDuration - eyeCloseAccumulated
                                if (delta > 0) eyeDrowsyTime += delta
                                eyeCloseAccumulated = effectiveDuration

                                if (!alreadyCounted) {
                                    eyeDrowsyCount++
                                    alreadyCounted = true
                                }
                            }
                        }

                        prevState = state

                        val statusText = buildString {
                            append("상태: $state")
                            append("\nEAR: %.2f (%s)\n".format(finalEAR, if (isMoving) "O" else "X"))
                            append("${eyeDrowsyCount + noMoveCount}회 | ${eyeDrowsyTime + noMoveTime}초\n")
                            append("범위 이탈: ${outOfRangeTime}초")
                        }

                        statusView.post { statusView.text = statusText }
                        imageProxy.close()
                    }
                    .addOnFailureListener {
                        Log.e("PoseAnalyzer", "자세 인식 실패: ${it.message}")
                        imageProxy.close()
                    }

                if (prevState == "범위 밖" && outOfRangeStart > 0) {
                    val duration = ((now - outOfRangeStart) / 1000).toInt()
                    outOfRangeTime += duration
                    outOfRangeStart = 0L
                }
            }
            .addOnFailureListener {
                Log.e("FaceAnalyzer", "감지 실패: ${it.message}")
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
}
