// Загрузка данных при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Проверяем, есть ли результат на странице
    const resultSection = document.querySelector('.tables-container');
    if (resultSection) {
        loadTableData();
    }
    
    // Обработчики для input полей
    const startTimeInput = document.getElementById("start_time");
    if (startTimeInput) {
        startTimeInput.addEventListener("input", () => {
            startTimeInput.classList.toggle("has-value", startTimeInput.value !== "");
        });
    }
    
    const endTimeInput = document.getElementById("end_time");
    if (endTimeInput) {
        endTimeInput.addEventListener("input", () => {
            endTimeInput.classList.toggle("has-value", endTimeInput.value !== "");
        });
    }
    
    const changeTimeInput = document.getElementById("change_time");
    if (changeTimeInput) {
        changeTimeInput.addEventListener("input", () => {
            changeTimeInput.classList.toggle("has-value", changeTimeInput.value !== "");
        });
    }
});

// Загрузка данных из API
function loadTableData() {
    fetch('/api/last-result')
        .then(response => {
            if (!response.ok) {
                throw new Error('Нет данных для отображения');
            }
            return response.json();
        })
        .then(data => {
            populateScheduleTable(data.schedule);
            populateWorktimeTable(data.worktime);
        })
        .catch(error => {
            console.error('Ошибка загрузки данных:', error);
            document.getElementById('schedule-tbody').innerHTML = 
                '<tr><td colspan="8" class="error">Ошибка загрузки данных. Попробуйте сгенерировать расписание заново.</td></tr>';
            document.getElementById('worktime-tbody').innerHTML = 
                '<tr><td colspan="7" class="error">Ошибка загрузки данных. Попробуйте сгенерировать расписание заново.</td></tr>';
        });
}

// Заполнение таблицы расписания
function populateScheduleTable(schedule) {
    const tbody = document.getElementById('schedule-tbody');
    if (!schedule || schedule.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">Нет данных</td></tr>';
        return;
    }
    
    tbody.innerHTML = schedule.map(trip => {
        const normClass = trip.norm_achieved ? 'status-normal' : '';
        return `
            <tr>
                <td>${trip.trip_number}</td>
                <td>${trip.driver_id}</td>
                <td>${trip.start_park}</td>
                <td>${trip.arrival_terminal}</td>
                <td>${trip.start_terminal}</td>
                <td>${trip.return_park}</td>
                <td>${trip.accumulated_hours || '-'}</td>
                <td class="${normClass}">${trip.norm_achieved || ''}</td>
            </tr>
        `;
    }).join('');
}

// Заполнение таблицы времени работы
function populateWorktimeTable(worktime) {
    const tbody = document.getElementById('worktime-tbody');
    if (!worktime || worktime.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">Нет данных</td></tr>';
        return;
    }
    
    tbody.innerHTML = worktime.map(driver => {
        let statusClass = 'status-normal';
        let statusValue = 'normal';
        if (driver.status === 'недоработка') {
            statusClass = 'status-underworked';
            statusValue = 'underworked';
        } else if (driver.status === 'переработка') {
            statusClass = 'status-overworked';
            statusValue = 'overworked';
        }
        return `
            <tr data-status="${statusValue}">
                <td>${driver.driver_id}</td>
                <td>${driver.start_time}</td>
                <td>${driver.end_time}</td>
                <td>${driver.duration || '-'}</td>
                <td class="${statusClass}">${driver.status}</td>
                <td>${driver.break_duration || '12:00'}</td>
                <td>${driver.next_start || '-'}</td>
            </tr>
        `;
    }).join('');
}

// Переключение вкладок
function showTab(tabName, buttonElement) {
    // Скрываем все вкладки
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Убираем активный класс у всех кнопок
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Показываем выбранную вкладку
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // Активируем соответствующую кнопку
    if (buttonElement) {
        buttonElement.classList.add('active');
    } else {
        // Если кнопка не передана, находим её по тексту
        document.querySelectorAll('.tab-button').forEach(btn => {
            if (btn.textContent.includes(tabName === 'schedule' ? 'Расписание' : 
                                          tabName === 'worktime' ? 'Время работы' : 'Текстовые')) {
                btn.classList.add('active');
            }
        });
    }
}

// Фильтрация таблицы расписания
function filterScheduleTable() {
    const searchInput = document.getElementById('schedule-search');
    const filter = searchInput.value.toLowerCase();
    const table = document.getElementById('schedule-table');
    const rows = table.getElementsByTagName('tr');
    
    for (let i = 1; i < rows.length; i++) {
        const row = rows[i];
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(filter) ? '' : 'none';
    }
}

// Фильтрация таблицы времени работы
function filterWorktimeTable() {
    const searchInput = document.getElementById('worktime-search');
    const statusFilter = document.getElementById('worktime-filter').value;
    const searchFilter = searchInput.value.toLowerCase();
    const table = document.getElementById('worktime-table');
    const rows = table.getElementsByTagName('tr');
    
    for (let i = 1; i < rows.length; i++) {
        const row = rows[i];
        const text = row.textContent.toLowerCase();
        const status = row.getAttribute('data-status');
        
        const matchesSearch = text.includes(searchFilter);
        const matchesStatus = statusFilter === 'all' || 
                            (statusFilter === 'normal' && status === 'normal') ||
                            (statusFilter === 'underworked' && (status === 'underworked' || status === 'overworked'));
        
        row.style.display = (matchesSearch && matchesStatus) ? '' : 'none';
    }
}

// Экспорт таблицы в CSV
function exportTable(tableType) {
    const table = document.getElementById(tableType + '-table');
    const rows = table.getElementsByTagName('tr');
    let csv = [];
    
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        // Пропускаем скрытые строки
        if (row.style.display === 'none') continue;
        
        const cols = row.getElementsByTagName('td');
        const headerCols = row.getElementsByTagName('th');
        const cells = cols.length > 0 ? cols : headerCols;
        let rowData = [];
        
        for (let j = 0; j < cells.length; j++) {
            let cellText = cells[j].textContent.trim();
            // Экранируем кавычки и запятые
            if (cellText.includes(',') || cellText.includes('"')) {
                cellText = '"' + cellText.replace(/"/g, '""') + '"';
            }
            rowData.push(cellText);
        }
        
        csv.push(rowData.join(','));
    }
    
    // Создаем и скачиваем файл
    const csvContent = csv.join('\n');
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', tableType + '_' + new Date().toISOString().split('T')[0] + '.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
