package com.dilhan.fuel

import androidx.activity.result.ActivityResult
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.request.AggregateGroupByPeriodRequest
import androidx.health.connect.client.time.TimeRangeFilter
import com.getcapacitor.JSArray
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.annotation.ActivityCallback
import com.getcapacitor.annotation.CapacitorPlugin
import com.getcapacitor.PluginMethod
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.Period

/**
 * Reads daily step totals from Health Connect.
 * JS: Capacitor.Plugins.HealthSteps.status() / requestPermission() / readDailySteps({days})
 */
@CapacitorPlugin(name = "HealthSteps")
class HealthStepsPlugin : Plugin() {

    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private val perms = setOf(HealthPermission.getReadPermission(StepsRecord::class))

    private fun client(): HealthConnectClient? {
        return if (HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE) {
            HealthConnectClient.getOrCreate(context)
        } else null
    }

    @PluginMethod
    fun status(call: PluginCall) {
        val c = client()
        if (c == null) {
            val o = JSObject()
            o.put("available", false)
            o.put("granted", false)
            call.resolve(o)
            return
        }
        scope.launch {
            try {
                val granted = c.permissionController.getGrantedPermissions()
                val o = JSObject()
                o.put("available", true)
                o.put("granted", granted.containsAll(perms))
                call.resolve(o)
            } catch (e: Exception) {
                call.reject(e.message ?: "status failed")
            }
        }
    }

    @PluginMethod
    fun requestPermission(call: PluginCall) {
        if (client() == null) {
            call.reject("Health Connect unavailable")
            return
        }
        val intent = PermissionController.createRequestPermissionResultContract()
            .createIntent(context, perms)
        startActivityForResult(call, intent, "permissionResult")
    }

    @ActivityCallback
    private fun permissionResult(call: PluginCall?, result: ActivityResult) {
        if (call == null) return
        val c = client()
        if (c == null) {
            call.reject("Health Connect unavailable")
            return
        }
        scope.launch {
            try {
                val granted = c.permissionController.getGrantedPermissions()
                val o = JSObject()
                o.put("granted", granted.containsAll(perms))
                call.resolve(o)
            } catch (e: Exception) {
                call.reject(e.message ?: "permission check failed")
            }
        }
    }

    @PluginMethod
    fun readDailySteps(call: PluginCall) {
        val c = client()
        if (c == null) {
            call.reject("Health Connect unavailable")
            return
        }
        var days = call.getInt("days") ?: 30
        if (days < 1) days = 1
        if (days > 30) days = 30
        scope.launch {
            try {
                val start = LocalDate.now().minusDays((days - 1).toLong()).atStartOfDay()
                val end = LocalDateTime.now()
                val groups = c.aggregateGroupByPeriod(
                    AggregateGroupByPeriodRequest(
                        metrics = setOf(StepsRecord.COUNT_TOTAL),
                        timeRangeFilter = TimeRangeFilter.between(start, end),
                        timeRangeSlicer = Period.ofDays(1)
                    )
                )
                val arr = JSArray()
                for (g in groups) {
                    val steps: Long = g.result[StepsRecord.COUNT_TOTAL] ?: 0L
                    val o = JSObject()
                    o.put("date", g.startTime.toLocalDate().toString())
                    o.put("steps", steps)
                    arr.put(o)
                }
                val out = JSObject()
                out.put("days", arr)
                call.resolve(out)
            } catch (e: Exception) {
                call.reject(e.message ?: "read failed")
            }
        }
    }
}
