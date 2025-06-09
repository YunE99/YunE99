package com.ondy.studybuddy.managers

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.PointF
import android.util.AttributeSet
import android.view.View

class FaceOverlay @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : View(context, attrs) {

    private val FacePoints = mutableListOf<PointF>()
    private var guideCircleCenter: PointF? = null
    private var guideCircleRadius: Float = 0f

    private val paint = Paint().apply {
        color = Color.RED
        style = Paint.Style.FILL
        strokeWidth = 8f
        isAntiAlias = true
    }

    // 손목 위치 및 정확도 관련 변수 추가
    private var leftWristPoint: PointF? = null
    private var rightWristPoint: PointF? = null
    private var leftWristConfidence: Float = 0f
    private var rightWristConfidence: Float = 0f

    //뷰 크기 변경 시 중앙에 기본 원 설정
    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        if (guideCircleCenter == null || guideCircleRadius == 0f) {
            val centerX = w / 2f
            val centerY = h / 2f
            guideCircleCenter = PointF(centerX, centerY)
            guideCircleRadius = (w.coerceAtMost(h) / 2f) - 10f //  양쪽 여백 10f
        }
    }

    // 외부에서 포인트 설정
    fun setAllPoints(points: List<PointF>) {
        FacePoints.clear()
        FacePoints.addAll(points)
        invalidate()
    }

    fun setGuideCircle(center: PointF, radius: Float) {
        guideCircleCenter = center
        guideCircleRadius = radius
        invalidate()
    }

    // 손목 좌표 및 정확도 설정 함수 추가
    fun setWristPoints(left: PointF?, right: PointF?, leftConf: Float, rightConf: Float) {
        leftWristPoint = left
        rightWristPoint = right
        leftWristConfidence = leftConf
        rightWristConfidence = rightConf
        invalidate()
    }

//    override fun onDraw(canvas: Canvas) {
//        canvas.save()
//
//        //  좌우 반전 적용 (전면 카메라용 미러링)
//        canvas.scale(-1f, 1f, width / 2f, height / 2f)
//
//        //  얼굴 포인트 그리기
//        val offsetX = +20f  // 왼쪽으로 20픽셀 이동
//        val offsetY = 15f   // 아래로 30픽셀 이동
//
//        for (point in FacePoints) {
//            canvas.drawCircle(point.x + offsetX, point.y + offsetY, 1f, paint)
//        }
//
//        //  안내 원 그리기
//        guideCircleCenter?.let { center ->
//            val guidePaint = Paint().apply {
//                color = android.graphics.Color.RED
//                style = Paint.Style.STROKE
//                strokeWidth = 1f
//                isAntiAlias = true
//            }
//            canvas.drawCircle(center.x, center.y, guideCircleRadius, guidePaint)
//        }
//
//        canvas.restore() //  반전 되돌리기
//    }

//    // 손목 오버레이 별도 onDraw 정의 (얼굴 오버레이 주석 그대로 유지)
//    override fun onDraw(canvas: Canvas) {
//        canvas.save()
//        canvas.scale(-1f, 1f, width / 2f, height / 2f)
//
//        val wristPaint = Paint().apply {
//            color = Color.BLUE
//            style = Paint.Style.FILL
//            isAntiAlias = true
//        }
//
//        val textPaint = Paint().apply {
//            color = Color.YELLOW
//            textSize = 24f
//            isAntiAlias = true
//        }
//
//        leftWristPoint?.let {
//            canvas.drawCircle(it.x, it.y, 10f, wristPaint)
//            canvas.drawText("LW: %.2f".format(leftWristConfidence), it.x + 12f, it.y, textPaint)
//        }
//        rightWristPoint?.let {
//            canvas.drawCircle(it.x, it.y, 10f, wristPaint)
//            canvas.drawText("RW: %.2f".format(rightWristConfidence), it.x + 12f, it.y, textPaint)
//        }
//
//        canvas.restore()
//    }

    fun getGuideCenter(): PointF {
        return guideCircleCenter ?: PointF(0f, 0f)
    }

    fun getGuideRadius(): Float {
        return guideCircleRadius
    }
}