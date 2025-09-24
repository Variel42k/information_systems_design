#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jelinski_moranda.py
Решение задачи расчёта метрик Холстеда и параметров модели Джелинского-Моранды.
Код переписан для читаемости, тестируемости и расширяемости.
"""

import math
import argparse
from dataclasses import dataclass
from typing import List, Tuple, Dict

# =============================
# Исходные данные
# =============================
@dataclass
class VariantData:
    targets: int
    measurements_per_param: int
    tracked_params: int
    calculated_params: int
    R0: float
    lambda_lang: float
    n_programs: int
    volumes_kb: List[float]
    errors_list: List[int]
    planned_kb: int

# Таблицы исходных данных
TABLE: Dict[int, VariantData] = {
    2: VariantData(
        targets=25,
        measurements_per_param=28,
        tracked_params=8,
        calculated_params=3,
        R0=2000,
        lambda_lang=1.6,
        n_programs=3,
        volumes_kb=[4, 8, 10],
        errors_list=[1, 2, 4],
        planned_kb=14
    )
}

# =============================
# Утилиты и формулы
# =============================

def log2(x: float) -> float:
    """Безопасный логарифм по основанию 2."""
    if x <= 0:
        raise ValueError("log2: вход должен быть > 0")
    return math.log(x, 2)

def compute_n2_star(data: VariantData) -> int:
    """Считает минимальное число операндов (n2*)."""
    return data.targets * (data.tracked_params + data.calculated_params)

def halstead_potential_volume(n2_star: int) -> float:
    """Потенциальный объём по Холстеду: V* = (2 + n2*) * log2(2 + n2*)."""
    return (2 + n2_star) * log2(2 + n2_star)

def modules_count(n2_star: int) -> Tuple[float, int]:
    """Число модулей: k_raw (дробное), k (округлённое вверх)."""
    k_raw = n2_star / 8.0
    return k_raw, math.ceil(k_raw)

def program_length(K: int, Nk: float = 220.0) -> float:
    """Длина программы N = K * (Nk + 20*log2(K))."""
    return K * (Nk + 20.0 * log2(K))

def halstead_volume(N: float, n_vocabulary: float) -> float:
    """Объём V = N * log2(n)."""
    return N * log2(n_vocabulary)

def asm_commands(N: float) -> float:
    """Количество команд ассемблера: P = 8/3 * N."""
    return (8.0 / 3.0) * N

def calendar_time_days(P_asm: float, nu: int, m: int) -> float:
    """Календарное время разработки (дни): Tk = P / (nu * m)."""
    return P_asm / (nu * m)

def halstead_errors(V: float) -> float:
    """Оценка числа ошибок: B = V / 3000."""
    return V / 3000.0

def initial_reliability(B: float, Tk_hours: float) -> float:
    """Начальная надёжность: t_n = ln(2) / (B * Tk)."""
    denom = B * Tk_hours
    return float('inf') if denom == 0 else math.log(2.0) / denom

def compute_programmer_rating_and_expected_errors(data: VariantData, coef_variant: int) -> Tuple[float, float]:
    """Вычисляет новый рейтинг программиста и ожидаемое число ошибок."""
    R = data.R0
    Rc_funcs = {
        1: lambda l, r: 1 / (l + r),
        2: lambda l, r: 1 / (l * r),
        3: lambda l, r: (1 / l) + (1 / r)
    }
    Rc = Rc_funcs[coef_variant](data.lambda_lang, R)

    sum_term = sum((Vj / (1 + Bj)) * Rc for Vj, Bj in zip(data.volumes_kb, data.errors_list))
    sum_term_for_Bexp = sum(Vj * Rc for Vj in data.volumes_kb)

    R_new = R + (1.0 / 3.0) * sum_term
    B_expected = (1.0 / 111.0) * sum_term_for_Bexp
    return R_new, B_expected

# =============================
# Основная функция
# =============================

def run_all_for_variant(data: VariantData, m: int, nu: int, work_day_hours: int) -> Dict:
    n2_star = compute_n2_star(data)
    V_star = halstead_potential_volume(n2_star)
    k_raw, k = modules_count(n2_star)
    N = program_length(k)
    vocabulary = n2_star + 2.0
    V = halstead_volume(N, vocabulary)
    P_asm = asm_commands(N)
    Tk_days = calendar_time_days(P_asm, nu, m)
    Tk_hours = Tk_days * work_day_hours
    B2 = halstead_errors(V)
    t_n = initial_reliability(B2, Tk_hours)

    results = {
        "n2_star": n2_star,
        "V_star": V_star,
        "B1_simple": V_star / 3000.0,
        "B1_lambda": V_star / (3000.0 * data.lambda_lang),
        "k_raw": k_raw,
        "k": k,
        "N": N,
        "vocabulary": vocabulary,
        "V": V,
        "P_asm": P_asm,
        "Tk_days": Tk_days,
        "Tk_hours": Tk_hours,
        "B2": B2,
        "t_n": t_n,
        "ratings": {}
    }

    for coef_variant in (1, 2, 3):
        R_new, B_expected = compute_programmer_rating_and_expected_errors(data, coef_variant)
        results["ratings"][coef_variant] = {
            "R_new": R_new,
            "B_expected": B_expected
        }

    return results

# =============================
# CLI
# =============================

def main():
    parser = argparse.ArgumentParser(description="Расчёт метрик Холстеда и модели Джелинского-Моранды.")
    parser.add_argument("-v", "--variant", type=int, default=2, choices=TABLE.keys(), help="Номер варианта (1..5)")
    parser.add_argument("-m", "--programmers", type=int, default=3, help="Число программистов (m)")
    parser.add_argument("-n", "--nu", type=int, default=20, help="Производительность ν (команд в день)")
    parser.add_argument("-w", "--work_hours", type=int, default=8, help="Часов в рабочем дне")
    args = parser.parse_args()

    data = TABLE[args.variant]
    results = run_all_for_variant(data, args.programmers, args.nu, args.work_hours)

    print("=== РЕЗУЛЬТАТЫ ===")
    for key, value in results.items():
        if key == "ratings":
            print("\nРейтинг программиста:")
            for variant, vals in value.items():
                print(f"  Вариант {variant}: R_new={vals['R_new']:.4f}, B_expected={vals['B_expected']:.4f}")
        else:
            print(f"{key} = {value}")

if __name__ == "__main__":
    main()