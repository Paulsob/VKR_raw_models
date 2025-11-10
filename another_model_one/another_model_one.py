from datetime import datetime, timedelta
from collections import defaultdict
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ScheduleConfig:
    start_time: str = "04:48"
    end_time: str = "01:34"
    change_time: str = "13:36"
    min_norm_work: float = 6.0
    max_norm_work: float = 10.0
    intervals_by_time: List[List[int]] = field(default_factory=lambda: [[4, 15], [8, 6], [10, 13], [17, 6], [20, 12],
                                                                        [23, 18]])
    route_duration_min: int = 76
    route_duration_max: int = 80
    terminal_stop_min: int = 1
    terminal_stop_max: int = 3
    seed: Optional[int] = None


class TramScheduleModel:
    def __init__(self, config: ScheduleConfig):
        self.config = config
        # Создаём изолированный генератор случайных чисел
        self.rng = random.Random(config.seed) if config.seed is not None else random

    def get_interval_for_time(self, t: datetime) -> int:
        hour = t.hour + t.minute / 60
        intervals = self.config.intervals_by_time
        for i, (start_hour, interval_val) in enumerate(intervals):
            if i == len(intervals) - 1 or hour < intervals[i + 1][0]:
                return interval_val
        return intervals[-1][1]

    def simulate_shift_optimized(self, departures: List[Dict], start_driver_id: int = 1):
        drivers = []  # (время_освобождения, id водителя, первый старт, накопленные часы)
        next_id = start_driver_id
        assignments = []

        for entry in departures:
            departure = entry["start_park"]
            available = [d for d in drivers if d[0] <= departure]

            chosen = None
            if available:
                # сортируем по приоритету (сначала те, кто не достиг 6 ч)
                available.sort(key=lambda x: (x[3] < self.config.min_norm_work, -x[3]), reverse=True)
                chosen = available[-1]

            if chosen is None:
                free_driver = next_id
                first_start = departure
                total_hours = 0
                next_id += 1
            else:
                free_driver = chosen[1]
                first_start = chosen[2]
                total_hours = chosen[3]
                drivers.remove(chosen)

            one_way = self.rng.randint(self.config.route_duration_min, self.config.route_duration_max)
            arr_terminal = departure + timedelta(minutes=one_way)
            dep_terminal = arr_terminal + timedelta(
                minutes=self.rng.randint(self.config.terminal_stop_min, self.config.terminal_stop_max))
            arr_park = dep_terminal + timedelta(minutes=one_way)

            total_hours = (arr_park - first_start).total_seconds() / 3600
            drivers.append((arr_park, free_driver, first_start, total_hours))

            entry["driver_id"] = free_driver
            assignments.append({
                "id": free_driver,
                "start_park": departure,
                "end_terminal": arr_terminal,
                "start_terminal": dep_terminal,
                "end_park": arr_park
            })

        return assignments, next_id

    def check_min_norm_at_return(self, first_start: datetime, return_time: datetime):
        worked_hours = (return_time - first_start).total_seconds() / 3600
        remaining = max(0.0, self.config.min_norm_work - worked_hours)
        return worked_hours, remaining

    def generate(self) -> Dict[str, Any]:
        cfg = self.config

        one_way_route_duration = self.rng.randint(cfg.route_duration_min, cfg.route_duration_max)
        total_route_duration = one_way_route_duration * 2

        form_start_time = datetime.strptime(cfg.start_time, "%H:%M")
        form_end_time = datetime.strptime(cfg.end_time, "%H:%M")
        form_change_time = datetime.strptime(cfg.change_time, "%H:%M")

        if form_end_time <= form_start_time:
            form_end_time += timedelta(days=1)

        list_of_schedule_drivers = []
        t = form_start_time

        while True:
            end_potential = t + timedelta(minutes=total_route_duration)
            if end_potential > form_end_time:
                break
            current_interval = self.get_interval_for_time(t)
            list_of_schedule_drivers.append({
                "start_park": t,
                "driver_id": None,
                "shift": None,
                "interval": current_interval
            })
            t += timedelta(minutes=current_interval)

        first_change_list = []
        second_change_list = []

        for entry in list_of_schedule_drivers:
            if entry["start_park"] < form_change_time:
                entry["shift"] = 1
                first_change_list.append(entry)
            else:
                entry["shift"] = 2
                second_change_list.append(entry)

        assignments_change1, next_id = self.simulate_shift_optimized(first_change_list, start_driver_id=1)
        assignments_change2, _ = self.simulate_shift_optimized(second_change_list, start_driver_id=next_id)

        all_assignments = sorted(assignments_change1 + assignments_change2, key=lambda x: x["start_park"])

        assignments_by_driver = defaultdict(list)
        for a in all_assignments:
            assignments_by_driver[a["id"]].append(a)

        for d in assignments_by_driver:
            assignments_by_driver[d].sort(key=lambda x: x["start_park"])

        def total_hours(driver_id):
            rides = assignments_by_driver[driver_id]
            return (rides[-1]["end_park"] - rides[0]["start_park"]).total_seconds() / 3600

        underworked = [d for d in assignments_by_driver if total_hours(d) < cfg.min_norm_work]
        overworked = [d for d in assignments_by_driver if total_hours(d) > cfg.max_norm_work]

        for ow_driver in overworked:
            rides = assignments_by_driver[ow_driver]
            if not rides:
                continue
            last_ride = rides[-1]

            for uw_driver in underworked:
                rides_uw = assignments_by_driver[uw_driver]
                if not rides_uw:
                    continue

                last_end_uw = rides_uw[-1]["end_park"]
                first_start_uw = rides_uw[0]["start_park"]

                if last_end_uw <= last_ride["start_park"]:
                    new_total_uw = (last_ride["end_park"] - first_start_uw).total_seconds() / 3600
                    if new_total_uw <= cfg.max_norm_work:
                        assignments_by_driver[ow_driver].remove(last_ride)
                        assignments_by_driver[uw_driver].append(last_ride)
                        last_ride["id"] = uw_driver
                        break

        all_assignments = []
        for d in assignments_by_driver:
            all_assignments.extend(assignments_by_driver[d])
        all_assignments.sort(key=lambda x: x["start_park"])

        first_start_by_driver = {d: min(r["start_park"] for r in rides) for d, rides in assignments_by_driver.items()}
        last_end_by_driver = {d: max(r["end_park"] for r in rides) for d, rides in assignments_by_driver.items()}
        work_time = {d: [first_start_by_driver[d], last_end_by_driver[d]] for d in assignments_by_driver.keys()}

        all_ids = [a["id"] for a in all_assignments]
        num_drivers = max(all_ids) if all_ids else 0
        total_drives = len(all_assignments)
        last_return_time = all_assignments[-1]["end_park"].strftime("%H:%M") if all_assignments else "-"

        summary = {
            "num_drivers": num_drivers,
            "total_drives": total_drives,
            "last_return_time": last_return_time,
            "assignments": all_assignments,
            "work_time": work_time,
            "assignments_by_driver": dict(assignments_by_driver),
            "underworked": [d for d in assignments_by_driver if total_hours(d) < cfg.min_norm_work],
            "overworked": [d for d in assignments_by_driver if total_hours(d) > cfg.max_norm_work],
            "config_used": {
                "start_time": cfg.start_time,
                "end_time": cfg.end_time,
                "change_time": cfg.change_time,
                "min_norm_work": cfg.min_norm_work,
                "max_norm_work": cfg.max_norm_work,
            }
        }

        return summary

    def write_schedule_to_file(self, assignments: List[Dict], filename: str = "output_files/schedule_one.txt"):
        with open(filename, "w", encoding="utf-8") as f:
            last_return = {}
            for i, a in enumerate(assignments):
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
                first_start = min(r["start_park"] for r in self.assignments_by_driver[a["id"]])
                worked_hours, remaining = self.check_min_norm_at_return(first_start, a["end_park"])
                if worked_hours + 1e-9 < self.config.min_norm_work:
                    f.write(
                        f"  На момент возврата: {worked_hours:.2f} ч — недоработка, требуется ещё {remaining:.2f} ч\n\n")
                else:
                    f.write(f"  На момент возврата: {worked_hours:.2f} ч — норма достигнута\n\n")
                last_return[a["id"]] = a["end_park"]

    def write_worktime_to_file(self, work_time: Dict, assignments_by_driver: Dict,
                               filename: str = "output_files/worktime_one.txt"):
        with open(filename, "w", encoding="utf-8") as f:
            f.write("Время работы водителей:\n")
            for d in sorted(work_time.keys()):
                start, end = work_time[d]
                duration = (end - start).total_seconds() / 3600
                next_start = (end + timedelta(hours=12)).strftime('%H:%M')
                if duration < self.config.min_norm_work:
                    f.write(
                        f"  Водитель {d}: с {start.strftime('%H:%M')} до {end.strftime('%H:%M')} — {duration:.2f} ч - недоработка. \t\t Сможет выйти на работу с {next_start}\n")
                elif duration > self.config.max_norm_work:
                    f.write(
                        f"  Водитель {d}: с {start.strftime('%H:%M')} до {end.strftime('%H:%M')} — {duration:.2f} ч - переработка. Сможет выйти на работу с {next_start}\n")
                else:
                    f.write(
                        f"  Водитель {d}: с {start.strftime('%H:%M')} до {end.strftime('%H:%M')} — {duration:.2f} ч \t\t\t\t\t\t\t\t Сможет выйти на работу с {next_start}\n")


if __name__ == "__main__":
    config = ScheduleConfig()
    model = TramScheduleModel(config)
    result = model.generate()

    print(f"\nНеобходимо водителей: {result['num_drivers']}")
    print(f"Всего рейсов: {result['total_drives']}")
    print(f"Последний рейс возвращается в парк в: {result['last_return_time']}")

    import os

    os.makedirs("output_files", exist_ok=True)
    model.assignments_by_driver = result["assignments_by_driver"]
    model.write_schedule_to_file(result["assignments"])
    model.write_worktime_to_file(result["work_time"], result["assignments_by_driver"])
