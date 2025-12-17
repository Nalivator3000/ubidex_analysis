import pandas as pd
import sqlite3
import sys
import io
import re

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("АНАЛИЗ ПАБЛИШЕРОВ ПО ФОРМАТАМ (с интеграцией Spend)")
print("=" * 80)
print()

# Function to extract publisher_id and format from publisher name
def extract_format(publisher_str):
    """Extract ad format from publisher name with improved logic"""
    name_upper = str(publisher_str).upper()
    
    # Используем регулярные выражения для более точного определения формата
    # Ищем формат после дефиса или в конце названия (например, "-PUSH", "PUSH-Premium", "UGW-VIDEO")
    
    # Используем более строгие паттерны - формат должен быть отдельным словом
    # после дефиса, перед дефисом, или в конце, но НЕ внутри другого слова
    # Проверяем форматы в правильном порядке - сначала более специфичные
    
    # POP - проверяем перед PUSH, чтобы перехватить "-POP" раньше
    if re.search(r'-POP\b|POP-|POP\s|POP$', name_upper):
        return 'POP'
    # BANNER - проверяем первым среди остальных, так как может быть в конце названия
    elif re.search(r'-BANNER\b|BANNER-|BANNER\s|BANNER$', name_upper):
        return 'BANNER'
    # VIDEO - проверяем перед PUSH
    elif re.search(r'-VIDEO\b|VIDEO-|VIDEO\s|VIDEO$', name_upper):
        return 'VIDEO'
    # PUSH - проверяем последним, исключая случаи где PUSH внутри слова
    # Ищем PUSH только как отдельное слово (после/перед дефисом или пробелом)
    elif (re.search(r'-PUSH\b|PUSH-|PUSH\s|PUSH$|IN-PAGE|INPAGE', name_upper) and 
          not re.search(r'[A-Z]PUSH[A-Z]', name_upper)):  # Исключаем PUSH внутри слова
        return 'PUSH'
    # NATIVE
    elif re.search(r'-NATIVE\b|NATIVE-|NATIVE\s|NATIVE$', name_upper):
        return 'NATIVE'
    else:
        return 'OTHER'

def extract_publisher_id(publisher_str):
    match = re.match(r'\((\d+)\)', str(publisher_str))
    if match:
        return int(match.group(1))
    return None

# Load November spend data
print("1. Загружаю данные по расходам (ноябрь)...")
print()

nov_spend = pd.read_csv('C:/Users/Nalivator3000/Downloads/export (1).csv', skiprows=1)
nov_spend['publisher_id'] = nov_spend['Publisher'].apply(extract_publisher_id)
nov_spend['format'] = nov_spend['Publisher'].apply(extract_format)

# Keep only relevant columns
nov_spend = nov_spend[['publisher_id', 'Publisher', 'format', 'FTD', 'Deposit', 'Spend']].copy()
nov_spend.columns = ['publisher_id', 'publisher_name', 'format', 'ftd_reported', 'deposit_reported', 'spend']

# Remove rows with missing publisher_id
nov_spend = nov_spend.dropna(subset=['publisher_id'])

# Convert to numeric
for col in ['ftd_reported', 'deposit_reported', 'spend']:
    nov_spend[col] = pd.to_numeric(nov_spend[col], errors='coerce').fillna(0)

print(f"   Загружено: {len(nov_spend)} паблишеров")
print()

# Get FTD/RD stats from database for November
print("2. Загружаю FTD/RD статистику из базы данных (ноябрь)...")
print()

from db_utils import get_db_connection
conn = get_db_connection()

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
conn.close()

print(f"   Загружено: {len(nov_db_stats)} паблишеров с депозитами")
print()

# Merge data
print("3. Объединяю данные...")
print()

merged = nov_db_stats.merge(
    nov_spend[['publisher_id', 'publisher_name', 'format', 'spend']],
    on='publisher_id',
    how='left'
)

# Fill missing formats
merged['format'] = merged['format'].fillna('OTHER')

# Calculate metrics
merged['ftd_cpa'] = (merged['spend'] / merged['ftd_db'].replace(0, 1)).round(2)
merged['rd_cpa'] = (merged['spend'] / merged['rd_db'].replace(0, 1)).round(4)
merged['total_cpa'] = (merged['spend'] / merged['total_deps'].replace(0, 1)).round(3)
merged['rd_rate'] = (merged['rd_db'] / merged['total_deps'] * 100).round(1)

# Filter to publishers with significant spend
significant = merged[merged['spend'] > 50].copy()

print(f"   Паблишеров с расходами > $50: {len(significant)}")
print()

# Group by format
print("=" * 80)
print("АНАЛИЗ ПО ФОРМАТАМ:")
print("=" * 80)
print()

formats = ['POP', 'PUSH', 'VIDEO', 'BANNER', 'NATIVE']

all_recommendations = []

for fmt in formats:
    format_data = significant[significant['format'] == fmt].copy()

    if len(format_data) == 0:
        continue

    # Filter out organic (publisher 0)
    format_data = format_data[format_data['publisher_id'] != 0]

    if len(format_data) == 0:
        continue

    print("=" * 80)
    print(f"ФОРМАТ: {fmt}")
    print("=" * 80)
    print()

    # Calculate format averages
    total_spend = format_data['spend'].sum()
    total_deps = format_data['total_deps'].sum()
    total_ftd = format_data['ftd_db'].sum()
    total_rd = format_data['rd_db'].sum()

    avg_total_cpa = total_spend / total_deps if total_deps > 0 else 0
    avg_ftd_cpa = total_spend / total_ftd if total_ftd > 0 else 0
    avg_rd_cpa = total_spend / total_rd if total_rd > 0 else 0
    avg_rd_rate = (total_rd / total_deps * 100) if total_deps > 0 else 0

    print(f"СРЕДНИЕ ПОКАЗАТЕЛИ ({fmt}):")
    print(f"  Паблишеров:       {len(format_data)}")
    print(f"  Всего расходов:   ${total_spend:,.0f}")
    print(f"  Всего депозитов:  {total_deps:,}")
    print(f"  Средний Total CPA: ${avg_total_cpa:.3f}")
    print(f"  Средний FTD CPA:   ${avg_ftd_cpa:.2f}")
    print(f"  Средний RD CPA:    ${avg_rd_cpa:.4f}")
    print(f"  Средний RD Rate:   {avg_rd_rate:.1f}%")
    print()

    # Sort by spend
    format_data = format_data.sort_values('spend', ascending=False)

    print(f"ВСЕ ПАБЛИШЕРЫ ({fmt}):")
    print("-" * 80)
    print("Pub ID | Publisher Name                    | Spend    | Deps   | Total CPA | Efficiency")
    print("-" * 80)

    for idx, row in format_data.iterrows():
        pub_id = int(row['publisher_id'])
        name = str(row['publisher_name'])[:30]
        spend = row['spend']
        deps = int(row['total_deps'])
        total_cpa = row['total_cpa']

        # Calculate efficiency vs format average
        efficiency = ((total_cpa / avg_total_cpa - 1) * 100) if avg_total_cpa > 0 else 0

        efficiency_str = f"{efficiency:+6.1f}%"

        print(f"{pub_id:6d} | {name:33s} | ${spend:7,.0f} | {deps:6,d} | ${total_cpa:7.3f} | {efficiency_str}")

    print()
    print("=" * 80)
    print()

    # Generate recommendations for this format
    print(f"РЕКОМЕНДАЦИИ ({fmt}):")
    print("-" * 80)
    print()

    for idx, row in format_data.iterrows():
        pub_id = int(row['publisher_id'])
        name = str(row['publisher_name'])[:40]
        spend = row['spend']
        deps = int(row['total_deps'])
        total_cpa = row['total_cpa']
        ftd_cpa = row['ftd_cpa']
        rd_cpa = row['rd_cpa']
        rd_rate = row['rd_rate']

        # Calculate efficiency relative to format average
        total_efficiency = ((total_cpa / avg_total_cpa - 1) * 100) if avg_total_cpa > 0 else 0

        # Determine recommendation based on format-specific benchmarks
        if total_efficiency <= -25 and deps >= 2000:
            recommendation = "УВЕЛИЧИТЬ ставку +30-50%"
            reason = f"Отлично: CPA на {abs(total_efficiency):.0f}% ниже среднего по {fmt}"
            priority = "HIGH"
        elif total_efficiency <= -15 and deps >= 1000:
            recommendation = "УВЕЛИЧИТЬ ставку +15-25%"
            reason = f"Хорошо: CPA на {abs(total_efficiency):.0f}% ниже среднего по {fmt}"
            priority = "MEDIUM"
        elif total_efficiency >= 25 and deps >= 2000:
            recommendation = "СНИЗИТЬ ставку -30-50%"
            reason = f"Низкая эффективность: CPA на {total_efficiency:.0f}% выше среднего по {fmt}"
            priority = "HIGH"
        elif total_efficiency >= 15 and deps >= 1000:
            recommendation = "СНИЗИТЬ ставку -15-25%"
            reason = f"Низкая эффективность: CPA на {total_efficiency:.0f}% выше среднего по {fmt}"
            priority = "MEDIUM"
        elif deps < 1000:
            recommendation = "НАБЛЮДАТЬ"
            reason = f"Мало данных ({deps} deps)"
            priority = "LOW"
        else:
            recommendation = "ОСТАВИТЬ ставку"
            reason = f"Близко к среднему по {fmt} (CPA {total_efficiency:+.0f}%)"
            priority = "LOW"

        all_recommendations.append({
            'format': fmt,
            'publisher_id': pub_id,
            'publisher_name': name,
            'spend': spend,
            'deps': deps,
            'total_cpa': total_cpa,
            'ftd_cpa': ftd_cpa,
            'rd_cpa': rd_cpa,
            'rd_rate': rd_rate,
            'efficiency_vs_format': total_efficiency,
            'format_avg_cpa': avg_total_cpa,
            'recommendation': recommendation,
            'reason': reason,
            'priority': priority
        })

    # Print format-specific recommendations
    format_recs = [r for r in all_recommendations if r['format'] == fmt]

    for priority in ['HIGH', 'MEDIUM']:
        priority_recs = [r for r in format_recs if r['priority'] == priority]

        if len(priority_recs) == 0:
            continue

        print(f"ПРИОРИТЕТ: {priority}")
        print()

        for rec in priority_recs:
            print(f"Publisher {rec['publisher_id']:3d} ({rec['publisher_name']})")
            print(f"  Spend: ${rec['spend']:,.0f} | Deps: {rec['deps']:,d} | CPA: ${rec['total_cpa']:.3f}")
            print(f"  vs {fmt} Avg: {rec['efficiency_vs_format']:+.1f}% (avg ${rec['format_avg_cpa']:.3f})")
            print(f"  => {rec['recommendation']}")
            print(f"     {rec['reason']}")
            print()

    print("=" * 80)
    print()

# Save results
rec_df = pd.DataFrame(all_recommendations)
rec_df = rec_df.sort_values(['format', 'efficiency_vs_format'], ascending=[True, True])

merged.to_csv('publishers_by_format_with_spend.csv', index=False)
rec_df.to_csv('publishers_recommendations_by_format.csv', index=False)

print("=" * 80)
print("ИТОГОВАЯ СТАТИСТИКА ПО ФОРМАТАМ:")
print("=" * 80)
print()

summary_by_format = significant[significant['publisher_id'] != 0].groupby('format').agg({
    'publisher_id': 'count',
    'spend': 'sum',
    'total_deps': 'sum',
    'ftd_db': 'sum',
    'rd_db': 'sum'
}).round(0)

summary_by_format.columns = ['publishers', 'total_spend', 'total_deps', 'ftd', 'rd']
summary_by_format['avg_total_cpa'] = (summary_by_format['total_spend'] / summary_by_format['total_deps']).round(3)
summary_by_format['avg_ftd_cpa'] = (summary_by_format['total_spend'] / summary_by_format['ftd']).round(2)
summary_by_format['avg_rd_cpa'] = (summary_by_format['total_spend'] / summary_by_format['rd']).round(4)
summary_by_format['rd_rate'] = (summary_by_format['rd'] / summary_by_format['total_deps'] * 100).round(1)

print("Format  | Pubs | Spend      | Deps      | Total CPA | FTD CPA | RD CPA   | RD Rate")
print("-" * 90)

for fmt in ['POP', 'PUSH', 'VIDEO', 'BANNER', 'NATIVE', 'OTHER']:
    if fmt in summary_by_format.index:
        row = summary_by_format.loc[fmt]
        pubs = int(row['publishers'])
        spend = row['total_spend']
        deps = int(row['total_deps'])
        total_cpa = row['avg_total_cpa']
        ftd_cpa = row['avg_ftd_cpa']
        rd_cpa = row['avg_rd_cpa']
        rd_rate = row['rd_rate']

        print(f"{fmt:7s} | {pubs:4d} | ${spend:9,.0f} | {deps:9,d} | ${total_cpa:7.3f} | ${ftd_cpa:6.2f} | ${rd_cpa:7.4f} | {rd_rate:5.1f}%")

print()
print("=" * 80)
print()

# Recommendations summary
print("СВОДКА РЕКОМЕНДАЦИЙ ПО ФОРМАТАМ:")
print("=" * 80)
print()

for fmt in formats:
    format_recs = rec_df[rec_df['format'] == fmt]

    if len(format_recs) == 0:
        continue

    increase_high = len(format_recs[(format_recs['recommendation'].str.contains('УВЕЛИЧИТЬ')) & (format_recs['priority'] == 'HIGH')])
    increase_med = len(format_recs[(format_recs['recommendation'].str.contains('УВЕЛИЧИТЬ')) & (format_recs['priority'] == 'MEDIUM')])
    decrease_high = len(format_recs[(format_recs['recommendation'].str.contains('СНИЗИТЬ')) & (format_recs['priority'] == 'HIGH')])
    decrease_med = len(format_recs[(format_recs['recommendation'].str.contains('СНИЗИТЬ')) & (format_recs['priority'] == 'MEDIUM')])
    maintain = len(format_recs[format_recs['recommendation'] == 'ОСТАВИТЬ ставку'])
    observe = len(format_recs[format_recs['recommendation'] == 'НАБЛЮДАТЬ'])

    print(f"{fmt}:")
    print(f"  Увеличить (высокий):  {increase_high}")
    print(f"  Увеличить (средний):  {increase_med}")
    print(f"  Снизить (высокий):    {decrease_high}")
    print(f"  Снизить (средний):    {decrease_med}")
    print(f"  Оставить:             {maintain}")
    print(f"  Наблюдать:            {observe}")
    print()

print("=" * 80)
print()

print("Сохранено:")
print("  - publishers_by_format_with_spend.csv (все данные)")
print("  - publishers_recommendations_by_format.csv (рекомендации)")
print()
