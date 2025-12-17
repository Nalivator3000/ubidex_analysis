import pandas as pd

print("=" * 80)
print("СРАВНЕНИЕ ПЕРИОДОВ: Абсолютные числа + Проценты")
print("=" * 80)
print()

# Load all summary files
aug_summary = pd.read_csv('all_aug18-23_reactivations_summary.csv', index_col=0)
sep_summary = pd.read_csv('all_sep18-23_reactivations_summary.csv', index_col=0)
oct_summary = pd.read_csv('all_oct18-23_reactivations_summary.csv', index_col=0)
nov_summary = pd.read_csv('all_nov18-23_reactivations_summary.csv', index_col=0)

# Get desired order
desired_order = ['0-7 days', '7-14 days', '14-30 days', '30-90 days', '90+ days']

# Create comparison dataframe with counts
comparison = pd.DataFrame({
    'Aug_count': aug_summary.reindex(desired_order)['count'],
    'Aug_%': aug_summary.reindex(desired_order)['percentage'],
    'Sep_count': sep_summary.reindex(desired_order)['count'],
    'Sep_%': sep_summary.reindex(desired_order)['percentage'],
    'Oct_count': oct_summary.reindex(desired_order)['count'],
    'Oct_%': oct_summary.reindex(desired_order)['percentage'],
    'Nov_count': nov_summary.reindex(desired_order)['count'],
    'Nov_%': nov_summary.reindex(desired_order)['percentage'],
})

# Calculate control average (count and %)
comparison['Control_avg_count'] = ((comparison['Aug_count'] +
                                     comparison['Sep_count'] +
                                     comparison['Oct_count']) / 3).round(0)

# Calculate control average percentage
control_total = (aug_summary['count'].sum() + sep_summary['count'].sum() + oct_summary['count'].sum()) / 3
comparison['Control_avg_%'] = (comparison['Control_avg_count'] / control_total * 100).round(1)

# Calculate differences from November
comparison['Diff_Nov_vs_Avg'] = comparison['Nov_count'] - comparison['Control_avg_count']
comparison['Diff_Nov_vs_Aug'] = comparison['Nov_count'] - comparison['Aug_count']
comparison['Diff_Nov_vs_Sep'] = comparison['Nov_count'] - comparison['Sep_count']
comparison['Diff_Nov_vs_Oct'] = comparison['Nov_count'] - comparison['Oct_count']

# Add totals row
totals = pd.Series({
    'Aug_count': aug_summary['count'].sum(),
    'Aug_%': 100.0,
    'Sep_count': sep_summary['count'].sum(),
    'Sep_%': 100.0,
    'Oct_count': oct_summary['count'].sum(),
    'Oct_%': 100.0,
    'Nov_count': nov_summary['count'].sum(),
    'Nov_%': 100.0,
    'Control_avg_count': (aug_summary['count'].sum() + sep_summary['count'].sum() + oct_summary['count'].sum()) / 3,
    'Control_avg_%': 100.0,
    'Diff_Nov_vs_Avg': nov_summary['count'].sum() - (aug_summary['count'].sum() + sep_summary['count'].sum() + oct_summary['count'].sum()) / 3,
    'Diff_Nov_vs_Aug': nov_summary['count'].sum() - aug_summary['count'].sum(),
    'Diff_Nov_vs_Sep': nov_summary['count'].sum() - sep_summary['count'].sum(),
    'Diff_Nov_vs_Oct': nov_summary['count'].sum() - oct_summary['count'].sum(),
}, name='TOTAL')

comparison = pd.concat([comparison, totals.to_frame().T])

# Print formatted table
print("СРАВНИТЕЛЬНАЯ ТАБЛИЦА:")
print()
print(comparison.to_string())
print()

# Save
comparison.to_csv('period_comparison_with_percentages.csv')
print("=" * 80)
print("Сохранено: period_comparison_with_percentages.csv")
print("=" * 80)
print()

# Print key insights
print("КЛЮЧЕВЫЕ ИНСАЙТЫ:")
print()
print("90+ дней:")
print(f"  Август:   {int(comparison.loc['90+ days', 'Aug_count']):,} ({comparison.loc['90+ days', 'Aug_%']:.1f}%)")
print(f"  Сентябрь: {int(comparison.loc['90+ days', 'Sep_count']):,} ({comparison.loc['90+ days', 'Sep_%']:.1f}%)")
print(f"  Октябрь:  {int(comparison.loc['90+ days', 'Oct_count']):,} ({comparison.loc['90+ days', 'Oct_%']:.1f}%)")
print(f"  Контроль: {int(comparison.loc['90+ days', 'Control_avg_count']):,} ({comparison.loc['90+ days', 'Control_avg_%']:.1f}%)")
print(f"  Ноябрь:   {int(comparison.loc['90+ days', 'Nov_count']):,} ({comparison.loc['90+ days', 'Nov_%']:.1f}%)")
print()
print(f"  Прирост от среднего: {int(comparison.loc['90+ days', 'Diff_Nov_vs_Avg']):+,}")
print(f"  Прирост %: {(comparison.loc['90+ days', 'Diff_Nov_vs_Avg'] / comparison.loc['90+ days', 'Control_avg_count'] * 100):.1f}%")
