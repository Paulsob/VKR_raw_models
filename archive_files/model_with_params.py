import math
import pandas as pd
from datetime import datetime

line_start = "04:49"
line_end = "13:36"
cycle_time = 64  # мин
available_drivers = 24
norm_range = range(6, 11)  # 6–10 ч
headway_range = range(4, 16)  # 4–15 мин

"""
    соблюсти график труда и отдыха
    учесть утренний инструтаж и ТО
    здесь тип графика работы только 4*2, надо остальные 
    динамическое изменение интервала: входной параметр на разные временные отрезки
    
    обеденный перерыв
    учесть кадры кондукторов
    вариативность трамваев: не все водители могут водить все трамваи
    резерв по ПС?
"""


def time_duration(time_start, time_end):
    start = datetime.strptime(time_start, "%H:%M")
    end = datetime.strptime(time_end, "%H:%M")
    delta = (end - start).total_seconds() / 3600
    if delta < 0:
        delta += 24
    return round(delta, 2)


line_hours = time_duration(line_start, line_end)
print(f"Время работы линии: {line_hours} часов\n")


def counting():
    results = []
    for headway in headway_range:
        vehicles_needed = math.ceil(cycle_time / headway)
        total_driver_hours = vehicles_needed * line_hours
        for norm in norm_range:
            drivers_needed = math.ceil(total_driver_hours / norm)
            enough_drivers = drivers_needed <= available_drivers
            results.append({
                "Интервал (мин)": headway,
                "Норма (ч)": norm,
                "Трамваев нужно": vehicles_needed,
                "Водителей нужно": drivers_needed,
                "Хватает?": "Да" if enough_drivers else "Нет"
            })

    df = pd.DataFrame(results)

    feasible = df[df["Хватает?"] == "Да"]

    if feasible.empty:
        return "Нет условий, при которых можно выйти на линию"

    best = feasible.sort_values(by=["Интервал (мин)", "Норма (ч)"]).iloc[0]
    return best


result = counting()
print("Минимальные условия для выхода на линию:\n", result)
