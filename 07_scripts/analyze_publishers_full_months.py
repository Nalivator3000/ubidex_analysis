import pandas as pd
import sqlite3
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("АНАЛИЗ ПАБЛИШЕРОВ: Полные месяцы (Октябрь и Ноябрь)")
print("=" * 80)
print()

conn = sqlite3.connect('events.db')

# Function to analyze a full month
def analyze_month(month_name, start_date, end_date):
    print(f"Анализирую {month_name} ({start_date} - {end_date})...")

    # Get FTD/RD stats
    query = f'''
    WITH user_first_deposit_ever AS (
        SELECT
            external_user_id,
            MIN(event_date) as first_deposit_ever
        FROM user_events
        WHERE event_type = 'deposit'
        GROUP BY external_user_id
    ),
    month_deposits AS (
        SELECT
            e.external_user_id,
            e.publisher_id,
            e.event_date,
            f.first_deposit_ever
        FROM user_events e
        LEFT JOIN user_first_deposit_ever f
            ON e.external_user_id = f.external_user_id
        WHERE e.event_type = 'deposit'
          AND e.event_date >= '{start_date} 00:00:00'
          AND e.event_date <= '{end_date} 23:59:59'
    )
    SELECT
        publisher_id,
        COUNT(*) as total_deps,
        SUM(CASE WHEN event_date = first_deposit_ever THEN 1 ELSE 0 END) as ftd,
        SUM(CASE WHEN event_date != first_deposit_ever THEN 1 ELSE 0 END) as rd
    FROM month_deposits
    GROUP BY publisher_id
    ORDER BY total_deps DESC
    '''

    stats = pd.read_sql(query, conn)
    stats['rd_rate'] = (stats['rd'] / stats['total_deps'] * 100).round(1)

    return stats

# Analyze October (full month)
print("=" * 80)
print("1. ОКТЯБРЬ 2025 (полный месяц: 1-31)")
print("=" * 80)
print()

oct_stats = analyze_month('Октябрь', '2025-10-01', '2025-10-31')

print(f"   Найдено депозитов: {oct_stats['total_deps'].sum():,}")
print()

# Analyze November (full month)
print("=" * 80)
print("2. НОЯБРЬ 2025 (полный месяц: 1-30)")
print("=" * 80)
print()

nov_stats = analyze_month('Ноябрь', '2025-11-01', '2025-11-30')

print(f"   Найдено депозитов: {nov_stats['total_deps'].sum():,}")
print()

# Calculate averages
oct_paid = oct_stats[oct_stats['publisher_id'] != 0]
nov_paid = nov_stats[nov_stats['publisher_id'] != 0]

oct_avg_rd_rate = (oct_paid['rd'].sum() / oct_paid['total_deps'].sum() * 100)
nov_avg_rd_rate = (nov_paid['rd'].sum() / nov_paid['total_deps'].sum() * 100)

print("=" * 80)
print("СРАВНЕНИЕ ОКТЯБРЬ vs НОЯБРЬ")
print("=" * 80)
print()

# Merge stats for comparison
comparison = oct_stats.merge(
    nov_stats,
    on='publisher_id',
    how='outer',
    suffixes=('_oct', '_nov')
).fillna(0)

# Calculate differences
comparison['total_deps_oct'] = comparison['total_deps_oct'].astype(int)
comparison['total_deps_nov'] = comparison['total_deps_nov'].astype(int)
comparison['ftd_oct'] = comparison['ftd_oct'].astype(int)
comparison['ftd_nov'] = comparison['ftd_nov'].astype(int)
comparison['rd_oct'] = comparison['rd_oct'].astype(int)
comparison['rd_nov'] = comparison['rd_nov'].astype(int)

comparison['deps_change'] = comparison['total_deps_nov'] - comparison['total_deps_oct']
comparison['deps_change_pct'] = ((comparison['total_deps_nov'] / comparison['total_deps_oct'].replace(0, 1) - 1) * 100).round(1)
comparison['rd_rate_change'] = comparison['rd_rate_nov'] - comparison['rd_rate_oct']

# Sort by November volume
comparison = comparison.sort_values('total_deps_nov', ascending=False)

# Print top 30 publishers
print("ТОП-30 ПАБЛИШЕРОВ:")
print()
print("Pub ID | Oct Deps | Nov Deps | Change    | Oct RD% | Nov RD% | RD Change")
print("-" * 80)

for idx, row in comparison.head(30).iterrows():
    pub_id = int(row['publisher_id'])
    oct_deps = int(row['total_deps_oct'])
    nov_deps = int(row['total_deps_nov'])
    change = int(row['deps_change'])
    change_pct = row['deps_change_pct']
    oct_rd = row['rd_rate_oct']
    nov_rd = row['rd_rate_nov']
    rd_change = row['rd_rate_change']

    # Format change with color indicator
    change_str = f"{change:+6,d} ({change_pct:+5.1f}%)"
    rd_change_str = f"{rd_change:+4.1f}п.п."

    print(f"{pub_id:6d} | {oct_deps:8,d} | {nov_deps:8,d} | {change_str:16} | {oct_rd:6.1f}% | {nov_rd:6.1f}% | {rd_change_str:10}")

print()
print("=" * 80)
print()

# Overall statistics
print("ОБЩАЯ СТАТИСТИКА:")
print()

oct_total = oct_stats['total_deps'].sum()
oct_ftd = oct_stats['ftd'].sum()
oct_rd = oct_stats['rd'].sum()

nov_total = nov_stats['total_deps'].sum()
nov_ftd = nov_stats['ftd'].sum()
nov_rd = nov_stats['rd'].sum()

print(f"ОКТЯБРЬ:")
print(f"  Всего депозитов: {oct_total:,}")
print(f"  FTD: {oct_ftd:,} ({oct_ftd/oct_total*100:.1f}%)")
print(f"  RD:  {oct_rd:,} ({oct_rd/oct_total*100:.1f}%)")
print(f"  RD Rate (платные): {oct_avg_rd_rate:.1f}%")
print()

print(f"НОЯБРЬ:")
print(f"  Всего депозитов: {nov_total:,}")
print(f"  FTD: {nov_ftd:,} ({nov_ftd/nov_total*100:.1f}%)")
print(f"  RD:  {nov_rd:,} ({nov_rd/nov_total*100:.1f}%)")
print(f"  RD Rate (платные): {nov_avg_rd_rate:.1f}%")
print()

print(f"ИЗМЕНЕНИЕ:")
print(f"  Депозиты: {nov_total-oct_total:+,d} ({(nov_total/oct_total-1)*100:+.1f}%)")
print(f"  FTD: {nov_ftd-oct_ftd:+,d} ({(nov_ftd/oct_ftd-1)*100:+.1f}%)")
print(f"  RD:  {nov_rd-oct_rd:+,d} ({(nov_rd/oct_rd-1)*100:+.1f}%)")
print(f"  RD Rate: {nov_avg_rd_rate-oct_avg_rd_rate:+.1f}п.п.")
print()

print("=" * 80)
print()

# Recommendations based on comparison
print("РЕКОМЕНДАЦИИ ПО ПАБЛИШЕРАМ (на основе изменений):")
print("=" * 80)
print()

recommendations = []

for idx, row in comparison.iterrows():
    pub_id = int(row['publisher_id'])

    # Skip organic
    if pub_id == 0:
        continue

    nov_deps = int(row['total_deps_nov'])

    # Only analyze publishers with significant volume in November
    if nov_deps < 1000:
        continue

    deps_change_pct = row['deps_change_pct']
    rd_change = row['rd_rate_change']
    nov_rd = row['rd_rate_nov']

    # Score based on volume growth and RD rate improvement
    volume_score = deps_change_pct / 10  # Weight: 10% growth = 1 point
    quality_score = rd_change * 2  # Weight: 1п.п. RD = 2 points
    total_score = volume_score + quality_score

    # Recommendations
    if total_score >= 5 and nov_deps >= 5000:
        recommendation = "УВЕЛИЧИТЬ ставку +20-30%"
        reason = f"Рост объема {deps_change_pct:+.1f}%, улучшение RD rate {rd_change:+.1f}п.п."
        priority = "HIGH"
    elif total_score >= 2 and nov_deps >= 2000:
        recommendation = "УВЕЛИЧИТЬ ставку +10-15%"
        reason = f"Позитивная динамика: объем {deps_change_pct:+.1f}%, RD {rd_change:+.1f}п.п."
        priority = "MEDIUM"
    elif total_score <= -5 and nov_deps >= 5000:
        recommendation = "СНИЗИТЬ ставку -20-30%"
        reason = f"Негативная динамика: объем {deps_change_pct:+.1f}%, RD {rd_change:+.1f}п.п."
        priority = "HIGH"
    elif total_score <= -2 and nov_deps >= 2000:
        recommendation = "СНИЗИТЬ ставку -10-15%"
        reason = f"Ухудшение: объем {deps_change_pct:+.1f}%, RD {rd_change:+.1f}п.п."
        priority = "MEDIUM"
    else:
        recommendation = "ОСТАВИТЬ ставку"
        reason = f"Стабильная динамика"
        priority = "LOW"

    recommendations.append({
        'publisher_id': pub_id,
        'nov_deps': nov_deps,
        'deps_change_pct': deps_change_pct,
        'rd_change': rd_change,
        'nov_rd_rate': nov_rd,
        'total_score': total_score,
        'recommendation': recommendation,
        'reason': reason,
        'priority': priority
    })

rec_df = pd.DataFrame(recommendations)
rec_df = rec_df.sort_values('total_score', ascending=False)

# Print by priority
for priority in ['HIGH', 'MEDIUM']:
    priority_recs = rec_df[rec_df['priority'] == priority]

    if len(priority_recs) == 0:
        continue

    print(f"ПРИОРИТЕТ: {priority}")
    print("-" * 80)

    for idx, row in priority_recs.iterrows():
        pub_id = int(row['publisher_id'])
        nov_deps = int(row['nov_deps'])
        deps_change = row['deps_change_pct']
        rd_change = row['rd_change']
        nov_rd = row['nov_rd_rate']
        score = row['total_score']
        rec = row['recommendation']
        reason = row['reason']

        print(f"Publisher {pub_id:3d} | Nov: {nov_deps:6,d} deps | RD Rate: {nov_rd:5.1f}% | Score: {score:+6.1f}")
        print(f"  => {rec}")
        print(f"     {reason}")
        print()

print("=" * 80)
print()

# Save results
comparison.to_csv('publishers_oct_vs_nov_full_months.csv', index=False)
rec_df.to_csv('publishers_monthly_comparison_recommendations.csv', index=False)

oct_stats.to_csv('publishers_october_full_month.csv', index=False)
nov_stats.to_csv('publishers_november_full_month.csv', index=False)

print("Сохранено:")
print("  - publishers_oct_vs_nov_full_months.csv (сравнение)")
print("  - publishers_monthly_comparison_recommendations.csv (рекомендации)")
print("  - publishers_october_full_month.csv (статистика октября)")
print("  - publishers_november_full_month.csv (статистика ноября)")
print()

# Top performers
print("=" * 80)
print("TOP-5 ПО РОСТУ:")
print("-" * 80)
top_growth = rec_df.nlargest(5, 'total_score')
for idx, row in top_growth.iterrows():
    pub_id = int(row['publisher_id'])
    score = row['total_score']
    deps_change = row['deps_change_pct']
    rd_change = row['rd_change']
    print(f"Publisher {pub_id:3d}: Score {score:+6.1f} | Объем {deps_change:+5.1f}% | RD {rd_change:+4.1f}п.п.")

print()
print("ХУДШИЕ-5:")
print("-" * 80)
bottom = rec_df.nsmallest(5, 'total_score')
for idx, row in bottom.iterrows():
    pub_id = int(row['publisher_id'])
    score = row['total_score']
    deps_change = row['deps_change_pct']
    rd_change = row['rd_change']
    print(f"Publisher {pub_id:3d}: Score {score:+6.1f} | Объем {deps_change:+5.1f}% | RD {rd_change:+4.1f}п.п.")

print()
print("=" * 80)

conn.close()
