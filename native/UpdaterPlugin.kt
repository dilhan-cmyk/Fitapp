package com.dilhan.fuel

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * Checks the private GitHub repo for a newer release and installs it.
 * JS: Capacitor.Plugins.Updater.info() / check({token}) / install({token, assetId})
 * The access token is passed in from the app each time; it is never stored in the APK.
 */
@CapacitorPlugin(name = "Updater")
class UpdaterPlugin : Plugin() {

    private val repo = "dilhan-cmyk/Fitapp"

    @Suppress("DEPRECATION")
    private fun versionCode(): Long {
        val pi = context.packageManager.getPackageInfo(context.packageName, 0)
        return if (Build.VERSION.SDK_INT >= 28) pi.longVersionCode else pi.versionCode.toLong()
    }

    private fun canInstall(): Boolean = context.packageManager.canRequestPackageInstalls()

    private fun open(url: String, token: String, accept: String): HttpURLConnection {
        val c = URL(url).openConnection() as HttpURLConnection
        c.instanceFollowRedirects = false
        c.connectTimeout = 15000
        c.readTimeout = 30000
        c.setRequestProperty("Accept", accept)
        c.setRequestProperty("User-Agent", "Fuel-App")
        c.setRequestProperty("X-GitHub-Api-Version", "2022-11-28")
        if (token.isNotEmpty()) c.setRequestProperty("Authorization", "Bearer $token")
        return c
    }

    /** Follows redirects by hand so the token is only ever sent to api.github.com. */
    private fun openFollowing(url0: String, token: String, accept: String): HttpURLConnection {
        var url = url0
        var tok = token
        for (hop in 0..6) {
            val c = open(url, tok, accept)
            val code = c.responseCode
            if (code in 301..308) {
                val loc = c.getHeaderField("Location") ?: throw Exception("Bad redirect from GitHub")
                c.disconnect()
                url = loc
                tok = ""
                continue
            }
            if (code != 200) {
                val hint = if (code == 401 || code == 403 || code == 404) " (check the access token)" else ""
                throw Exception("GitHub said HTTP $code$hint")
            }
            return c
        }
        throw Exception("Too many redirects")
    }

    @PluginMethod
    fun info(call: PluginCall) {
        try {
            val pi = context.packageManager.getPackageInfo(context.packageName, 0)
            val o = JSObject()
            o.put("versionName", pi.versionName ?: "")
            o.put("versionCode", versionCode())
            o.put("canInstall", canInstall())
            call.resolve(o)
        } catch (e: Exception) {
            call.reject(e.message ?: "info failed")
        }
    }

    @PluginMethod
    fun check(call: PluginCall) {
        val token = call.getString("token") ?: ""
        Thread {
            try {
                val c = openFollowing("https://api.github.com/repos/$repo/releases/latest", token, "application/vnd.github+json")
                val body = c.inputStream.bufferedReader().use { it.readText() }
                val j = JSONObject(body)
                var assetId = 0L
                var size = 0L
                val assets = j.optJSONArray("assets")
                if (assets != null) {
                    for (i in 0 until assets.length()) {
                        val a = assets.getJSONObject(i)
                        if (a.optString("name") == "Fuel.apk") {
                            assetId = a.getLong("id")
                            size = a.optLong("size")
                        }
                    }
                }
                val o = JSObject()
                o.put("tag", j.optString("tag_name"))
                o.put("name", j.optString("name"))
                o.put("notes", j.optString("body"))
                o.put("assetId", assetId)
                o.put("size", size)
                call.resolve(o)
            } catch (e: Exception) {
                call.reject(e.message ?: "check failed")
            }
        }.start()
    }

    @PluginMethod
    fun install(call: PluginCall) {
        val token = call.getString("token") ?: ""
        val assetId = call.getString("assetId") ?: ""
        if (assetId.isEmpty()) {
            call.reject("No download found on the latest release")
            return
        }
        if (!canInstall()) {
            // Android asks for "Install unknown apps" once per app; send the user to that switch.
            val i = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + context.packageName))
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(i)
            val o = JSObject()
            o.put("needsPermission", true)
            call.resolve(o)
            return
        }
        Thread {
            try {
                val dir = File(context.cacheDir, "update")
                dir.mkdirs()
                val out = File(dir, "Fuel.apk")
                if (out.exists()) out.delete()

                val conn = openFollowing(
                    "https://api.github.com/repos/$repo/releases/assets/$assetId",
                    token, "application/octet-stream"
                )
                val total = conn.contentLengthLong
                conn.inputStream.use { input ->
                    out.outputStream().use { os ->
                        val buf = ByteArray(65536)
                        var read = 0
                        var done = 0L
                        var last = -1
                        while (input.read(buf).also { read = it } >= 0) {
                            os.write(buf, 0, read)
                            done += read
                            if (total > 0) {
                                val pct = (done * 100 / total).toInt()
                                if (pct != last) {
                                    last = pct
                                    val p = JSObject()
                                    p.put("pct", pct)
                                    notifyListeners("progress", p)
                                }
                            }
                        }
                    }
                }

                val uri = FileProvider.getUriForFile(context, context.packageName + ".updates", out)
                val intent = Intent(Intent.ACTION_VIEW)
                intent.setDataAndType(uri, "application/vnd.android.package-archive")
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.runOnUiThread { context.startActivity(intent) }

                val o = JSObject()
                o.put("started", true)
                call.resolve(o)
            } catch (e: Exception) {
                call.reject(e.message ?: "download failed")
            }
        }.start()
    }
}

/** Dedicated provider so the installer can read the downloaded APK from the cache folder. */
class UpdateFileProvider : FileProvider()
