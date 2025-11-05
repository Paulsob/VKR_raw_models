from datetime import datetime, timedelta

start_time = "04:48"
end_time = "01:34"
change_time = "12:48"
interval = 5.4
one_way_route_duration = 78
min_norm_work = 6
max_norm_work = 10

total_route_duration = one_way_route_duration * 2
form_start_time = datetime.strptime(start_time, "%H:%M")
form_end_time = datetime.strptime(end_time, "%H:%M")
form_change_time = datetime.strptime(change_time, "%H:%M")

if form_end_time <= form_start_time:
    form_end_time += timedelta(days=1)

list_of_schedule_drivers = []
t = form_start_time
driver_counter = 1

while True:
    end_potential = t + timedelta(minutes=total_route_duration)
    if end_potential > form_end_time:
        break
    list_of_schedule_drivers.append({
        "start_park": t,
        "driver_id": None,
        "shift": None
    })
    t += timedelta(minutes=interval)

first_change_list = []
second_change_list = []

for entry in list_of_schedule_drivers:
    if entry["start_park"] < form_change_time:
        entry["shift"] = 1
        first_change_list.append(entry)
    else:
        entry["shift"] = 2
        second_change_list.append(entry)

def simulate_shift(departures, start_driver_id=1):
    drivers = []
    next_id = start_driver_id
    assignments = []

    for entry in departures:
        departure = entry["start_park"]
        free_driver = None
        for i, (free_time, driver_id) in enumerate(drivers):
            if free_time < departure:
                free_driver = driver_id
                drivers[i] = None
                break
        if free_driver is None:
            free_driver = next_id
            next_id += 1
        drivers = [d for d in drivers if d is not None]
        arr_terminal = departure + timedelta(minutes=one_way_route_duration)
        dep_terminal = arr_terminal + timedelta(minutes=2)
        arr_park = dep_terminal + timedelta(minutes=one_way_route_duration)
        drivers.append((arr_park, free_driver))
        entry["driver_id"] = free_driver
        assignments.append({
            "id": free_driver,
            "start_park": departure,
            "end_terminal": arr_terminal,
            "start_terminal": dep_terminal,
            "end_park": arr_park
        })
    return assignments, next_id

assignments_change1, next_id = simulate_shift(first_change_list, start_driver_id=1)
assignments_change2, _ = simulate_shift(second_change_list, start_driver_id=next_id)

work_time = {}
for a in assignments_change1 + assignments_change2:
    d = a["id"]
    if d not in work_time:
        work_time[d] = [a["start_park"], a["end_park"]]
    else:
        work_time[d][1] = a["end_park"]

num_drivers = max(person["id"] for person in assignments_change2)
total_drives = len(assignments_change1) + len(assignments_change2)
last_return_time = assignments_change2[-1]["end_park"].strftime("%H:%M")

with open("../output_files/schedule.txt", "w", encoding="utf-8") as f:
    last_return = {}
    for i, a in enumerate(assignments_change1):
        f.write(f"Рейс {i+1} (водитель {a['id']}, смена 1):\n")
        if a["id"] in last_return:
            prev = last_return[a["id"]]
            diff = a["start_park"] - prev
            f.write(f"  Предыдущий возврат:    {prev.strftime('%H:%M')}\n")
            f.write(f"  Перерыв:               {int(diff.total_seconds()/60)} мин\n")
        f.write(f"  Старт в парке:        {a['start_park'].strftime('%H:%M')}\n")
        f.write(f"  Прибытие на конечную: {a['end_terminal'].strftime('%H:%M')}\n")
        f.write(f"  Старт с конечной:     {a['start_terminal'].strftime('%H:%M')}\n")
        f.write(f"  Возврат в парк:       {a['end_park'].strftime('%H:%M')}\n\n")
        last_return[a["id"]] = a["end_park"]
    f.write("\n=============ПЕРЕСМЕНКА==================\n\n\n")
    last_return = {}
    for i, a in enumerate(assignments_change2):
        f.write(f"Рейс {i+1} (водитель {a['id']}, смена 2):\n")
        if a["id"] in last_return:
            prev = last_return[a["id"]]
            diff = a["start_park"] - prev
            f.write(f"  Предыдущий возврат:    {prev.strftime('%H:%M')}\n")
            f.write(f"  Перерыв:               {int(diff.total_seconds()/60)} мин\n")
        f.write(f"  Старт в парке:        {a['start_park'].strftime('%H:%M')}\n")
        f.write(f"  Прибытие на конечную: {a['end_terminal'].strftime('%H:%M')}\n")
        f.write(f"  Старт с конечной:     {a['start_terminal'].strftime('%H:%M')}\n")
        f.write(f"  Возврат в парк:       {a['end_park'].strftime('%H:%M')}\n\n")
        last_return[a["id"]] = a["end_park"]

print(f"Необходимо водителей: {num_drivers}")
print(f"Всего рейсов: {total_drives}")
print(f"Последний рейс возвращается в парк в: {last_return_time}")

with open("../output_files/worktime.txt", "w", encoding="utf-8") as f:
    f.write("Время работы водителей:\n")
    for d, (start, end) in work_time.items():
        duration = (end - start).total_seconds() / 3600
        if duration < min_norm_work:
            f.write(f"  Водитель {d}: с {start.strftime('%H:%M')} до {end.strftime('%H:%M')} — {duration:.2f} ч - недоработка\n")
        elif duration > max_norm_work:
            f.write(f"  Водитель {d}: с {start.strftime('%H:%M')} до {end.strftime('%H:%M')} — {duration:.2f} ч - переработка\n")
        else:
            f.write(f"  Водитель {d}: с {start.strftime('%H:%M')} до {end.strftime('%H:%M')} — {duration:.2f} ч\n")
