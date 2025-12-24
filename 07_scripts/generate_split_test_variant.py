#!/usr/bin/env python3
"""
Генератор SQL запросов для разных вариантов сплит-теста
Создает SQL файл с заданными параметрами для контрольной и тестовой групп
"""
import sys
import io
import argparse

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def expand_char_range(char_spec):
    """
    Расширяет диапазон символов в список.
    Поддерживает:
    - '0-7' -> ['0', '1', '2', '3', '4', '5', '6', '7']
    - 'a-z' -> ['a', 'b', 'c', ..., 'z']
    - '0,1,2' -> ['0', '1', '2']
    - Комбинации: '0-7,8,9,a-z' -> все символы
    - '8-9a-z' -> ['8', '9', 'a', 'b', ..., 'z']
    """
    result = []
    # Сначала разбиваем по запятым
    parts = char_spec.split(',')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        # Обрабатываем части без запятых, но с возможными диапазонами
        # Например: '8-9a-z' нужно разбить на '8-9' и 'a-z'
        import re
        # Находим все диапазоны вида "цифра-цифра" или "буква-буква"
        ranges = re.findall(r'([0-9a-z])-([0-9a-z])', part, re.IGNORECASE)
        single_chars = re.findall(r'[^0-9a-z-]', part, re.IGNORECASE)
        
        # Обрабатываем диапазоны
        for start, end in ranges:
            start = start.lower()
            end = end.lower()
            if start.isdigit() and end.isdigit():
                # Числовой диапазон
                for i in range(int(start), int(end) + 1):
                    result.append(str(i))
            elif start.isalpha() and end.isalpha():
                # Буквенный диапазон
                for i in range(ord(start), ord(end) + 1):
                    result.append(chr(i))
        
        # Обрабатываем одиночные символы (не входящие в диапазоны)
        # Удаляем уже обработанные диапазоны из строки
        processed_part = part
        for start, end in ranges:
            processed_part = processed_part.replace(f'{start}-{end}', '')
        
        # Добавляем оставшиеся одиночные символы
        for char in processed_part:
            if char.isalnum() and char not in result:
                result.append(char.lower())
    
    return sorted(set(result))  # Убираем дубликаты и сортируем

def generate_sql(char_position, control_chars, test_chars, exclude_top_percent=0, exclude_bottom_percent=0, output_file=None):
    """
    Генерирует SQL запрос для сплит-теста с заданными параметрами
    """
    # Расширяем диапазоны символов
    control_list = expand_char_range(control_chars)
    test_list = expand_char_range(test_chars)
    
    control_chars_expanded = ','.join(control_list)
    test_chars_expanded = ','.join(test_list)
    
    # Генерируем SQL
    sql_template = f"""-- Анализ сплит-теста: сравнение контрольной и тестовой групп
-- Настройки:
-- - Позиция символа с конца: {char_position}
-- - Контрольная группа: {control_chars} ({len(control_list)} символов)
-- - Тестовая группа: {test_chars} ({len(test_list)} символов)
-- - Исключить топ {exclude_top_percent}% самых активных
-- - Исключить низ {exclude_bottom_percent}% самых неактивных

WITH 
-- 1. Настройки групп
char_expansion AS (
    SELECT 
        '{control_chars_expanded}' as control_chars_expanded,
        '{test_chars_expanded}' as test_chars_expanded,
        {char_position} as char_position
),

-- 2. Получаем все депозиты с определением группы
deposits_with_groups AS (
    SELECT 
        ue.external_user_id as user_id,
        ue.event_date,
        ue.converted_amount as deposit_amount,
        ue.advertiser,
        -- Извлекаем символ на нужной позиции с конца
        CASE 
            WHEN LENGTH(ue.external_user_id) >= ce.char_position 
            THEN LOWER(SUBSTRING(ue.external_user_id FROM LENGTH(ue.external_user_id) - ce.char_position + 1 FOR 1))
            ELSE NULL
        END as char_at_position,
        -- Определяем группу
        CASE 
            -- Контрольная группа: символ входит в список control_chars
            WHEN LENGTH(ue.external_user_id) >= ce.char_position 
                 AND LOWER(SUBSTRING(ue.external_user_id FROM LENGTH(ue.external_user_id) - ce.char_position + 1 FOR 1)) = ANY(
                     string_to_array(ce.control_chars_expanded, ',')
                 ) THEN 'Control'
            -- Тестовая группа: символ входит в список test_chars
            WHEN LENGTH(ue.external_user_id) >= ce.char_position 
                 AND LOWER(SUBSTRING(ue.external_user_id FROM LENGTH(ue.external_user_id) - ce.char_position + 1 FOR 1)) = ANY(
                     string_to_array(ce.test_chars_expanded, ',')
                 ) THEN 'Test'
            ELSE 'Unknown'
        END as test_group
    FROM public.user_events ue
    CROSS JOIN char_expansion ce
    WHERE ue.event_type = 'deposit'
      AND ue.converted_amount > 0
      AND ue.external_user_id IS NOT NULL
      AND LENGTH(ue.external_user_id) >= ce.char_position
),

-- 3. Агрегируем по пользователям для расчета активности
user_totals AS (
    SELECT 
        user_id,
        test_group,
        COUNT(*) as deposit_count,
        SUM(deposit_amount) as total_deposits_usd,
        MIN(event_date) as first_deposit_date,
        MAX(event_date) as last_deposit_date
    FROM deposits_with_groups
    WHERE test_group IN ('Control', 'Test')
    GROUP BY user_id, test_group
),

-- 4. Исключаем выбросы (топ и низ активных игроков)
user_percentiles AS (
    SELECT 
        user_id,
        test_group,
        deposit_count,
        total_deposits_usd,
        first_deposit_date,
        last_deposit_date,
        PERCENT_RANK() OVER (PARTITION BY test_group ORDER BY total_deposits_usd) as activity_percentile
    FROM user_totals
),

-- 5. Фильтруем выбросы
filtered_users AS (
    SELECT 
        user_id,
        test_group,
        deposit_count,
        total_deposits_usd,
        first_deposit_date,
        last_deposit_date
    FROM user_percentiles
    WHERE 
        activity_percentile <= (1.0 - {exclude_top_percent} / 100.0)
        AND activity_percentile >= {exclude_bottom_percent} / 100.0
),

-- 6. Возвращаемся к депозитам отфильтрованных пользователей
filtered_deposits AS (
    SELECT 
        d.user_id,
        d.test_group,
        d.event_date,
        d.deposit_amount,
        d.advertiser
    FROM deposits_with_groups d
    INNER JOIN filtered_users fu ON d.user_id = fu.user_id AND d.test_group = fu.test_group
),

-- 7. Финальная агрегация по группам
group_comparison AS (
    SELECT 
        test_group,
        COUNT(DISTINCT user_id) as unique_users,
        COUNT(*) as total_deposits,
        SUM(deposit_amount) as total_deposits_usd,
        AVG(deposit_amount) as avg_deposit_amount,
        COUNT(*)::NUMERIC / NULLIF(COUNT(DISTINCT user_id), 0) as avg_deposits_per_user,
        SUM(deposit_amount)::NUMERIC / NULLIF(COUNT(DISTINCT user_id), 0) as avg_total_per_user,
        MIN(event_date) as min_date,
        MAX(event_date) as max_date
    FROM filtered_deposits
    GROUP BY test_group
)

-- Итоговый результат
SELECT 
    test_group as "Группа",
    unique_users as "Уникальных пользователей",
    total_deposits as "Всего депозитов",
    ROUND(total_deposits_usd::NUMERIC, 2) as "Сумма депозитов (USD)",
    ROUND(avg_deposit_amount::NUMERIC, 2) as "Средний депозит (USD)",
    ROUND(avg_deposits_per_user::NUMERIC, 2) as "Среднее депозитов на пользователя",
    ROUND(avg_total_per_user::NUMERIC, 2) as "Средняя сумма на пользователя (USD)",
    min_date as "Первая дата",
    max_date as "Последняя дата"
FROM group_comparison
ORDER BY test_group;
"""
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(sql_template)
        print(f"✓ SQL запрос сохранен в: {output_file}")
    else:
        print(sql_template)
    
    return sql_template

def main():
    parser = argparse.ArgumentParser(description='Генератор SQL запросов для сплит-теста')
    parser.add_argument('--position', type=int, default=1, 
                       help='Позиция символа с конца (1 = последний, 2 = предпоследний, и т.д.)')
    parser.add_argument('--control', required=True,
                       help='Символы для контрольной группы (например: "0-7" или "0,1,2,3,4,5,6,7")')
    parser.add_argument('--test', required=True,
                       help='Символы для тестовой группы (например: "8-9a-z" или "8,9,a,b,c,...,z")')
    parser.add_argument('--exclude-top', type=float, default=0,
                       help='Исключить топ N%% самых активных (по умолчанию 0)')
    parser.add_argument('--exclude-bottom', type=float, default=0,
                       help='Исключить низ N%% самых неактивных (по умолчанию 0)')
    parser.add_argument('--output', '-o',
                       help='Имя выходного файла (если не указано, выводится в консоль)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("ГЕНЕРАТОР SQL ЗАПРОСОВ ДЛЯ СПЛИТ-ТЕСТА")
    print("=" * 80)
    print()
    print(f"Позиция символа: {args.position}")
    print(f"Контрольная группа: {args.control}")
    print(f"Тестовая группа: {args.test}")
    print(f"Исключить топ: {args.exclude_top}%")
    print(f"Исключить низ: {args.exclude_bottom}%")
    print()
    
    generate_sql(
        args.position,
        args.control,
        args.test,
        args.exclude_top,
        args.exclude_bottom,
        args.output
    )
    
    print()
    print("=" * 80)
    print("ГОТОВО!")
    print("=" * 80)

if __name__ == "__main__":
    main()

