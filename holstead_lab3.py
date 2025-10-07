#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Расчёт метрик Холстеда
(обновлённая версия с небольшими проверками и подготовкой к CI)
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


# Таблицы исходных данных (вариант 2 как в ТЗ)
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
    """
    Длина программы N = K * (Nk + 20 * log2(K))
    (в методичке иногда используются множители типа 20 в логарифме)
    """
    if K <= 0:
        raise ValueError("K должно быть > 0 для расчёта длины программы")
    return K * (Nk + 20.0 * log2(K))


def asm_commands(N: float) -> float:
    """Количество команд ассемблера: P = 3/8 * N."""
    if N < 0:
        raise ValueError("N должно быть >= 0")
    return (3.0 / 8.0) * N


def calendar_time_days(P_asm: float, nu: int, m: int) -> float:
    """Календарное время разработки (дни): T_k = P / (ν * m)."""
    if nu <= 0 or m <= 0:
        raise ValueError("nu и m должны быть > 0")
    return P_asm / (nu * m)


def potential_errors_task1(V_star: float, lambda_lang: float) -> float:
    """Задание 1(в): B = (V*)^2 / (3000 · λ)."""
    if lambda_lang <= 0:
        raise ValueError("lambda_lang должна быть > 0")
    return (V_star * V_star) / (3000.0 * lambda_lang)


def potential_errors_task2(V: float) -> float:
    """Задание 2(е): B = V / 3000."""
    return V / 3000.0


def c_coef(variant: int, lambd: float, R: float) -> float:
    """Коэффициент c(λ, R) для Задания 3 (три варианта)."""
    if lambd <= 0 or R <= 0:
        raise ValueError("lambda и R должны быть > 0 для расчёта c")
    if variant == 1:
        return 1.0 / (lambd + R)
    if variant == 2:
        return 1.0 / (lambd * R)
    if variant == 3:
        return (1.0 / lambd) + (1.0 / R)
    raise ValueError("Неизвестный вариант коэффициента c")


def compute_rating_and_expected_errors(data: VariantData, coef_variant: int, R_prev: float) -> Tuple[float, float]:
    """
    Задание 3:
    R_i = R_{i-1} * [1 + 1e-3 * (Σ V_j − Σ B_k / c(λ, R_{i-1}))],
    B_{n+1} = c(λ, R_i) * V_{n+1}, где V_{n+1} = planned_kb.
    """
    c_prev = c_coef(coef_variant, data.lambda_lang, R_prev)
    sum_V = sum(data.volumes_kb)
    # Защита: если c_prev == 0, это даст деление на 0
    if c_prev == 0:
        raise ZeroDivisionError("Коэффициент c_prev равен 0, деление невозможно")

    sum_B_over_c = sum(Bk / c_prev for Bk in data.errors_list)
    R_new = R_prev * (1.0 + 1e-3 * (sum_V - sum_B_over_c))

    # 🔹 Защита от отрицательного или нулевого значения R_new
    if R_new <= 0:
        R_new = max(abs(R_new), 1e-6)

    c_new = c_coef(coef_variant, data.lambda_lang, R_new)
    B_expected_next = c_new * data.planned_kb

    return R_new, B_expected_next


# =============================
# Основная функция
# =============================

def run_all_for_variant(data: VariantData, m: int, nu: int, work_day_hours: int) -> Dict:
    """
    Выполняет все расчёты для данного варианта и возвращает словарь результатов.
    """
    # Валидация входных данных
    if data.targets <= 0 or data.tracked_params < 0 or data.calculated_params < 0:
        raise ValueError("Некорректные входные данные по параметрам цели/операндов")
    if work_day_hours <= 0:
        raise ValueError("Часы в рабочем дне должны быть > 0")
    if data.n_programs != len(data.volumes_kb) or data.n_programs != len(data.errors_list):
        raise ValueError("Длины volumes_kb и errors_list должны соответствовать n_programs")

    n2_star = compute_n2_star(data)
    V_star = halstead_potential_volume(n2_star)

    # Задание 1(в): потенциальное число ошибок по V* и λ
    B1 = potential_errors_task1(V_star, data.lambda_lang)

    # Задание 2(а): число модулей
    k_raw, k_simple = modules_count(n2_star)
    # Иерархическая аппроксимация при k_raw > 8: K ≈ n2*/8 + n2*/8^2
    K_hier = math.ceil(n2_star / 8.0 + n2_star / (8.0 ** 2))
    K = K_hier if k_raw > 8.0 else k_simple

    # Задание 2(б): длина программы
    N = program_length(K)

    # Задание 2(в): объём ПО по формуле V ≈ K · 220 · log2(48)
    V = K * 220.0 * log2(48.0)

    # Задание 2(г): число команд ассемблера
    P_asm = asm_commands(N)

    # Задание 2(д): календарное время программирования (в днях) и перевод в часы
    Tk_days = calendar_time_days(P_asm, nu, m)
    Tk_hours = Tk_days * work_day_hours

    # Задание 2(е): потенциальное количество ошибок по V
    B2 = potential_errors_task2(V)

    # Задание 2(ж): начальная надёжность (время наработки на отказ)
    # t_k = T_k / (2 · ln B). Защитимся от B <= 1 (ln <= 0).
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

    # Задание 3: три варианта коэффициента c(λ, R)
    for coef_variant in (1, 2, 3):
        R_new, B_expected = compute_rating_and_expected_errors(data, coef_variant, data.R0)
        results["ratings"][coef_variant] = {
            "R_new": R_new,
            "B_expected_next": B_expected
        }

    return results


# =============================
# CLI
# =============================

def main():
    parser = argparse.ArgumentParser(description="Метрики Холстеда (Задания 1–3) по методичке.")
    parser.add_argument("-v", "--variant", type=int, default=2, choices=list(TABLE.keys()), help="Номер варианта")
    parser.add_argument("-m", "--programmers", type=int, default=3, help="Число программистов (m)")
    parser.add_argument("-n", "--nu", type=int, default=20, help="Производительность ν (команд в день)")
    parser.add_argument("-w", "--work_hours", type=int, default=8, help="Часов в рабочем дне")
    args = parser.parse_args()

    data = TABLE[args.variant]
    results = run_all_for_variant(data, args.programmers, args.nu, args.work_hours)

    # Задание 1
    print("=== МЕТРИКИ ХОЛСТЕДА — Задание 1 ===")
    print(f"V* = (2 + n2*) · log2(2 + n2*) = {results['V_star']:.6f}")
    print(f"B1 = (V*)^2 / (3000·λ) = {results['B1_from_Vstar_lambda']:.6f}")

    # Задание 2
    print("\n=== ПАРАМЕТРЫ ПО — Задание 2 ===")
    print(f"k_raw = {results['k_raw']:.6f}, k_simple = {results['k_simple']}, K_used = {results['K_used']}")
    # Исправленная формула вывода для N (соответствует реализации program_length)
    print(f"N = K * (220 + 20*log2(K)) = {results['N']:.6f}")
    print(f"V ≈ K·220·log2(48) = {results['V']:.6f}")
    print(f"P (команд ассемблера) = 3·N/8 = {results['P_asm']:.6f}")
    print(f"T_k (дни) = P/(ν·m) = {results['Tk_days']:.6f}")
    print(f"T_k (часы) = {results['Tk_hours']:.6f}")
    print(f"B2 = V/3000 = {results['B2_from_V']:.6f}")
    print(f"t_k = T_k/(2·ln B2) (в часах) = {results['t_k']:.6f}")

    # Задание 3
    print("\n=== РЕЙТИНГ И ОЖИДАЕМЫЕ ОШИБКИ — Задание 3 ===")
    for variant, vals in results["ratings"].items():
        print(f"  Коэффициент вариант {variant}: R_new = {vals['R_new']:.6f}, B_expected_next = {vals['B_expected_next']:.6f}")


if __name__ == "__main__":
    main()
