from typing import List, Dict, Any, Optional
from statistics import mean


DOC = """ГОСТ 28195-89 — расчет показателей надежности ПС для лабораторной работы №5.
Реализованы формулы (номера соответствуют документу пользователя):
(1) Н0401 — вероятность безотказной работы: 1 - Q/N
(2) Н0501 — оценка по среднему времени восстановления: min(1, TдопВ / ТВ)
(3) ТВ — среднее время восстановления: (1/N) * sum(TВi)
(4) Н0502 — оценка по продолжительности преобразования: min(1, Tдопп / Tпi) для каждого i
(5) m_kq — усреднение значений ОЭ: среднее по значениям одного оценочного элемента
(6) Оценка метрики — среднее по входящим в нее ОЭ
(7) Абсолютный показатель критерия — взвешенное среднее по метрикам
(8) Относительный показатель критерия — Абсолютный / Pбаз
(9) Фактор качества — взвешенное среднее относительных показателей критериев (в нашей работе — один критерий)
"""


def h0401_prob_no_failure(Q: int, N: int) -> float:
    if N <= 0:
        raise ValueError("N must be > 0")
    if Q < 0 or Q > N:
        raise ValueError("Q must be in [0, N]")
    return 1.0 - (Q / N)


def tv_mean(Tv_samples: List[float]) -> float:
    if not Tv_samples:
        raise ValueError("Tv_samples must be non-empty")
    return float(mean(Tv_samples))


def h0501_restore_time_score(Tv_avg: float, T_dopV: float) -> float:
    if T_dopV <= 0 or Tv_avg <= 0:
        raise ValueError("Times must be > 0")
    print(Tv_avg)
    print(T_dopV)
    return min(1.0, T_dopV / Tv_avg)


def h0502_transform_time_scores(Tpi_samples: List[float], T_dopp: float) -> List[float]:
    if T_dopp <= 0:
        raise ValueError("T_dopp must be > 0")
    if not Tpi_samples:
        raise ValueError("Tpi_samples must be non-empty")
    return [min(1.0, T_dopp / max(1e-12, ti)) for ti in Tpi_samples]


def average(values: List[float]) -> float:
    if not values:
        raise ValueError("Cannot average empty list")
    return float(mean(values))


def metric_score(oe_values: List[float]) -> float:
    return average(oe_values)


def weighted_average(values: List[float], weights: Optional[List[float]] = None) -> float:
    if not values:
        raise ValueError("values must be non-empty")
    if weights is None:
        return average(values)
    if len(weights) != len(values):
        raise ValueError("weights and values length mismatch")
    s = sum(weights)
    if s <= 0:
        raise ValueError("sum of weights must be > 0")
    return sum(v * w for v, w in zip(values, weights)) / s


def compute_all(
    Q: int,
    N: int,
    Tv_samples: List[float],
    T_dopV: float,
    Tpi_samples: List[float],
    T_dopp: float,
    P_baz: float = 0.94,
    metric_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    n0401 = h0401_prob_no_failure(Q, N)
    tv_avg = tv_mean(Tv_samples)
    n0501 = h0501_restore_time_score(tv_avg, T_dopV)
    n0502_list = h0502_transform_time_scores(Tpi_samples, T_dopp)
    n0502_avg = average(n0502_list)

    metric4 = metric_score([n0401])
    metric5 = metric_score([n0501, n0502_avg])

    if metric_weights is None:
        w4 = w5 = 0.5
    else:
        w4 = metric_weights.get("4", 0.0)
        w5 = metric_weights.get("5", 0.0)
        s = w4 + w5
        if s <= 0:
            raise ValueError("Sum of metric weights must be > 0")
        w4 /= s
        w5 /= s

    absolute_criterion = weighted_average([metric4, metric5], [w4, w5])

    if P_baz <= 0:
        raise ValueError("P_baz (базовый показатель) must be > 0")
    relative_criterion = absolute_criterion / P_baz
    quality_factor = relative_criterion

    return {
        "Н0401 — вероятность безотказной работы": n0401,
        "ТВ — среднее время восстановления, с": tv_avg,
        "Н0501 — по среднему времени восстановления": n0501,
        "Н0502 — по времени преобразования (среднее по всем наборам)": n0502_avg,
        "Метрика 4 — функционирование в заданных режимах": metric4,
        "Метрика 5 — обработка заданного объема информации": metric5,
        "Абсолютный показатель критерия «работоспособность»": absolute_criterion,
        "Относительный показатель критерия «работоспособность»": relative_criterion,
        "Фактор качества (надежность ПС)": quality_factor,
        "Н0502 — min": min(n0502_list),
        "Н0502 — max": max(n0502_list),
        "Н0502 — count": len(n0502_list),
        "Примечание": "Метрика 4 = Н0401; Метрика 5 = среднее(Н0501, Н0502_среднее). Веса метрик равные по умолчанию.",
        "Справка": DOC.strip(),
    }


print(compute_all(Q=6, N=1200, Tv_samples=[
      0.8, 1.4], T_dopV=0.95, Tpi_samples=[8, 12], T_dopp=14))
