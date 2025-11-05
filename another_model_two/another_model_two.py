from datetime import datetime, timedelta
import random

# --- Исходные данные ---
start_time = "04:48"
end_time = "01:34"
change_time = "12:48"
one_way_route_duration = random.randint(76, 80)
min_norm_work = 6
max_norm_work = 10
intervals_by_time = [[4, 13], [8, 5], [10, 10], [17, 5], [20, 12], [23, 18]]

# --- Предварительные вычисления ---
# полный круг (туда-обратно + 2 мин на манёвр)
total_route_duration = one_way_route_duration * 2 + 2

form_start_time = datetime.strptime(start_time, "%H:%M")
form_end_time = datetime.strptime(end_time, "%H:%M")
form_change_time = datetime.strptime(change_time, "%H:%M")

if form_end_time <= form_start_time:
    form_end_time += timedelta(days=1)

list_of_schedule_drivers = []
t = form_start_time


def get_interval_for_time(t):
    """Возвращает интервал (минут между отправлениями) в зависимости от текущего часа"""
    hour = t.hour + t.minute / 60
    for i, (start_hour, interval_val) in enumerate(intervals_by_time):
        if i == len(intervals_by_time) - 1 or hour < intervals_by_time[i + 1][0]:
            return interval_val
    return intervals_by_time[-1][1]


# --- Формируем расписание отправлений ---
while True:
    end_potential = t + timedelta(minutes=total_route_duration)
    if end_potential > form_end_time:
        break
    current_interval = get_interval_for_time(t)
    list_of_schedule_drivers.append({
        "start_park": t,
        "driver_id": None,
        "shift": None,
        "interval": current_interval
    })
    t += timedelta(minutes=current_interval)


# --- Новый оптимизированный симулятор назначения водителей ---
def simulate_with_chaining(departures, start_driver_id=1, min_norm_work=min_norm_work, max_norm_work=max_norm_work):
    """
    Greedy-алгоритм:
      - старается дозагружать существующих водителей, не превышая max_norm
      - при создании нового водителя формирует ему цепочку рейсов, чтобы достичь min_norm
    """
    departures = sorted(departures, key=lambda x: x["start_park"])
    n = len(departures)
    assigned = [False] * n
    drivers = []  # список (time_free, driver_id, first_start, total_hours)
    next_id = start_driver_id
    assignments = []
    starts = [d["start_park"] for d in departures]

    i = 0
    while i < n:
        if assigned[i]:
            i += 1
            continue

        entry = departures[i]
        departure = entry["start_park"]

        # --- ищем доступных водителей ---
        available = []
        for d in drivers:
            time_free, drv_id, first_start, total_hours = d
            if time_free <= departure:
                arr_terminal = departure + timedelta(minutes=one_way_route_duration)
                dep_terminal = arr_terminal + timedelta(minutes=random.randint(1, 3))
                arr_park = dep_terminal + timedelta(minutes=one_way_route_duration)
                new_total_hours = (arr_park - first_start).total_seconds() / 3600.0
                if new_total_hours <= max_norm_work + 1e-9:
                    available.append((d, new_total_hours, arr_park, dep_terminal, arr_terminal))

        chosen = None
        if available:
            # сортируем: приоритет — водители с недоработкой (<min_norm) и с наименьшими часами
            available.sort(key=lambda x: (x[0][3] >= min_norm_work, x[0][3]))
            chosen = available[0]

        if chosen is not None:
            d_tuple, new_total_hours, arr_park, dep_terminal, arr_terminal = chosen
            drivers.remove(d_tuple)
            free_driver = d_tuple[1]
            first_start = d_tuple[2]
            drivers.append((arr_park, free_driver, first_start, new_total_hours))

            departures[i]["driver_id"] = free_driver
            assignments.append({
                "id": free_driver,
                "start_park": departure,
                "end_terminal": arr_terminal,
                "start_terminal": dep_terminal,
                "end_park": arr_park
            })
            assigned[i] = True
            i += 1
            continue

        # --- создаём нового водителя и набиваем ему смену цепочкой ---
        free_driver = next_id
        next_id += 1
        first_start = departure
        arr_terminal = departure + timedelta(minutes=one_way_route_duration)
        dep_terminal = arr_terminal + timedelta(minutes=2)
        arr_park = dep_terminal + timedelta(minutes=one_way_route_duration)
        total_hours = (arr_park - first_start).total_seconds() / 3600.0

        departures[i]["driver_id"] = free_driver
        assignments.append({
            "id": free_driver,
            "start_park": departure,
            "end_terminal": arr_terminal,
            "start_terminal": dep_terminal,
            "end_park": arr_park
        })
        assigned[i] = True

        current_return = arr_park
        j = i + 1
        while j < n:
            if assigned[j]:
                j += 1
                continue
            next_departure = starts[j]
            if next_departure >= current_return:
                next_arr_terminal = next_departure + timedelta(minutes=one_way_route_duration)
                next_dep_terminal = next_arr_terminal + timedelta(minutes=2)
                next_arr_park = next_dep_terminal + timedelta(minutes=one_way_route_duration)
                new_total = (next_arr_park - first_start).total_seconds() / 3600.0
                if new_total <= max_norm_work + 1e-9:
                    departures[j]["driver_id"] = free_driver
                    assignments.append({
                        "id": free_driver,
                        "start_park": next_departure,
                        "end_terminal": next_arr_terminal,
                        "start_terminal": next_dep_terminal,
                        "end_park": next_arr_park
                    })
                    assigned[j] = True
                    current_return = next_arr_park
                    total_hours = new_total
                    if total_hours >= min_norm_work - 1e-9:
                        break
                    j += 1
                    continue
                else:
                    break
            else:
                j += 1

        drivers.append((current_return, free_driver, first_start, total_hours))
        i += 1

    return assignments, next_id


# --- Запуск симуляции ---
assignments_all, _ = simulate_with_chaining(list_of_schedule_drivers, start_driver_id=1)

# --- Формируем сводные данные ---
all_assignments = sorted(assignments_all, key=lambda x: x["start_park"])
first_start_by_driver = {}
last_end_by_driver = {}

for a in all_assignments:
    d = a["id"]
    if d not in first_start_by_driver:
        first_start_by_driver[d] = a["start_park"]
    last_end_by_driver[d] = a["end_park"]

work_time = {d: [first_start_by_driver[d], last_end_by_driver[d]] for d in first_start_by_driver.keys()}


def check_min_norm_at_return(driver_id, return_time):
    first_start = first_start_by_driver.get(driver_id)
    if not first_start:
        return None
    worked_hours = (return_time - first_start).total_seconds() / 3600
    remaining = max(0.0, min_norm_work - worked_hours)
    return worked_hours, remaining


# --- Итоговые статистики ---
all_ids = [a["id"] for a in all_assignments]
num_drivers = len(set(all_ids))
total_drives = len(all_assignments)
last_return_time = all_assignments[-1]["end_park"].strftime("%H:%M") if all_assignments else "-"

print(f"Необходимо водителей: {num_drivers}")
print(f"Всего рейсов: {total_drives}")
print(f"Последний рейс возвращается в парк в: {last_return_time}")

# --- Запись расписания ---
with open("output_files/schedule_two.txt", "w", encoding="utf-8") as f:
    last_return = {}
    for i, a in enumerate(all_assignments):
        f.write(f"Рейс {i + 1} (водитель {a['id']}):\n")
        if a["id"] in last_return:
            prev = last_return[a["id"]]
            diff = a["start_park"] - prev
            f.write(f"  Предыдущий возврат:    {prev.strftime('%H:%M')}\n")
            f.write(f"  Перерыв:               {int(diff.total_seconds() / 60)} мин\n")
        f.write(f"  Старт в парке:        {a['start_park'].strftime('%H:%M')}\n")
        f.write(f"  Прибытие на конечную: {a['end_terminal'].strftime('%H:%M')}\n")
        f.write(f"  Старт с конечной:     {a['start_terminal'].strftime('%H:%M')}\n")
        f.write(f"  Возврат в парк:       {a['end_park'].strftime('%H:%M')}\n")
        chk = check_min_norm_at_return(a["id"], a["end_park"])
        if chk is not None:
            worked_hours, remaining = chk
            if worked_hours + 1e-9 < min_norm_work:
                f.write(f"  На момент возврата: {worked_hours:.2f} ч — недоработка, требуется ещё {remaining:.2f} ч\n\n")
            else:
                f.write(f"  На момент возврата: {worked_hours:.2f} ч — норма достигнута\n\n")
        last_return[a["id"]] = a["end_park"]

# --- Файл с итоговым временем работы ---
with open("output_files/worktime_two.txt", "w", encoding="utf-8") as f:
    f.write("Время работы водителей:\n")
    for d in sorted(work_time.keys()):
        start, end = work_time[d]
        duration = (end - start).total_seconds() / 3600
        if duration < min_norm_work:
            f.write(f"  Водитель {d}: с {start.strftime('%H:%M')} до {end.strftime('%H:%M')} — {duration:.2f} ч - недоработка\n")
        elif duration > max_norm_work:
            f.write(f"  Водитель {d}: с {start.strftime('%H:%M')} до {end.strftime('%H:%M')} — {duration:.2f} ч - переработка\n")
        else:
            f.write(f"  Водитель {d}: с {start.strftime('%H:%M')} до {end.strftime('%H:%M')} — {duration:.2f} ч\n")
