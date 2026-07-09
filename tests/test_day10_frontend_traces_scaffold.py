import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class Day10FrontendTracesScaffoldTest(unittest.TestCase):
    def test_trace_frontend_files_exist(self):
        expected_files = [
            "frontend/lib/traces.ts",
            "frontend/app/admin/traces/page.tsx",
        ]

        missing = [path for path in expected_files if not (ROOT / path).is_file()]

        self.assertEqual(missing, [])

    def test_trace_client_calls_backend_endpoints(self):
        traces_ts = read_text("frontend/lib/traces.ts")

        self.assertIn("/api/traces", traces_ts)
        self.assertIn("listTraces", traces_ts)
        self.assertIn("getTrace", traces_ts)
        self.assertIn("Authorization", traces_ts)
        self.assertIn("TraceRecord", traces_ts)

    def test_traces_page_requires_admin_session_and_renders_trace_fields(self):
        page_tsx = read_text("frontend/app/admin/traces/page.tsx")

        self.assertIn("getStoredSession", page_tsx)
        self.assertIn("router.replace(\"/login\")", page_tsx)
        self.assertIn("currentUser.role === \"admin\"", page_tsx)
        self.assertIn("listTraces", page_tsx)
        self.assertIn("approval_status", page_tsx)
        self.assertIn("tool_name", page_tsx)
        self.assertIn("final_result", page_tsx)

    def test_dashboard_trace_card_links_to_traces_page(self):
        dashboard_data = read_text("frontend/lib/dashboard-data.ts")

        self.assertIn("/admin/traces", dashboard_data)


if __name__ == "__main__":
    unittest.main()
