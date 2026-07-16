import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class Day2FrontendAuthScaffoldTest(unittest.TestCase):
    def test_frontend_auth_files_exist(self):
        expected_files = [
            "frontend/app/login/page.tsx",
            "frontend/lib/auth.ts",
            "frontend/lib/session.ts",
        ]

        missing = [path for path in expected_files if not (ROOT / path).is_file()]

        self.assertEqual(missing, [])

    def test_auth_client_calls_login_and_me_endpoints(self):
        auth_ts = read_text("frontend/lib/auth.ts")

        self.assertIn("/api/auth/login", auth_ts)
        self.assertIn("/api/auth/me", auth_ts)
        self.assertIn("Authorization", auth_ts)
        self.assertIn("Bearer", auth_ts)
        self.assertIn("NEXT_PUBLIC_API_BASE_URL", auth_ts)

    def test_session_storage_persists_token_and_user(self):
        session_ts = read_text("frontend/lib/session.ts")

        self.assertIn("localStorage", session_ts)
        self.assertIn("accessToken", session_ts)
        self.assertIn("currentUser", session_ts)
        self.assertIn("clearSession", session_ts)

    def test_home_page_guards_dashboard_behind_login(self):
        page_tsx = read_text("frontend/app/page.tsx")

        self.assertIn("getStoredSession", page_tsx)
        self.assertIn("router.replace(\"/login\")", page_tsx)
        self.assertIn("currentUser=", page_tsx)

    def test_dashboard_renders_authenticated_user(self):
        dashboard_tsx = read_text("frontend/components/Dashboard.tsx")

        self.assertIn("currentUser", dashboard_tsx)
        self.assertIn("currentUser.name", dashboard_tsx)
        self.assertIn("currentUser.email", dashboard_tsx)
        self.assertIn("displayName", dashboard_tsx)
        self.assertNotIn("Yunlong Li", dashboard_tsx)

    def test_login_page_offers_seed_accounts(self):
        login_page = read_text("frontend/app/login/page.tsx")

        self.assertIn("employee@example.com", login_page)
        self.assertIn("handler@example.com", login_page)
        self.assertIn("approver@example.com", login_page)
        self.assertIn("admin@example.com", login_page)
        self.assertIn("login(", login_page)


if __name__ == "__main__":
    unittest.main()
