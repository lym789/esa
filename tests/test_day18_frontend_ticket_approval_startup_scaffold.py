import os
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))


def read_text(path: str) -> str:
    with open(os.path.join(ROOT_DIR, path), "r", encoding="utf-8") as file:
        return file.read()


class Day18TicketApprovalStartupTest(unittest.TestCase):
    def test_ticket_page_has_search_filters_and_pagination(self) -> None:
        page = read_text("frontend/app/tickets/page.tsx")
        css = read_text("frontend/app/globals.css")

        for expected in [
            "ticketSearchText",
            "setTicketSearchText",
            "ticketStatusFilter",
            "setTicketStatusFilter",
            "ticketPriorityFilter",
            "setTicketPriorityFilter",
            "filteredTickets",
            "paginatedTickets",
            "currentPage",
            "setCurrentPage",
            "搜索工单",
            "全部状态",
            "全部优先级",
            "上一页",
            "下一页",
        ]:
            self.assertIn(expected, page)

        for expected in [
            ".tickets-filters",
            ".tickets-filter-input",
            ".tickets-pagination",
        ]:
            self.assertIn(expected, css)

    def test_approval_page_has_status_filter_and_ticket_link(self) -> None:
        page = read_text("frontend/app/approvals/page.tsx")
        css = read_text("frontend/app/globals.css")

        for expected in [
            "approvalStatusFilter",
            "setApprovalStatusFilter",
            "filteredApprovals",
            "全部审批",
            "只看待审批",
            "查看工单",
            "execution_result.ticket_id",
            "router.push(`/tickets/${",
        ]:
            self.assertIn(expected, page)

        for expected in [
            ".approvals-filters",
            ".approval-ticket-link",
        ]:
            self.assertIn(expected, css)

    def test_startup_scripts_and_docs_are_present(self) -> None:
        for path in [
            "scripts/check-ports.sh",
            "scripts/start-local.sh",
            "scripts/stop-local.sh",
            "docs/day18-ticket-approval-startup.md",
        ]:
            self.assertTrue(os.path.exists(os.path.join(ROOT_DIR, path)), path)

        readme = read_text("README.md")
        start_script = read_text("scripts/start-local.sh")
        for expected in [
            "./scripts/check-ports.sh",
            "./scripts/start-local.sh",
            "./scripts/stop-local.sh",
        ]:
            self.assertIn(expected, readme)

        self.assertIn("nohup", start_script)


if __name__ == "__main__":
    unittest.main()
