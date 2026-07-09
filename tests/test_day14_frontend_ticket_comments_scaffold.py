import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class Day14FrontendTicketCommentsScaffoldTest(unittest.TestCase):
    def test_ticket_client_supports_comments(self):
        tickets_ts = read_text("frontend/lib/tickets.ts")

        self.assertIn("TicketCommentRecord", tickets_ts)
        self.assertIn("listTicketComments", tickets_ts)
        self.assertIn("createTicketComment", tickets_ts)
        self.assertIn("/comments", tickets_ts)
        self.assertIn("content", tickets_ts)

    def test_ticket_detail_page_lists_and_creates_comments(self):
        page_tsx = read_text("frontend/app/tickets/[ticketId]/page.tsx")

        self.assertIn("listTicketComments", page_tsx)
        self.assertIn("createTicketComment", page_tsx)
        self.assertIn("comments", page_tsx)
        self.assertIn("工单评论", page_tsx)
        self.assertIn("新增评论", page_tsx)
        self.assertIn("commentText", page_tsx)

    def test_ticket_comments_have_scrollable_layout(self):
        css = read_text("frontend/app/globals.css")

        self.assertIn(".ticket-comments-card", css)
        self.assertIn(".ticket-comments-list", css)
        self.assertIn("overflow-y: auto", css)
        self.assertIn(".ticket-comment-form", css)


if __name__ == "__main__":
    unittest.main()
