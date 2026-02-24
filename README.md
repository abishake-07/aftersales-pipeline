# BMW Aftersales Support Ticket Pipeline — AWS Free Tier Demo

## Architecture Overview

```
┌──────────────┐    ┌───────────────┐    ┌───────────────────┐    ┌──────────────┐    ┌────────────┐
│  Python       │    │  S3 Bucket     │    │  S3 Bucket         │    │  AWS Glue    │    │  Amazon    │
│  Synthetic    │───▶│  /raw/         │───▶│  /curated/         │───▶│  Catalog +   │───▶│ QuickSight │
│  Generator    │    │  (JSON-Lines)  │    │  (Parquet, part.)  │    │  Athena      │    │  SPICE     │
└──────────────┘    └───────────────┘    └───────────────────┘    └──────────────┘    └────────────┘
       local              landing            transform                 query              dashboard
```

### Components
| Layer | Service | Free Tier Notes |
|-------|---------|-----------------|
| Ingest | Local Python script → `aws s3 cp` | Free (local) |
| Landing | S3 `s3://bmw-aftersales-raw/` | 5 GB free (12 months) |
| Transform | Local Python (pandas + pyarrow) or AWS Glue* | Local = free |
| Catalog | AWS Glue Data Catalog | 1 M objects free |
| Query | Amazon Athena | 5 TB scan/month free (first year) |
| Visualize | Amazon QuickSight | 30-day free trial, 1 author |

> *AWS Glue ETL jobs are **not** free-tier. For zero cost, run the Parquet conversion locally.

---

## Step-by-Step Implementation Plan

### Evening 1 — Local Generator & Raw Data
- [ ] Install Python deps: `pip install -r requirements.txt`
- [ ] Run `python src/generate_tickets.py --count 5000 --output data/raw/`
- [ ] Inspect sample JSON-Lines files in `data/raw/`

### Evening 2 — S3 Buckets & Upload
- [ ] Create S3 buckets via CLI (see `infra/s3_setup.sh`)
- [ ] Upload raw files: `aws s3 sync data/raw/ s3://bmw-aftersales-raw/tickets/`
- [ ] Verify in S3 console

### Evening 3 — Transform to Parquet
- [ ] Run `python src/transform_to_parquet.py`
- [ ] Upload curated Parquet: `aws s3 sync data/curated/ s3://bmw-aftersales-curated/tickets/`
- [ ] Confirm partitioned structure (`market=DE/`, `market=US/`, …)

### Evening 4 — Glue Catalog & Athena
- [ ] Run Glue Crawler or execute DDL in `infra/athena_ddl.sql`
- [ ] Open Athena console → run sample queries from `queries/sample_queries.sql`
- [ ] Validate row counts, partition pruning

### Evening 5 — QuickSight Dashboard
- [ ] Start QuickSight free trial (Standard Edition, 1 author)
- [ ] Create Athena data source → import dataset into SPICE
- [ ] Build visuals (see KPI list below)
- [ ] Publish dashboard, share link

---

## KPIs & Dashboard Visuals

| # | KPI | Visual Type | Fields |
|---|-----|-------------|--------|
| 1 | **Daily ticket volume** | Line chart | `created_at` (day) vs COUNT | 
| 2 | **Severity distribution** | Donut / Pie | `severity` vs COUNT |
| 3 | **SLA breach rate** | KPI number + gauge | `sla_breached` = TRUE / total |
| 4 | **Avg resolution time (hrs)** | KPI number | AVG(`resolution_hours`) |
| 5 | **Tickets by market** | Horizontal bar | `market` vs COUNT |
| 6 | **Top 5 issue categories** | Tree map | `category` vs COUNT |
| 7 | **Open vs Closed trend** | Stacked area | `status`, `created_at` (week) |
| 8 | **P1 tickets still open** | Table / conditional | `severity`=P1 AND `status`≠Closed |
| 9 | **Resolution time by severity** | Box plot / bar | `severity` vs AVG(`resolution_hours`) |
| 10 | **Market × Severity heatmap** | Heat map | `market` vs `severity` → COUNT |

---

## Project Structure
```
aftersales-pipeline/
├── README.md
├── requirements.txt
├── src/
│   ├── generate_tickets.py      # synthetic ticket generator
│   ├── transform_to_parquet.py  # JSON-Lines → partitioned Parquet
│   └── schema.py                # ticket schema & enums
├── infra/
│   ├── s3_setup.sh              # create S3 buckets
│   └── athena_ddl.sql           # Glue/Athena table DDL
├── queries/
│   └── sample_queries.sql       # example Athena queries
└── data/                        # local data (gitignored)
    ├── raw/
    └── curated/
```
