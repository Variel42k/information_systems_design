#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модель Джелинского–Моранды (Jelinski–Moranda model)

Реализует:
- численное определение оценки общего числа ошибок (B̂) методом Ньютона;
- вычисление коэффициента пропорциональности (K̂);
- среднее время до следующей ошибки (Xₙ₊₁);
- оценку времени до окончания тестирования.

Подходит для автоматических CI-проверок (pytest / GitHub Actions).
"""

import math
from typing import List, Dict, Tuple

__all__ = ["compute"]


# ---------------------------------------------------------------------
# Основная численная функция — решение уравнения для B̂
# ---------------------------------------------------------------------
def solve_B_newton(X: List[float], tol: float = 1e-10, maxiter: int = 200) -> Tuple[float, int, bool]:
    """Находит оценку максимального правдоподобия для B̂ методом Ньютона."""
    n = len(X)
    Sx = math.fsum(X)
    data = [(i, Xi) for i, Xi in enumerate(X, start=1)]

    def f_and_s2(B: float) -> Tuple[float, float]:
        """Возвращает значение функции f(B) и промежуточную сумму s2."""
        s1 = s2 = 0.0
        for i, Xi in data:
            denom = B - i + 1
            s1 += 1.0 / denom
            s2 += denom * Xi
        return s1 - (n * Sx) / s2, s2

    def fprime(B: float, s2: float) -> float:
        """Производная функции f(B)."""
        s1 = math.fsum(1.0 / ((B - i + 1) ** 2) for i, _ in data)
        return -s1 + (n * (Sx ** 2)) / (s2 ** 2)

    # Начальное приближение (чуть выше n)
    B = n + 2.0

    for it in range(1, maxiter + 1):
        val, s2 = f_and_s2(B)
        if abs(val) < tol:
            return B, it, True

        deriv = fprime(B, s2)
        if abs(deriv) < 1e-16:
            deriv = 1e-16

        B_new = B - val / deriv
        if B_new <= n:
            B_new = (B + n + 1.0) / 2.0

        if abs(B_new - B) < 1e-12:
            return B_new, it, True

        B = B_new

    return B, maxiter, False


# ---------------------------------------------------------------------
# Основная функция вычислений
# ---------------------------------------------------------------------
def compute(X: List[float]) -> Dict[str, float]:
    """
    Вычисляет параметры модели Джелинского–Моранды.

    Аргументы:
        X — список интервалов между ошибками (Xi, часы)

    Возвращает:
        dict с параметрами:
        {
            "n": количество ошибок,
            "B_hat": оценка общего числа ошибок,
            "K_hat": коэффициент пропорциональности,
            "X_next": среднее время до следующей ошибки,
            "time_to_finish": оценка времени до конца тестирования,
            "iterations": число итераций,
            "converged": признак сходимости
        }
    """
    n = len(X)
    B_hat, iterations, converged = solve_B_newton(X)

    denom = math.fsum((B_hat - i + 1) * Xi for i, Xi in enumerate(X, start=1))
    K_hat = n / denom

    remaining = B_hat - n
    X_next = math.inf if remaining <= 0 else 1.0 / (K_hat * remaining)

    # Гармоническая и логарифмическая аппроксимации для времени до конца тестирования
    if remaining > 0:
        H_m = math.fsum(1.0 / k for k in range(1, int(remaining) + 1))
        # Выбираем большее из гармонической и логарифмической оценок (устойчивее)
        time_to_finish = max(H_m, math.log(B_hat / (B_hat - n))) / K_hat
    else:
        time_to_finish = 0.0

    return {
        "n": n,
        "B_hat": B_hat,
        "K_hat": K_hat,
        "X_next": X_next,
        "time_to_finish": time_to_finish,
        "iterations": iterations,
        "converged": converged,
        "remaining": remaining,
    }


# ---------------------------------------------------------------------
# Демонстрационный запуск для ручной проверки
# ---------------------------------------------------------------------
if __name__ == "__main__":
    variants = {
        1: [9,12,11,4,7,2,5,8,5,7,1,6,1,9,4,1,3,3,6,1,1,11,33,7,91,2],
        2: [7,10,12,6,7,3,5,9,5,7,2,6,1,8,3,1,2,3,5,1,84,30,7,3,1],
        3: [5,4,11,13,6,2,7,5,8,7,1,4,2,7,6,2,3,1,4,78,25,10,7,16,3,1,2],
        4: [5,8,12,7,6,4,3,7,8,5,2,9,3,6,5,2,4,3,77,2,9,8,10,1,5,3,4,2],
        5: [4,13,10,5,8,1,6,7,4,9,5,2,3,8,6,3,2,3,94,5,12,8,28,3],
    }

    for v, X in variants.items():
        res = compute(X)
        print(
            f"Variant {v}: "
            f"B̂={res['B_hat']:.6f}, "
            f"K̂={res['K_hat']:.6e}, "
            f"Xₙ₊₁={res['X_next']:.6f}, "
            f"T_finish={res['time_to_finish']:.6f}, "
            f"Converged={res['converged']} (iter={res['iterations']})"
        )
