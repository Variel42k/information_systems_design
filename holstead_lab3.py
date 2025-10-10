#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправленный скрипт расчёта метрик Холстеда (ЛР №3).
- Включает подробные комментарии.
- Формулы соответствуют обсуждённой методичке.
- В задании 3 используется выражение с делением ΣB / c(λ, R_{i-1}),
  что даёт отрицательные значения R_new и (для вариантов 1 и 2) отрицательные B_expected_next.
"""

import math
import argparse
from dataclasses import dataclass
from typing import List, Dict, Tuple


# -----------------------------
# 1) Структура данных варианта
# -----------------------------
@dataclass
class VariantData:
    # Параметры варианта лабораторной
    targets: int                 # число целей (объектов наблюдения)
    measurements_per_param: int  # число измерений на один параметр
    tracked_params: int          # число отслеживаемых параметров
    calculated_params: int       # число вычисляемых параметров
    R0: float                    # начальный рейтинг (R_0)
    lambda_lang: float           # языковой коэффициент λ
    n_programs: int              # число уже написанных программ
    volumes_kb: List[float]      # объёмы уже написанных программ (Кбайт)
    errors_list: List[int]       # найденные ошибки в этих программах
    planned_kb: int              # планируемый объём следующей программы (Кбайт)


# -----------------------------
# 2) Пример таблицы вариантов
# -----------------------------
TABLE: Dict[int, VariantData] = {
    # Здесь данные для варианта 2 (взяты из задания/приклада)
    2: VariantData(
        targets=25,
        measurements_per_param=28,
        tracked_params=8,
        calculated_params=3,
        R0=2000.0,
        lambda_lang=1.6,
        n_programs=3,
        volumes_kb=[4.0, 8.0, 10.0],
        errors_list=[1, 2, 4],
        planned_kb=14
    )
}


# -----------------------------
# 3) Вспомогательные функции
# -----------------------------
def log2(x: float) -> float:
    """Безопасный логарифм по основанию 2."""
    if x <= 0:
        raise ValueError("log2: аргумент должен быть > 0")
    return math.log(x, 2)


def compute_n2_star(data: VariantData) -> int:
    """
    Исправленная формула для n2* (минимальное число операндов).
    В методичке и условиях этой ЛР используется:
        n2* = targets * (measurements_per_param * tracked_params + calculated_params)
    Это даёт "реалистичную" оценку при множественных измерениях на параметр.
    """
    return data.targets * (data.measurements_per_param * data.tracked_params + data.calculated_params)


def halstead_potential_volume(n2_star: int) -> float:
    """Потенциальный объём по Холстеду: V* = (2 + n2*) * log2(2 + n2*)."""
    return (2 + n2_star) * log2(2 + n2_star)


def modules_count(n2_star: int) -> Tuple[float, int]:
    """Число модулей: сырое и округлённое вверх (k_raw и k_simple)."""
    k_raw = n2_star / 8.0
    return k_raw, math.ceil(k_raw)


def program_length(K: int) -> float:
    """
    Длина программы N = 220·K + K·log2(K).
    По методичке — базовая аппроксимация длины в условных единицах.
    """
    if K <= 0:
        raise ValueError("K должно быть > 0")
    return 220.0 * K + K * log2(K)


def asm_commands(N: float) -> float:
    """P = 3/8 * N — число ассемблерных команд."""
    return (3.0 / 8.0) * N


def calendar_time_days(N: float, m: int, nu: int) -> float:
    """
    Календарное время T_k (в днях): T_k = 3·N / (8·m·ν)
    m — число программистов, ν — производительность (команд в день).
    """
    if m <= 0 or nu <= 0:
        raise ValueError("m и nu должны быть > 0")
    return (3.0 * N) / (8.0 * m * nu)


def potential_errors_task1(V_star: float, lambda_lang: float) -> float:
    """B = (V*)^2 / (3000 · λ) — потенциальное число ошибок по V*."""
    return (V_star * V_star) / (3000.0 * lambda_lang)


def potential_errors_task2(V: float) -> float:
    """B = V / 3000 — потенциальное число ошибок по объёму V."""
    return V / 3000.0


def c_coef(variant: int, lambd: float, R: float) -> float:
    """
    Коэффициент c(λ, R) — три варианта (по условию лабораторной).
    Обратите внимание: при отрицательном R этот коэффициент может стать отрицательным:
      - variant 1: c = 1/(λ + R)
      - variant 2: c = 1/(λ * R)
      - variant 3: c = 1/λ + 1/R
    Это влияет на знак B_expected_next в задании 3.
    """
    if variant == 1:
        return 1.0 / (lambd + R)
    if variant == 2:
        return 1.0 / (lambd * R)
    if variant == 3:
        return (1.0 / lambd) + (1.0 / R)
    raise ValueError("Неизвестный вариант коэффициента c")


def compute_rating_and_expected_errors(data: VariantData, coef_variant: int, R_prev: float) -> Tuple[float, float]:
    """
    Задание 3 (реализация строго по методичке):
      R_i = R_{i-1} * [1 + 1e-3 * (Σ V_j − Σ B_k / c(λ, R_{i-1}))]
      B_{n+1} = c(λ, R_i) * V_{n+1}, где V_{n+1} = planned_kb

    Важно:
    - Здесь специально реализовано деление ΣB / c_prev (а не умножение),
      потому что методичка именно так формулирует выражение.
    - При малом (положительном) c_prev значение ΣB / c_prev может быть очень большим,
      что приведёт к отрицательному R_new. Это ожидаемое поведение модели.
    - Если R_new отрицателен, для вариантов 1 и 2 c(λ, R_new) также будет отрицательным,
      и B_expected_next (c · planned_kb) станет отрицательным — как вы и требовали.
    """
    # вычисляем c при предыдущем рейтинге
    c_prev = c_coef(coef_variant, data.lambda_lang, R_prev)

    # защита от деления на ноль (на практике для R_prev != 0 и λ != 0 это маловероятно)
    if abs(c_prev) < 1e-18:
        # если c_prev практически ноль — сообщаем об ошибке, чтобы не делить на ноль
        raise ZeroDivisionError("c(λ, R_prev) почти ноль — деление приведёт к ошибке. Проверьте входные данные.")

    # сумма объёмов уже написанных программ
    sum_V = sum(data.volumes_kb)

    # ПО МЕТОДИЧКЕ: Σ B_k / c_prev  (именно деление)
    sum_B_over_c = sum(data.errors_list) / c_prev

    # вычисление нового рейтинга R_i
    R_new = R_prev * (1.0 + 1e-3 * (sum_V - sum_B_over_c))

    # вычисление ожидаемого числа ошибок в следующей (планируемой) программе
    # по формуле B_{n+1} = c(λ, R_i) * V_{n+1}
    c_new = c_coef(coef_variant, data.lambda_lang, R_new)
    B_expected_next = c_new * data.planned_kb

    return R_new, B_expected_next


# -----------------------------
# Основной проход расчётов
# -----------------------------
def run_all_for_variant(data: VariantData, m: int, nu: int, work_day_hours: int) -> Dict:
    """
    Выполняет полный набор расчётов (Задание 1, Задание 2, Задание 3)
    и возвращает словарь с результатами.
    """
    # базовые проверки корректности входных данных
    if data.targets <= 0:
        raise ValueError("targets должен быть > 0")
    if data.measurements_per_param <= 0:
        raise ValueError("measurements_per_param должен быть > 0")
    if data.n_programs != len(data.volumes_kb) or data.n_programs != len(data.errors_list):
        raise ValueError("n_programs должен соответствовать длине volumes_kb и errors_list")
    if work_day_hours <= 0:
        raise ValueError("work_day_hours должен быть > 0")
    if m <= 0 or nu <= 0:
        raise ValueError("m и nu должны быть > 0")

    # 1) n2* (минимальное число операндов)
    n2_star = compute_n2_star(data)

    # 2) потенциальный объём V*
    V_star = halstead_potential_volume(n2_star)

    # 3) потенциальное число ошибок по V* и λ (Задание 1)
    B1 = potential_errors_task1(V_star, data.lambda_lang)

    # 4) число модулей (k_raw и округление вверх)
    k_raw, k_simple = modules_count(n2_star)

    # 5) иерархическая аппроксимация (если применимо)
    K_hier = math.ceil(n2_star / 8.0 + n2_star / (8.0 ** 2))
    # выбираем K_hier при больших k_raw, иначе простое округление вверх
    K_used = K_hier if k_raw > 8.0 else k_simple

    # 6) длина программы N
    N = program_length(K_used)

    # 7) объём ПО V (по приближению из методички)
    V = K_used * 220.0 * log2(48.0)

    # 8) число ассемблерных команд P
    P_asm = asm_commands(N)

    # 9) календарное время (в днях и часах)
    Tk_days = calendar_time_days(N, m, nu)
    Tk_hours = Tk_days * work_day_hours

    # 10) потенциальное количество ошибок по объёму (B2)
    B2 = potential_errors_task2(V)

    # 11) начальная надёжность t_k (в часах)
    if B2 <= 1.0:
        t_k = float('inf')  # логарифм не определён/неподходящая область — считаем бесконечностью
    else:
        t_k = Tk_hours / (2.0 * math.log(B2))

    # 12) Задание 3 — расчёт рейтингов и ожидаемых ошибок для трёх вариантов c
    ratings = {}
    for variant in (1, 2, 3):
        try:
            R_new, B_expected = compute_rating_and_expected_errors(data, variant, data.R0)
        except ZeroDivisionError as e:
            # в случае проблем (очень малое c_prev) возвращаем None и сообщение
            R_new, B_expected = None, None
        ratings[variant] = {"R_new": R_new, "B_expected_next": B_expected}

    # собираем результаты в словарь
    return {
        "n2_star": n2_star,
        "V_star": V_star,
        "B1_from_Vstar_lambda": B1,
        "k_raw": k_raw,
        "k_simple": k_simple,
        "K_used": K_used,
        "N": N,
        "V": V,
        "P_asm": P_asm,
        "Tk_days": Tk_days,
        "Tk_hours": Tk_hours,
        "B2_from_V": B2,
        "t_k_hours": t_k,
        "ratings": ratings
    }


# -----------------------------
# CLI и вывод результатов
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Расчёт метрик Холстеда (ЛР №3) — исправленная версия")
    parser.add_argument("-v", "--variant", type=int, default=2, choices=list(TABLE.keys()), help="Номер варианта (по таблице)")
    parser.add_argument("-m", "--programmers", type=int, default=3, help="Число программистов (m)")
    parser.add_argument("-n", "--nu", type=int, default=20, help="Производительность ν (команд в день)")
    parser.add_argument("-w", "--work-hours", type=int, default=8, help="Часов в рабочем дне")
    args = parser.parse_args()

    data = TABLE[args.variant]
    results = run_all_for_variant(data, args.programmers, args.nu, args.work_hours)

    # Печатный вывод с пояснениями
    print("=== РЕЗУЛЬТАТЫ РАСЧЁТА МЕТРИК ХОЛСТЕДА ===\n")
    print(f"Вариант: {args.variant}")
    print(f"Исходные: targets={data.targets}, measurements_per_param={data.measurements_per_param}, "
          f"tracked_params={data.tracked_params}, calculated_params={data.calculated_params}")
    print()

    print("=== Задание 1 ===")
    print(f"n2* = {results['n2_star']}")
    print(f"V* = (2 + n2*)·log2(2 + n2*) = {results['V_star']:.6f}")
    print(f"B1 (по V* и λ) = (V*)^2 / (3000·λ) = {results['B1_from_Vstar_lambda']:.6f}")
    print()

    print("=== Задание 2 ===")
    print(f"k_raw = {results['k_raw']:.6f}, k_simple = {results['k_simple']}, K_used = {results['K_used']}")
    print(f"N = 220·K + K·log2(K) = {results['N']:.6f}")
    print(f"V ≈ K·220·log2(48) = {results['V']:.6f} (условные единицы)")
    print(f"P (асм) = 3/8·N = {results['P_asm']:.6f}")
    print(f"T_k = {results['Tk_days']:.6f} дней = {results['Tk_hours']:.6f} часов")
    print(f"B2 (по V) = V/3000 = {results['B2_from_V']:.6f}")
    t_k_val = results['t_k_hours']
    print(f"t_k (начальная надёжность, часы) = {('inf' if t_k_val == float('inf') else f'{t_k_val:.6f}')}")
    print()

    print("=== Задание 3 (рейтинги и ожидаемые ошибки) ===")
    # Для каждого варианта c выводим R_new и B_expected_next.
    # Для вариантов 1 и 2 B_expected_next ожидаемо может быть отрицательным (если c получили отрицательное значение).
    for variant, vals in results["ratings"].items():
        Rn = vals["R_new"]
        Be = vals["B_expected_next"]
        if Rn is None:
            print(f"Variant {variant}: вычисление не удалось (деление на ноль или недопустимые значения)")
        else:
            print(f"Variant {variant}: R_new = {Rn:.6f}, B_expected_next = {Be:.6f}")

    print("\nПримечание: в соответствии с формулами методички отрицательные значения R_new и B_expected_next")
    print("для некоторых вариантов являются корректным результатом модели (означают деградацию/отрицательную динамику).")


if __name__ == "__main__":
    main()
