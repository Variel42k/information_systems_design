#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Оптимизированная программа для расчётов по модели Джелинского–Моранды.
- Использует метод Ньютона для оценки B̂.
- Считает коэффициент K̂, среднее время до следующей ошибки и время до окончания тестирования.
Оптимизации:
- Меньше повторных проходов по данным (предварительное вычисление индексов и Xi).
- math.fsum для повышения точности.
- Чище структура и документация.
"""

import math
from typing import List, Dict, Tuple

def solve_B_newton(X: List[float], tol: float = 1e-10, maxiter: int = 200) -> Tuple[float, int, bool]:
    """Численно находит оценку максимального правдоподобия для B методом Ньютона."""
    n = len(X)
    Sx = math.fsum(X)
    data = [(i, Xi) for i, Xi in enumerate(X, start=1)]  # предварительно вычисляем индексы

    def f_and_s2(B: float) -> Tuple[float, float]:
        s1 = 0.0
        s2 = 0.0
        for i, Xi in data:
            denom = B - i + 1
            s1 += 1.0 / denom
            s2 += denom * Xi
        return s1 - (n * Sx) / s2, s2

    def fprime(B: float, s2: float) -> float:
        s1 = 0.0
        for i, _ in data:
            denom = B - i + 1
            s1 += 1.0 / (denom * denom)
        return -s1 + (n * (Sx**2)) / (s2**2)

    B = max(n + 1.0, n + Sx / max(1, n))

    for it in range(1, maxiter + 1):
        val, s2 = f_and_s2(B)
        if abs(val) < tol:
            return B, it, True

        deriv = fprime(B, s2)
        if abs(deriv) < 1e-16:
            deriv = 1e-16 if deriv >= 0 else -1e-16

        B_new = B - val / deriv
        if B_new <= n:
            B_new = (B + n + 1e-6) / 2.0

        if abs(B_new - B) < 1e-12:
            return B_new, it, True
        B = B_new

    return B, maxiter, False

def harmonic_sum(m: int) -> float:
    """Вычисляет гармоническую сумму H_m = Σ 1/k."""
    return math.fsum(1.0 / k for k in range(1, m + 1)) if m > 0 else 0.0

def compute(X: List[float]) -> Dict[str, float]:
    """Вычисляет все параметры модели Джелинского–Моранды."""
    n = len(X)
    B_hat, iterations, converged = solve_B_newton(X)

    denom = math.fsum((B_hat - i + 1) * Xi for i, Xi in enumerate(X, start=1))
    K_hat = n / denom

    remaining = B_hat - n
    X_next = math.inf if remaining <= 0 else 1.0 / (K_hat * remaining)

    B_int = max(n + 1, math.ceil(B_hat))
    m = B_int - n
    time_to_finish = harmonic_sum(m) / K_hat

    return {
        "n": n,
        "B_hat": B_hat,
        "B_int": B_int,
        "iterations": iterations,
        "converged": converged,
        "K_hat": K_hat,
        "X_next": X_next,
        "time_to_finish": time_to_finish,
        "remaining_real": remaining,
        "m": m,
    }

if __name__ == "__main__":
    variants = {
        2: [7,10,12,6,7,3,5,9,5,7,2,6,1,8,3,1,2,3,5,1,84,30,7,3,1],
    }

    for v, X in variants.items():
        r = compute(X)
        print(
            f"Variant {v}: "
            f"n={r['n']}, B_hat={r['B_hat']:.6f}, B_int={r['B_int']}, "
            f"K={r['K_hat']:.6e}, X_next={r['X_next']:.6f}, "
            f"time_to_finish={r['time_to_finish']:.6f}"
        )