import pandas as pd
import sqlite3
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("АНАЛИЗ ПАБЛИШЕРОВ: Стоимость FTD и RD (Ноябрь 18-23, 2025)")
print("=" * 80)
print()

conn = sqlite3.connect('events.db')

# Get deposit data for November 18-23
print("1. Загружаю данные о депозитах...")
print()

query = '''
WITH user_first_deposit_ever AS (
    -- Find the very first deposit for each user (across all time)
    SELECT
        external_user_id,
        MIN(event_date) as first_deposit_ever
    FROM user_events
    WHERE event_type = 'deposit'
    GROUP BY external_user_id
),
nov_deposits AS (
    -- All deposits in November 18-23
    SELECT
        e.external_user_id,
        e.publisher_id,
        e.event_date,
        e.deposit_amount,
        e.converted_amount,
        f.first_deposit_ever
    FROM user_events e
    LEFT JOIN user_first_deposit_ever f
        ON e.external_user_id = f.external_user_id
    WHERE e.event_type = 'deposit'
      AND e.event_date >= '2025-11-18 00:00:00'
      AND e.event_date <= '2025-11-23 23:59:59'
)
SELECT
    external_user_id,
    publisher_id,
    event_date,
    deposit_amount,
    converted_amount,
    first_deposit_ever,
    CASE
        WHEN event_date = first_deposit_ever THEN 'FTD'
        ELSE 'RD'
    END as deposit_type
FROM nov_deposits
'''

deposits = pd.read_sql(query, conn)
conn.close()

print(f"   Всего депозитов: {len(deposits):,}")
print()

# Count FTD vs RD by publisher
print("2. Подсчет FTD и RD по паблишерам...")
print()

stats_by_publisher = deposits.groupby(['publisher_id', 'deposit_type']).agg({
    'external_user_id': 'count'
}).reset_index()

stats_by_publisher.columns = ['publisher_id', 'deposit_type', 'count']

# Pivot to get FTD and RD in columns
pivot = stats_by_publisher.pivot(
    index='publisher_id',
    columns='deposit_type',
    values='count'
).fillna(0)

pivot['FTD'] = pivot.get('FTD', 0).astype(int)
pivot['RD'] = pivot.get('RD', 0).astype(int)
pivot['TOTAL'] = pivot['FTD'] + pivot['RD']
pivot['RD_rate'] = (pivot['RD'] / pivot['TOTAL'] * 100).round(1)

# Sort by total
pivot = pivot.sort_values('TOTAL', ascending=False)

print("=" * 80)
print("СТАТИСТИКА ПО ВСЕМ ПАБЛИШЕРАМ:")
print("=" * 80)
print()

print("Publisher | Total Deps | FTD    | RD     | RD Rate")
print("-" * 80)

for pub_id in pivot.head(30).index:
    total = int(pivot.loc[pub_id, 'TOTAL'])
    ftd = int(pivot.loc[pub_id, 'FTD'])
    rd = int(pivot.loc[pub_id, 'RD'])
    rd_rate = pivot.loc[pub_id, 'RD_rate']

    print(f"{pub_id:8d} | {total:10,d} | {ftd:6,d} | {rd:6,d} | {rd_rate:5.1f}%")

print()
print("=" * 80)
print()

# Calculate averages (excluding publisher 0 = organic)
paid_publishers = pivot[pivot.index != 0]
avg_rd_rate = (paid_publishers['RD'].sum() / paid_publishers['TOTAL'].sum() * 100)

print(f"СРЕДНИЙ RD RATE (платные паблишеры): {avg_rd_rate:.1f}%")
print()

# Now we need cost data to calculate CPA
# Since we don't have cost data in the database, let's ask user for it
print("=" * 80)
print("ВАЖНО: Для расчета стоимости FTD и RD нужны данные о расходах")
print("=" * 80)
print()
print("У нас есть данные о количестве FTD и RD по каждому паблишеру.")
print("Для расчета CPA (Cost Per Acquisition) нужны:")
print()
print("1. Общие расходы на каждого паблишера за период ноябрь 18-23")
print("   ИЛИ")
print("2. CPC/CPM ставки для каждого паблишера")
print()
print("Без этих данных мы можем только:")
print("- Показать объемы FTD/RD по паблишерам")
print("- Рассчитать RD Rate (доля повторных депозитов)")
print("- Сравнить эффективность относительно друг друга")
print()

# Performance analysis based on RD rate
print("=" * 80)
print("АНАЛИЗ ЭФФЕКТИВНОСТИ (на основе RD Rate):")
print("=" * 80)
print()

recommendations = []

for pub_id in paid_publishers.index:
    total = int(pivot.loc[pub_id, 'TOTAL'])
    ftd = int(pivot.loc[pub_id, 'FTD'])
    rd = int(pivot.loc[pub_id, 'RD'])
    rd_rate = pivot.loc[pub_id, 'RD_rate']

    # Skip if too few deposits
    if total < 100:
        continue

    rd_diff = rd_rate - avg_rd_rate

    # Recommendations based on RD rate
    # Higher RD rate = more reactivations = better quality traffic
    if rd_diff >= 5.0:
        recommendation = "УВЕЛИЧИТЬ ставку +20-30%"
        reason = f"RD rate {rd_diff:+.1f}п.п. выше среднего - качественный трафик"
        priority = "HIGH"
    elif rd_diff >= 2.0:
        recommendation = "УВЕЛИЧИТЬ ставку +10-15%"
        reason = f"RD rate {rd_diff:+.1f}п.п. выше среднего"
        priority = "MEDIUM"
    elif rd_diff <= -5.0:
        recommendation = "СНИЗИТЬ ставку -20-30%"
        reason = f"RD rate {rd_diff:.1f}п.п. ниже среднего - мало повторных депозитов"
        priority = "HIGH"
    elif rd_diff <= -2.0:
        recommendation = "СНИЗИТЬ ставку -10-15%"
        reason = f"RD rate {rd_diff:.1f}п.п. ниже среднего"
        priority = "MEDIUM"
    else:
        recommendation = "ОСТАВИТЬ ставку"
        reason = "Близко к среднему"
        priority = "LOW"

    recommendations.append({
        'publisher_id': pub_id,
        'total_deps': total,
        'ftd': ftd,
        'rd': rd,
        'rd_rate': rd_rate,
        'rd_diff': rd_diff,
        'recommendation': recommendation,
        'reason': reason,
        'priority': priority
    })

rec_df = pd.DataFrame(recommendations)
rec_df = rec_df.sort_values('rd_diff', ascending=False)

# Print recommendations by priority
for priority in ['HIGH', 'MEDIUM', 'LOW']:
    priority_recs = rec_df[rec_df['priority'] == priority]

    if len(priority_recs) == 0:
        continue

    print(f"ПРИОРИТЕТ: {priority}")
    print("-" * 80)

    for idx, row in priority_recs.iterrows():
        pub_id = int(row['publisher_id'])
        total = int(row['total_deps'])
        ftd = int(row['ftd'])
        rd = int(row['rd'])
        rd_rate = row['rd_rate']
        rd_diff = row['rd_diff']
        rec = row['recommendation']
        reason = row['reason']

        print(f"Publisher {pub_id:3d} | Total: {total:6,d} | FTD: {ftd:5,d} | RD: {rd:5,d} | RD Rate: {rd_rate:5.1f}% ({rd_diff:+5.1f}п.п.)")
        print(f"  => {rec}")
        print(f"     {reason}")
        print()

print("=" * 80)
print()

# Save results
pivot.to_csv('publishers_ftd_rd_stats_nov18-23.csv')
rec_df.to_csv('publishers_rd_rate_recommendations.csv', index=False)

print("Сохранено:")
print("  - publishers_ftd_rd_stats_nov18-23.csv (статистика FTD/RD)")
print("  - publishers_rd_rate_recommendations.csv (рекомендации)")
print()

# Summary
print("=" * 80)
print("ИТОГОВАЯ СТАТИСТИКА:")
print("=" * 80)
print()

total_ftd = int(paid_publishers['FTD'].sum())
total_rd = int(paid_publishers['RD'].sum())
total_deps = int(paid_publishers['TOTAL'].sum())

print(f"Всего депозитов (платные): {total_deps:,}")
print(f"  FTD: {total_ftd:,} ({total_ftd/total_deps*100:.1f}%)")
print(f"  RD:  {total_rd:,} ({total_rd/total_deps*100:.1f}%)")
print()

increase_high = len(rec_df[(rec_df['recommendation'].str.contains('УВЕЛИЧИТЬ')) & (rec_df['priority'] == 'HIGH')])
increase_med = len(rec_df[(rec_df['recommendation'].str.contains('УВЕЛИЧИТЬ')) & (rec_df['priority'] == 'MEDIUM')])
decrease_high = len(rec_df[(rec_df['recommendation'].str.contains('СНИЗИТЬ')) & (rec_df['priority'] == 'HIGH')])
decrease_med = len(rec_df[(rec_df['recommendation'].str.contains('СНИЗИТЬ')) & (rec_df['priority'] == 'MEDIUM')])
maintain = len(rec_df[rec_df['recommendation'] == 'ОСТАВИТЬ ставку'])

print(f"Увеличить ставку (высокий приоритет): {increase_high}")
print(f"Увеличить ставку (средний приоритет): {increase_med}")
print(f"Снизить ставку (высокий приоритет): {decrease_high}")
print(f"Снизить ставку (средний приоритет): {decrease_med}")
print(f"Оставить без изменений: {maintain}")
print()

# Top performers
print("TOP-5 ПО RD RATE (лучшие для повторных депозитов):")
print("-" * 80)
top_5 = rec_df.nlargest(5, 'rd_rate')
for idx, row in top_5.iterrows():
    pub_id = int(row['publisher_id'])
    rd_rate = row['rd_rate']
    rd_diff = row['rd_diff']
    print(f"Publisher {pub_id:3d}: RD Rate {rd_rate:5.1f}% ({rd_diff:+5.1f}п.п. от среднего)")

print()
print("ХУДШИЕ-5 ПО RD RATE:")
print("-" * 80)
bottom_5 = rec_df.nsmallest(5, 'rd_rate')
for idx, row in bottom_5.iterrows():
    pub_id = int(row['publisher_id'])
    rd_rate = row['rd_rate']
    rd_diff = row['rd_diff']
    print(f"Publisher {pub_id:3d}: RD Rate {rd_rate:5.1f}% ({rd_diff:+5.1f}п.п. от среднего)")

print()
print("=" * 80)
print()
print("СЛЕДУЮЩИЕ ШАГИ:")
print("-" * 80)
print("1. Получить данные о расходах (spend) по каждому паблишеру")
print("2. Рассчитать CPA для FTD и RD отдельно")
print("3. Сравнить CPA с LTV пользователей")
print("4. Оптимизировать ставки на основе ROI")
print()
