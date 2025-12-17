#!/usr/bin/env python3
"""Тестирование функции extract_format"""
import re

def extract_format(publisher_str):
    """Улучшенная функция определения формата"""
    name_upper = str(publisher_str).upper()
    
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

# Test cases
test_cases = [
    ('(120) RealPush-UGW-POP', 'POP'),
    ('(121) RealPush-UGW-Banner', 'BANNER'),
    ('(115) Pushub-UGW-Video', 'VIDEO'),
    ('(113) Pushub-UGW-Banner', 'BANNER'),
    ('(37) Kadam-UGW-PUSH', 'PUSH'),
    ('(36) Kadam-UGW-POP', 'POP'),
    ('(112) Adright-UGW-Video', 'VIDEO'),
    ('(18) TrafficStars-UGW-POP-Premium', 'POP'),
    ('(12) PropellerAds-UGW-In-Page-PUSH', 'PUSH'),
]

print("Тестирование функции extract_format:")
print()
for name, expected in test_cases:
    result = extract_format(name)
    status = "✓" if result == expected else "✗"
    print(f"{status} {name}")
    print(f"  Ожидается: {expected}, Получено: {result}")
    if result != expected:
        print(f"  ⚠ НЕСООТВЕТСТВИЕ!")
    print()

