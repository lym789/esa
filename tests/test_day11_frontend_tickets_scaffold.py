import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class Day11FrontendTicketsScaffoldTest(unittest.TestCase):
    def test_ticket_frontend_files_exist(self):
        expected_files = [
            "frontend/lib/tickets.ts",
            "frontend/app/tickets/page.tsx",
        ]

        missing = [path for path in expected_files if not (ROOT / path).is_file()]

        self.assertEqual(missing, [])

    def test_ticket_client_calls_backend_endpoints(self):
        tickets_ts = read_text("frontend/lib/tickets.ts")

        self.assertIn("/api/tickets", tickets_ts)
        self.assertIn("/api/tickets/draft", tickets_ts)
        self.assertIn("listTickets", tickets_ts)
        self.assertIn("createTicketDraft", tickets_ts)
        self.assertIn("createTicket", tickets_ts)
        self.assertIn("Authorization", tickets_ts)

    def test_tickets_page_requires_session_and_supports_draft_and_create(self):
        page_tsx = read_text("frontend/app/tickets/page.tsx")

        self.assertIn("getStoredSession", page_tsx)
        self.assertIn("router.replace(\"/login\")", page_tsx)
        self.assertIn("createTicketDraft", page_tsx)
        self.assertIn("createTicket", page_tsx)
        self.assertIn("listTickets", page_tsx)
        self.assertIn("pending_approval", page_tsx)

    def test_dashboard_ticket_card_links_to_tickets_page(self):
        dashboard_data = read_text("frontend/lib/dashboard-data.ts")

        self.assertIn("/tickets", dashboard_data)

    def test_tickets_page_keeps_generated_draft_reachable(self):
        css = read_text("frontend/app/globals.css")

        self.assertIn(".tickets-page", css)
        self.assertIn("height: 100vh", css)
        self.assertIn("overflow-y: auto", css)
        self.assertIn(".tickets-table", css)
        self.assertIn("max-height: calc(100vh - 344px)", css)
        self.assertIn("overflow: auto", css)


if __name__ == "__main__":
    unittest.main()
