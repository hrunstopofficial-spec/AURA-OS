import datetime
from typing import Dict, Any, List


class SystemAnalysisEngine:
    """
    Intelligent Diagnosis Engine for AURA Server Agent.
    Interprets raw telemetry facts + historical deltas to produce:
    1. Overall Health Score (0 - 100)
    2. Trend & Comparative Evaluation ('System-la enna better-aa irukku?')
    3. Actionable Senior Engineering Recommendations in Tanglish.
    """

    def analyze(self, vitals: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
        cpu_info = vitals.get("cpu", {})
        mem_info = vitals.get("memory", {})
        disk_info = vitals.get("disk", {})
        battery_info = vitals.get("battery", {})
        top_procs = vitals.get("top_processes", [])

        cpu_pct = cpu_info.get("cpu_percent", 0.0)
        mem_pct = mem_info.get("percent", 0.0)
        disk_pct = disk_info.get("percent", 0.0)
        avail_ram_gb = round(mem_info.get("available_mb", 0.0) / 1024, 1)

        # ── 1. HEALTH SCORE CALCULATION (0 - 100) ─────────────────────────
        score = 100

        # CPU Deductions
        if cpu_pct > 85:
            score -= 30
        elif cpu_pct > 65:
            score -= 15
        elif cpu_pct > 50:
            score -= 5

        # RAM Deductions
        if mem_pct > 90:
            score -= 35
        elif mem_pct > 80:
            score -= 20
        elif mem_pct > 65:
            score -= 10

        # Disk Deductions
        if disk_pct > 92:
            score -= 20
        elif disk_pct > 85:
            score -= 10

        # Battery Deductions
        bat_pct = battery_info.get("battery_percent", 100.0)
        is_charging = battery_info.get("is_charging", True)
        if not is_charging and bat_pct < 20:
            score -= 15

        health_score = max(10, min(100, score))

        if health_score >= 85:
            status = "EXCELLENT 🔥"
        elif health_score >= 70:
            status = "HEALTHY & STABLE ✅"
        elif health_score >= 50:
            status = "MODERATE PRESSURE ⚠️"
        else:
            status = "CRITICAL RESOURCE BOTTLENECK 🚨"

        # ── 2. RECOMMENDATIONS & ACTION ITEMS ─────────────────────────────
        recommendations: List[str] = []

        if mem_pct > 75 and top_procs:
            top_ram_hog = top_procs[0]
            recommendations.append(
                f"RAM usage {mem_pct}% irukku. Top consumer: '{top_ram_hog['name']}' ({top_ram_hog['memory_mb']} MB)."
            )

        if not is_charging and bat_pct < 30:
            recommendations.append(
                f"Battery {bat_pct}% dhaan irukku & discharging-la irukku. Connect charger for peak CPU performance."
            )

        if disk_pct > 80:
            recommendations.append(
                f"C: Drive storage {disk_pct}% filled ({disk_info.get('free_gb')} GB free). Consider clearing temp caches."
            )

        if not recommendations:
            recommendations.append("All primary resources operating within optimal green thresholds.")

        # ── 3. COMPARATIVE DIAGNOSIS (TANGLISH) ───────────────────────────
        lines = []
        lines.append(f"Mapla, system overall health score **{health_score}/100** ({status})!")

        if delta.get("has_history"):
            trend = delta.get("trend")
            cpu_d = delta.get("cpu_delta", 0.0)
            mem_d = delta.get("memory_delta", 0.0)

            if trend == "BETTER / COOLER":
                lines.append(
                    f"🔥 **Improvement Alert**: Past history-oda compare pannumbodhu CPU {abs(cpu_d)}% cooler-aa irukku, RAM {abs(mem_d)}% free aagirukku!"
                )
            elif trend == "UNDER PRESSURE":
                lines.append(
                    f"⚠️ **Pressure Warning**: Average-a vida CPU +{cpu_d}% and RAM +{mem_d}% athigama irukku."
                )
            else:
                lines.append(
                    f"📊 Historical baseline-oda compare pannumbodhu system **very stable-aa** irukku (CPU delta: {cpu_d}%, RAM delta: {mem_d}%)."
                )
        else:
            lines.append("📌 First baseline telemetry snapshot successfully recorded.")

        lines.append(f"- **CPU**: {cpu_pct}% ({cpu_info.get('cores_logical')} logical cores)")
        lines.append(f"- **RAM**: {mem_pct}% used ({avail_ram_gb} GB available)")
        lines.append(f"- **Disk**: {disk_pct}% used ({disk_info.get('free_gb')} GB free)")
        if battery_info.get("has_battery"):
            lines.append(f"- **Power**: {bat_pct}% ({battery_info.get('status')})")

        diagnosis_summary = "\n".join(lines)

        return {
            "health_score": health_score,
            "status": status,
            "recommendations": recommendations,
            "tanglish_summary": diagnosis_summary,
            "telemetry_snapshot": vitals,
            "historical_delta": delta
        }


# Global singleton
analysis_engine = SystemAnalysisEngine()
