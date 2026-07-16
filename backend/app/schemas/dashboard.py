from datetime import datetime

from pydantic import BaseModel


class DashboardStatRead(BaseModel):
    key: str
    label: str
    value: int | float
    detail: str


class DashboardStatusRead(BaseModel):
    backend: str
    database: str
    llm_configured: bool
    embedding_configured: bool


class DashboardNotificationRead(BaseModel):
    id: str
    kind: str
    title: str
    message: str
    href: str
    created_at: datetime


class DashboardIntegrationRead(BaseModel):
    key: str
    name: str
    status: str
    detail: str


class DashboardAnalyticsRead(BaseModel):
    ticket_status: dict[str, int]
    ticket_priority: dict[str, int]
    ticket_category: dict[str, int]


class DashboardOverviewRead(BaseModel):
    stats: list[DashboardStatRead]
    status: DashboardStatusRead
    notifications: list[DashboardNotificationRead]
    analytics: DashboardAnalyticsRead
    integrations: list[DashboardIntegrationRead]


class DashboardSearchResultRead(BaseModel):
    kind: str
    title: str
    snippet: str
    href: str


class DashboardSearchResponse(BaseModel):
    query: str
    results: list[DashboardSearchResultRead]
