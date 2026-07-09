import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class Day15FrontendTicketAssignmentScaffoldTest(unittest.TestCase):
    def test_ticket_client_supports_handler_list_and_assignment(self):
        tickets_ts = read_text("frontend/lib/tickets.ts")

        self.assertIn("TicketHandlerOption", tickets_ts)
        self.assertIn("listTicketHandlers", tickets_ts)
        self.assertIn("assignTicket", tickets_ts)
        self.assertIn("/api/auth/handlers", tickets_ts)
        self.assertIn("/assignee", tickets_ts)
        self.assertIn("assignee_id", tickets_ts)

    def test_ticket_comments_show_author_names(self):
        tickets_ts = read_text("frontend/lib/tickets.ts")
        page_tsx = read_text("frontend/app/tickets/[ticketId]/page.tsx")

        self.assertIn("author_name", tickets_ts)
        self.assertIn("author_role", tickets_ts)
        self.assertIn("comment.author_name", page_tsx)

    def test_ticket_detail_page_supports_assignment_controls(self):
        page_tsx = read_text("frontend/app/tickets/[ticketId]/page.tsx")

        self.assertIn("listTicketHandlers", page_tsx)
        self.assertIn("assignTicket", page_tsx)
        self.assertIn("handlerOptions", page_tsx)
        self.assertIn("selectedAssigneeId", page_tsx)
        self.assertIn("分配处理人", page_tsx)
        self.assertIn("保存分配", page_tsx)

    def test_ticket_assignment_has_styled_layout(self):
        css = read_text("frontend/app/globals.css")

        self.assertIn(".ticket-assignee-card", css)
        self.assertIn(".ticket-assignee-form", css)
        self.assertIn(".ticket-assignee-form select", css)


if __name__ == "__main__":
    unittest.main()
