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
import kotlin.math.pow
import kotlin.math.sqrt

class FaceAnalyzer(
    private val statusView: TextView,        // ◼ 상태 텍스트뷰
    private val overlayView: FaceOverlay,    // ◼ 얼굴 오버레이 출력 뷰
    private val previewView: PreviewView,     // ◼ 카메라 프리뷰 화면
    private val heartRateLabel: TextView?,
) : ImageAnalysis.Analyzer {

    // ◼ EAR 보정용 얼굴 박스 높이 이력
    private val bboxWindow = mutableListOf<Double>()
    private val bboxWindowSize = 5

    // ◼ 범위 이탈 관련 변수
    private var outOfRangeTotalTime = 0
    private var outOfRangeStart = 0L
    private var isOutOfRange = false

    // ◼ 눈 감음 상태 관리 변수
    private var eyeCloseStart = 0L
    private var alreadyCounted = false
    private var eyeCloseAccumulated = 0
    private var eyeDrowsyCount = 0
    private var eyeDrowsyTime = 0

    // ◼ 손목 무움직임 상태 관리 변수
    private var noMoveStartTime = 0L
    private var moveAlreadyCounted = false
    private var noMoveAccumulated = 0
    private var noMoveCount = 0
    private var noMoveTime = 0

    // ◼ 동시 발생 상태 (눈감음+무움직임) 변수
    private var overlapStartTime = 0L
    private var overlapActive = false
    private var overlapCount = 0
    private var overlapTime = 0

    // ◼ 손목 좌표 상태 변수
    private val movementThreshold = 50f
    private var lastLeftWrist: PointF? = null
    private var lastRightWrist: PointF? = null

    // ◼ 얼굴 좌우 각도(Yaw) 상태 저장 변수
    private var lastYaw: Float? = null
    private val yawDiffThreshold = 3f // ◼ 3도 이내 변화는 정지 상태로 간주

    // ◼ 자세 벗어남 변수
    private var postureOutStart = 0L
    private var postureOutAccumulated = 0
    private var postureOutTime = 0
    private var postureOutCount = 0
    private var postureAlreadyCounted = false

    // ◼ 범위 이탈 변수
    private var outOfRangeAccumulated = 0
    private var outOfRangeCount = 0
    private var outOfRangeAlreadyCounted = false

    // ◼ 통합변수
    private var F_outTimeValue = 5000 // 범위 이탈(자리 이탈) 시간 값
    private var F_poseTimeValue = 10000 // 자세 벗어남 시간 값
    private var F_MoveAndBothValue = 60000 // 움직임, 동시상태 시간 값
    private var F_isCloseValue = 5000 // 눈 감음 시간 값

    // ◼ 얼굴 랜드마크 탐지 및 초기화
    private val detector: FaceMeshDetector by lazy {
        val options = FaceMeshDetectorOptions.Builder()
            .setUseCase(FaceMeshDetectorOptions.FACE_MESH)
            .build()
        FaceMeshDetection.getClient(options)
    }

    // ◼ 포즈(손목) 탐지 및 초기화
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
        // ◼ 현재시간
        val now = System.currentTimeMillis()

        detector.process(inputImage)
            .addOnSuccessListener { meshes ->
                val now = System.currentTimeMillis()

                // 얼굴 감지 실패 상태 → 범위 밖
                if (meshes.isEmpty()) {
                    if (!isOutOfRange) {
                        outOfRangeStart = now
                        isOutOfRange = true
                    }
                    postureOutStart = 0L
                    postureOutAccumulated = 0
                    postureAlreadyCounted = false

                    val elapsedMs = now - outOfRangeStart
                    val duration2 = (elapsedMs / 1000).toInt()

                    if (elapsedMs >= F_outTimeValue) { // 자리 이탈 대기시간
                        val seconds = duration2
                        if (seconds  > outOfRangeAccumulated) {
                            outOfRangeTotalTime += seconds  - outOfRangeAccumulated
                            outOfRangeAccumulated = seconds
                        }
                        if (!outOfRangeAlreadyCounted) {
                            outOfRangeCount++
                            outOfRangeAlreadyCounted = true
                        }
                    }

                    statusView.post {
                        statusView.text = "범위 밖 (감지 실패)\n경과: ${duration2}초"
                    }

                    imageProxy.close()
                    return@addOnSuccessListener
                }

                //  ◼ 범위 복귀 초기화
                if (isOutOfRange) {
                    val elapsedMs = now - outOfRangeStart
                    if (elapsedMs >= F_outTimeValue) { // 범위 이탈 대기시간
                        val seconds = (elapsedMs / 1000).toInt()
                        if (seconds > outOfRangeAccumulated) {
                            outOfRangeTotalTime += seconds - outOfRangeAccumulated
                        }
                    }

                    outOfRangeStart = 0L
                    isOutOfRange = false
                    outOfRangeAccumulated = 0
                    outOfRangeAlreadyCounted = false
                }

                runFullAnalysis(inputImage, meshes, now, imageProxy)
            }
            .addOnFailureListener {
                imageProxy.close()
            }
    }

    private fun runFullAnalysis(inputImage: InputImage, meshes: List<FaceMesh>, now: Long, imageProxy: ImageProxy) {
        if (isOutOfRange) {
            outOfRangeStart = 0L
            isOutOfRange = false
            outOfRangeAccumulated = 0
            outOfRangeAlreadyCounted = false
        }

        val mesh = meshes[0]
        val allPoints = mesh.allPoints.map { PointF(it.position.x, it.position.y) }
        val viewPoints = allPoints.map { translateToViewCoordinates(it, imageProxy, previewView) }
        overlayView.post { overlayView.setAllPoints(viewPoints) }

        val FinalScore = FinalScore()
        val FinalScoreByCountRate = FinalScoreByCountRate()
        val StateScore = when{
            FinalScoreByCountRate >= 95 -> "완벽"
            FinalScoreByCountRate >= 90 -> "우수"
            FinalScoreByCountRate >= 85 -> "보통"
            FinalScoreByCountRate >= 80 -> "주의"
            FinalScoreByCountRate >= 75 -> "산만"
            else -> "위험"
        }
        heartRateLabel?.post {
            heartRateLabel.text = "%.0f | %s".format((FinalScore + FinalScoreByCountRate)/2, StateScore)

        }

        // ◼ 자세 벗어남 판단
        val scaledHeight = getScaledBoxHeight(mesh.boundingBox.height().toFloat(), imageProxy, previewView)
        val faceBoxHeight = getSmoothedBoxHeight(scaledHeight)
        val isOutside = viewPoints.any {
            val safeGuideRadius = overlayView.getGuideRadius() * 0.95f // 95%만 허용
            val dx = it.x - overlayView.getGuideCenter().x
            val dy = it.y - overlayView.getGuideCenter().y
            sqrt(dx * dx + dy * dy) > safeGuideRadius
        }
        val dynamicThreshold = overlayView.getGuideRadius() * 0.4f // 80%로 설정

        if (!isOutOfRange && (faceBoxHeight < dynamicThreshold || isOutside)) {
            eyeCloseStart = 0L
            eyeCloseAccumulated = 0
            alreadyCounted = false

            noMoveStartTime = 0L
            noMoveAccumulated = 0
            moveAlreadyCounted = false

            overlapStartTime = 0L
            overlapActive = false

            if (postureOutStart == 0L) postureOutStart = now
            val elapsedMs = now - postureOutStart
            val duration3 = (elapsedMs / 1000).toInt()

            if (elapsedMs >= F_poseTimeValue) { // 10초 이상일때
                val seconds = duration3
                if (seconds > postureOutAccumulated) {
                    postureOutTime += seconds - postureOutAccumulated
                    postureOutAccumulated = seconds
                }
                if (!postureAlreadyCounted) {
                    postureOutCount++
                    postureAlreadyCounted = true
                }
            }

            statusView.post {
                statusView.text = "자세 벗어남\n경과: ${duration3}초"
            }

            imageProxy.close()
            return
        } else {
            postureOutStart = 0L
            postureOutAccumulated = 0
            postureAlreadyCounted = false
        }


//        if (faceBoxHeight < 170.0 || isOutside) {
//            statusView.post { statusView.text = "자세 벗어남" }
//            imageProxy.close()
//            return
//        }

        poseDetector.process(inputImage)
            .addOnSuccessListener { pose ->
                // ◼ 손목 좌표 계산 및 움직임 여부 판단
                val left = pose.getPoseLandmark(PoseLandmark.LEFT_WRIST)
                val right = pose.getPoseLandmark(PoseLandmark.RIGHT_WRIST)
                val lw = left?.position
                val rw = right?.position
                val lwConf = left?.inFrameLikelihood ?: 0f
                val rwConf = right?.inFrameLikelihood ?: 0f

                val moveL = if (lw != null && lwConf >= 0.85f && lastLeftWrist != null)
                    distance(lastLeftWrist!!, PointF(lw.x, lw.y)) > movementThreshold else false
                val moveR = if (rw != null && rwConf >= 0.85f && lastRightWrist != null)
                    distance(lastRightWrist!!, PointF(rw.x, rw.y)) > movementThreshold else false

                // ◼ 얼굴 yaw 추정 (얼굴 좌우 움직임 판단)
                val moveYaw = if (mesh != null && mesh.allPoints.size > 263) {
                    val leftEyeOuter = mesh.allPoints[33].position
                    val rightEyeOuter = mesh.allPoints[263].position
                    val noseCenter = mesh.allPoints[168].position

                    val yawEstimate = estimateYaw(
                        PointF(leftEyeOuter.x, leftEyeOuter.y),
                        PointF(rightEyeOuter.x, rightEyeOuter.y),
                        PointF(noseCenter.x, noseCenter.y)
                    )
                    val movedYaw = lastYaw != null && kotlin.math.abs(yawEstimate - lastYaw!!) > yawDiffThreshold
                    lastYaw = yawEstimate
                    movedYaw
                } else {
                    false // ◀︎ yaw 계산 실패한 경우 움직임으로 간주하지 않음
                }

                val moved = moveL || moveR || moveYaw

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

                val adjustedThreshold = threshold + (((0.1 - threshold) * 100).pow(2)) * 0.01 - 0.065

//                val diff = finalEAR - threshold
//                threshold = when {
//                     diff >= 0.35 -> 0.3
//                     diff >= 0.25 -> 0.2
//                     diff >= 0.15 -> 0.1
//                     else -> 0.0
//                }
                val isClosed = finalEAR < adjustedThreshold

                // ◼ 눈 감음 판단
                if (isClosed) {
                    if (eyeCloseStart == 0L) eyeCloseStart = now
                    val elapsedMs = now - eyeCloseStart
                    if (elapsedMs >= F_isCloseValue) {
                        val seconds = (elapsedMs / 1000).toInt()
                        if (seconds > eyeCloseAccumulated) {
                            eyeDrowsyTime += seconds - eyeCloseAccumulated
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
                    if (elapsedMs >= F_MoveAndBothValue) { // 60초 이상일때
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
                        if (elapsedMs >= F_MoveAndBothValue) { // 안움직임 시간을 따라감
                            val seconds = (elapsedMs / 1000).toInt()
                            if (seconds > overlapTime) {
                                overlapTime = seconds  // 항상 최신 유지시간으로 설정
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
//                    append("상태: ${if (isClosed) "눈 감김" else "눈 뜸"}")
//                    append(" | : ${if (moved) "O" else "X"}\n")
//                    append("총 ${totalCount}회 | ${totalTime}초\n")
//                    append("범위 이탈: ${outOfRangeTotalTime}초")
//                    append("상태: ${if (isClosed) "눈 감김" else "눈 뜸"}")
//                    append(" | ${if (moved) "O" else "X"}\n")
                    append("졸음 | 자세 | 이탈 \n")
                    append("${totalCount}회 | ${postureOutCount} 회 | ${outOfRangeCount}회\n")
                    append("${totalTime}초 | ${postureOutTime}초 | ${outOfRangeTotalTime}초")
                }
                statusView.post { statusView.text = statusText }
                imageProxy.close()
            }
            .addOnFailureListener {
                imageProxy.close()
            }
    }

    // ◼ FaceMesh 포인트 추출
    private fun getMeshPoints(mesh: FaceMesh, indexes: List<Int>): List<PointF> {
        return indexes.mapNotNull { idx ->
            mesh.allPoints.getOrNull(idx)?.position?.let { PointF(it.x, it.y) }
        }
    }

    // ◼ EAR 보정 계산
    private fun computeEAR(points: List<PointF>): Double {
        if (points.size < 6) return 1.0
        val vertical = (distance(points[1], points[5]) + distance(points[2], points[4])) / 2
        val horizontal = distance(points[0], points[3])
        return if (horizontal != 0f) (vertical / horizontal).toDouble() else 1.0
    }

    // ◼ 거리 계산
    private fun distance(p1: PointF, p2: PointF): Float {
        return hypot(p1.x - p2.x, p1.y - p2.y)
    }

    // ◼ 얼굴 yaw 추정 함수: 눈 중심과 코의 상대 위치로 판단
    private fun estimateYaw(left: PointF?, right: PointF?, nose: PointF?): Float {
        // ◼ null 또는 비정상 좌표 방어 처리
        if (left == null || right == null || nose == null) return 0f
        if (left.x == 0f && left.y == 0f) return 0f
        if (right.x == 0f && right.y == 0f) return 0f
        if (nose.x == 0f && nose.y == 0f) return 0f

        // ◼ 정상 계산
        val eyeCenterX = (left.x + right.x) / 2f
        return nose.x - eyeCenterX
    }


    // ◼ 카운트 변수 초기화
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

    private fun FinalScore(): Double {
        val eyeScore = if (eyeDrowsyCount > 0) eyeDrowsyTime.toDouble() / (eyeDrowsyCount * 5) else 0.0
        val moveScore = if (noMoveCount > 0) noMoveTime.toDouble() / (noMoveCount * 30) else 0.0
        val overlapScore = if (overlapCount > 0) overlapTime.toDouble() / (overlapCount * 5) else 0.0
        val postureScore = if (postureOutCount > 0) postureOutTime.toDouble() / (postureOutCount * 5) else 0.0
        val outOfRangeScore = if (outOfRangeCount > 0) outOfRangeTotalTime.toDouble() / (outOfRangeCount * 5) else 0.0

        val totalScore = 100.0 - ((eyeScore + moveScore - overlapScore + postureScore + outOfRangeScore) / 4.0)
        return totalScore.coerceIn(0.0, 100.0)
    }

    private fun FinalScoreByCountRate(): Double {
        val eyeScore = if (eyeDrowsyTime > 0) (eyeDrowsyCount * 10.0) / eyeDrowsyTime/30 else 0.0
        val moveScore = if (noMoveTime > 0) (noMoveCount * 60.0) / noMoveTime/180 else 0.0
        val overlapScore = if (overlapTime > 0) (overlapCount * 10.0) / overlapTime/30 else 0.0
        val postureScore = if (postureOutTime > 0) (postureOutCount * 10.0) / postureOutTime/30 else 0.0
        val outOfRangeScore = if (outOfRangeTotalTime > 0) (outOfRangeCount * 10.0) / outOfRangeTotalTime/30 else 0.0

        val totalScore = 100.0 - (eyeDrowsyCount + noMoveCount - overlapCount + postureOutCount + outOfRangeCount)
        return totalScore.coerceIn(0.0, 100.0)
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

    private fun getScaledBoxHeight(
        rawHeight: Float,
        imageProxy: ImageProxy,
        previewView: PreviewView
    ): Double {
        val rotation = imageProxy.imageInfo.rotationDegrees
        val isRotated = rotation == 90 || rotation == 270
        val imageWidth = if (isRotated) imageProxy.height else imageProxy.width
        val imageHeight = if (isRotated) imageProxy.width else imageProxy.height
        val viewWidth = previewView.width.toFloat()
        val viewHeight = previewView.height.toFloat()
        val scale = minOf(viewWidth / imageWidth, viewHeight / imageHeight)
        return (rawHeight * scale).toDouble()
    }
}
