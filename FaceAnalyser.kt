package com.ondy.studybuddy.managers

import android.annotation.SuppressLint
import android.graphics.PointF
import android.util.Log
import android.widget.TextView
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.view.PreviewView
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.face.*
import kotlin.math.hypot
import kotlin.math.sqrt

class FaceAnalyzer(
    private val statusView: TextView,
    private val overlayView: FaceOverlay,
    private val previewView: PreviewView
) : ImageAnalysis.Analyzer {

    private val offsetX = -1f
    private val offsetY = +10f

    fun translateToViewCoordinates(
        point: PointF,
        imageProxy: ImageProxy,
        previewView: PreviewView,
        isFrontCamera: Boolean,
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

    private val detector: FaceDetector by lazy {
        val options = FaceDetectorOptions.Builder()
            .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_FAST)
            .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_ALL)
            .setContourMode(FaceDetectorOptions.CONTOUR_MODE_ALL)
            .build()
        FaceDetection.getClient(options)
    }

    @SuppressLint("UnsafeOptInUsageError")
    override fun analyze(imageProxy: ImageProxy) {
        val mediaImage = imageProxy.image ?: run {
            imageProxy.close()
            return
        }
        val inputImage = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)

        detector.process(inputImage)
            .addOnSuccessListener { faces ->
                if (faces.isNotEmpty()) {
                    val face = faces[0]
                    val isFrontCamera = true

                    val contourTypes = listOf(
                        FaceContour.LEFT_EYE, FaceContour.RIGHT_EYE,
                        FaceContour.LEFT_EYEBROW_TOP, FaceContour.LEFT_EYEBROW_BOTTOM,
                        FaceContour.RIGHT_EYEBROW_TOP, FaceContour.RIGHT_EYEBROW_BOTTOM,
                        FaceContour.NOSE_BRIDGE, FaceContour.NOSE_BOTTOM,
                        FaceContour.UPPER_LIP_TOP, FaceContour.UPPER_LIP_BOTTOM,
                        FaceContour.LOWER_LIP_TOP, FaceContour.LOWER_LIP_BOTTOM
                    )

                    val allContourPoints = mutableListOf<PointF>()
                    for (type in contourTypes) {
                        val points = face.getContour(type)?.points ?: emptyList()
                        allContourPoints.addAll(points)
                    }

                    val transformedPoints = allContourPoints.map {
                        translateToViewCoordinates(
                            point = it,
                            imageProxy = imageProxy,
                            previewView = previewView,
                            isFrontCamera = isFrontCamera,
                            offsetX = offsetX,
                            offsetY = offsetY
                        )
                    }

                    overlayView.post {
                        overlayView.setAllPoints(transformedPoints)
                    }

                    val center = overlayView.getGuideCenter()
                    val radius = overlayView.getGuideRadius()
                    val isOutside = transformedPoints.any {
                        val dx = it.x - center.x
                        val dy = it.y - center.y
                        sqrt(dx * dx + dy * dy) > radius
                    }

                    val faceBoxHeight = face.boundingBox.height().toDouble()
                    val mouthThreshold = 0.70
                    val minFaceBoxHeight = 170.0

                    if (
                        faceBoxHeight == 0.0 ||
                        faceBoxHeight < minFaceBoxHeight ||
                        isOutside
                    ) {
                        statusView.post { statusView.text = "범위 밖" }
                        imageProxy.close()
                        return@addOnSuccessListener
                    }

                    val leftEye = face.getContour(FaceContour.LEFT_EYE)?.points
                    val rightEye = face.getContour(FaceContour.RIGHT_EYE)?.points
                    val leftEAR = computeEAR(leftEye)
                    val rightEAR = computeEAR(rightEye)
                    val avgEAR = (leftEAR + rightEAR) / 2.0

                    // [수정] 화면 내 얼굴 비율 기반 EAR 기준 보정
                    val viewHeight = previewView.height.toDouble()
                    val faceRatio = faceBoxHeight / viewHeight
                    val baseThreshold = 0.18
                    val scaleFactor = 0.2
                    val earThreshold = baseThreshold - (faceRatio * scaleFactor)

                    val isClosed = avgEAR < earThreshold // [수정 적용 완료]

                    val upperLip = face.getContour(FaceContour.UPPER_LIP_TOP)?.points
                    val lowerLip = face.getContour(FaceContour.LOWER_LIP_BOTTOM)?.points
                    val mouthOpenRatio = computeMouthOpenRatio(upperLip, lowerLip)

                    val isYawning = (!isClosed && mouthOpenRatio > mouthThreshold)

                    statusView.post {
                        statusView.text = when {
                            isYawning -> "하품\n(avgEAR: %.4f)".format(avgEAR)
                            isClosed -> "눈 감김\n(avgEAR: %.4f)".format(avgEAR)
                            else -> "눈 뜸\n(avgEAR: %.4f)".format(avgEAR)
                        }
                    }

                    Log.d("FaceAnalyzer", "avgEAR=$avgEAR, mouthOpenRatio=$mouthOpenRatio, faceRatio=$faceRatio, earThreshold=$earThreshold") // [로그 추가]
                } else {
                    statusView.post { statusView.text = "범위 밖" }
                }
            }
            .addOnFailureListener {
                Log.e("FaceAnalyzer", "감지 실패: ${it.message}")
            }
            .addOnCompleteListener {
                imageProxy.close()
            }
    }

    private fun computeEAR(points: List<PointF>?): Double {
        if (points == null || points.size < 16) return 1.0

        val verticalPairs = listOf(
            1 to 15,
            2 to 14,
            3 to 13,
            4 to 12,
            5 to 11,
            6 to 10,
            7 to 9
        )

        val verticalDistances = verticalPairs.map { (top, bottom) ->
            distance(points[top], points[bottom])
        }

        val verticalAvg = verticalDistances.average()
        val horizontal = distance(points[0], points[8])

        return if (horizontal != 0f) (verticalAvg / horizontal).toDouble() else 1.0
    }

    private fun computeMouthOpenRatio(topLip: List<PointF>?, bottomLip: List<PointF>?): Double {
        if (topLip.isNullOrEmpty() || bottomLip.isNullOrEmpty()) return 0.0

        val top = topLip.getOrNull(topLip.size / 2) ?: return 0.0
        val bottom = bottomLip.getOrNull(bottomLip.size / 2) ?: return 0.0
        val left = topLip.getOrNull(0) ?: return 0.0
        val right = topLip.getOrNull(topLip.size - 1) ?: return 0.0

        val vertical = distance(top, bottom)
        val horizontal = distance(left, right)

        return if (horizontal != 0f) (vertical / horizontal).toDouble() else 0.0
    }

    private fun distance(p1: PointF, p2: PointF): Float {
        return hypot(p1.x - p2.x, p1.y - p2.y)
    }

}
