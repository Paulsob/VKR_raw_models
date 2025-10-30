from datetime import datetime, timedelta

# --- Исходные данные ---
time_start = "05:00"
time_end = "23:00"
interval = 5.4  # интервал между отправлениями из парка (в минутах)
time_of_one_drive = 78  # одна сторона маршрута (в минутах)
round_trip = time_of_one_drive * 2  # полный круг (в парк обратно)

# --- Преобразование времени ---
time_start_obj = datetime.strptime(time_start, "%H:%M")
time_end_obj = datetime.strptime(time_end, "%H:%M")

# --- Генерация расписания выездов ---
list_of_drives = []
t = time_start_obj
while True:
    end_potential = t + timedelta(minutes=round_trip)
    if end_potential > time_end_obj:  # если водитель не успеет вернуться к 23:00
        break
    list_of_drives.append(t)
    t += timedelta(minutes=interval)

# --- Моделирование ---
drivers = []  # список [(время_освобождения, id)]
next_id = 1
assignments = []  # список всех рейсов с водителями

for departure in list_of_drives:
    # ищем, кто освободился к этому моменту
    free_driver = None
    for i, (free_time, driver_id) in enumerate(drivers):
        if free_time <= departure:
            free_driver = driver_id
            drivers[i] = None
            break

    # если никто не освободился — новый водитель
    if free_driver is None:
        free_driver = next_id
        next_id += 1

    # очистим список от None
    drivers = [d for d in drivers if d is not None]

    # время маршрута
    arr_terminal = departure + timedelta(minutes=time_of_one_drive)
    dep_terminal = arr_terminal  # без простоев
    arr_park = dep_terminal + timedelta(minutes=time_of_one_drive)

    # добавляем нового водителя с временем освобождения
    drivers.append((arr_park, free_driver))

    # сохраняем информацию
    assignments.append({
        "id": free_driver,
        "start_park": departure,
        "end_terminal": arr_terminal,
        "start_terminal": dep_terminal,
        "end_park": arr_park
    })

# --- Результат ---
num_drivers = max(a["id"] for a in assignments)
print(f"Необходимо водителей: {num_drivers}")
print(f"Всего рейсов: {len(assignments)}")

# --- Вывод ---
last_return = None
for i, a in enumerate(assignments):
    print(f"\nРейс {i+1} (водитель {a['id']}):")
    if last_return and a["id"] in last_return:
        prev = last_return[a["id"]]
        diff = a["start_park"] - prev
        print(f"  Предыдущий возврат:   {prev.strftime('%H:%M')}  (перерыв {int(diff.total_seconds()/60)} мин)")
    print("  Старт в парке:        ", a["start_park"].strftime("%H:%M"))
    print("  Прибытие на конечную: ", a["end_terminal"].strftime("%H:%M"))
    print("  Старт с конечной:     ", a["start_terminal"].strftime("%H:%M"))
    print("  Возврат в парк:       ", a["end_park"].strftime("%H:%M"))
    last_return = last_return or {}
    last_return[a["id"]] = a["end_park"]

print(f"\nПоследний рейс возвращается в парк в: {assignments[-1]['end_park'].strftime('%H:%M')}")
