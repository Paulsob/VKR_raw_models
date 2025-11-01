import pandas as pd

file_path = "Timetable.xlsx"
df = pd.read_excel(file_path, sheet_name="4х2")

df.columns = ["0", "Таб.№", "График", "Режим", "см", "вых"] + [str(x) for x in range(1, 32)]
need_strings = df.iloc[list(range(123, 135)), [1, 3] + list(range(6, 36))]
# + list(range(136, 148)) + list(range(149, 161))
reserv = df.iloc[list(range(163, 181)), [1, 3] + list(range(6, 36))]

number_of_employers = 24  # число сотрудников
work_standard = 9  # норма работы в день

# Функция для подсчета значений в столбце с учетом разных типов данных
def count_values_in_column(column_data):
    clean_data = column_data.dropna()
    
    count_1 = 0
    count_2 = 0
    count_v = 0
    
    for value in clean_data:
        if str(value) == "1":
            count_1 += 1
        elif str(value) == "2":
            count_2 += 1
        elif str(value) == "В":
            count_v += 1
        elif pd.isna(value):
            continue  # Пропускаем NaN
        elif isinstance(value, (int, float)):
            if value == 1:
                count_1 += 1
            elif value == 2:
                count_2 += 1
    
    return count_1, count_2, count_v

def count_values_robust(column_data):
    str_values = column_data.astype(str).str.strip()

    count_1 = (str_values == "1").sum()
    count_2 = (str_values == "2").sum()
    count_v = (str_values == "В").sum()
    
    return count_1, count_2, count_v

print("\n ПЕРВОНАЧАЛЬНЫЙ ВИД ДАТАФРЕЙМА")
print(need_strings)

nan_rows = need_strings[need_strings.isna().any(axis=1)]

"""
    В каждом блоке для каждого дня считаем, какого расписания не хватает.
    Мы знаем, что нужно 4 "В", 4 "1" и 4 "2". 
    Сформируем идеальное расписание для каждого блока.
    Объединим эти идеальные расписания в единый блок.
    Будем искать полные совпадения в резерве.
    Если точного совпадения нет, то ищем минимальные различия.
    Находим подходящий вариант и вставляем его в датафрейм (уже реализовано)
"""
data_columns = need_strings.columns[2:]

all_days = []
print("\n ДАННЫЕ ПО КАЖДОМУ ДНЮ")
for col in data_columns:
    count_1, count_2, count_v = count_values_robust(need_strings[col])
    one_day = [int(count_1), int(count_2), int(count_v)]
    all_days.append(one_day)
    total = count_1 + count_2 + count_v
    print(f"Столбец {col}: 1={count_1}, 2={count_2}, В={count_v}, всего={total}")

print("\n КАКИХ СОТРУДНИКОВ НЕ ХВАТАЕТ")
# Анализируем каждый день и определяем, каких сотрудников не хватает
for day_idx, day_data in enumerate(all_days):
    count_1, count_2, count_v = day_data
    day_name = data_columns[day_idx] if day_idx < len(data_columns) else f"День {day_idx + 1}"
    
    print(f"{day_name}: Текущее состояние: '1'={count_1}, '2'={count_2}, 'В'={count_v}")
    
    needed_1 = 4 - count_1  # Нужно 4 сотрудника с графиком "1"
    needed_2 = 4 - count_2  # Нужно 4 сотрудника с графиком "2" 
    needed_v = 4 - count_v  # Нужно 4 сотрудника с графиком "В"
    
    missing = []
    if needed_1 > 0:
        missing.append(f"{needed_1} с графиком '1'")
    if needed_2 > 0:
        missing.append(f"{needed_2} с графиком '2'")
    if needed_v > 0:
        missing.append(f"{needed_v} с графиком 'В'")
    
    if missing:
        print(f"Не хватает: {', '.join(missing)}")
    else:
        print(f"Все сотрудники на месте")
    
    excess = []
    if needed_1 < 0:
        excess.append(f"{abs(needed_1)} лишний с графиком '1'")
    if needed_2 < 0:
        excess.append(f"{abs(needed_2)} лишний с графиком '2'")
    if needed_v < 0:
        excess.append(f"{abs(needed_v)} лишний с графиком 'В'")
    
    if excess:
        print(f"    Избыток: {', '.join(excess)}")


if not nan_rows.empty and not reserv.empty:
    nan_indices = nan_rows.index.tolist()
    print("\n СТРОКИ С NaN")
    print(nan_indices)
    reserve_rows_to_use = reserv.iloc[:len(nan_indices)]
    for i, nan_idx in enumerate(nan_indices):
        if i < len(reserve_rows_to_use):
            need_strings.loc[nan_idx] = reserve_rows_to_use.iloc[i]

else:
    print("Нет NaN строк или резерв пуст")
print(need_strings)

