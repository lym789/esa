import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class Day12FrontendApprovalsScaffoldTest(unittest.TestCase):
    def test_approval_frontend_files_exist(self):
        expected_files = [
            "frontend/lib/approvals.ts",
            "frontend/app/approvals/page.tsx",
        ]

        missing = [path for path in expected_files if not (ROOT / path).is_file()]

        self.assertEqual(missing, [])

    def test_approval_client_calls_backend_endpoints(self):
        approvals_ts = read_text("frontend/lib/approvals.ts")

        self.assertIn("/api/approvals", approvals_ts)
        self.assertIn("/approve", approvals_ts)
        self.assertIn("/reject", approvals_ts)
        self.assertIn("listApprovals", approvals_ts)
        self.assertIn("approveApproval", approvals_ts)
        self.assertIn("rejectApproval", approvals_ts)
        self.assertIn("decision_comment", approvals_ts)
        self.assertIn("Authorization", approvals_ts)

    def test_approvals_page_requires_session_and_supports_decisions(self):
        page_tsx = read_text("frontend/app/approvals/page.tsx")

        self.assertIn("getStoredSession", page_tsx)
        self.assertIn("router.replace(\"/login\")", page_tsx)
        self.assertIn("listApprovals", page_tsx)
        self.assertIn("approveApproval", page_tsx)
        self.assertIn("rejectApproval", page_tsx)
        self.assertIn("pending", page_tsx)
        self.assertIn("审批意见", page_tsx)

    def test_dashboard_approval_card_links_to_approvals_page(self):
        dashboard_data = read_text("frontend/lib/dashboard-data.ts")

        self.assertIn("/approvals", dashboard_data)

    def test_approvals_page_has_scrollable_layout(self):
        css = read_text("frontend/app/globals.css")

        self.assertIn(".approvals-page", css)
        self.assertIn("height: 100vh", css)
        self.assertIn(".approvals-list-items", css)
        self.assertIn("overflow-y: auto", css)
        self.assertIn(".approval-tool-args", css)


if __name__ == "__main__":
    unittest.main()
