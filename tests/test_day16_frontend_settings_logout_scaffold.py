import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class Day16FrontendSettingsLogoutScaffoldTest(unittest.TestCase):
    def test_settings_page_file_exists(self):
        self.assertTrue((ROOT / "frontend/app/settings/page.tsx").is_file())

    def test_dashboard_links_settings_to_settings_page(self):
        dashboard_data = read_text("frontend/lib/dashboard-data.ts")
        dashboard = read_text("frontend/components/Dashboard.tsx")

        self.assertIn('title: "设置"', dashboard_data)
        self.assertIn('href: "/settings"', dashboard_data)
        self.assertIn('label: "设置"', dashboard_data)
        self.assertIn("item.href", dashboard)
        self.assertIn("router.push(item.href)", dashboard)
        self.assertNotIn('label: "logout"', dashboard_data)

    def test_settings_page_can_logout(self):
        settings_page = read_text("frontend/app/settings/page.tsx")

        self.assertIn("getStoredSession", settings_page)
        self.assertIn("clearSession", settings_page)
        self.assertIn('router.replace("/login")', settings_page)
        self.assertIn("退出登录", settings_page)
        self.assertIn("当前账号", settings_page)
        self.assertIn('router.push("/")', settings_page)
        self.assertIn("返回", settings_page)

    def test_settings_page_has_styled_layout(self):
        css = read_text("frontend/app/globals.css")

        self.assertIn(".settings-page", css)
        self.assertIn(".settings-card", css)
        self.assertIn(".settings-logout-button", css)


if __name__ == "__main__":
    unittest.main()
