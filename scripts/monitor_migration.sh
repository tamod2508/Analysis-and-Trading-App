#!/bin/bash
# Monitor HDF5 to QuestDB migration progress
# Usage: ./scripts/monitor_migration.sh

QUESTDB_URL="http://localhost:9000/exec"
INTERVAL=5  # seconds between updates

echo "=========================================="
echo "QuestDB Migration Monitor"
echo "=========================================="
echo "Updates every ${INTERVAL}s (Ctrl+C to stop)"
echo ""

while true; do
    clear
    echo "=========================================="
    echo "QuestDB Migration Progress"
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================="
    echo ""

    # Total row count
    echo "📊 TOTAL ROWS:"
    curl -s "${QUESTDB_URL}?query=SELECT+COUNT(*)+as+total+FROM+ohlcv_equity" | \
        python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"   {data['dataset'][0][0]:,} rows\")" 2>/dev/null || echo "   Error querying QuestDB"
    echo ""

    # Unique symbols
    echo "🏢 UNIQUE SYMBOLS:"
    curl -s "${QUESTDB_URL}?query=SELECT+COUNT(DISTINCT+symbol)+as+symbols+FROM+ohlcv_equity" | \
        python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"   {data['dataset'][0][0]:,} symbols\")" 2>/dev/null || echo "   Error querying QuestDB"
    echo ""

    # By exchange
    echo "📈 BY EXCHANGE:"
    curl -s "${QUESTDB_URL}" --data-urlencode "query=SELECT exchange, COUNT(*) as rows FROM ohlcv_equity GROUP BY exchange ORDER BY exchange" | \
        python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for row in data.get('dataset', []):
        exchange = row[0]
        count = row[1]
        print(f'   {exchange:4s}: {count:>15,} rows')
except:
    print('   Error parsing data')
" 2>/dev/null
    echo ""

    # By interval
    echo "⏱️  BY INTERVAL:"
    curl -s "${QUESTDB_URL}" --data-urlencode "query=SELECT interval, COUNT(*) as rows FROM ohlcv_equity GROUP BY interval ORDER BY interval" | \
        python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for row in data.get('dataset', []):
        interval = row[0]
        count = row[1]
        print(f'   {interval:10s}: {count:>15,} rows')
except:
    print('   Error parsing data')
" 2>/dev/null
    echo ""

    # Recent writes
    echo "🕐 MOST RECENT WRITE:"
    curl -s "${QUESTDB_URL}" --data-urlencode "query=SELECT max(inserted_at) as latest FROM ohlcv_equity" | \
        python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    latest = data['dataset'][0][0]
    if latest:
        print(f'   {latest}')
    else:
        print('   No data yet')
except:
    print('   Error parsing data')
" 2>/dev/null
    echo ""

    echo "=========================================="
    echo "Target: 233,478,666 rows | 5,380 datasets"
    echo "=========================================="
    echo ""
    echo "Press Ctrl+C to stop monitoring"

    sleep ${INTERVAL}
done
