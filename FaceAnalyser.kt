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

    private val earBuffer = mutableListOf<Double>()
    private var lastEarDisplayTime = System.currentTimeMillis()

    private val bboxWindow = mutableListOf<Double>()
    private val bboxWindowSize = 5

    private var outOfRangeDurationSec = 0
    private var lastOutOfRangeStart = 0L

    private var yawnCount = 0
    private var closedDurationSec = 0
    private var closedCount = 0
    private var lastClosedTime = 0L

    private var lastState: String = ""

    private fun getSmoothedBoundingBoxHeight(newHeight: Double): Double {
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
        val scaleX = viewWidth / imageWidth
        val scaleY = viewHeight / imageHeight
        val scale = minOf(scaleX, scaleY)
        val dx = (viewWidth - imageWidth * scale) / 2f
        val dy = (viewHeight - imageHeight * scale) / 2f
        val mappedX = point.x * scale + dx + offsetX
        val mappedY = point.y * scale + dy + offsetY
        return PointF(mappedX, mappedY)
    }

    private val detector: FaceMeshDetector by lazy {
        val options = FaceMeshDetectorOptions.Builder()
            .setUseCase(FaceMeshDetectorOptions.FACE_MESH)
            .build()
        FaceMeshDetection.getClient(options)
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
                    if (lastState != "범위 밖") {
                        lastOutOfRangeStart = now
                        lastState = "범위 밖"
                    }

                    val duration = ((now - lastOutOfRangeStart) / 1000).toInt()
                    statusView.post {
                        statusView.text = "범위 밖 (감지 실패)\n경과: ${duration}초"
                    }
                    return@addOnSuccessListener
                }

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

                val leftEyePoints = getMeshPoints(mesh, listOf(33, 160, 158, 133, 153, 144))
                val rightEyePoints = getMeshPoints(mesh, listOf(362, 385, 387, 263, 373, 380))
                val leftEAR = computeEAR(leftEyePoints)
                val rightEAR = computeEAR(rightEyePoints)
                val ear = (leftEAR + rightEAR) / 2.0
                earBuffer.add(ear)

                val upperLip = getMeshPoints(mesh, listOf(13, 14, 15))
                val lowerLip = getMeshPoints(mesh, listOf(17, 18, 87))
                val mouthOpenRatio = computeMouthOpenRatio(upperLip, lowerLip)

                val isClosed = ear < 0.1
                val isYawning = !isClosed && mouthOpenRatio > 0.9

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

                statusView.post {
                    statusView.text = "$status | EAR: %.3f\n$closedCount, ${closedDurationSec}s \n${outOfRangeDurationSec}s".format(ear)
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

    private fun getMeshPoints(mesh: FaceMesh, indexes: List<Int>): List<PointF> {
        return indexes.mapNotNull { idx ->
            val point = mesh.allPoints.getOrNull(idx)
            val pos = point?.position
            if (pos != null) PointF(pos.x, pos.y) else null
        }
    }

    private fun computeEAR(points: List<PointF>): Double {
        if (points.size < 6) return 1.0
        val vertical1 = distance(points[1], points[5])
        val vertical2 = distance(points[2], points[4])
        val verticalAvg = (vertical1 + vertical2) / 2
        val horizontal = distance(points[0], points[3])
        return if (horizontal != 0f) (verticalAvg / horizontal).toDouble() else 1.0
    }

    private fun computeMouthOpenRatio(top: List<PointF>, bottom: List<PointF>): Double {
        if (top.isEmpty() || bottom.isEmpty()) return 0.0
        val topMid = top[top.size / 2]
        val bottomMid = bottom[bottom.size / 2]
        val left = top.first()
        val right = top.last()
        val vertical = distance(topMid, bottomMid)
        val horizontal = distance(left, right)
        return if (horizontal != 0f) (vertical / horizontal).toDouble() else 0.0
    }

    private fun distance(p1: PointF, p2: PointF): Float {
        return hypot(p1.x - p2.x, p1.y - p2.y)
    }
}
