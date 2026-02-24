# BMW Aftersales Support Ticket Pipeline

> End-to-end data pipeline that generates synthetic BMW aftersales customer support tickets, lands them in Amazon S3, transforms to columnar format, queries via Athena, and visualises KPIs in Amazon QuickSight — all within **AWS Free Tier**.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Free%20Tier-FF9900?logo=amazonaws&logoColor=white)


---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Data Schema](#data-schema)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Generate Synthetic Data](#1-generate-synthetic-data)
  - [Transform to Parquet](#2-transform-to-parquet)
  - [Deploy to AWS](#3-deploy-to-aws)
  - [Query with Athena](#4-query-with-athena)
  - [Visualise in QuickSight](#5-visualise-in-quicksight)
- [KPIs & Dashboard](#kpis--dashboard)
- [Configuration](#configuration)
- [Cost Estimate](#cost-estimate)


---

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌────────────┐
│   Python      │     │  Amazon S3    │     │  Amazon S3        │     │  AWS Glue   │     │  Amazon    │
│   Synthetic   │────▶│  /raw/        │────▶│  /curated/        │────▶│  Catalog +  │────▶│ QuickSight │
│   Generator   │     │  (JSON-Lines) │     │  (Parquet, part.) │     │  Athena     │     │  SPICE     │
└──────────────┘     └──────────────┘     └──────────────────┘     └─────────────┘     └────────────┘
     Local               Landing              Transform               Query             Dashboard
```

**Data flow:**
1. **Ingest** — Python script generates realistic support tickets as JSON-Lines
2. **Land** — Raw files uploaded to S3 landing zone
3. **Transform** — Local pandas + pyarrow job converts to Snappy-compressed, Hive-partitioned Parquet
4. **Catalog & Query** — Glue Data Catalog registers the schema; Athena provides serverless SQL
5. **Visualise** — QuickSight imports data into SPICE for interactive dashboards

---

## Tech Stack

| Layer | Technology | Free Tier Coverage |
|-------|-----------|-------------------|
| Generator | Python 3.10+, stdlib | Free (local) |
| Storage | Amazon S3 | 5 GB / 12 months |
| Transform | pandas, pyarrow | Free (local) |
| Catalog | AWS Glue Data Catalog | 1M objects free |
| Query Engine | Amazon Athena | 5 TB scanned/month |
| Visualisation | Amazon QuickSight | 30-day trial (1 author) |
| IaC | AWS CLI, shell scripts | Free |

---

## Data Schema

15-field ticket schema modelling real-world aftersales workflows:

| # | Field | Type | Description |
|---|-------|------|-------------|
| 1 | `ticket_id` | `UUID` | Unique ticket identifier |
| 2 | `created_at` | `timestamp` | Ticket creation time (UTC) |
| 3 | `updated_at` | `timestamp` | Last update time (UTC) |
| 4 | `resolved_at` | `timestamp?` | Resolution time (nullable) |
| 5 | `severity` | `enum` | P1 (Critical) → P4 (Low) |
| 6 | `status` | `enum` | Open / In Progress / Waiting / Resolved / Closed |
| 7 | `category` | `enum` | Engine, Electrical, iDrive, Brake, Recall, etc. |
| 8 | `channel` | `enum` | Phone / Email / Dealer Portal / BMW App / Walk-In |
| 9 | `market` | `string` | ISO 3166-1 country code *(partition key)* |
| 10 | `dealer_id` | `string` | Service center identifier |
| 11 | `customer_id` | `string` | Pseudonymised customer ID |
| 12 | `vin_last6` | `string` | Last 6 characters of VIN |
| 13 | `model_series` | `string` | e.g. "X5", "3 Series", "iX" |
| 14 | `model_year` | `int` | Model year (2018–2026) |
| 15 | `sla_breached` | `bool` | True if resolution exceeded SLA target |

**Computed fields** (via Athena view `tickets_enriched`):
- `resolution_hours` — time from creation to resolution
- `days_open` — days a ticket has been open (unresolved only)
- `hours_since_created` — total hours since ticket opened

---

## Project Structure

```
aftersales-pipeline/
│
├── src/
│   ├── schema.py                # Ticket dataclass, enums, SLA targets
│   ├── generate_tickets.py      # Synthetic data generator (JSON-Lines)
│   └── transform_to_parquet.py  # JSON-Lines → Hive-partitioned Parquet
│
├── infra/
│   ├── s3_setup.sh              # Create & configure S3 buckets
│   └── athena_ddl.sql           # Glue database, tables, and enriched view
│
├── queries/
│   └── sample_queries.sql       # 10 ready-to-run Athena KPI queries
│
├── data/                        # Generated data (gitignored)
│   ├── raw/                     #   └── *.jsonl files
│   └── curated/                 #   └── market=XX/part-0.parquet
│
├── .env.example                 # Template for local config (copy to .env)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- **AWS CLI v2** — [Install guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **AWS Account** with Free Tier eligibility
- AWS CLI configured: `aws configure`

### Installation

```bash
# Clone the repository
git clone https://github.com/abishake-07/aftersales-pipeline.git
cd aftersales-pipeline

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment config
cp .env.example .env
# Edit .env → set your AWS_ACCOUNT_ID
```

### 1. Generate Synthetic Data

```bash
cd src
python generate_tickets.py --count 5000 --output ../data/raw/
```

Options:
| Flag | Default | Description |
|------|---------|-------------|
| `--count` | 5000 | Number of tickets |
| `--days-back` | 90 | Spread across N past days |
| `--batch-size` | 1000 | Tickets per output file |
| `--seed` | 42 | Random seed for reproducibility |

### 2. Transform to Parquet

```bash
python transform_to_parquet.py --input ../data/raw --output ../data/curated
```

Produces Hive-style partitioned Parquet files:
```
data/curated/tickets/market=DE/part-0.parquet
data/curated/tickets/market=US/part-0.parquet
...
```

### 3. Deploy to AWS

```bash
# Create S3 buckets (run from project root)
bash infra/s3_setup.sh

# Upload raw data
aws s3 sync data/raw/ s3://bmw-aftersales-raw-<ACCOUNT_ID>/tickets/

# Upload curated Parquet
aws s3 sync data/curated/tickets/ s3://bmw-aftersales-curated-<ACCOUNT_ID>/tickets/
```

### 4. Query with Athena

Run the DDL statements from `infra/athena_ddl.sql` in the Athena Query Editor (replace `<ACCOUNT_ID>` with your value):

```sql
-- Create database
CREATE DATABASE IF NOT EXISTS bmw_aftersales;

-- Create table (see infra/athena_ddl.sql for full DDL)
-- Load partitions
MSCK REPAIR TABLE bmw_aftersales.tickets;

-- Verify
SELECT market, COUNT(*) AS tickets
FROM bmw_aftersales.tickets_enriched
GROUP BY market ORDER BY tickets DESC;
```

See `queries/sample_queries.sql` for 10 pre-built KPI queries.

### 5. Visualise in QuickSight

1. Start **QuickSight Standard** free trial (30 days)
2. Grant QuickSight access to **Athena** + your **S3 buckets** (Security & Permissions)
3. **New Dataset** → Athena → database `bmw_aftersales` → view `tickets_enriched`
4. Choose **Import to SPICE** for fast interactive dashboards
5. Build visuals (see KPI table below)

---

## KPIs & Dashboard

| # | KPI | Visual Type | Key Fields |
|---|-----|-------------|------------|
| 1 | Daily ticket volume | Line chart | `created_at` (day) → COUNT |
| 2 | Severity distribution | Donut chart | `severity` → COUNT |
| 3 | SLA breach rate | KPI + Gauge | `sla_breached` TRUE / total |
| 4 | Avg resolution time | KPI number | AVG(`resolution_hours`) |
| 5 | Tickets by market | Horizontal bar | `market` → COUNT |
| 6 | Top 5 issue categories | Tree map | `category` → COUNT |
| 7 | Open vs Closed trend | Stacked area | `status`, `created_at` (week) |
| 8 | P1 open tickets | Table | `severity`=P1, `status`≠Closed |
| 9 | Resolution time by severity | Bar chart | `severity` → AVG(`resolution_hours`) |
| 10 | Market × Severity heatmap | Heat map | `market` × `severity` → COUNT |

---

## Configuration

All non-secret configuration lives in `.env` (gitignored). Copy the template:

```bash
cp .env.example .env
```

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID | `123456789012` |
| `AWS_REGION` | AWS region for all resources | `eu-central-1` |
| `AWS_PROFILE` | AWS CLI profile name | `default` |

> **Security:** AWS credentials (access keys) are managed via `aws configure` and stored in `~/.aws/credentials` — never in this repository.

---

## Cost Estimate

Running this demo end-to-end should cost **$0** on AWS Free Tier:

| Service | Usage | Free Tier Limit |
|---------|-------|-----------------|
| S3 | ~5 MB stored | 5 GB |
| Athena | ~50 KB scanned per query | 5 TB/month |
| Glue Catalog | 1 database, 2 tables | 1M objects |
| QuickSight | 1 author, 1 GB SPICE | 30-day trial |

> ⚠️ **Do not** run AWS Glue ETL jobs — they are billed outside Free Tier. All transforms are run locally.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m "Add my feature"`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---


<p align="center">
  Built as a portfolio project demonstrating end-to-end data engineering on AWS.
</p>
