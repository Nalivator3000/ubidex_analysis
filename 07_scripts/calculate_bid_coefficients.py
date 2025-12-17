import pandas as pd
import sqlite3
import sys
import io
import re

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("РАСЧЕТ КОЭФФИЦИЕНТОВ ДЛЯ ЦЕЛЕВОЙ ЦЕНЫ ДЕПОЗИТА")
print("=" * 80)
print()

# Function to extract publisher_id and format
def extract_publisher_id(publisher_str):
    match = re.match(r'\((\d+)\)', str(publisher_str))
    if match:
        return int(match.group(1))
    return None

def extract_format(publisher_str):
    """Extract ad format from publisher name"""
    name_upper = str(publisher_str).upper()

    if 'POP' in name_upper:
        return 'POP'
    elif 'PUSH' in name_upper or 'IN-PAGE' in name_upper or 'INPAGE' in name_upper:
        return 'PUSH'
    elif 'VIDEO' in name_upper:
        return 'VIDEO'
    elif 'BANNER' in name_upper:
        return 'BANNER'
    elif 'NATIVE' in name_upper:
        return 'NATIVE'
    else:
        return 'OTHER'

# Load November spend data
print("1. Загружаю данные по расходам (ноябрь)...")
print()

nov_spend = pd.read_csv('C:/Users/Nalivator3000/Downloads/export (1).csv', skiprows=1)
nov_spend['publisher_id'] = nov_spend['Publisher'].apply(extract_publisher_id)
nov_spend['format'] = nov_spend['Publisher'].apply(extract_format)

# Keep only relevant columns
nov_spend = nov_spend[['publisher_id', 'Publisher', 'format', 'Deposit', 'Spend']].copy()
nov_spend.columns = ['publisher_id', 'publisher_name', 'format', 'deposits_reported', 'spend']

# Remove rows with missing publisher_id
nov_spend = nov_spend.dropna(subset=['publisher_id'])

# Convert to numeric
for col in ['deposits_reported', 'spend']:
    nov_spend[col] = pd.to_numeric(nov_spend[col], errors='coerce').fillna(0)

# Calculate CPA (cost per deposit)
nov_spend['current_cpa'] = (nov_spend['spend'] / nov_spend['deposits_reported'].replace(0, 1)).round(3)

print(f"   Загружено: {len(nov_spend)} паблишеров")
print()

# Filter to PLR/NOR campaigns
print("2. Фильтрация кампаний PLR/NOR и расчет целевых CPA по форматам...")
print()

plr_nor = nov_spend[
    nov_spend['publisher_name'].str.upper().str.contains('PLR|NOR', na=False, regex=True)
].copy()

print(f"   Найдено PLR/NOR кампаний: {len(plr_nor)}")

if len(plr_nor) > 0:
    print()
    print("   PLR/NOR кампании:")
    for idx, row in plr_nor.iterrows():
        pub_id = int(row['publisher_id'])
        name = row['publisher_name']
        fmt = row['format']
        deps = int(row['deposits_reported'])
        spend = row['spend']
        cpa = row['current_cpa']
        print(f"   - Publisher {pub_id} ({fmt}): {name}")
        print(f"     Deposits: {deps:,} | Spend: ${spend:,.0f} | CPA: ${cpa:.3f}")
    print()

# Calculate target CPA for each format separately
formats = ['POP', 'PUSH', 'VIDEO', 'BANNER', 'NATIVE']
target_cpa_by_format = {}

print("=" * 80)
print("ЦЕЛЕВЫЕ CPA ПО ФОРМАТАМ (-30% от PLR/NOR):")
print("=" * 80)
print()

for fmt in formats:
    # Get PLR/NOR campaigns for this format
    plr_nor_fmt = plr_nor[plr_nor['format'] == fmt]

    if len(plr_nor_fmt) > 0 and plr_nor_fmt['deposits_reported'].sum() > 0:
        # Use PLR/NOR average for this format
        avg_cpa = (plr_nor_fmt['spend'].sum() / plr_nor_fmt['deposits_reported'].sum())
        target_cpa = avg_cpa * 0.7
        source = "PLR/NOR"
    else:
        # Use all campaigns average for this format
        all_fmt = nov_spend[nov_spend['format'] == fmt]
        if len(all_fmt) > 0 and all_fmt['deposits_reported'].sum() > 0:
            avg_cpa = (all_fmt['spend'].sum() / all_fmt['deposits_reported'].sum())
            target_cpa = avg_cpa * 0.7
            source = "Все кампании"
        else:
            avg_cpa = 0
            target_cpa = 0
            source = "Нет данных"

    target_cpa_by_format[fmt] = target_cpa

    if target_cpa > 0:
        print(f"{fmt:8s}: ${avg_cpa:.3f} → ${target_cpa:.3f} (-30%) [{source}]")
    else:
        print(f"{fmt:8s}: Нет данных")

print()
print("=" * 80)
print()

# Get FTD/RD stats from database for November
print("3. Загружаю статистику депозитов из базы данных...")
print()

conn = sqlite3.connect('events.db')

query_nov = '''
WITH user_first_deposit_ever AS (
    SELECT
        external_user_id,
        MIN(event_date) as first_deposit_ever
    FROM user_events
    WHERE event_type = 'deposit'
    GROUP BY external_user_id
),
nov_deposits AS (
    SELECT
        e.external_user_id,
        e.publisher_id,
        e.event_date,
        f.first_deposit_ever
    FROM user_events e
    LEFT JOIN user_first_deposit_ever f
        ON e.external_user_id = f.external_user_id
    WHERE e.event_type = 'deposit'
      AND e.event_date >= '2025-11-01 00:00:00'
      AND e.event_date <= '2025-11-30 23:59:59'
)
SELECT
    publisher_id,
    COUNT(*) as total_deps
FROM nov_deposits
GROUP BY publisher_id
'''

nov_db_stats = pd.read_sql(query_nov, conn)
conn.close()

print(f"   Загружено: {len(nov_db_stats)} паблишеров")
print()

# Merge data
print("4. Расчет коэффициентов...")
print()

merged = nov_db_stats.merge(
    nov_spend[['publisher_id', 'publisher_name', 'format', 'spend', 'current_cpa']],
    on='publisher_id',
    how='left'
)

# Fill missing values
merged['format'] = merged['format'].fillna('OTHER')
merged['spend'] = merged['spend'].fillna(0)
merged['current_cpa'] = merged['current_cpa'].fillna(0)

# Calculate coefficient based on format-specific target CPA
# Coefficient = Target CPA (for format) / Current CPA
# If coefficient > 1: можно увеличить ставку (текущая CPA ниже целевой)
# If coefficient < 1: нужно уменьшить ставку (текущая CPA выше целевой)

def calculate_coefficient(row):
    fmt = row['format']
    target = target_cpa_by_format.get(fmt, 0)
    current = row['current_cpa']

    if current == 0 or target == 0:
        return 1.0

    coef = target / current
    # Cap coefficient at reasonable values
    return max(0.1, min(3.0, coef))

merged['target_cpa_format'] = merged['format'].map(target_cpa_by_format).fillna(0)
merged['coefficient'] = merged.apply(calculate_coefficient, axis=1).round(3)

# Calculate recommended change percentage
merged['change_pct'] = ((merged['coefficient'] - 1) * 100).round(1)

# Filter to publishers with significant spend
significant = merged[merged['spend'] > 50].copy()
significant = significant.sort_values('spend', ascending=False)

print("=" * 80)
print("КОЭФФИЦИЕНТЫ ПО ВСЕМ ПАБЛИШЕРАМ:")
print("=" * 80)
print()
print("Pub ID | Publisher Name                    | Format | Target CPA | Current CPA | Coef  | Change  | Action")
print("-" * 110)

for idx, row in significant.head(50).iterrows():
    pub_id = int(row['publisher_id'])
    name = str(row['publisher_name'])[:30] if pd.notna(row['publisher_name']) else f"Publisher {pub_id}"
    fmt = row['format']
    target = row['target_cpa_format']
    current_cpa = row['current_cpa']
    coef = row['coefficient']
    change = row['change_pct']

    # Determine action
    if coef >= 1.3:
        action = "УВЕЛИЧИТЬ ставку"
    elif coef >= 1.1:
        action = "Увеличить немного"
    elif coef >= 0.9:
        action = "Оставить"
    elif coef >= 0.7:
        action = "Снизить немного"
    else:
        action = "СНИЗИТЬ ставку"

    print(f"{pub_id:6d} | {name:33s} | {fmt:6s} | ${target:8.3f} | ${current_cpa:9.3f} | {coef:5.2f} | {change:+6.1f}% | {action}")

print()
print("=" * 80)
print()

# Group by format
print("КОЭФФИЦИЕНТЫ ПО ФОРМАТАМ:")
print("=" * 80)
print()

formats = ['POP', 'PUSH', 'VIDEO', 'BANNER', 'NATIVE']

for fmt in formats:
    format_data = significant[significant['format'] == fmt].copy()

    if len(format_data) == 0:
        continue

    # Filter out organic
    format_data = format_data[format_data['publisher_id'] != 0]

    if len(format_data) == 0:
        continue

    print(f"ФОРМАТ: {fmt}")
    print("-" * 80)

    # Get target CPA for this format
    target_cpa_fmt = target_cpa_by_format.get(fmt, 0)

    # Calculate format average
    format_avg_cpa = (format_data['spend'].sum() / format_data['total_deps'].sum())

    print(f"Целевая CPA ({fmt}):   ${target_cpa_fmt:.3f}")
    print(f"Средняя CPA формата:   ${format_avg_cpa:.3f}")
    print()

    # Sort by coefficient descending
    format_data_sorted = format_data.sort_values('coefficient', ascending=False)

    print("Pub ID | Publisher Name                    | Current CPA | Coef  | Change    | Action")
    print("-" * 95)

    for idx, row in format_data_sorted.iterrows():
        pub_id = int(row['publisher_id'])
        name = str(row['publisher_name'])[:30] if pd.notna(row['publisher_name']) else f"Publisher {pub_id}"
        current_cpa = row['current_cpa']
        coef = row['coefficient']
        change = row['change_pct']

        # Determine action
        if coef >= 1.3:
            action = "УВЕЛИЧИТЬ +30%+"
        elif coef >= 1.1:
            action = "Увеличить +10-30%"
        elif coef >= 0.9:
            action = "Оставить"
        elif coef >= 0.7:
            action = "Снизить -10-30%"
        else:
            action = "СНИЗИТЬ -30%+"

        print(f"{pub_id:6d} | {name:33s} | ${current_cpa:9.3f} | {coef:5.2f} | {change:+8.1f}% | {action}")

    print()
    print("=" * 80)
    print()

# Save results
merged.to_csv('publishers_bid_coefficients.csv', index=False)

print("Сохранено:")
print("  - publishers_bid_coefficients.csv")
print()

# Summary statistics
print("=" * 80)
print("ИТОГОВАЯ СТАТИСТИКА ПО ФОРМАТАМ:")
print("=" * 80)
print()

print("Format  | Целевая CPA | Средняя CPA | Изменение | Паблишеров")
print("-" * 70)

for fmt in ['POP', 'PUSH', 'VIDEO', 'BANNER', 'NATIVE']:
    format_data = significant[(significant['format'] == fmt) & (significant['publisher_id'] != 0)]

    if len(format_data) == 0:
        continue

    target_cpa_fmt = target_cpa_by_format.get(fmt, 0)
    format_avg_cpa = (format_data['spend'].sum() / format_data['total_deps'].sum()) if format_data['total_deps'].sum() > 0 else 0
    change = ((target_cpa_fmt / format_avg_cpa - 1) * 100) if format_avg_cpa > 0 else 0
    count = len(format_data)

    print(f"{fmt:7s} | ${target_cpa_fmt:10.3f} | ${format_avg_cpa:10.3f} | {change:+8.1f}% | {count:10d}")

print()
print("=" * 80)
print()

# Count recommendations by format
print("РАСПРЕДЕЛЕНИЕ РЕКОМЕНДАЦИЙ ПО ФОРМАТАМ:")
print("=" * 80)
print()

for fmt in ['POP', 'PUSH', 'VIDEO', 'BANNER', 'NATIVE']:
    format_data = significant[(significant['format'] == fmt) & (significant['publisher_id'] != 0)]

    if len(format_data) == 0:
        continue

    increase_strong = len(format_data[format_data['coefficient'] >= 1.3])
    increase_light = len(format_data[(format_data['coefficient'] >= 1.1) & (format_data['coefficient'] < 1.3)])
    maintain = len(format_data[(format_data['coefficient'] >= 0.9) & (format_data['coefficient'] < 1.1)])
    decrease_light = len(format_data[(format_data['coefficient'] >= 0.7) & (format_data['coefficient'] < 0.9)])
    decrease_strong = len(format_data[format_data['coefficient'] < 0.7])

    print(f"{fmt}:")
    print(f"  УВЕЛИЧИТЬ ставку (+30%+):     {increase_strong}")
    print(f"  Увеличить немного (+10-30%):  {increase_light}")
    print(f"  Оставить без изменений:       {maintain}")
    print(f"  Снизить немного (-10-30%):    {decrease_light}")
    print(f"  СНИЗИТЬ ставку (-30%+):       {decrease_strong}")
    print()

print("=" * 80)
print()

# Top to increase by format
print("TOP ДЛЯ УВЕЛИЧЕНИЯ СТАВКИ ПО ФОРМАТАМ (самые эффективные):")
print("=" * 80)
print()

for fmt in ['POP', 'PUSH', 'VIDEO', 'BANNER', 'NATIVE']:
    format_data = significant[(significant['format'] == fmt) & (significant['publisher_id'] != 0)]

    if len(format_data) == 0:
        continue

    # Get top 5 to increase for this format
    top_increase_fmt = format_data.nlargest(min(5, len(format_data)), 'coefficient')

    if len(top_increase_fmt[top_increase_fmt['coefficient'] >= 1.1]) == 0:
        continue

    print(f"{fmt}:")
    for idx, row in top_increase_fmt.iterrows():
        if row['coefficient'] < 1.1:
            continue
        pub_id = int(row['publisher_id'])
        name = str(row['publisher_name'])[:40] if pd.notna(row['publisher_name']) else f"Publisher {pub_id}"
        coef = row['coefficient']
        change = row['change_pct']
        current_cpa = row['current_cpa']
        target_cpa = row['target_cpa_format']
        print(f"  Pub {pub_id:3d}: {name:40s}")
        print(f"           Coef: {coef:.2f} ({change:+6.1f}%) | Current: ${current_cpa:.3f} → Target: ${target_cpa:.3f}")
    print()

print("=" * 80)
print()

# Top to decrease by format
print("TOP ДЛЯ СНИЖЕНИЯ СТАВКИ ПО ФОРМАТАМ (самые дорогие):")
print("=" * 80)
print()

for fmt in ['POP', 'PUSH', 'VIDEO', 'BANNER', 'NATIVE']:
    format_data = significant[(significant['format'] == fmt) & (significant['publisher_id'] != 0)]

    if len(format_data) == 0:
        continue

    # Get top 5 to decrease for this format
    top_decrease_fmt = format_data.nsmallest(min(5, len(format_data)), 'coefficient')

    if len(top_decrease_fmt[top_decrease_fmt['coefficient'] < 0.9]) == 0:
        continue

    print(f"{fmt}:")
    for idx, row in top_decrease_fmt.iterrows():
        if row['coefficient'] >= 0.9:
            continue
        pub_id = int(row['publisher_id'])
        name = str(row['publisher_name'])[:40] if pd.notna(row['publisher_name']) else f"Publisher {pub_id}"
        coef = row['coefficient']
        change = row['change_pct']
        current_cpa = row['current_cpa']
        target_cpa = row['target_cpa_format']
        print(f"  Pub {pub_id:3d}: {name:40s}")
        print(f"           Coef: {coef:.2f} ({change:+6.1f}%) | Current: ${current_cpa:.3f} → Target: ${target_cpa:.3f}")
    print()

print()
print("=" * 80)
print()
print("ИНСТРУКЦИЯ ПО ПРИМЕНЕНИЮ:")
print("-" * 80)
print("1. Найдите паблишера в списке")
print("2. Умножьте текущую ставку на коэффициент")
print("3. Установите новую ставку")
print()
print("Пример:")
print("  Текущая ставка: $1.00")
print("  Коэффициент: 1.50")
print("  Новая ставка: $1.00 × 1.50 = $1.50")
print()
print("=" * 80)
