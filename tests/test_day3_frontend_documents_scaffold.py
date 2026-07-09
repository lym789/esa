import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class Day3FrontendDocumentsScaffoldTest(unittest.TestCase):
    def test_document_frontend_files_exist(self):
        expected_files = [
            "frontend/lib/documents.ts",
            "frontend/app/admin/documents/page.tsx",
        ]

        missing = [path for path in expected_files if not (ROOT / path).is_file()]

        self.assertEqual(missing, [])

    def test_document_client_calls_backend_endpoints(self):
        documents_ts = read_text("frontend/lib/documents.ts")

        self.assertIn("/api/documents", documents_ts)
        self.assertIn("/api/documents/upload", documents_ts)
        self.assertIn("uploadDocument", documents_ts)
        self.assertIn("listDocuments", documents_ts)
        self.assertIn("deleteDocument", documents_ts)
        self.assertIn("reindexDocument", documents_ts)
        self.assertIn("Authorization", documents_ts)

    def test_documents_page_requires_session_and_supports_upload(self):
        page_tsx = read_text("frontend/app/admin/documents/page.tsx")

        self.assertIn("getStoredSession", page_tsx)
        self.assertIn("router.replace(\"/login\")", page_tsx)
        self.assertIn("uploadDocument", page_tsx)
        self.assertIn("listDocuments", page_tsx)
        self.assertIn("currentUser.role === \"admin\"", page_tsx)

    def test_dashboard_document_card_links_to_documents_page(self):
        dashboard_data = read_text("frontend/lib/dashboard-data.ts")
        dashboard_tsx = read_text("frontend/components/Dashboard.tsx")

        self.assertIn("/admin/documents", dashboard_data)
        self.assertIn("router.push(item.href)", dashboard_tsx)


if __name__ == "__main__":
    unittest.main()
