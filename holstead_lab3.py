#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправленный расчёт метрик Холстеда (вариант для прямого запуска / импорта).
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict

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

# Пример: данные варианта 2 (взяты из PDF задания).
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

def log2(x: float) -> float:
    if x <= 0:
        raise ValueError("log2: вход должен быть > 0")
    return math.log(x, 2)

def compute_n2_star(data: VariantData) -> int:
    # ИСПРАВЛЕНИЕ: учитываем measurements_per_param
    return data.targets * (data.measurements_per_param * data.tracked_params + data.calculated_params)

def halstead_potential_volume(n2_star: int) -> float:
    return (2 + n2_star) * log2(2 + n2_star)

def modules_count(n2_star: int) -> Tuple[float, int]:
    k_raw = n2_star / 8.0
    return k_raw, math.ceil(k_raw)

def program_length(K: int) -> float:
    if K <= 0:
        raise ValueError("K must be > 0")
    return 220.0 * K + K * log2(K)

def asm_commands(N: float) -> float:
    return (3.0 / 8.0) * N

def calendar_time_days(N: float, m: int, nu: int) -> float:
    if m <= 0 or nu <= 0:
        raise ValueError("m и nu должны быть > 0")
    return (3.0 * N) / (8.0 * m * nu)

def potential_errors_task1(V_star: float, lambda_lang: float) -> float:
    return (V_star * V_star) / (3000.0 * lambda_lang)

def potential_errors_task2(V: float) -> float:
    return V / 3000.0

def c_coef(variant: int, lambd: float, R: float) -> float:
    if variant == 1:
        return 1.0 / (lambd + R)
    if variant == 2:
        return 1.0 / (lambd * R)
    if variant == 3:
        return (1.0 / lambd) + (1.0 / R)
    raise ValueError("Неизвестный вариант c")

def compute_rating_and_expected_errors(data: VariantData, coef_variant: int, R_prev: float) -> Tuple[float, float]:
    # c_prev = c(λ, R_{i-1})
    c_prev = c_coef(coef_variant, data.lambda_lang, R_prev)
    sum_V = sum(data.volumes_kb)
    # Σ B_k / c_prev == sum(errors) / c_prev
    sum_B_over_c = sum(data.errors_list) / c_prev
    R_new = R_prev * (1.0 + 1e-3 * (sum_V - sum_B_over_c))
    # опционально: не допускать отрицательного рейтинга
    # R_new = max(R_new, 0.0)
    B_expected_next = c_coef(coef_variant, data.lambda_lang, R_new) * data.planned_kb
    return R_new, B_expected_next

def run_all_for_variant(data: VariantData, m: int, nu: int, work_day_hours: int) -> Dict:
    if data.targets <= 0 or data.tracked_params < 0 or data.calculated_params < 0:
        raise ValueError("Некорректные входные данные по параметрам")
    if work_day_hours <= 0:
        raise ValueError("Часы в рабочем дне должны быть > 0")
    if data.n_programs != len(data.volumes_kb) or data.n_programs != len(data.errors_list):
        raise ValueError("Длины volumes_kb и errors_list должны соответствовать n_programs")

    n2_star = compute_n2_star(data)
    V_star = halstead_potential_volume(n2_star)

    B1 = potential_errors_task1(V_star, data.lambda_lang)

    k_raw, k_simple = modules_count(n2_star)
    K_hier = math.ceil(n2_star / 8.0 + n2_star / (8.0 ** 2))
    K = K_hier if k_raw > 8.0 else k_simple

    N = program_length(K)
    V = K * 220.0 * log2(48.0)
    P_asm = asm_commands(N)
    Tk_days = calendar_time_days(N, m, nu)
    Tk_hours = Tk_days * work_day_hours
    B2 = potential_errors_task2(V)

    if B2 <= 1.0:
        t_k = float('inf')
    else:
        t_k = Tk_hours / (2.0 * math.log(B2))

    results = {
        "n2_star": n2_star,
        "V_star": V_star,
        "B1_from_Vstar_lambda": B1,
        "k_raw": k_raw,
        "k_simple": k_simple,
        "K_used": K,
        "N": N,
        "V": V,
        "P_asm": P_asm,
        "Tk_days": Tk_days,
        "Tk_hours": Tk_hours,
        "B2_from_V": B2,
        "t_k": t_k,
        "ratings": {}
    }

    for coef_variant in (1,2,3):
        R_new, B_expected = compute_rating_and_expected_errors(data, coef_variant, data.R0)
        results["ratings"][coef_variant] = {
            "R_new": R_new,
            "B_expected_next": B_expected
        }

    return results

# Пример запуска (если хотите):
if __name__ == "__main__":
    data = TABLE[2]
    res = run_all_for_variant(data, m=3, nu=20, work_day_hours=8)
    for k,v in res.items():
        if k != "ratings":
            print(k, "=", v)
    print("ratings:")
    for cv,vals in res["ratings"].items():
        print(cv, vals)
