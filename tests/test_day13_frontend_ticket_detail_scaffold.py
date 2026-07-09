import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class Day13FrontendTicketDetailScaffoldTest(unittest.TestCase):
    def test_ticket_detail_frontend_file_exists(self):
        self.assertTrue((ROOT / "frontend/app/tickets/[ticketId]/page.tsx").is_file())

    def test_ticket_client_supports_detail_and_status_update(self):
        tickets_ts = read_text("frontend/lib/tickets.ts")

        self.assertIn("getTicket", tickets_ts)
        self.assertIn("updateTicketStatus", tickets_ts)
        self.assertIn("/api/tickets/${ticketId}", tickets_ts)
        self.assertIn("/status", tickets_ts)
        self.assertIn("PATCH", tickets_ts)

    def test_tickets_list_links_to_detail_page(self):
        page_tsx = read_text("frontend/app/tickets/page.tsx")

        self.assertIn("router.push(`/tickets/${ticket.id}`)", page_tsx)
        self.assertIn("查看详情", page_tsx)

    def test_ticket_detail_page_requires_session_and_updates_status(self):
        page_tsx = read_text("frontend/app/tickets/[ticketId]/page.tsx")

        self.assertIn("getStoredSession", page_tsx)
        self.assertIn("router.replace(\"/login\")", page_tsx)
        self.assertIn("getTicket", page_tsx)
        self.assertIn("updateTicketStatus", page_tsx)
        self.assertIn("工单详情", page_tsx)
        self.assertIn("处理状态", page_tsx)
        self.assertIn("in_progress", page_tsx)
        self.assertIn("resolved", page_tsx)

    def test_ticket_detail_page_has_scrollable_layout(self):
        css = read_text("frontend/app/globals.css")

        self.assertIn(".ticket-detail-page", css)
        self.assertIn("height: 100vh", css)
        self.assertIn(".ticket-detail-content", css)
        self.assertIn("overflow-y: auto", css)
        self.assertIn(".ticket-status-actions", css)


if __name__ == "__main__":
    unittest.main()
