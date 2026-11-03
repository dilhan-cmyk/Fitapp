package com.dilhan.fuel

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.util.Base64
import com.getcapacitor.JSArray
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.Text
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions

/**
 * On-device text recognition for nutrition labels (ML Kit, bundled model, no network).
 * JS: Capacitor.Plugins.LabelOcr.recognize({base64}) -> {lines:[{t,l,tp,r,b,el:[{t,l,r}]}], rotation}
 * Tries the photo at 4 rotations and keeps the one that reads most nutrition words.
 */
@CapacitorPlugin(name = "LabelOcr")
class LabelOcrPlugin : Plugin() {

    private val keys = listOf(
        "energy", "calories", "protein", "fat", "carbohydrate", "sugars", "sodium",
        "fibre", "fiber", "serving", "per 100", "saturated", "nutrition"
    )

    private fun score(t: Text): Int {
        val low = t.text.lowercase()
        var s = 0
        for (k in keys) if (low.contains(k)) s += 3
        s += Regex("\\d").findAll(low).count().coerceAtMost(40) / 8
        return s
    }

    private fun rotate(b: Bitmap, deg: Int): Bitmap {
        if (deg == 0) return b
        val m = Matrix()
        m.postRotate(deg.toFloat())
        return Bitmap.createBitmap(b, 0, 0, b.width, b.height, m, true)
    }

    @PluginMethod
    fun recognize(call: PluginCall) {
        val b64 = call.getString("base64")
        if (b64.isNullOrEmpty()) {
            call.reject("No image")
            return
        }
        Thread {
            try {
                val bytes = Base64.decode(b64, Base64.DEFAULT)
                val bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                    ?: throw Exception("Could not open the image")
                val rec = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
                var best: Text? = null
                var bestScore = -1
                var bestRot = 0
                for (deg in intArrayOf(0, 90, 270, 180)) {
                    val rb = rotate(bmp, deg)
                    val t = Tasks.await(rec.process(InputImage.fromBitmap(rb, 0)))
                    val sc = score(t)
                    if (sc > bestScore) {
                        best = t; bestScore = sc; bestRot = deg
                    }
                    // A clearly good reading at the first orientation tried is enough.
                    if (deg == 0 && sc >= 24) break
                }
                rec.close()
                val arr = JSArray()
                best?.textBlocks?.forEach { blk ->
                    blk.lines.forEach { ln ->
                        val bb = ln.boundingBox ?: return@forEach
                        val o = JSObject()
                        o.put("t", ln.text)
                        o.put("l", bb.left); o.put("tp", bb.top)
                        o.put("r", bb.right); o.put("b", bb.bottom)
                        val els = JSArray()
                        ln.elements.forEach { el ->
                            val eb = el.boundingBox ?: return@forEach
                            val e = JSObject()
                            e.put("t", el.text); e.put("l", eb.left); e.put("r", eb.right)
                            els.put(e)
                        }
                        o.put("el", els)
                        arr.put(o)
                    }
                }
                val res = JSObject()
                res.put("lines", arr)
                res.put("rotation", bestRot)
                call.resolve(res)
            } catch (e: Exception) {
                call.reject(e.message ?: "recognition failed")
            }
        }.start()
    }
}
