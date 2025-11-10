from flask import Flask, request, jsonify, render_template, send_file
import sys
import os
import glob
import json
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from another_model_one.another_model_one import TramScheduleModel, ScheduleConfig

# Создаем папки для файлов
output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output_files")
archive_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "archive")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(archive_dir, exist_ok=True)

app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(__file__), '..', 'front'),
            static_folder=os.path.join(os.path.dirname(__file__), '..', 'front'),
            static_url_path='')


def get_file_list():
    """Получить список всех сгенерированных файлов"""
    files = []

    for file_path in glob.glob(os.path.join(output_dir, "*.txt")):
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))

        files.append({
            "name": filename,
            "size": file_size,
            "modified": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
            "url": f"/output_files/{filename}"
        })

    return sorted(files, key=lambda x: x["modified"], reverse=True)


def archive_files():
    """Архивировать текущие файлы"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_archive_dir = os.path.join(archive_dir, f"generation_{timestamp}")
    os.makedirs(current_archive_dir, exist_ok=True)

    for file_path in glob.glob(os.path.join(output_dir, "*.txt")):
        filename = os.path.basename(file_path)
        os.rename(file_path, os.path.join(current_archive_dir, filename))


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            # Архивируем старые файлы перед генерацией новых
            archive_files()

            config = ScheduleConfig(
                start_time=request.form.get("start_time", "04:48"),
                end_time=request.form.get("end_time", "01:34"),
                change_time=request.form.get("change_time", "13:36"),
                min_norm_work=float(request.form.get("min_norm_work", 6)),
                max_norm_work=float(request.form.get("max_norm_work", 10))
            )
            model = TramScheduleModel(config)
            result = model.generate()

            model.assignments_by_driver = result["assignments_by_driver"]

            # Сохраняем файлы в правильную директорию
            schedule_path = os.path.join(output_dir, "schedule_one.txt")
            worktime_path = os.path.join(output_dir, "worktime_one.txt")
            stats_path = os.path.join(output_dir, "stats.txt")

            model.write_schedule_to_file(result["assignments"], schedule_path)
            model.write_worktime_to_file(result["work_time"], result["assignments_by_driver"], worktime_path)

            # Создаем дополнительный файл с общей статистикой
            with open(stats_path, "w", encoding="utf-8") as f:
                f.write(f"СТАТИСТИКА РАСПИСАНИЯ\n")
                f.write(f"Дата генерации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Количество водителей: {result['num_drivers']}\n")
                f.write(f"Общее количество рейсов: {result['total_drives']}\n")
                f.write(f"Время последнего возврата: {result['last_return_time']}\n")
                f.write(f"Время начала работы: {config.start_time}\n")
                f.write(f"Время окончания работы: {config.end_time}\n")
                f.write(f"Минимальная норма работы: {config.min_norm_work} ч\n")
                f.write(f"Максимальная норма работы: {config.max_norm_work} ч\n")

            # Сохраняем данные в JSON для удобного доступа через API
            json_path = os.path.join(output_dir, "result.json")
            # Преобразуем datetime объекты в строки для JSON
            json_result = {
                "num_drivers": result["num_drivers"],
                "total_drives": result["total_drives"],
                "last_return_time": result["last_return_time"],
                "schedule": [],
                "worktime": [],
                "stats": {
                    "date_generated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "num_drivers": result['num_drivers'],
                    "total_drives": result['total_drives'],
                    "last_return_time": result['last_return_time'],
                    "start_time": config.start_time,
                    "end_time": config.end_time,
                    "min_norm_work": config.min_norm_work,
                    "max_norm_work": config.max_norm_work
                }
            }
            
            # Создаем словарь для отслеживания первого старта каждого водителя
            first_start_by_driver = {}
            for assignment in result["assignments"]:
                driver_id = assignment["id"]
                if driver_id not in first_start_by_driver:
                    first_start_by_driver[driver_id] = assignment["start_park"]
            
            # Преобразуем assignments в удобный формат
            for i, assignment in enumerate(result["assignments"], 1):
                driver_id = assignment["id"]
                first_start = first_start_by_driver[driver_id]
                return_time = assignment["end_park"]
                
                # Вычисляем накопленные часы работы
                accumulated_hours = (return_time - first_start).total_seconds() / 3600
                
                # Конвертируем в формат ЧЧ:ММ
                hours = int(accumulated_hours)
                minutes = int((accumulated_hours - hours) * 60)
                accumulated_time_str = f"{hours:02d}:{minutes:02d}"
                
                # Проверяем, достигнута ли норма
                norm_achieved = "норма достигнута" if accumulated_hours >= config.min_norm_work else ""
                
                json_result["schedule"].append({
                    "trip_number": i,
                    "driver_id": driver_id,
                    "start_park": assignment["start_park"].strftime("%H:%M"),
                    "arrival_terminal": assignment["end_terminal"].strftime("%H:%M"),
                    "start_terminal": assignment["start_terminal"].strftime("%H:%M"),
                    "return_park": assignment["end_park"].strftime("%H:%M"),
                    "accumulated_hours": accumulated_time_str,
                    "norm_achieved": norm_achieved
                })
            
            # Преобразуем work_time в удобный формат
            for driver_id, (start, end) in result["work_time"].items():
                duration = (end - start).total_seconds() / 3600
                if duration < config.min_norm_work:
                    status = "недоработка"
                elif duration > config.max_norm_work:
                    status = "переработка"
                else:
                    status = "норма достигнута"
                
                # Конвертируем длительность в формат ЧЧ:ММ
                hours = int(duration)
                minutes = int((duration - hours) * 60)
                duration_str = f"{hours:02d}:{minutes:02d}"
                
                # Вычисляем время следующего выхода (через 12 часов после окончания)
                next_start = (end + timedelta(hours=12)).strftime("%H:%M")
                json_result["worktime"].append({
                    "driver_id": driver_id,
                    "start_time": start.strftime("%H:%M"),
                    "end_time": end.strftime("%H:%M"),
                    "duration": duration_str,
                    "status": status,
                    "next_start": next_start,
                    "break_duration": "12:00"  # Пока везде 12 часов
                })
            
            # Сортируем по driver_id
            json_result["worktime"].sort(key=lambda x: int(x["driver_id"]))
            
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_result, f, ensure_ascii=False, indent=2)

            files = get_file_list()

            return render_template(
                "index.html",
                result={
                    "num_drivers": result["num_drivers"],
                    "total_drives": result["total_drives"],
                    "last_return_time": result["last_return_time"]
                },
                files=files
            )
        except Exception as e:
            files = get_file_list()
            return render_template("index.html", error=str(e), files=files)

    files = get_file_list()
    return render_template("index.html", files=files)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    try:
        data = request.json or {}
        config = ScheduleConfig(
            start_time=data.get("start_time", "04:48"),
            end_time=data.get("end_time", "01:34"),
            change_time=data.get("change_time", "13:36"),
            min_norm_work=float(data.get("min_norm_work", 6.0)),
            max_norm_work=float(data.get("max_norm_work", 10.0)),
            seed=data.get("seed")
        )
        model = TramScheduleModel(config)
        result = model.generate()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/output_files/<path:filename>")
def custom_static(filename):
    """Отдача файлов из output_files"""
    file_path = os.path.join(output_dir, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        return "File not found", 404


@app.route("/download/<filename>")
def download_file(filename):
    """Скачивание файла"""
    file_path = os.path.join(output_dir, filename)
    if os.path.exists(file_path):
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
    else:
        return "File not found", 404


@app.route("/api/files")
def api_files():
    """API для получения списка файлов"""
    files = get_file_list()
    return jsonify(files)


@app.route("/api/last-result")
def api_last_result():
    """API для получения последних сгенерированных данных в JSON формате"""
    try:
        json_path = os.path.join(output_dir, "result.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                result = json.load(f)
            return jsonify(result)
        else:
            return jsonify({"error": "Нет сгенерированных данных"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/clear-files", methods=["POST"])
def clear_files():
    """Очистка всех файлов"""
    try:
        for file_path in glob.glob(os.path.join(output_dir, "*.txt")):
            os.remove(file_path)
        return jsonify({"success": True, "message": "Файлы очищены"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)