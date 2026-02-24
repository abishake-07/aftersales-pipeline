"""
Synthetic BMW Aftersales Support Ticket Generator

Produces realistic-looking JSON-Lines files for the demo pipeline.
All data is fake — no real customer or vehicle information.

Usage:
    python src/generate_tickets.py --count 5000 --output data/raw/
    python src/generate_tickets.py --count 500  --output data/raw/ --days-back 30
"""

import argparse
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Import schema enums ────────────────────────────────────────
from schema import (
    MARKETS,
    MODEL_SERIES,
    MODEL_YEARS,
    SLA_TARGETS_HOURS,
    Category,
    Channel,
    Severity,
    Status,
)

# ── Probability weights (make data look realistic) ─────────────

SEVERITY_WEIGHTS = {
    Severity.P1: 0.05,
    Severity.P2: 0.15,
    Severity.P3: 0.45,
    Severity.P4: 0.35,
}

STATUS_WEIGHTS = {
    Status.OPEN: 0.10,
    Status.IN_PROGRESS: 0.15,
    Status.WAITING_CUSTOMER: 0.08,
    Status.RESOLVED: 0.47,
    Status.CLOSED: 0.20,
}

CATEGORY_WEIGHTS = {
    Category.ENGINE: 0.12,
    Category.ELECTRICAL: 0.14,
    Category.INFOTAINMENT: 0.18,
    Category.BODYWORK: 0.08,
    Category.SUSPENSION: 0.07,
    Category.BRAKE: 0.09,
    Category.HVAC: 0.10,
    Category.WARRANTY: 0.12,
    Category.RECALL: 0.05,
    Category.OTHER: 0.05,
}

CHANNEL_WEIGHTS = {
    Channel.PHONE: 0.25,
    Channel.EMAIL: 0.20,
    Channel.DEALER_PORTAL: 0.30,
    Channel.BMW_APP: 0.15,
    Channel.WALK_IN: 0.10,
}

MARKET_WEIGHTS = {
    "DE": 0.25, "US": 0.20, "GB": 0.10, "CN": 0.15,
    "FR": 0.07, "IT": 0.06, "JP": 0.05, "KR": 0.04,
    "AU": 0.04, "AE": 0.04,
}

# Number of fictional dealers per market
DEALERS_PER_MARKET = 8


# ── Helpers ─────────────────────────────────────────────────────

def _weighted_choice(options_weights: dict):
    """Pick a random key from {option: weight} dict."""
    items = list(options_weights.keys())
    weights = list(options_weights.values())
    return random.choices(items, weights=weights, k=1)[0]


def _random_ts(start: datetime, end: datetime) -> datetime:
    """Random timestamp between start and end (UTC)."""
    delta = (end - start).total_seconds()
    offset = random.random() * delta
    return start + timedelta(seconds=offset)


def _dealer_id(market: str) -> str:
    """Generate a deterministic-looking dealer ID."""
    num = random.randint(1, DEALERS_PER_MARKET)
    return f"DLR-{market}-{num:03d}"


def _customer_id() -> str:
    return f"CUST-{uuid.uuid4().hex[:10].upper()}"


def _vin_last6() -> str:
    chars = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"  # VIN-valid chars
    return "".join(random.choices(chars, k=6))


# ── Ticket generator ───────────────────────────────────────────

def generate_ticket(now: datetime, days_back: int) -> dict:
    """Return a single synthetic ticket as a dict."""

    created = _random_ts(
        now - timedelta(days=days_back),
        now - timedelta(hours=1),
    )

    severity = _weighted_choice(SEVERITY_WEIGHTS)
    status = _weighted_choice(STATUS_WEIGHTS)

    # Determine resolution timestamp
    resolved_at = None
    resolution_hours = None
    if status in (Status.RESOLVED, Status.CLOSED):
        # Resolution time depends on severity (with noise)
        base_hours = SLA_TARGETS_HOURS[severity]
        actual_hours = max(0.5, random.gauss(base_hours * 0.8, base_hours * 0.6))
        resolved_at = created + timedelta(hours=actual_hours)
        if resolved_at > now:
            resolved_at = now - timedelta(minutes=random.randint(5, 120))
        resolution_hours = round((resolved_at - created).total_seconds() / 3600, 2)

    # SLA breach check
    sla_breached = False
    if resolution_hours is not None:
        sla_breached = resolution_hours > SLA_TARGETS_HOURS[severity]
    elif status in (Status.OPEN, Status.IN_PROGRESS, Status.WAITING_CUSTOMER):
        # Still open — breached if already past SLA window
        hours_open = (now - created).total_seconds() / 3600
        sla_breached = hours_open > SLA_TARGETS_HOURS[severity]

    updated = resolved_at or _random_ts(created, now)

    market = _weighted_choice(MARKET_WEIGHTS)

    return {
        "ticket_id": str(uuid.uuid4()),
        "created_at": created.isoformat(timespec="seconds"),
        "updated_at": updated.isoformat(timespec="seconds"),
        "resolved_at": resolved_at.isoformat(timespec="seconds") if resolved_at else None,
        "severity": severity.value,
        "status": status.value,
        "category": _weighted_choice(CATEGORY_WEIGHTS).value,
        "channel": _weighted_choice(CHANNEL_WEIGHTS).value,
        "market": market,
        "dealer_id": _dealer_id(market),
        "customer_id": _customer_id(),
        "vin_last6": _vin_last6(),
        "model_series": random.choice(MODEL_SERIES),
        "model_year": random.choice(MODEL_YEARS),
        "sla_breached": sla_breached,
    }


# ── File writer ─────────────────────────────────────────────────

def write_jsonlines(tickets: list[dict], output_dir: Path, batch_size: int = 1000):
    """
    Write tickets as JSON-Lines files, split into batches.
    Each file: tickets_YYYYMMDD_HHMMSS_<batch>.jsonl
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ts_label = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    file_count = 0
    for i in range(0, len(tickets), batch_size):
        batch = tickets[i : i + batch_size]
        fname = output_dir / f"tickets_{ts_label}_{file_count:04d}.jsonl"
        with open(fname, "w", encoding="utf-8") as f:
            for t in batch:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
        file_count += 1
        print(f"  ✓ Wrote {len(batch):,} tickets → {fname}")

    return file_count


# ── CLI ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic BMW aftersales support tickets."
    )
    parser.add_argument(
        "--count", type=int, default=5000,
        help="Number of tickets to generate (default: 5000)",
    )
    parser.add_argument(
        "--output", type=str, default="data/raw",
        help="Output directory for JSON-Lines files (default: data/raw)",
    )
    parser.add_argument(
        "--days-back", type=int, default=90,
        help="Spread tickets over this many past days (default: 90)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=1000,
        help="Tickets per output file (default: 1000)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    args = parser.parse_args()

    random.seed(args.seed)
    now = datetime.now(timezone.utc)

    print(f"Generating {args.count:,} synthetic tickets (past {args.days_back} days)…")
    tickets = [generate_ticket(now, args.days_back) for _ in range(args.count)]

    output_path = Path(args.output)
    n_files = write_jsonlines(tickets, output_path, args.batch_size)

    print(f"\nDone! {args.count:,} tickets written across {n_files} file(s) in {output_path}/")

    # Quick stats
    breached = sum(1 for t in tickets if t["sla_breached"])
    print(f"  SLA breach rate: {breached / len(tickets) * 100:.1f}%")
    from collections import Counter
    sev = Counter(t["severity"] for t in tickets)
    print(f"  Severity mix: { {k: v for k, v in sorted(sev.items())} }")


if __name__ == "__main__":
    main()
