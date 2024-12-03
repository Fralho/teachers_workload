from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import sqlite3
import FormatToSQL as disciplite_to

app = Flask(__name__)
DB_TEACHERS = 'Teachers.db'
DB_DISCIPLINE = 'database.db'

def initialize_database():
    conn = sqlite3.connect(DB_TEACHERS)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Преподаватели (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ФИО TEXT,
                        Должность TEXT,
                        Ставка REAL,
                        Максимально_часов REAL,
                        Назначено_часов REAL,
                        Лекции REAL,
                        Семинары REAL,
                        Лабораторные REAL)''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return send_from_directory('static', 'Main.html')

@app.route('/upload_teachers', methods=['POST'])
def upload_teacher_file():
    file = request.files['file']
    data = pd.read_excel(file)

    conn = sqlite3.connect(DB_TEACHERS)
    cursor = conn.cursor()

    for _, row in data.iterrows():
        ФИО = row['Сотрудник']
        Должность = row['Должность']
        Ставка = row['Ставка']
        Максимально_часов = Ставка * 840
        Назначено_часов = row.get('Назначено_часов', 0)
        Лекции= row.get('Лекции', 0)
        Семинары = row.get('Семинары', 0)
        Лабораторные = row.get('Лабораторные', 0)

        # Проверяем, существует ли преподаватель в базе
        cursor.execute("SELECT COUNT(*) FROM Преподаватели WHERE ФИО = ?", (ФИО,))
        existing_teacher = cursor.fetchone()[0]

        # Если преподаватель не существует, добавляем его
        if existing_teacher == 0:
            cursor.execute('''INSERT INTO Преподаватели (ФИО, Должность, Ставка, Максимально_часов, Назначено_часов, Лекции, Семинары, Лабораторные)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (ФИО, Должность, Ставка, Максимально_часов, Назначено_часов, Лекции, Семинары, Лабораторные))

    conn.commit()

    # Возвращаем список преподавателей для отображения
    cursor.execute("SELECT id, ФИО, Максимально_часов, Назначено_часов, Лекции, Семинары, Лабораторные FROM Преподаватели")
    teachers = [{'id': row[0], 'ФИО': row[1], 'Максимально_часов': row[2], 'Назначено_часов': row[3], 'Лекции': row[4], 'Семинары': row[5], 'Лабораторный': row[6] or 0} for row in cursor.fetchall()]

    conn.close()
    return jsonify({'teachers': teachers})

@app.route('/upload_disciplines', methods=['POST'])
def upload_discipline_file():
    file = request.files['file']
    df = pd.read_excel(file, skiprows=6)
    
    formatted_df = disciplite_to.load_excel_file(df, disciplite_to.stop_marker_1, disciplite_to.stop_marker_2)
    output_data = disciplite_to.format_excel(formatted_df)
    
    conn = sqlite3.connect(DB_DISCIPLINE)
    cursor = conn.cursor()

    # Drop tables if they already exist to reset them
    cursor.execute('DROP TABLE IF EXISTS Семестры')
    cursor.execute('DROP TABLE IF EXISTS Группы')
    cursor.execute('DROP TABLE IF EXISTS Дисциплины')

    # Step 1: Create the "Семестры" table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Семестры (
        id_семестра INTEGER PRIMARY KEY AUTOINCREMENT,
        название_семестра TEXT UNIQUE
    )
    ''')
    unique_semesters = output_data['Семестр'].unique()
    for semester in unique_semesters:
        cursor.execute('INSERT OR IGNORE INTO Семестры (название_семестра) VALUES (?)', (semester,))

    # Step 2: Create the "Группы" table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Группы (
        id_группы INTEGER PRIMARY KEY AUTOINCREMENT,
        название_группы TEXT UNIQUE
    )
    ''')
    all_groups_corrected = set()
    for groups in output_data['Группы']:
        group_names = [group.strip() for group in groups.split(', ') if group.strip()]
        all_groups_corrected.update(group_names)

    for group in all_groups_corrected:
        cursor.execute('INSERT OR IGNORE INTO Группы (название_группы) VALUES (?)', (group,))

    # Step 3: Create the "Дисциплины" table
    formatted_discipline_columns = ", ".join([f'"{col}" TEXT' for col in output_data.columns[3:]])
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS Дисциплины (
        id_дисциплины INTEGER PRIMARY KEY AUTOINCREMENT,
        название_дисциплины TEXT,
        id_семестра INTEGER,
        id_группы TEXT,
        {formatted_discipline_columns},
        П_Лекции REAL,
        П_Семинары REAL,
        П_Лабораторные REAL,
        FOREIGN KEY (id_семестра) REFERENCES Семестры(id_семестра)
    )
    ''')
    for _, row in output_data.iterrows():
        cursor.execute('SELECT id_семестра FROM Семестры WHERE название_семестра = ?', (row['Семестр'],))
        id_семестра = cursor.fetchone()[0]
        group_names = row['Группы'].split(', ')
        group_ids = []
        for group in group_names:
            cursor.execute('SELECT id_группы FROM Группы WHERE название_группы = ?', (group,))
            group_id = cursor.fetchone()[0]
            group_ids.append(str(group_id))
        id_группы_str = ','.join(group_ids)
        П_Лекции = row.get('П_Лекции', 0)
        П_Семинары = row.get('П_Семинары', 0)
        П_Лабораторные = row.get('П_Лабораторные', 0)
        discipline_values = (row['Дисциплина'], id_семестра, id_группы_str) + tuple(row[3:].fillna("").tolist()) + (П_Лекции, П_Семинары, П_Лабораторные)
        
        cursor.execute(f'''
        INSERT INTO Дисциплины (название_дисциплины, id_семестра, id_группы, {", ".join([f'"{col}"' for col in output_data.columns[3:]])}, П_Лекции, П_Семинары, П_Лабораторные)
        VALUES ({", ".join(["?"] * len(discipline_values))})
        ''', discipline_values)

    conn.commit()

    # Возвращаем данные из таблицы "Дисциплины" для отображения на клиенте
    cursor.execute("SELECT название_дисциплины, Лекции, Практические, Лабы, id_семестра, П_Лекции, П_Семинары, П_Лабораторные FROM Дисциплины")
    disciplines = [{'название_дисциплины': row[0], 'Лекции': row[1], 'Практические': row[2], 'Лабы': row[3], 'id_семестра': row[4], 'П_Лекции': row[5], 'П_Семинары': row[6], 'П_Лабораторные': row[7]} for row in cursor.fetchall()]
    conn.close()

    return jsonify({'disciplines': disciplines})

@app.route('/update_load', methods=['POST'])
def update_load():
    data = request.json
    teacher = data['teacher']
    discipline_id = data['disciplineId']
    selected = data['selected']

    # Преобразуем часы в float
    hours = {key: float(value) for key, value in data['hours'].items()}

    conn = sqlite3.connect(DB_TEACHERS)
    cursor = conn.cursor()

    # Получаем текущие данные преподавателя
    cursor.execute("SELECT Лекции, Семинары, Лабораторные, Назначено_часов FROM Преподаватели WHERE ФИО = ?", (teacher,))
    result = cursor.fetchone()

    if not result:
        return jsonify({'error': 'Преподаватель не найден'}), 400

    lectures = result[0].split(',') if result[0] else []
    seminars = result[1].split(',') if result[1] else []
    labs = result[2].split(',') if result[2] else []
    current_load = float(result[3])  # Преобразуем текущую нагрузку в float

    # Обновляем нагрузку
    if selected['lectures']:
        lectures.append(str(discipline_id))
        current_load += hours['lectures']

    if selected['seminars']:
        seminars.append(str(discipline_id))
        current_load += hours['seminars']

    if selected['labs']:
        labs.append(str(discipline_id))
        current_load += hours['labs']

    # Обновляем преподавателя в базе данных
    cursor.execute('''
        UPDATE Преподаватели
        SET Лекции = ?, Семинары = ?, Лабораторные = ?, Назначено_часов = ?
        WHERE ФИО = ?
    ''', (','.join(lectures), ','.join(seminars), ','.join(labs), current_load, teacher))

    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

@app.route('/get_teachers', methods=['GET'])
def get_teachers():
    conn = sqlite3.connect(DB_TEACHERS)
    cursor = conn.cursor()

    # Получаем список преподавателей с их нагрузкой
    cursor.execute('SELECT ФИО, Назначено_часов, Максимально_часов FROM Преподаватели')
    teachers = [
        {'ФИО': row[0], 'Назначено_часов': row[1] or 0, 'Максимально_часов': row[2]}
        for row in cursor.fetchall()
    ]
    conn.close()

    return jsonify({'teachers': teachers})

if __name__ == '__main__':
    initialize_database()
    app.run(port=5000)