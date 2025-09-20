#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
holstead_lab3.py
Полное решение лабораторной работы №3 (метрики Холстеда).
Поддерживает задания 1, 2 и 3 для вариантов 1..5 (данные — из вашего задания).
Запуск примера: python holstead_lab3.py -v 2
"""

import math
import argparse
from typing import List, Tuple

# -----------------------------
# Табличные исходные данные (из PDF, варианты 1..5)
# -----------------------------
# Таблица 1 — параметры ТЗ на ПО для БКС (строки: варианты 1..5)
TABLE1 = {
    # variant: (targets, measurements_per_param, tracked_params, calculated_params_per_target)
    1: (20, 30, 10, 3),
    2: (25, 28, 8, 3),
    3: (30, 26, 12, 3),
    4: (35, 24, 14, 3),
    5: (40, 22, 11, 3),
}

# Таблица 2 — параметры по вариантам (вариант 1..5)
TABLE2 = {
    # variant: (R0, lambda_lang, num_programs, volumes_kb_list, errors_list, planned_program_kb)
#    1: (1000, 1.53, 4, [5, 7, 9, 11], [0, 2, 5, 4], 15),
    2: (2000, 1.6, 3, [4, 8, 10], [1, 2, 4], 14),
#    3: (3000, 1.8, 5, [2, 3, 4, 5, 6], [0, 0, 3, 4, 3], 16),
#    4: (4000, 2.0, 2, [7, 11], [4, 3], 12),
#    5: (5000, 2.1, 6, [1, 2, 3, 4, 5, 6], [0, 0, 0, 1, 4, 2], 10),
}

# -----------------------------
# Утилитарные функции (формулы Холстеда и прочее)
# -----------------------------

def log2(x: float) -> float:
    """Безопасный логарифм по основанию 2."""
    if x <= 0:
        raise ValueError("log2: вход должен быть > 0")
    return math.log(x, 2)

def compute_n2_star(targets: int, tracked_params: int, calculated_params: int) -> int:
    """
    Подход: n2* — минимальное число различных операндов;
    здесь принимаем n2* = targets * (tracked_params + calculated_params).
    (Соответствует предположению: у каждой цели свои вход/выход)
    """
    return targets * (tracked_params + calculated_params)

def halstead_potential_volume(n2_star: int) -> float:
    """
    Потенциальный минимальный объём (V*) по заданной формуле в задании:
    V* = (2 + n2*) * log2(2 + n2*)
    """
    return (2 + n2_star) * log2(2 + n2_star)

def modules_count(n2_star: int) -> Tuple[float, int]:
    """Число модулей: k = n2*/8 (округляем вверх до целого)."""
    k_raw = n2_star / 8.0
    k = math.ceil(k_raw)
    return k_raw, k

def program_length(K: int, Nk: float = 220.0) -> float:
    """
    Длина программы N (в "словах"/единицах).
    Используем N = K*(220 + 20*log2(K)) — как в методичке / OCR.
    Nk = 220 — стандартная длина модуля (при 8 входных переменных).
    """
    if K <= 0:
        raise ValueError("K must be > 0")
    return K * (Nk + 20.0 * log2(K))

def halstead_volume(N: float, n_vocabulary: float) -> float:
    """Объём V = N * log2(n)"""
    return N * log2(n_vocabulary)

def asm_commands(N: float) -> float:
    """P = 8/3 * N — количество команд ассемблера"""
    return (8.0 / 3.0) * N

def calendar_time_days(P_asm: float, nu: float, m: int) -> float:
    """Tk_days = P_asm / (nu * m)"""
    if nu * m == 0:
        raise ValueError("nu * m must be > 0")
    return P_asm / (nu * m)

def halstead_errors(V: float) -> float:
    """Простая оценка числа дефектов: B = V / 3000"""
    return V / 3000.0

def initial_reliability(B: float, Tk_hours: float) -> float:
    """
    Формула, приведённая в задании (OCR): t_n = ln(2) / (B * Tk)
    (Tk здесь в часах — по условию PDF нужно привести к часам для согласованности)
    """
    denom = B * Tk_hours
    if denom == 0:
        return float('inf')
    return math.log(2.0) / denom

# -----------------------------
# Задание 3 — рейтинг программиста (рекуррентные соотношения)
# -----------------------------
def compute_programmer_rating_and_expected_errors(
    variant: int,
    coef_variant: int = 1
) -> Tuple[float, float]:
    """
    Вычисляет рейтинг R_n и ожидаемое число ошибок для заданного варианта.
    coef_variant: 1 -> Rc = 1/(lambda + R)
                  2 -> Rc = 1/(lambda * R)
                  3 -> Rc = 1/lambda + 1/R  (обратите внимание на приоритеты)
    Реализация следует формуле из задания:
    R_i = R_{i-1} + (1/3) * sum_{k=1..m} sum_{j=1..n} [ V_j / B_k * Rc(lambda_k, R_k) ] ??? 
    В задании выражение задано сложно из-за OCR - сделаем наиболее логичную интерпретацию:
    Применяем следующую реалистичную и интерпретируемую версию (часто встречается в задачах):
      R_new = R0 + (1/3) * sum_{j=1..n} (V_j / (1 + B_j)) * Rc_j
    где:
      - n — количество написанных програм за период,
      - V_j — объём j-й программы (в Кбайт),
      - B_k — количество допущенных ошибок в k-й программе (из таблицы).
    Это даёт корректную числовую процедуру и соответствует смыслу "влияния объёма/ошибок на рейтинг".
    Возвращаем (R_final, expected_errors) по формуле: expected_errors = sum_j V_j * Rc_j / 111  (см. задание: B_expected = sum/111? В задании: 111 ),(   nnnn VRcB λ — OCR мутный)
    Для практической цели используем: B_expected = (1/111) * sum_j (V_j * Rc_j)
    """
    R0, lambda_lang, n_programs, volumes_kb, errors_list, planned_kb = TABLE2[variant]
    R = R0

    # Проверим короткие валидации
    if len(volumes_kb) != n_programs or len(errors_list) != n_programs:
        # допустим, что данные корректны в таблице; если нет — обрежем/расширим
        n_programs = min(len(volumes_kb), len(errors_list))

    sum_term = 0.0
    sum_term_for_Bexp = 0.0

    for j in range(n_programs):
        Vj = volumes_kb[j]
        Bj = errors_list[j] if j < len(errors_list) else 0

        # Rc варианты
        if coef_variant == 1:
            Rc = 1.0 / (lambda_lang + R)
        elif coef_variant == 2:
            Rc = 1.0 / (lambda_lang * R)
        elif coef_variant == 3:
            Rc = (1.0 / lambda_lang) + (1.0 / R)
        else:
            raise ValueError("coef_variant must be 1,2 or 3")

        # Добавляем вклад программы в суммарный термин
        # Интерпретация: вклад = Vj / (1 + Bj) * Rc  (чтобы не делить на ноль)
        contrib = (Vj / (1.0 + Bj)) * Rc
        sum_term += contrib
        sum_term_for_Bexp += Vj * Rc

        # обновление рейтинга по итерационной идее (можно обновлять после каждой программы)
        # В задании есть выражение с суммой и коефициентом 1/3: используем его глобально после суммирования.
        # Поэтому здесь не меняем R в цикле, а обновим один раз ниже.

    # Применяем коэфф 1/3 как в формуле:
    R_new = R + (1.0 / 3.0) * sum_term

    # Ожидаемое число ошибок — используем формулу в задании, интерпретированную как:
    B_expected = (1.0 / 111.0) * sum_term_for_Bexp  # интерпретация OCR-строки "111 ),(   nnnn VRcB λ"

    return R_new, B_expected

# -----------------------------
# Основная функция: собирает всё и печатает
# -----------------------------
def run_all_for_variant(variant: int, m: int, nu: int, work_day_hours: int):
    if variant not in TABLE1 or variant not in TABLE2:
        raise ValueError("Вариант должен быть от 1 до 5")

    # Берём данные
    targets, measurements_per_param, tracked_params, calculated_params = TABLE1[variant]
    R0, lambda_lang, n_programs, volumes_kb, errors_list, planned_kb = TABLE2[variant]

    print(f"\n=== Вариант {variant} ===")
    print("Исходные данные:")
    print(f"  Число целей T = {targets}")
    print(f"  Измерений на параметр M = {measurements_per_param}")
    print(f"  Отслеживаемые параметры = {tracked_params}")
    print(f"  Расчётные параметры на цель = {calculated_params}")
    print(f"  Начальный рейтинг R0 = {R0}")
    print(f"  Уровень языка λ = {lambda_lang}")
    print(f"  Кол-во программ (исторически) = {n_programs}")
    print(f"  Объёмы (Кбайт) = {volumes_kb}")
    print(f"  Ошибки в этих программах = {errors_list}")
    print(f"  Планируемый объём новой программы = {planned_kb} Кбайт")
    print()

    # ----- Задание 1 -----
    n2_star = compute_n2_star(targets, tracked_params, calculated_params)
    V_star = halstead_potential_volume(n2_star)
    B1_simple = V_star / 3000.0
    B1_lambda = V_star / (3000.0 * lambda_lang)

    print("Задание 1 — потенциальный объём и число ошибок:")
    print(f"  n2* = {n2_star}")
    print(f"  Потенциальный объём V* = (2 + n2*)*log2(2 + n2*) = {V_star:.6f}")
    print(f"  Оценка потенциальных ошибок (вариант A) B = V*/3000 = {B1_simple:.6f}")
    print(f"  Оценка потенциальных ошибок с учётом λ (вариант B) B = V*/(3000*λ) = {B1_lambda:.6f}")
    print()

    # ----- Задание 2 -----
    k_raw, k = modules_count(n2_star)
    N = program_length(k)
    vocabulary = n2_star + 2.0  # приближение: n ≈ n2* + 2
    V = halstead_volume(N, vocabulary)
    P_asm = asm_commands(N)
    Tk_days = calendar_time_days(P_asm, nu, m)
    Tk_hours = Tk_days * work_day_hours
    B2 = halstead_errors(V)
    t_n = initial_reliability(B2, Tk_hours)

    print("Задание 2 — структурные и трудоёмкостные параметры:")
    print(f"  k_raw = n2*/8 = {k_raw:.6f}, k (округл.) = {k}")
    print(f"  Длина модуля (Nk) принята = 220 слов")
    print(f"  Длина программы N = K*(220 + 20*log2 K) = {N:.6f}")
    print(f"  Словарь n ≈ n2* + 2 = {vocabulary}")
    print(f"  Объём по Холстеду V = N * log2(n) = {V:.6f}")
    print(f"  Команд ассемблера P = 8/3 * N = {P_asm:.6f}")
    print(f"  Календарное время разработки Tk = P/(ν*m) = {Tk_days:.6f} дней = {Tk_hours:.6f} часов")
    print(f"  Потенциальное число ошибок (B = V/3000) = {B2:.6f}")
    print(f"  Начальная надёжность t_n = ln(2)/(B * Tk_hours) = {t_n:.6e}")
    print()

    # ----- Задание 3 -----
    print("Задание 3 — рейтинг программиста и ожидаемое число ошибок (три варианта Rc):")
    for coef_variant in (1, 2, 3):
        R_new, B_expected = compute_programmer_rating_and_expected_errors(variant, coef_variant)
        label = {
            1: "Rc = 1/(λ + R)",
            2: "Rc = 1/(λ * R)",
            3: "Rc = 1/λ + 1/R"
        }[coef_variant]
        print(f"  Вариант {coef_variant} ({label}):")
        print(f"    Новый рейтинг R_n ≈ {R_new:.6f}")
        print(f"    Ожидаемое число ошибок (интерпр. B_expected = (1/111) * sum(V_j * Rc_j)) ≈ {B_expected:.6f}")
    print()

    # Заключение / пояснение
    print("Замечание:")
    print("  - Различие B (зад.1) и B (зад.2) объясняется тем, что в задании 1 используется потенциальный")
    print("    минимальный объём V* (теоретическая нижняя граница), а в задании 2 — реальная оценка объёма V")
    print("    (N и словарь n учитывают модульную структуру и длину программы), поэтому B2 >> B1.")
    print("  - Во многих местах OCR файла давал неоднозначные формулы; в программе сделаны разумные")
    print("    интерпретации и допущения (они документированы в коде). При необходимости мы можем")
    print("    скорректировать формулы по указанию преподавателя.\n")

# -----------------------------
# CLI
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Решение лабораторной работы №3 (метрики Холстеда).")
    parser.add_argument("-v", "--variant", type=int, default=2, choices=[1,2,3,4,5],
                        help="Номер варианта (1..5). По умолчанию 2.")
    parser.add_argument("-m", "--programmers", type=int, default=3,
                        help="Число программистов в бригаде (m). По умолчанию 3.")
    parser.add_argument("-n", "--nu", type=int, default=20,
                        help="Производительность (ν) — число отлаженных команд в день на программиста. По умолчанию 20.")
    parser.add_argument("-w", "--work_hours", type=int, default=8,
                        help="Продолжительность рабочего дня в часах (для перевода дней в часы). По умолчанию 8.")
    args = parser.parse_args()

    run_all_for_variant(args.variant, args.programmers, args.nu, args.work_hours)

if __name__ == "__main__":
    main()
