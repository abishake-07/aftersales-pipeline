"""
BMW Aftersales Support Ticket — Schema & Enumerations

15-field schema designed to be realistic yet minimal for a demo pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ── Enumerations ────────────────────────────────────────────────

class Severity(str, Enum):
    P1 = "P1"   # Critical — vehicle immobile / safety
    P2 = "P2"   # High     — major function degraded
    P3 = "P3"   # Medium   — minor inconvenience
    P4 = "P4"   # Low      — cosmetic / informational


class Status(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    WAITING_CUSTOMER = "Waiting on Customer"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class Category(str, Enum):
    ENGINE = "Engine & Drivetrain"
    ELECTRICAL = "Electrical System"
    INFOTAINMENT = "Infotainment / iDrive"
    BODYWORK = "Bodywork & Paint"
    SUSPENSION = "Suspension & Steering"
    BRAKE = "Brake System"
    HVAC = "HVAC / Climate"
    WARRANTY = "Warranty Claim"
    RECALL = "Recall / Campaign"
    OTHER = "Other"


class Channel(str, Enum):
    PHONE = "Phone"
    EMAIL = "Email"
    DEALER_PORTAL = "Dealer Portal"
    BMW_APP = "BMW App"
    WALK_IN = "Walk-In"


# Markets (ISO 3166-1 alpha-2 subset relevant to BMW)
MARKETS = ["DE", "US", "GB", "CN", "FR", "IT", "JP", "KR", "AU", "AE"]

# BMW model series for synthetic data
MODEL_SERIES = [
    "3 Series", "5 Series", "7 Series", "X1", "X3", "X5", "X7",
    "i4", "iX", "iX3", "Z4", "M3", "M5", "2 Series Gran Coupé",
]

MODEL_YEARS = list(range(2018, 2027))


# ── Ticket Schema ───────────────────────────────────────────────

@dataclass
class SupportTicket:
    """
    Field inventory (15 fields):

    ┌───┬──────────────────────┬───────────┬──────────────────────────────────┐
    │ # │ Field                │ Type      │ Description                      │
    ├───┼──────────────────────┼───────────┼──────────────────────────────────┤
    │ 1 │ ticket_id            │ str       │ UUID-v4 unique identifier        │
    │ 2 │ created_at           │ datetime  │ Ticket creation timestamp (UTC)  │
    │ 3 │ updated_at           │ datetime  │ Last update timestamp (UTC)      │
    │ 4 │ resolved_at          │ datetime? │ Resolution timestamp (nullable)  │
    │ 5 │ severity             │ enum      │ P1–P4                            │
    │ 6 │ status               │ enum      │ Open → … → Closed               │
    │ 7 │ category             │ enum      │ Issue category                   │
    │ 8 │ channel              │ enum      │ How the ticket was raised        │
    │ 9 │ market               │ str       │ ISO country code (partition key) │
    │10 │ dealer_id            │ str       │ Dealer / service center ID       │
    │11 │ customer_id          │ str       │ Pseudonymised customer ID        │
    │12 │ vin_last6            │ str       │ Last 6 chars of VIN              │
    │13 │ model_series         │ str       │ e.g. "X5", "3 Series"           │
    │14 │ model_year           │ int       │ e.g. 2023                        │
    │15 │ sla_breached         │ bool      │ True if resolution > SLA target  │
    └───┴──────────────────────┴───────────┴──────────────────────────────────┘

    Derived (computed at query time):
      • resolution_hours  = (resolved_at − created_at) in hours
      • days_open         = (now − created_at) in days  (if still open)
    """

    ticket_id: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    severity: Severity
    status: Status
    category: Category
    channel: Channel
    market: str
    dealer_id: str
    customer_id: str
    vin_last6: str
    model_series: str
    model_year: int
    sla_breached: bool


# SLA target hours by severity (used by generator to set sla_breached)
SLA_TARGETS_HOURS = {
    Severity.P1: 4,
    Severity.P2: 8,
    Severity.P3: 48,
    Severity.P4: 120,
}
