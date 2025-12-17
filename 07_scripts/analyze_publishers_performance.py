import pandas as pd
import sqlite3
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("АНАЛИЗ ПАБЛИШЕРОВ: Ноябрь 18-23, 2025")
print("=" * 80)
print()

from db_utils import get_db_connection
conn = get_db_connection()

# Get all reactivations by publisher for November 18-23
print("1. Анализирую реактивации по паблишерам...")
print()

query = '''
WITH nov_first_deposit AS (
    SELECT
        external_user_id,
        publisher_id,
        MIN(event_date) as first_deposit_nov
    FROM user_events
    WHERE event_type = 'deposit'
      AND event_date >= '2025-11-18 00:00:00'
      AND event_date <= '2025-11-23 23:59:59'
    GROUP BY external_user_id, publisher_id
),
prev_deposits AS (
    SELECT
        n.external_user_id,
        n.publisher_id,
        n.first_deposit_nov,
        MAX(e.event_date) as prev_deposit_date
    FROM nov_first_deposit n
    LEFT JOIN user_events e
        ON n.external_user_id = e.external_user_id
        AND e.event_type = 'deposit'
        AND e.event_date < n.first_deposit_nov
    GROUP BY n.external_user_id, n.publisher_id, n.first_deposit_nov
)
SELECT
    publisher_id,
    external_user_id as user_id,
    first_deposit_nov,
    prev_deposit_date,
    CAST((julianday(first_deposit_nov) - julianday(prev_deposit_date)) AS INTEGER) as days_inactive
FROM prev_deposits
WHERE prev_deposit_date IS NOT NULL
'''

reactivations = pd.read_sql(query, conn)
conn.close()

print(f"   Найдено реактиваций: {len(reactivations):,}")
print()

# Categorize
def categorize(days):
    if days < 7:
        return '0-7 days'
    elif days < 14:
        return '7-14 days'
    elif days < 30:
        return '14-30 days'
    elif days < 90:
        return '30-90 days'
    else:
        return '90+ days'

reactivations['period'] = reactivations['days_inactive'].apply(categorize)

# Calculate metrics by publisher and period
print("2. Подсчет метрик по паблишерам и сегментам...")
print()

# Pivot table: publisher x period
pivot = reactivations.pivot_table(
    index='publisher_id',
    columns='period',
    values='user_id',
    aggfunc='count',
    fill_value=0
)

# Reorder columns
desired_order = ['0-7 days', '7-14 days', '14-30 days', '30-90 days', '90+ days']
pivot = pivot[[col for col in desired_order if col in pivot.columns]]

# Add totals
pivot['TOTAL'] = pivot.sum(axis=1)

# Calculate percentages for each publisher
for col in desired_order:
    if col in pivot.columns:
        pivot[f'{col}_pct'] = (pivot[col] / pivot['TOTAL'] * 100).round(1)

# Calculate overall averages (excluding publisher 0 = organic)
paid_publishers = pivot[pivot.index != 0]
averages = {}
for col in desired_order:
    if col in pivot.columns:
        averages[col] = paid_publishers[col].sum() / paid_publishers['TOTAL'].sum() * 100

print("=" * 80)
print("СРЕДНИЕ ПОКАЗАТЕЛИ (все платные паблишеры):")
print("=" * 80)
print()
for seg, avg in averages.items():
    print(f"  {seg:12} {avg:5.1f}%")
print()

# Sort publishers by total reactivations
pivot_sorted = pivot.sort_values('TOTAL', ascending=False)

print("=" * 80)
print("ТОП-20 ПАБЛИШЕРОВ ПО РЕАКТИВАЦИЯМ:")
print("=" * 80)
print()

# Create detailed report for top publishers
top_20 = pivot_sorted.head(20)

results = []
for pub_id in top_20.index:
    row = {'publisher_id': pub_id, 'total': int(top_20.loc[pub_id, 'TOTAL'])}

    for seg in desired_order:
        if seg in pivot.columns:
            count = int(top_20.loc[pub_id, seg])
            pct = top_20.loc[pub_id, f'{seg}_pct']
            avg_pct = averages[seg]
            diff = pct - avg_pct

            row[f'{seg}_count'] = count
            row[f'{seg}_pct'] = pct
            row[f'{seg}_diff'] = diff

    results.append(row)

results_df = pd.DataFrame(results)

# Print summary table
print("Publisher | Total | 0-7d | 7-14d | 14-30d | 30-90d | 90+ d")
print("-" * 80)

for idx, row in results_df.iterrows():
    pub_id = int(row['publisher_id'])
    total = int(row['total'])

    segments = []
    for seg in desired_order:
        if f'{seg}_count' in row:
            count = int(row[f'{seg}_count'])
            pct = row[f'{seg}_pct']
            segments.append(f"{count:5d} ({pct:4.1f}%)")
        else:
            segments.append("    0 (0.0%)")

    print(f"{pub_id:8d} | {total:5d} | {' | '.join(segments)}")

print()
print("=" * 80)
print()

# Calculate performance scores
print("3. АНАЛИЗ ЭФФЕКТИВНОСТИ И РЕКОМЕНДАЦИИ ПО СТАВКАМ:")
print("=" * 80)
print()

recommendations = []

for idx, row in results_df.iterrows():
    pub_id = int(row['publisher_id'])
    total = int(row['total'])

    # Skip organic
    if pub_id == 0:
        continue

    # Calculate quality score based on 90+ days performance
    if '90+ days_pct' in row:
        days_90_pct = row['90+ days_pct']
        days_90_diff = row['90+ days_diff']
    else:
        continue

    # Calculate overall quality score
    # Higher 90+ days % = better quality
    # Lower 0-7 days % = better (less cannibalization)
    days_07_pct = row.get('0-7 days_pct', 0)
    days_07_diff = row.get('0-7 days_diff', 0)

    quality_score = (days_90_diff * 2) - (days_07_diff * 0.5)  # Weight 90+ more heavily

    # Determine recommendation
    if days_90_diff >= 1.0 and total >= 100:
        recommendation = "УВЕЛИЧИТЬ ставку +20-30%"
        reason = f"90+ дней на {days_90_diff:+.1f}п.п. выше среднего"
        priority = "HIGH"
    elif days_90_diff >= 0.5 and total >= 50:
        recommendation = "УВЕЛИЧИТЬ ставку +10-15%"
        reason = f"90+ дней на {days_90_diff:+.1f}п.п. выше среднего"
        priority = "MEDIUM"
    elif days_90_diff <= -1.0 and total >= 100:
        recommendation = "СНИЗИТЬ ставку -20-30%"
        reason = f"90+ дней на {days_90_diff:.1f}п.п. ниже среднего"
        priority = "HIGH"
    elif days_90_diff <= -0.5 and total >= 50:
        recommendation = "СНИЗИТЬ ставку -10-15%"
        reason = f"90+ дней на {days_90_diff:.1f}п.п. ниже среднего"
        priority = "MEDIUM"
    elif total < 50:
        recommendation = "НАБЛЮДАТЬ"
        reason = f"Мало данных (всего {total} реактиваций)"
        priority = "LOW"
    else:
        recommendation = "ОСТАВИТЬ ставку"
        reason = "Близко к среднему"
        priority = "LOW"

    recommendations.append({
        'publisher_id': pub_id,
        'total': total,
        '90+_pct': days_90_pct,
        '90+_diff': days_90_diff,
        'quality_score': quality_score,
        'recommendation': recommendation,
        'reason': reason,
        'priority': priority
    })

rec_df = pd.DataFrame(recommendations)
rec_df = rec_df.sort_values('quality_score', ascending=False)

# Print recommendations by priority
for priority in ['HIGH', 'MEDIUM', 'LOW']:
    priority_recs = rec_df[rec_df['priority'] == priority]

    if len(priority_recs) == 0:
        continue

    print(f"ПРИОРИТЕТ: {priority}")
    print("-" * 80)

    for idx, row in priority_recs.iterrows():
        pub_id = int(row['publisher_id'])
        total = int(row['total'])
        pct_90 = row['90+_pct']
        diff_90 = row['90+_diff']
        score = row['quality_score']
        rec = row['recommendation']
        reason = row['reason']

        print(f"Publisher {pub_id:3d} | Всего: {total:4d} | 90+ дней: {pct_90:4.1f}% ({diff_90:+5.1f}п.п.) | Score: {score:+6.1f}")
        print(f"  => {rec}")
        print(f"     Причина: {reason}")
        print()

print("=" * 80)
print()

# Save results
pivot_sorted.to_csv('publishers_performance_nov18-23.csv')
rec_df.to_csv('publishers_bid_recommendations.csv', index=False)

print("Сохранено:")
print("  - publishers_performance_nov18-23.csv (полная статистика)")
print("  - publishers_bid_recommendations.csv (рекомендации по ставкам)")
print()

# Summary statistics
print("=" * 80)
print("ИТОГОВАЯ СТАТИСТИКА:")
print("=" * 80)
print()

increase_high = len(rec_df[(rec_df['recommendation'].str.contains('УВЕЛИЧИТЬ')) & (rec_df['priority'] == 'HIGH')])
increase_med = len(rec_df[(rec_df['recommendation'].str.contains('УВЕЛИЧИТЬ')) & (rec_df['priority'] == 'MEDIUM')])
decrease_high = len(rec_df[(rec_df['recommendation'].str.contains('СНИЗИТЬ')) & (rec_df['priority'] == 'HIGH')])
decrease_med = len(rec_df[(rec_df['recommendation'].str.contains('СНИЗИТЬ')) & (rec_df['priority'] == 'MEDIUM')])
maintain = len(rec_df[rec_df['recommendation'] == 'ОСТАВИТЬ ставку'])
observe = len(rec_df[rec_df['recommendation'] == 'НАБЛЮДАТЬ'])

print(f"Увеличить ставку (высокий приоритет): {increase_high}")
print(f"Увеличить ставку (средний приоритет): {increase_med}")
print(f"Снизить ставку (высокий приоритет): {decrease_high}")
print(f"Снизить ставку (средний приоритет): {decrease_med}")
print(f"Оставить без изменений: {maintain}")
print(f"Наблюдать (мало данных): {observe}")
print()

# Top performers
print("TOP-5 ЛУЧШИХ ПАБЛИШЕРОВ (по качеству реактиваций):")
print("-" * 80)
top_5 = rec_df.nlargest(5, 'quality_score')
for idx, row in top_5.iterrows():
    print(f"Publisher {int(row['publisher_id']):3d}: Score {row['quality_score']:+6.1f} | 90+ дней: {row['90+_pct']:4.1f}% ({row['90+_diff']:+5.1f}п.п.)")

print()
print("TOP-5 ХУДШИХ ПАБЛИШЕРОВ:")
print("-" * 80)
bottom_5 = rec_df.nsmallest(5, 'quality_score')
for idx, row in bottom_5.iterrows():
    print(f"Publisher {int(row['publisher_id']):3d}: Score {row['quality_score']:+6.1f} | 90+ дней: {row['90+_pct']:4.1f}% ({row['90+_diff']:+5.1f}п.п.)")

print()
print("=" * 80)
