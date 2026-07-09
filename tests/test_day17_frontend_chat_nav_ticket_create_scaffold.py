import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class Day17FrontendChatNavTicketCreateScaffoldTest(unittest.TestCase):
    def test_chat_frontend_files_exist(self):
        expected_files = [
            "frontend/lib/chat.ts",
            "frontend/app/chat/page.tsx",
        ]

        missing = [path for path in expected_files if not (ROOT / path).is_file()]

        self.assertEqual(missing, [])

    def test_chat_client_calls_backend_endpoints(self):
        chat_ts = read_text("frontend/lib/chat.ts")

        self.assertIn("/api/chat/conversations", chat_ts)
        self.assertIn("/messages", chat_ts)
        self.assertIn("createChatConversation", chat_ts)
        self.assertIn("sendChatMessage", chat_ts)
        self.assertIn("listChatConversations", chat_ts)
        self.assertIn("Authorization", chat_ts)

    def test_chat_page_requires_session_and_sends_messages(self):
        page_tsx = read_text("frontend/app/chat/page.tsx")

        self.assertIn("getStoredSession", page_tsx)
        self.assertIn('router.replace("/login")', page_tsx)
        self.assertIn("createChatConversation", page_tsx)
        self.assertIn("sendChatMessage", page_tsx)
        self.assertIn("智能助手", page_tsx)
        self.assertIn("发送", page_tsx)
        self.assertIn("引用来源", page_tsx)

    def test_dashboard_left_nav_and_ai_button_link_to_real_pages(self):
        dashboard_data = read_text("frontend/lib/dashboard-data.ts")
        dashboard = read_text("frontend/components/Dashboard.tsx")

        for href in [
            "/admin/documents",
            "/tickets",
            "/approvals",
            "/admin/traces",
            "/settings",
        ]:
            self.assertIn(f'href: "{href}"', dashboard_data)

        self.assertIn('router.push("/chat")', dashboard)
        self.assertIn("item.href", dashboard)
        self.assertIn("router.push(item.href)", dashboard)

    def test_ticket_page_supports_manual_priority_and_clear_create_button(self):
        page_tsx = read_text("frontend/app/tickets/page.tsx")
        css = read_text("frontend/app/globals.css")

        self.assertIn("editableDraft", page_tsx)
        self.assertIn("setEditableDraft", page_tsx)
        self.assertIn("ticketPriorityOptions", page_tsx)
        self.assertIn("<select", page_tsx)
        self.assertIn("创建工单", page_tsx)
        self.assertIn("提交审批", page_tsx)
        self.assertIn(".ticket-draft-editor", css)
        self.assertIn(".ticket-draft-actions", css)


if __name__ == "__main__":
    unittest.main()
