import pandas as pd
import sqlite3
import sys
import io
import re

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("ИНТЕГРАЦИЯ SPEND С FTD/RD СТАТИСТИКОЙ")
print("=" * 80)
print()

# Function to extract publisher_id from format "(ID) Name"
def extract_publisher_id(publisher_str):
    match = re.match(r'\((\d+)\)', str(publisher_str))
    if match:
        return int(match.group(1))
    return None

# Load November spend data
print("1. Загружаю данные по расходам...")
print()

nov_spend = pd.read_csv('C:/Users/Nalivator3000/Downloads/export (1).csv', skiprows=1)
oct_spend = pd.read_csv('C:/Users/Nalivator3000/Downloads/export (2).csv', skiprows=1)

# Extract publisher IDs
nov_spend['publisher_id'] = nov_spend['Publisher'].apply(extract_publisher_id)
oct_spend['publisher_id'] = oct_spend['Publisher'].apply(extract_publisher_id)

# Keep only relevant columns and rename
nov_spend = nov_spend[['publisher_id', 'Publisher', 'FTD', 'Deposit', 'Spend']].copy()
nov_spend.columns = ['publisher_id', 'publisher_name', 'ftd_reported', 'deposit_reported', 'spend_nov']

oct_spend = oct_spend[['publisher_id', 'Publisher', 'FTD', 'Deposit', 'Spend']].copy()
oct_spend.columns = ['publisher_id', 'publisher_name', 'ftd_reported', 'deposit_reported', 'spend_oct']

# Remove rows with missing publisher_id
nov_spend = nov_spend.dropna(subset=['publisher_id'])
oct_spend = oct_spend.dropna(subset=['publisher_id'])

# Convert to numeric
for col in ['ftd_reported', 'deposit_reported', 'spend_nov']:
    nov_spend[col] = pd.to_numeric(nov_spend[col], errors='coerce').fillna(0)

for col in ['ftd_reported', 'deposit_reported', 'spend_oct']:
    oct_spend[col] = pd.to_numeric(oct_spend[col], errors='coerce').fillna(0)

print(f"   November: {len(nov_spend)} паблишеров")
print(f"   October:  {len(oct_spend)} паблишеров")
print()

# Get FTD/RD stats from database for November
print("2. Загружаю FTD/RD статистику из базы данных...")
print()

conn = sqlite3.connect('events.db')

# November FTD/RD
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
    COUNT(*) as total_deps,
    SUM(CASE WHEN event_date = first_deposit_ever THEN 1 ELSE 0 END) as ftd_db,
    SUM(CASE WHEN event_date != first_deposit_ever THEN 1 ELSE 0 END) as rd_db
FROM nov_deposits
GROUP BY publisher_id
'''

nov_db_stats = pd.read_sql(query_nov, conn)

# October FTD/RD
query_oct = '''
WITH user_first_deposit_ever AS (
    SELECT
        external_user_id,
        MIN(event_date) as first_deposit_ever
    FROM user_events
    WHERE event_type = 'deposit'
    GROUP BY external_user_id
),
oct_deposits AS (
    SELECT
        e.external_user_id,
        e.publisher_id,
        e.event_date,
        f.first_deposit_ever
    FROM user_events e
    LEFT JOIN user_first_deposit_ever f
        ON e.external_user_id = f.external_user_id
    WHERE e.event_type = 'deposit'
      AND e.event_date >= '2025-10-01 00:00:00'
      AND e.event_date <= '2025-10-31 23:59:59'
)
SELECT
    publisher_id,
    COUNT(*) as total_deps,
    SUM(CASE WHEN event_date = first_deposit_ever THEN 1 ELSE 0 END) as ftd_db,
    SUM(CASE WHEN event_date != first_deposit_ever THEN 1 ELSE 0 END) as rd_db
FROM oct_deposits
GROUP BY publisher_id
'''

oct_db_stats = pd.read_sql(query_oct, conn)
conn.close()

print(f"   November: {len(nov_db_stats)} паблишеров с депозитами")
print(f"   October:  {len(oct_db_stats)} паблишеров с депозитами")
print()

# Merge November data
print("3. Объединяю данные...")
print()

nov_merged = nov_db_stats.merge(
    nov_spend[['publisher_id', 'publisher_name', 'spend_nov', 'ftd_reported', 'deposit_reported']],
    on='publisher_id',
    how='left'
)

oct_merged = oct_db_stats.merge(
    oct_spend[['publisher_id', 'publisher_name', 'spend_oct', 'ftd_reported', 'deposit_reported']],
    on='publisher_id',
    how='left'
)

# Calculate CPAs
nov_merged['ftd_cpa'] = (nov_merged['spend_nov'] / nov_merged['ftd_db'].replace(0, 1)).round(2)
nov_merged['rd_cpa'] = (nov_merged['spend_nov'] / nov_merged['rd_db'].replace(0, 1)).round(4)
nov_merged['total_cpa'] = (nov_merged['spend_nov'] / nov_merged['total_deps'].replace(0, 1)).round(3)
nov_merged['rd_rate'] = (nov_merged['rd_db'] / nov_merged['total_deps'] * 100).round(1)

oct_merged['ftd_cpa'] = (oct_merged['spend_oct'] / oct_merged['ftd_db'].replace(0, 1)).round(2)
oct_merged['rd_cpa'] = (oct_merged['spend_oct'] / oct_merged['rd_db'].replace(0, 1)).round(4)
oct_merged['total_cpa'] = (oct_merged['spend_oct'] / oct_merged['total_deps'].replace(0, 1)).round(3)
oct_merged['rd_rate'] = (oct_merged['rd_db'] / oct_merged['total_deps'] * 100).round(1)

# Full month-to-month comparison
print("4. Создаю сравнительный анализ Октябрь vs Ноябрь...")
print()

comparison = nov_merged.merge(
    oct_merged[['publisher_id', 'total_deps', 'ftd_db', 'rd_db', 'spend_oct', 'ftd_cpa', 'rd_cpa', 'total_cpa', 'rd_rate']],
    on='publisher_id',
    how='outer',
    suffixes=('_nov', '_oct')
).fillna(0)

# Calculate changes
comparison['spend_change'] = comparison['spend_nov'] - comparison['spend_oct']
comparison['spend_change_pct'] = ((comparison['spend_nov'] / comparison['spend_oct'].replace(0, 1) - 1) * 100).round(1)
comparison['deps_change'] = comparison['total_deps_nov'] - comparison['total_deps_oct']
comparison['deps_change_pct'] = ((comparison['total_deps_nov'] / comparison['total_deps_oct'].replace(0, 1) - 1) * 100).round(1)
comparison['ftd_cpa_change'] = comparison['ftd_cpa_nov'] - comparison['ftd_cpa_oct']
comparison['rd_cpa_change'] = comparison['rd_cpa_nov'] - comparison['rd_cpa_oct']

# Filter to publishers with significant spend
significant = comparison[comparison['spend_nov'] > 100].copy()
significant = significant.sort_values('spend_nov', ascending=False)

print("=" * 80)
print("ТОП-30 ПАБЛИШЕРОВ ПО РАСХОДАМ (НОЯБРЬ):")
print("=" * 80)
print()
print("Pub ID | Spend Nov | Deps Nov | Total CPA | FTD CPA | RD CPA   | RD Rate")
print("-" * 80)

for idx, row in significant.head(30).iterrows():
    pub_id = int(row['publisher_id'])
    spend = row['spend_nov']
    deps = int(row['total_deps_nov'])
    total_cpa = row['total_cpa_nov']
    ftd_cpa = row['ftd_cpa_nov']
    rd_cpa = row['rd_cpa_nov']
    rd_rate = row['rd_rate_nov']

    print(f"{pub_id:6d} | ${spend:9,.0f} | {deps:8,d} | ${total_cpa:7.3f} | ${ftd_cpa:6.2f} | ${rd_cpa:7.4f} | {rd_rate:5.1f}%")

print()
print("=" * 80)
print()

# Performance analysis
print("5. АНАЛИЗ ЭФФЕКТИВНОСТИ И РЕКОМЕНДАЦИИ:")
print("=" * 80)
print()

recommendations = []

# Calculate overall averages
paid_pubs = significant[significant['publisher_id'] != 0]
avg_ftd_cpa_nov = (paid_pubs['spend_nov'].sum() / paid_pubs['ftd_db_nov'].sum())
avg_rd_cpa_nov = (paid_pubs['spend_nov'].sum() / paid_pubs['rd_db_nov'].sum())
avg_total_cpa_nov = (paid_pubs['spend_nov'].sum() / paid_pubs['total_deps_nov'].sum())

print(f"СРЕДНИЕ ПОКАЗАТЕЛИ (платные паблишеры, ноябрь):")
print(f"  Средний Total CPA: ${avg_total_cpa_nov:.3f}")
print(f"  Средний FTD CPA:   ${avg_ftd_cpa_nov:.2f}")
print(f"  Средний RD CPA:    ${avg_rd_cpa_nov:.4f}")
print()

for idx, row in significant.iterrows():
    pub_id = int(row['publisher_id'])

    # Skip organic
    if pub_id == 0:
        continue

    # Skip if insufficient data
    if row['spend_nov'] < 100 or row['total_deps_nov'] < 100:
        continue

    # Metrics
    ftd_cpa = row['ftd_cpa_nov']
    rd_cpa = row['rd_cpa_nov']
    total_cpa = row['total_cpa_nov']
    deps_nov = int(row['total_deps_nov'])
    spend_nov = row['spend_nov']

    # Changes from October
    ftd_cpa_change = row['ftd_cpa_change']
    rd_cpa_change = row['rd_cpa_change']
    deps_change_pct = row['deps_change_pct']

    # Score based on CPA efficiency relative to average
    ftd_efficiency = (ftd_cpa / avg_ftd_cpa_nov - 1) * 100  # negative = better
    rd_efficiency = (rd_cpa / avg_rd_cpa_nov - 1) * 100     # negative = better
    total_efficiency = (total_cpa / avg_total_cpa_nov - 1) * 100  # negative = better

    # Combined efficiency score (weight total CPA more heavily)
    efficiency_score = (total_efficiency * 3 + ftd_efficiency + rd_efficiency) / 5

    # Determine recommendation
    if efficiency_score <= -20 and deps_nov >= 5000:
        recommendation = "УВЕЛИЧИТЬ ставку +30-50%"
        reason = f"Отличная эффективность: CPA на {abs(efficiency_score):.0f}% ниже среднего"
        priority = "HIGH"
    elif efficiency_score <= -10 and deps_nov >= 2000:
        recommendation = "УВЕЛИЧИТЬ ставку +15-25%"
        reason = f"Хорошая эффективность: CPA на {abs(efficiency_score):.0f}% ниже среднего"
        priority = "MEDIUM"
    elif efficiency_score >= 20 and deps_nov >= 5000:
        recommendation = "СНИЗИТЬ ставку -30-50%"
        reason = f"Низкая эффективность: CPA на {efficiency_score:.0f}% выше среднего"
        priority = "HIGH"
    elif efficiency_score >= 10 and deps_nov >= 2000:
        recommendation = "СНИЗИТЬ ставку -15-25%"
        reason = f"Низкая эффективность: CPA на {efficiency_score:.0f}% выше среднего"
        priority = "MEDIUM"
    else:
        recommendation = "ОСТАВИТЬ ставку"
        reason = f"Близко к среднему (CPA {efficiency_score:+.0f}%)"
        priority = "LOW"

    recommendations.append({
        'publisher_id': pub_id,
        'publisher_name': row['publisher_name'],
        'spend_nov': spend_nov,
        'deps_nov': deps_nov,
        'total_cpa_nov': total_cpa,
        'ftd_cpa_nov': ftd_cpa,
        'rd_cpa_nov': rd_cpa,
        'efficiency_score': efficiency_score,
        'deps_change_pct': deps_change_pct,
        'ftd_cpa_change': ftd_cpa_change,
        'rd_cpa_change': rd_cpa_change,
        'recommendation': recommendation,
        'reason': reason,
        'priority': priority
    })

rec_df = pd.DataFrame(recommendations)
rec_df = rec_df.sort_values('efficiency_score', ascending=True)

# Print recommendations by priority
for priority in ['HIGH', 'MEDIUM']:
    priority_recs = rec_df[rec_df['priority'] == priority]

    if len(priority_recs) == 0:
        continue

    print(f"ПРИОРИТЕТ: {priority}")
    print("-" * 80)

    for idx, row in priority_recs.iterrows():
        pub_id = int(row['publisher_id'])
        name = str(row['publisher_name'])[:40]
        spend = row['spend_nov']
        deps = int(row['deps_nov'])
        total_cpa = row['total_cpa_nov']
        ftd_cpa = row['ftd_cpa_nov']
        rd_cpa = row['rd_cpa_nov']
        score = row['efficiency_score']
        rec = row['recommendation']
        reason = row['reason']

        print(f"Publisher {pub_id:3d} ({name})")
        print(f"  Spend: ${spend:,.0f} | Deps: {deps:,d} | Total CPA: ${total_cpa:.3f}")
        print(f"  FTD CPA: ${ftd_cpa:.2f} | RD CPA: ${rd_cpa:.4f}")
        print(f"  Efficiency Score: {score:+.1f}%")
        print(f"  => {rec}")
        print(f"     {reason}")
        print()

print("=" * 80)
print()

# Save results
nov_merged.to_csv('publishers_nov_spend_ftd_rd.csv', index=False)
oct_merged.to_csv('publishers_oct_spend_ftd_rd.csv', index=False)
comparison.to_csv('publishers_oct_vs_nov_spend_comparison.csv', index=False)
rec_df.to_csv('publishers_spend_based_recommendations.csv', index=False)

print("Сохранено:")
print("  - publishers_nov_spend_ftd_rd.csv (ноябрь с расходами)")
print("  - publishers_oct_spend_ftd_rd.csv (октябрь с расходами)")
print("  - publishers_oct_vs_nov_spend_comparison.csv (сравнение)")
print("  - publishers_spend_based_recommendations.csv (рекомендации)")
print()

# Summary statistics
print("=" * 80)
print("ИТОГОВАЯ СТАТИСТИКА:")
print("=" * 80)
print()

total_spend_nov = paid_pubs['spend_nov'].sum()
total_spend_oct = paid_pubs['spend_oct'].sum()
total_deps_nov = int(paid_pubs['total_deps_nov'].sum())
total_deps_oct = int(paid_pubs['total_deps_oct'].sum())
total_ftd_nov = int(paid_pubs['ftd_db_nov'].sum())
total_ftd_oct = int(paid_pubs['ftd_db_oct'].sum())
total_rd_nov = int(paid_pubs['rd_db_nov'].sum())
total_rd_oct = int(paid_pubs['rd_db_oct'].sum())

print(f"НОЯБРЬ:")
print(f"  Расходы:        ${total_spend_nov:,.0f}")
print(f"  Депозиты:       {total_deps_nov:,}")
print(f"  FTD:            {total_ftd_nov:,}")
print(f"  RD:             {total_rd_nov:,}")
print(f"  Avg Total CPA:  ${avg_total_cpa_nov:.3f}")
print(f"  Avg FTD CPA:    ${avg_ftd_cpa_nov:.2f}")
print(f"  Avg RD CPA:     ${avg_rd_cpa_nov:.4f}")
print()

print(f"ОКТЯБРЬ:")
print(f"  Расходы:        ${total_spend_oct:,.0f}")
print(f"  Депозиты:       {total_deps_oct:,}")
print(f"  FTD:            {total_ftd_oct:,}")
print(f"  RD:             {total_rd_oct:,}")
print()

print(f"ИЗМЕНЕНИЕ:")
print(f"  Расходы:        {total_spend_nov-total_spend_oct:+,.0f} ({(total_spend_nov/total_spend_oct-1)*100:+.1f}%)")
print(f"  Депозиты:       {total_deps_nov-total_deps_oct:+,d} ({(total_deps_nov/total_deps_oct-1)*100:+.1f}%)")
print(f"  FTD:            {total_ftd_nov-total_ftd_oct:+,d} ({(total_ftd_nov/total_ftd_oct-1)*100:+.1f}%)")
print(f"  RD:             {total_rd_nov-total_rd_oct:+,d} ({(total_rd_nov/total_rd_oct-1)*100:+.1f}%)")
print()

# Recommendation counts
increase_high = len(rec_df[(rec_df['recommendation'].str.contains('УВЕЛИЧИТЬ')) & (rec_df['priority'] == 'HIGH')])
increase_med = len(rec_df[(rec_df['recommendation'].str.contains('УВЕЛИЧИТЬ')) & (rec_df['priority'] == 'MEDIUM')])
decrease_high = len(rec_df[(rec_df['recommendation'].str.contains('СНИЗИТЬ')) & (rec_df['priority'] == 'HIGH')])
decrease_med = len(rec_df[(rec_df['recommendation'].str.contains('СНИЗИТЬ')) & (rec_df['priority'] == 'MEDIUM')])
maintain = len(rec_df[rec_df['recommendation'] == 'ОСТАВИТЬ ставку'])

print(f"РЕКОМЕНДАЦИИ:")
print(f"  Увеличить ставку (высокий приоритет):  {increase_high}")
print(f"  Увеличить ставку (средний приоритет):  {increase_med}")
print(f"  Снизить ставку (высокий приоритет):    {decrease_high}")
print(f"  Снизить ставку (средний приоритет):    {decrease_med}")
print(f"  Оставить без изменений:                {maintain}")
print()

# Top performers by efficiency
print("=" * 80)
print("TOP-10 САМЫХ ЭФФЕКТИВНЫХ ПАБЛИШЕРОВ (по CPA):")
print("-" * 80)
top_10 = rec_df.nsmallest(10, 'efficiency_score')
for idx, row in top_10.iterrows():
    pub_id = int(row['publisher_id'])
    name = str(row['publisher_name'])[:35]
    score = row['efficiency_score']
    total_cpa = row['total_cpa_nov']
    deps = int(row['deps_nov'])
    print(f"Publisher {pub_id:3d} ({name:35s}) | Score: {score:+6.1f}% | CPA: ${total_cpa:.3f} | Deps: {deps:6,d}")

print()
print("ХУДШИЕ-10 ПО ЭФФЕКТИВНОСТИ:")
print("-" * 80)
bottom_10 = rec_df.nlargest(10, 'efficiency_score')
for idx, row in bottom_10.iterrows():
    pub_id = int(row['publisher_id'])
    name = str(row['publisher_name'])[:35]
    score = row['efficiency_score']
    total_cpa = row['total_cpa_nov']
    deps = int(row['deps_nov'])
    print(f"Publisher {pub_id:3d} ({name:35s}) | Score: {score:+6.1f}% | CPA: ${total_cpa:.3f} | Deps: {deps:6,d}")

print()
print("=" * 80)
