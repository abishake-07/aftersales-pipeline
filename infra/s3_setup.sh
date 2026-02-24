#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# S3 Bucket Setup — BMW Aftersales Pipeline (Free Tier)
# ─────────────────────────────────────────────────────────────
# Run once:  bash infra/s3_setup.sh
#
# Prerequisites:
#   - AWS CLI v2 configured (`aws configure`)
#   - A unique suffix to avoid global bucket-name collisions
# ─────────────────────────────────────────────────────────────

set -euo pipefail

# ── Load .env (non-secret config) ───────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    set -a; source "$ENV_FILE"; set +a
    echo "Loaded config from .env"
else
    echo "⚠  No .env file found. Copy .env.example → .env and fill in your values."
    echo "   cp .env.example .env"
    exit 1
fi

# ── Configuration ───────────────────────────────────────────
REGION="${AWS_REGION:-eu-central-1}"
export AWS_PROFILE="${AWS_PROFILE:-default}"
SUFFIX="${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID in .env}"

RAW_BUCKET="bmw-aftersales-raw-${SUFFIX}"
CURATED_BUCKET="bmw-aftersales-curated-${SUFFIX}"
ATHENA_RESULTS="bmw-aftersales-athena-results-${SUFFIX}"

echo "Creating S3 buckets in ${REGION}…"

for BUCKET in "$RAW_BUCKET" "$CURATED_BUCKET" "$ATHENA_RESULTS"; do
    if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
        echo "  ⏭  ${BUCKET} already exists"
    else
        aws s3api create-bucket \
            --bucket "$BUCKET" \
            --region "$REGION" \
            --create-bucket-configuration LocationConstraint="$REGION"
        echo "  ✓  Created ${BUCKET}"
    fi
done

# ── Lifecycle rule: auto-delete raw files after 30 days ────
# (keeps free-tier storage low)
aws s3api put-bucket-lifecycle-configuration \
    --bucket "$RAW_BUCKET" \
    --lifecycle-configuration '{
        "Rules": [{
            "ID": "ExpireRawAfter30d",
            "Status": "Enabled",
            "Filter": {"Prefix": "tickets/"},
            "Expiration": {"Days": 30}
        }]
    }'
echo "  ✓  Lifecycle rule set on ${RAW_BUCKET}"

# ── Block all public access (best practice) ────────────────
for BUCKET in "$RAW_BUCKET" "$CURATED_BUCKET" "$ATHENA_RESULTS"; do
    aws s3api put-public-access-block \
        --bucket "$BUCKET" \
        --public-access-block-configuration \
            BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
done
echo "  ✓  Public access blocked on all buckets"

echo ""
echo "Done! Your buckets:"
echo "  Raw:      s3://${RAW_BUCKET}/tickets/"
echo "  Curated:  s3://${CURATED_BUCKET}/tickets/"
echo "  Athena:   s3://${ATHENA_RESULTS}/"
echo ""
echo "Next: upload raw data with"
echo "  aws s3 sync data/raw/ s3://${RAW_BUCKET}/tickets/"
