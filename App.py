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
        П_Лекции INTEGER,
        П_Семинары INTEGER,
        П_Лабораторные INTEGER,
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
        П_Лекции = row.get('П_Лекции')
        П_Семинары = row.get('П_Семинары')
        П_Лабораторные = row.get('П_Лабораторные')
        discipline_values = (row['Дисциплина'], id_семестра, id_группы_str) + tuple(row[3:].fillna("").tolist()) + (П_Лекции, П_Семинары, П_Лабораторные)
        
        cursor.execute(f'''
        INSERT INTO Дисциплины (название_дисциплины, id_семестра, id_группы, {", ".join([f'"{col}"' for col in output_data.columns[3:]])}, П_Лекции, П_Семинары, П_Лабораторные)
        VALUES ({", ".join(["?"] * len(discipline_values))})
        ''', discipline_values)

    conn.commit()

    # Возвращаем данные из таблицы "Дисциплины" для отображения на клиенте
    cursor.execute("SELECT id_дисциплины, название_дисциплины, Лекции, Практические, Лабы, id_семестра, П_Лекции, П_Семинары, П_Лабораторные FROM Дисциплины")
    disciplines = [{'id_дисциплины': row[0], 'название_дисциплины': row[1], 'Лекции': row[2], 'Практические': row[3], 'Лабы': row[4], 'id_семестра': row[5], 'П_Лекции': row[6], 'П_Семинары': row[7], 'П_Лабораторные': row[8] } for row in cursor.fetchall()]
    conn.close()

    return jsonify({'disciplines': disciplines})

@app.route('/update_load', methods=['POST'])
def update_load():
    data = request.json
    id = data['id']
    teacher_fio = data['teacher']
    selected = data['selected']
    hours = data['hours']

    
    # Получаем ID преподавателя
    conn = sqlite3.connect(DB_TEACHERS)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Преподаватели WHERE ФИО = ?", (teacher_fio,))
    teacher_id = cursor.fetchone()

    if not teacher_id:
        return jsonify({'error': 'Преподаватель не найден'}), 400

    teacher_id = teacher_id[0]
    conn.close()

    # Обновляем таблицу дисциплин
    conn = sqlite3.connect(DB_DISCIPLINE)
    cursor = conn.cursor()

    if selected['lectures']:
        cursor.execute("UPDATE Дисциплины SET П_Лекции = ? WHERE id_дисциплины = ?", (teacher_id, id))
    if selected['seminars']:
        cursor.execute("UPDATE Дисциплины SET П_Семинары = ? WHERE id_дисциплины = ?", (teacher_id, id))
    if selected['labs']:
        cursor.execute("UPDATE Дисциплины SET П_Лабораторные = ? WHERE id_дисциплины = ?", (teacher_id, id))

    conn.commit()

    # Обновляем нагрузку преподавателя
    conn = sqlite3.connect(DB_TEACHERS)
    cursor = conn.cursor()

    # Добавляем нагрузку
    cursor.execute("SELECT Назначено_часов FROM Преподаватели WHERE id = ?", (teacher_id,))
    current_load = cursor.fetchone()[0] or 0

    new_load = current_load
    if selected['lectures']:
        new_load += float(hours['lectures'])
    if selected['seminars']:
        new_load += float(hours['seminars'])
    if selected['labs']:
        new_load += float(hours['labs'])

    cursor.execute("UPDATE Преподаватели SET Назначено_часов = ? WHERE id = ?", (new_load, teacher_id))

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

@app.route('/get_teacher_by_id', methods=['GET'])
def get_teacher_by_id():
    teacher_id = request.args.get('id')
    conn = sqlite3.connect(DB_TEACHERS)
    cursor = conn.cursor()

    cursor.execute("SELECT id, ФИО FROM Преподаватели WHERE id = ?", (teacher_id,))
    teachers = [
        {'id': row[0], 'ФИО': row[1]}
        for row in cursor.fetchall()
    ]
    conn.close()
 
    return jsonify({'teachers': teachers})
    

@app.route('/update_disciplines', methods=['GET'])
def update_disciplines():
    discipline_id = request.args.get('id_дисциплины')
    
    conn = sqlite3.connect(DB_DISCIPLINE)
    cursor = conn.cursor()
    # Возвращаем данные из таблицы "Дисциплины" для отображения на клиенте
    
    cursor.execute("SELECT П_Лекции, П_Семинары, П_Лабораторные FROM Дисциплины WHERE id_дисциплины = ?", (discipline_id,))
    row = cursor.fetchone()
    conn.close()
    
    return jsonify({'П_Лекции': row[0], 'П_Семинары': row[1], 'П_Лабораторные': row[2]})

if __name__ == '__main__':
    initialize_database()
    app.run(port=5000)