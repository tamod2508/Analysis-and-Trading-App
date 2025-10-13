#!/bin/bash
# Wrapper script for HDF5 to QuestDB migration
# Usage: ./scripts/run_migration.sh [fast|normal|careful|dry-run]

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if QuestDB is running
check_questdb() {
    echo -e "${YELLOW}Checking QuestDB connection...${NC}"
    if curl -s "http://localhost:9000/exec?query=SELECT+1" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ QuestDB is running${NC}"
        return 0
    else
        echo -e "${RED}✗ QuestDB is not running${NC}"
        echo ""
        echo "Start QuestDB with:"
        echo "  brew services start questdb"
        echo "  OR"
        echo "  questdb start"
        exit 1
    fi
}

# Show current status
show_status() {
    echo ""
    echo "Current QuestDB status:"
    echo "----------------------"

    # Get current row count
    CURRENT_ROWS=$(curl -s "http://localhost:9000/exec?query=SELECT+COUNT(*)+FROM+ohlcv_equity" | \
        python3 -c "import sys, json; data=json.load(sys.stdin); print(data['dataset'][0][0])" 2>/dev/null || echo "0")

    echo "Rows in QuestDB: $(printf "%'d" $CURRENT_ROWS)"
    echo "Target rows:     233,478,666"
    echo ""
}

# Run migration based on mode
MODE=${1:-normal}

echo "=========================================="
echo "HDF5 to QuestDB Migration"
echo "=========================================="
echo ""

check_questdb
show_status

case $MODE in
    fast)
        echo -e "${YELLOW}Mode: FAST (16 workers, 100K batch)${NC}"
        echo "Best for: High-performance systems with good CPU/RAM"
        echo ""
        read -p "Press Enter to start or Ctrl+C to cancel..."
        python3 scripts/migrate_hdf5_to_questdb.py --parallel=16 --batch-size=100000
        ;;

    normal)
        echo -e "${YELLOW}Mode: NORMAL (8 workers, 50K batch)${NC}"
        echo "Best for: Most systems (recommended)"
        echo ""
        read -p "Press Enter to start or Ctrl+C to cancel..."
        python3 scripts/migrate_hdf5_to_questdb.py
        ;;

    careful)
        echo -e "${YELLOW}Mode: CAREFUL (4 workers, 25K batch)${NC}"
        echo "Best for: Systems with limited resources"
        echo ""
        read -p "Press Enter to start or Ctrl+C to cancel..."
        python3 scripts/migrate_hdf5_to_questdb.py --parallel=4 --batch-size=25000
        ;;

    dry-run)
        echo -e "${YELLOW}Mode: DRY RUN (analyze only)${NC}"
        echo "Preview migration without writing data"
        echo ""
        python3 scripts/migrate_hdf5_to_questdb.py --dry-run
        exit 0
        ;;

    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo ""
        echo "Usage: $0 [fast|normal|careful|dry-run]"
        echo ""
        echo "Modes:"
        echo "  fast    - 16 workers, 100K batch (high-performance systems)"
        echo "  normal  - 8 workers, 50K batch (default, recommended)"
        echo "  careful - 4 workers, 25K batch (low-resource systems)"
        echo "  dry-run - Analyze only, no writes"
        exit 1
        ;;
esac

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "✓ Migration completed successfully!"
    echo -e "==========================================${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Verify migration:"
    echo "   python3 scripts/check_migration_status.py"
    echo ""
    echo "2. Query data:"
    echo "   curl -s \"http://localhost:9000/exec\" --data-urlencode \"query=SELECT COUNT(*) FROM ohlcv_equity\""
    echo ""
else
    echo ""
    echo -e "${RED}=========================================="
    echo "✗ Migration failed"
    echo -e "==========================================${NC}"
    echo ""
    echo "Check logs for details:"
    echo "  tail -f logs/migration.log"
    exit 1
fi
