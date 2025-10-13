# Transfer Checklist for New MacBook

## ✅ Already Done

**Code and Scripts (pushed to GitHub):**
- ✅ All QuestDB code (`quest/` module)
- ✅ Migration scripts (`scripts/` directory)
- ✅ Setup instructions (`NEW_MAC_SETUP.md`)
- ✅ All existing code (api, database, flask_app, etc.)

**Repository:** https://github.com/tamod2508/Analysis-and-Trading-App

---

## 📦 Files to Transfer Manually

**CRITICAL - Must Transfer:**

1. **HDF5 Data Files** (NOT in git - too large)
   ```
   Location: ~/Desktop/kite_app/data/hdf5/

   Files needed:
   ✅ EQUITY_repacked.h5     (1.35 GB) ← MAIN FILE
   ✅ EQUITY_chunk1.h5       (~500 MB)
   ✅ EQUITY_chunk2.h5       (~500 MB)

   Total: ~2.4 GB
   ```

2. **Environment File** (contains API keys - NOT in git)
   ```
   Location: ~/Desktop/kite_app/.env

   Contains:
   - KITE_API_KEY
   - KITE_API_SECRET
   - KITE_ACCESS_TOKEN
   ```

---

## 🚀 Setup on New Mac

**Step 1: Clone Repository**
```bash
cd ~/Desktop
git clone https://github.com/tamod2508/Analysis-and-Trading-App.git kite_app
cd kite_app
```

**Step 2: Copy HDF5 Files**
```bash
# Create directory
mkdir -p data/hdf5

# Copy the 3 .h5 files from external drive/cloud
cp /path/to/backup/*.h5 data/hdf5/

# Verify
ls -lh data/hdf5/
```

**Step 3: Copy .env file**
```bash
# Copy from backup
cp /path/to/backup/.env .

# Or recreate manually:
nano .env
# Add your Kite API credentials
```

**Step 4: Follow Setup Guide**
```bash
# Open the setup guide
cat NEW_MAC_SETUP.md

# Follow all steps in NEW_MAC_SETUP.md
```

---

## 📋 Transfer Methods

**Option 1: External Drive (Fastest)**
```bash
# On old Mac:
cp -r ~/Desktop/kite_app/data/hdf5 /Volumes/ExternalDrive/
cp ~/Desktop/kite_app/.env /Volumes/ExternalDrive/

# On new Mac:
cp -r /Volumes/ExternalDrive/hdf5 ~/Desktop/kite_app/data/
cp /Volumes/ExternalDrive/.env ~/Desktop/kite_app/
```

**Option 2: AirDrop**
- Drag and drop the `data/hdf5` folder
- Drag and drop the `.env` file

**Option 3: iCloud/Dropbox**
```bash
# Upload to cloud from old Mac
# Download to new Mac
```

**Option 4: Rsync over Network** (if both Macs on same network)
```bash
# On new Mac:
rsync -avz --progress oldmac.local:~/Desktop/kite_app/data/hdf5/ ~/Desktop/kite_app/data/hdf5/
rsync -avz --progress oldmac.local:~/Desktop/kite_app/.env ~/Desktop/kite_app/
```

---

## 🔍 Verification

After transfer, verify on new Mac:

```bash
cd ~/Desktop/kite_app

# Check HDF5 files
ls -lh data/hdf5/
# Should show 3 .h5 files (~2.4 GB total)

# Check .env file
cat .env
# Should show your API keys

# Test HDF5 files can be read
python3 << 'EOF'
import h5py
import hdf5plugin

file = h5py.File('data/hdf5/EQUITY_repacked.h5', 'r')
print(f"✓ File opened successfully")
print(f"✓ Keys: {list(file.keys())}")
file.close()
EOF
```

---

## 📊 What's in the HDF5 Files

**Data Summary:**
- Total rows: 233,478,666
- Symbols: ~1,230 unique
- Exchanges: NSE, BSE
- Intervals: day, 60minute, 15minute, 5minute, 3minute, minute
- Date range: 2017-2025 (approx)
- File format: HDF5 with Blosc:LZ4 compression

**File Details:**
- `EQUITY_repacked.h5` - Main file (optimized, 1.35 GB)
- `EQUITY_chunk1.h5` - Additional data chunk 1
- `EQUITY_chunk2.h5` - Additional data chunk 2

---

## ⚠️ Important Notes

**DO NOT TRANSFER:**
- ❌ `data/hdf5/EQUITY.h5` (old unoptimized file - 7.25 GB)
- ❌ `logs/` directory (will be recreated)
- ❌ `exports/` directory (temporary exports)
- ❌ `__pycache__/` (Python cache)
- ❌ `.git/` (will be cloned fresh)

**MUST TRANSFER:**
- ✅ The 3 HDF5 files (2.4 GB total)
- ✅ `.env` file (API keys)

---

## 🎯 Quick Start After Transfer

```bash
cd ~/Desktop/kite_app

# 1. Install dependencies
brew install questdb python@3.11
pip3 install pandas numpy h5py hdf5plugin requests psycopg2-binary tqdm

# 2. Configure QuestDB (see NEW_MAC_SETUP.md)

# 3. Start QuestDB
brew services start questdb

# 4. Create table
python3 -c "
from quest.client import QuestDBClient
from quest.table_functions import QuestDBSchemaManager
from quest.config import TableNames
client = QuestDBClient()
manager = QuestDBSchemaManager(client)
manager.create_table(TableNames.OHLCV_EQUITY)
client.close()
"

# 5. Run migration
python3 scripts/migrate_hdf5_to_questdb.py --batch-size=25000
```

---

## 📞 Need Help?

If you encounter issues:
1. Check `NEW_MAC_SETUP.md` for detailed instructions
2. Check logs in `logs/` directory
3. Verify HDF5 files transferred correctly
4. Verify QuestDB is running: `brew services list`

---

**Repository:** https://github.com/tamod2508/Analysis-and-Trading-App

**Last Updated:** 2025-10-14

Good luck with the new Mac! 🚀
