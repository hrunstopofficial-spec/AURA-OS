import os
import sys
import unittest

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.registry import registry
from tools import system_tools
from storage.memory.system_metrics import metrics_store
from agents.analysis_engine import analysis_engine


class TestPhase1Vitals(unittest.TestCase):

    def test_01_tool_registry(self):
        """Verify tools are properly registered and generate LLM schemas."""
        registered_tools = [t.name for t in registry.list_tools()]
        expected = [
            "get_cpu_usage", "get_memory_usage", "get_disk_usage",
            "get_battery_status", "get_top_processes", "get_network_ping", "get_system_vitals"
        ]
        for name in expected:
            self.assertIn(name, registered_tools, f"Missing tool: {name}")

        schemas = registry.get_schemas(category="server")
        self.assertGreaterEqual(len(schemas), 6)
        first_schema = schemas[0]
        self.assertEqual(first_schema["type"], "function")
        self.assertIn("name", first_schema["function"])
        self.assertIn("parameters", first_schema["function"])
        print("✅ Test 01: Tool Registry & LLM Schemas Validated.")

    def test_02_live_vitals_execution(self):
        """Test live execution of get_system_vitals tool via registry."""
        res = registry.execute_tool("get_system_vitals")
        self.assertTrue(res["success"], f"Tool execution failed: {res.get('error')}")
        vitals = res["result"]

        self.assertIn("cpu", vitals)
        self.assertIn("memory", vitals)
        self.assertIn("disk", vitals)
        self.assertIn("battery", vitals)
        self.assertIn("network", vitals)
        self.assertIn("top_processes", vitals)

        print(f"✅ Test 02: Live Execution Succeeded in {res['execution_ms']} ms.")
        print(f"   CPU: {vitals['cpu']['cpu_percent']}% | RAM: {vitals['memory']['percent']}% | Battery: {vitals['battery']['battery_percent']}%")

    def test_03_sqlite_timeseries_logging(self):
        """Test recording snapshot into SQLite and querying historical average."""
        vitals_res = registry.execute_tool("get_system_vitals")
        self.assertTrue(vitals_res["success"])
        vitals = vitals_res["result"]

        # Insert snapshot
        row_id = metrics_store.record_snapshot(vitals)
        self.assertGreater(row_id, 0)

        # Retrieve recent
        recent = metrics_store.get_recent_history(limit=5)
        self.assertGreaterEqual(len(recent), 1)

        # Compute delta
        delta = metrics_store.compute_telemetry_delta(vitals, hours=24.0)
        self.assertIn("has_history", delta)
        print(f"✅ Test 03: SQLite Snapshot #{row_id} Logged. Historical samples: {delta.get('sample_count')}")

    def test_04_system_diagnosis_engine(self):
        """Test AI analysis and health score generation."""
        vitals = registry.execute_tool("get_system_vitals")["result"]
        delta = metrics_store.compute_telemetry_delta(vitals, hours=24.0)

        diagnosis = analysis_engine.analyze(vitals, delta)
        self.assertIn("health_score", diagnosis)
        self.assertGreaterEqual(diagnosis["health_score"], 0)
        self.assertLessEqual(diagnosis["health_score"], 100)
        self.assertTrue(len(diagnosis["recommendations"]) > 0)
        self.assertIn("tanglish_summary", diagnosis)

        print(f"✅ Test 04: Health Diagnosis Complete -> Score: {diagnosis['health_score']}/100")
        print("\n--- LIVE SYSTEM DIAGNOSIS REPORT ---")
        print(diagnosis["tanglish_summary"])
        print("\nRecommendations:")
        for r in diagnosis["recommendations"]:
            print(f"  • {r}")
        print("------------------------------------\n")


if __name__ == "__main__":
    unittest.main()
