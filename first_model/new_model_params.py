import math
import pandas as pd
from datetime import datetime, timedelta

shift1_start = "04:49"
shift1_end = "13:36"

shift2_start = "13:36"
shift2_end = "23:18"

cycle_time = 64  # мин
available_drivers = 24
schedule_type = "4*2"  # или "5*2"
is_weekday = True  # True = будний, False = выходной

intervals_weekday = [
    [6, 10], [8, 5], [10, 7], [17, 8], [20, 9], [23, 12]
]
intervals_weekend = [
    [6, 12], [8, 7], [10, 10], [17, 9], [20, 13], [23, 16]
]


def time_to_hours(time_str):
    h, m = map(int, time_str.split(":"))
    return h + m / 60


def time_duration(time_start, time_end):
    start = time_to_hours(time_start)
    end = time_to_hours(time_end)
    if end < start:
        end += 24
    return round(end - start, 2)


def calc_rest_required(shift_hours):
    return max(12, 2 * shift_hours if shift_hours > 6 else 12)


def check_schedule(start_time, work_hours):
    start = datetime.strptime(start_time, "%H:%M")
    end = start + timedelta(hours=float(work_hours))
    next_start = start + timedelta(days=1)

    rest_required = calc_rest_required(work_hours)
    rest_actual = (next_start - end).total_seconds() / 3600

    if rest_actual >= rest_required:
        return f"Допустимо. Отдых {rest_actual:.1f} ч (норма {rest_required:.1f} ч)"
    else:
        shift_needed = rest_required - rest_actual
        new_start = next_start + timedelta(hours=shift_needed)
        return (f"Недостаточно отдыха ({rest_actual:.1f} ч). "
                f"Следующую смену нужно начинать в {new_start.strftime('%H:%M')}")


def get_intervals(is_weekday):
    data = intervals_weekday if is_weekday else intervals_weekend
    intervals = []
    prev_hour = 0
    prev_int = 10 if is_weekday else 12
    for hour, interval in data:
        intervals.append(((prev_hour, hour), prev_int))
        prev_hour, prev_int = hour, interval
    intervals.append(((prev_hour, 24), prev_int))
    return intervals


def get_active_segments(start_h, end_h, intervals):
    active = []
    for (i_start, i_end), headway in intervals:
        seg_start = max(start_h, i_start)
        seg_end = min(end_h, i_end)
        if seg_end > seg_start:
            active.append(((seg_start, seg_end), headway))
    return active


def calc_vehicle_needs(shift_start, shift_end, is_weekday):
    start_h = time_to_hours(shift_start)
    end_h = time_to_hours(shift_end)
    if end_h < start_h:
        end_h += 24

    intervals = get_intervals(is_weekday)
    segments = get_active_segments(start_h, end_h, intervals)

    total_hours = 0
    weighted_vehicle_sum = 0
    for (s, e), headway in segments:
        duration = e - s  # часы
        total_hours += duration
        vehicles_needed = math.ceil(cycle_time / headway)
        weighted_vehicle_sum += vehicles_needed * duration

    avg_vehicles = weighted_vehicle_sum / total_hours
    return round(avg_vehicles, 2), total_hours


v1_vehicles, shift1_hours = calc_vehicle_needs(shift1_start, shift1_end, is_weekday)
v2_vehicles, shift2_hours = calc_vehicle_needs(shift2_start, shift2_end, is_weekday)

line_hours = shift1_hours + shift2_hours
avg_vehicles = (v1_vehicles + v2_vehicles) / 2

print("Тип дня:", "Будний" if is_weekday else "Выходной")
print(f"\n1-я смена: {shift1_start}–{shift1_end} = {shift1_hours:.2f} ч")
print(f"2-я смена: {shift2_start}–{shift2_end} = {shift2_hours:.2f} ч")
print(f"Общее время работы линии: {line_hours:.2f} ч")
print(f"Среднее количество трамваев в работе: {avg_vehicles:.2f}\n")


total_driver_hours = avg_vehicles * line_hours
norm_hours = 8  # допустимая рабочая норма (для сравнения)
drivers_needed = math.ceil(total_driver_hours / norm_hours)
enough = drivers_needed <= available_drivers

print(f"Всего водительских часов: {total_driver_hours:.1f}")
print(f"Необходимо водителей: {drivers_needed} (доступно {available_drivers}) — {'достаточно' if enough else 'не хватает'}\n")

print("Проверка режима труда и отдыха:")
print("Водитель 1:", check_schedule(shift1_start, shift1_hours))
print("Водитель 2:", check_schedule(shift2_start, shift2_hours))
