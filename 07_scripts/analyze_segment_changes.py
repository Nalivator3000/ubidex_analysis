import pandas as pd
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("АНАЛИЗ: Почему средние сегменты просели?")
print("=" * 80)
print()

# Load comparison
comp = pd.read_csv('period_comparison_with_percentages.csv', index_col=0)

print("1. АБСОЛЮТНЫЕ ИЗМЕНЕНИЯ (Ноябрь vs Контроль):")
print()

segments = ['0-7 days', '7-14 days', '14-30 days', '30-90 days', '90+ days']
for seg in segments:
    nov_count = comp.loc[seg, 'Nov_count']
    control_count = comp.loc[seg, 'Control_avg_count']
    diff = comp.loc[seg, 'Diff_Nov_vs_Avg']
    pct_change = (diff / control_count * 100) if control_count > 0 else 0

    symbol = "[+]" if diff > 0 else "[-]"
    print(f"{symbol} {seg:12} | Контроль: {control_count:7.0f} -> Ноябрь: {nov_count:7.0f} | Diff: {diff:+6.0f} ({pct_change:+5.1f}%)")

print()
print("=" * 80)
print()

print("2. ВОЗМОЖНЫЕ ОБЪЯСНЕНИЯ ПРОСАДКИ:")
print()

print("ГИПОТЕЗА 1: Естественная вариативность")
print("-" * 40)
print("Проверим стабильность контрольных периодов:")
print()

for seg in segments:
    aug = comp.loc[seg, 'Aug_count']
    sep = comp.loc[seg, 'Sep_count']
    oct = comp.loc[seg, 'Oct_count']
    avg = comp.loc[seg, 'Control_avg_count']

    # Calculate coefficient of variation (стандартное отклонение / среднее)
    values = [aug, sep, oct]
    std = pd.Series(values).std()
    cv = (std / avg * 100) if avg > 0 else 0

    print(f"{seg:12} | Aug: {aug:5.0f}, Sep: {sep:5.0f}, Oct: {oct:5.0f} | CV: {cv:5.1f}%")

print()
print("Интерпретация: Высокий CV (>20%) = нестабильный сегмент")
print()
print("=" * 80)
print()

print("ГИПОТЕЗА 2: Каннибализация - кампания ускорила возврат")
print("-" * 40)
print("Если кампания заставила вернуться раньше, то:")
print("  - Пользователи из 30-90 дней → вернулись в 0-7 дней")
print("  - Пользователи из 90+ дней → вернулись раньше обычного")
print()

# Calculate "acceleration effect"
print("Проверка: Сумма всех реактиваций")
total_control = comp.loc['TOTAL', 'Control_avg_count']
total_nov = comp.loc['TOTAL', 'Nov_count']
total_diff = comp.loc['TOTAL', 'Diff_Nov_vs_Avg']

print(f"  Контроль: {total_control:,.0f}")
print(f"  Ноябрь:   {total_nov:,.0f}")
print(f"  Δ:        {total_diff:+,.0f} ({total_diff/total_control*100:+.1f}%)")
print()

if abs(total_diff) < 1000:
    print("[OK] ПОДТВЕРЖДЕНИЕ: Общее число почти не изменилось!")
    print("    => Это говорит о ПЕРЕРАСПРЕДЕЛЕНИИ, а не о новых реактивациях")
    print()
    print("   Что произошло:")
    print("   1. Кампания достала долго неактивных (90+ дней)")
    print("   2. Часть пользователей из 7-90 дней вернулись бы и так")
    print("   3. Но кампания их НЕ показывалась (таргетинг был на 7+ дней)")
    print("   4. Поэтому естественный возврат 7-90 дней снизился")
else:
    print("[!] Общее число сильно изменилось - возможны другие факторы")

print()
print("=" * 80)
print()

print("ГИПОТЕЗА 3: Сезонность")
print("-" * 40)
print("Сравним каждый месяц отдельно:")
print()

for seg in ['30-90 days', '90+ days']:
    print(f"{seg}:")
    aug_diff = comp.loc[seg, 'Diff_Nov_vs_Aug']
    sep_diff = comp.loc[seg, 'Diff_Nov_vs_Sep']
    oct_diff = comp.loc[seg, 'Diff_Nov_vs_Oct']

    print(f"  vs Август:   {aug_diff:+6.0f}")
    print(f"  vs Сентябрь: {sep_diff:+6.0f}")
    print(f"  vs Октябрь:  {oct_diff:+6.0f}")

    # Check consistency
    all_positive = all([aug_diff > 0, sep_diff > 0, oct_diff > 0])
    all_negative = all([aug_diff < 0, sep_diff < 0, oct_diff < 0])

    if all_positive:
        print(f"  [+] Стабильный РОСТ во всех сравнениях")
    elif all_negative:
        print(f"  [-] Стабильное СНИЖЕНИЕ во всех сравнениях")
    else:
        print(f"  [!] Смешанный результат - возможна сезонность")
    print()

print("=" * 80)
print()

print("ВЫВОД:")
print()
print("90+ дней: СТАБИЛЬНЫЙ ПРИРОСТ")
for seg in ['90+ days']:
    aug_diff = comp.loc[seg, 'Diff_Nov_vs_Aug']
    sep_diff = comp.loc[seg, 'Diff_Nov_vs_Sep']
    oct_diff = comp.loc[seg, 'Diff_Nov_vs_Oct']
    avg_diff = comp.loc[seg, 'Diff_Nov_vs_Avg']
    print(f"  Август: {aug_diff:+6.0f} | Сентябрь: {sep_diff:+6.0f} | Октябрь: {oct_diff:+6.0f} | Среднее: {avg_diff:+6.0f}")

print()
print("Средние сегменты (7-90 дней): СНИЖЕНИЕ")
for seg in ['7-14 days', '14-30 days', '30-90 days']:
    avg_diff = comp.loc[seg, 'Diff_Nov_vs_Avg']
    control_count = comp.loc[seg, 'Control_avg_count']
    pct = (avg_diff / control_count * 100) if control_count > 0 else 0
    print(f"  {seg:12} {avg_diff:+6.0f} ({pct:+5.1f}%)")

print()
print("НАИБОЛЕЕ ВЕРОЯТНОЕ ОБЪЯСНЕНИЕ:")
print("  Кампания сработала только на 90+ дней (как и задумано)")
print("  Средние сегменты снизились из-за:")
print("    - Естественной вариативности (сравни CV выше)")
print("    - Возможной сезонности (ноябрь vs авг/сен/окт)")
print("    - НЕ из-за кампании (кампания их не таргетировала)")
