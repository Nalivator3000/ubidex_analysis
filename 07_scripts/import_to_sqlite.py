"""
Import CSV to SQLite database (no size limits!)
"""

import pandas as pd
import sqlite3
from datetime import datetime

CSV_FILE = r"C:\Users\Nalivator3000\Downloads\pixels-019b0312-fc43-7d21-b9c4-4f4b98deaa2a-12-09-2025-12-25-34-01.csv"
SQLITE_DB = r"C:\Users\Nalivator3000\superset-data-import\events.db"
CHUNK_SIZE = 50000
SKIP_ROWS = 11100000  # Skip first 11.1M rows (already imported)

COLUMNS_TO_KEEP = [
    'ID', 'EXTERNAL_USER_ID', 'UBIDEX_ID', 'TYPE', 'PIXEL_TS',
    'PUBLISHER_ID', 'CAMPAIGN_ID', 'SUB_ID', 'AFFILIATE_ID',
    'DEPOSIT_AMOUNT', 'CURRENCY', 'CONVERTED_AMOUNT', 'CONVERTED_CURRENCY',
    'WEBSITE', 'COUNTRY', 'TRANSACTION_ID'
]

def create_table(conn):
    """Create table and indexes"""
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_events (
        event_id TEXT PRIMARY KEY,
        external_user_id TEXT,
        ubidex_id TEXT,
        event_type TEXT NOT NULL,
        event_date TIMESTAMP NOT NULL,
        publisher_id INTEGER,
        campaign_id INTEGER,
        sub_id TEXT,
        affiliate_id TEXT,
        deposit_amount REAL,
        currency TEXT,
        converted_amount REAL,
        converted_currency TEXT,
        website TEXT,
        country TEXT,
        transaction_id TEXT
    )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_external_user_id ON user_events(external_user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON user_events(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_date ON user_events(event_date)")

    conn.commit()
    print("OK Table created!")

def process_chunk(chunk_df):
    """Process chunk"""
    chunk_df = chunk_df[COLUMNS_TO_KEEP].copy()
    chunk_df.columns = [
        'event_id', 'external_user_id', 'ubidex_id', 'event_type',
        'event_date', 'publisher_id', 'campaign_id', 'sub_id',
        'affiliate_id', 'deposit_amount', 'currency', 'converted_amount',
        'converted_currency', 'website', 'country', 'transaction_id'
    ]

    # Fix dates
    chunk_df['event_date'] = chunk_df['event_date'].str.replace(' UTC', '', regex=False)
    chunk_df['event_date'] = pd.to_datetime(chunk_df['event_date'], format='%Y-%m-%d %H:%M:%S %z', errors='coerce')
    chunk_df = chunk_df.dropna(subset=['event_date'])

    # Convert timestamp to string for SQLite
    chunk_df['event_date'] = chunk_df['event_date'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Convert numeric (but keep ubidex_id as string - it's too large for SQLite INTEGER)
    chunk_df['publisher_id'] = pd.to_numeric(chunk_df['publisher_id'], errors='coerce').astype('Int64')
    chunk_df['campaign_id'] = pd.to_numeric(chunk_df['campaign_id'], errors='coerce').astype('Int64')
    chunk_df['deposit_amount'] = pd.to_numeric(chunk_df['deposit_amount'], errors='coerce')
    chunk_df['converted_amount'] = pd.to_numeric(chunk_df['converted_amount'], errors='coerce')

    # Convert ubidex_id to string to avoid overflow
    chunk_df['ubidex_id'] = chunk_df['ubidex_id'].astype(str)

    # Replace NaN with None for SQL NULL
    chunk_df = chunk_df.where(pd.notnull(chunk_df), None)

    return chunk_df

print("=" * 80)
print("CSV to SQLite Import (RESUME)")
print("=" * 80)
print(f"\nCSV File: {CSV_FILE}")
print(f"SQLite DB: {SQLITE_DB}")
print(f"Chunk size: {CHUNK_SIZE:,}")
print(f"Skipping first: {SKIP_ROWS:,} rows (already imported)")

# Connect to SQLite
print("\nConnecting to SQLite...")
conn = sqlite3.connect(SQLITE_DB)
print("OK Connected!")

# Create table
create_table(conn)

# Check if we have existing data
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM user_events")
existing_count = cursor.fetchone()[0]
print(f"\nExisting rows: {existing_count:,}")

if existing_count > 0:
    print(f"\nDatabase already has {existing_count:,} rows. Continuing with import...")

print("\nStarting import...")
print("Progress updates every 100k rows.\n")

rows_processed = SKIP_ROWS  # Start counting from where we left off
rows_inserted = 0
start_time = datetime.now()
total_rows = 21583338

try:
    for chunk_num, chunk in enumerate(pd.read_csv(
        CSV_FILE,
        chunksize=CHUNK_SIZE,
        skiprows=range(1, SKIP_ROWS + 1),  # Skip header row 0 + data rows 1 to SKIP_ROWS
        low_memory=False
    ), 1):
        processed_chunk = process_chunk(chunk)

        # Insert into SQLite with INSERT OR IGNORE to skip duplicates
        cursor = conn.cursor()
        data = [tuple(row) for row in processed_chunk.values]
        cursor.executemany("""
            INSERT OR IGNORE INTO user_events (
                event_id, external_user_id, ubidex_id, event_type, event_date,
                publisher_id, campaign_id, sub_id, affiliate_id,
                deposit_amount, currency, converted_amount, converted_currency,
                website, country, transaction_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        conn.commit()

        rows_processed += len(chunk)
        rows_inserted += len(processed_chunk)

        if rows_processed % 100000 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = (rows_processed - SKIP_ROWS) / elapsed
            remaining = total_rows - rows_processed
            eta = remaining / rate / 60 if rate > 0 else 0

            print(f"Progress: {rows_processed:,} / {total_rows:,} ({rows_processed/total_rows*100:.1f}%) | "
                  f"Rate: {rate:.0f} rows/sec | ETA: {eta:.0f} min")

    elapsed_total = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 80)
    print("OK Import completed!")
    print("=" * 80)
    print(f"New rows processed: {rows_processed - SKIP_ROWS:,}")
    print(f"New rows inserted: {rows_inserted:,}")
    print(f"Time elapsed: {elapsed_total/60:.1f} minutes")
    print(f"Average rate: {(rows_processed - SKIP_ROWS)/elapsed_total:.0f} rows/sec")

    # Final count
    cursor.execute("SELECT COUNT(*) FROM user_events")
    final_count = cursor.fetchone()[0]
    print(f"\nFinal row count: {final_count:,}")

    cursor.execute("SELECT event_type, COUNT(*) FROM user_events GROUP BY event_type")
    types = cursor.fetchall()
    print("\nEvent types:")
    for event_type, count in types:
        print(f"  {event_type}: {count:,}")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
    print("\nDatabase connection closed.")
