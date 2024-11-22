import pandas as pd
import sqlite3

# Path to the uploaded file
filename = '/Users/kalek/Desktop/Учеба/Информатика/Проект АЯП/Преподаватели.xlsx'

# Load the Excel file
data = pd.read_excel(filename)

def teach_to_sql(data):
    # Connect to SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect('/Users/kalek/Desktop/Учеба/Информатика/Проект АЯП/Teachers.db')
    cursor = conn.cursor()

    # Create the table with the required fields
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Преподаватели (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ФИО TEXT,
        Должность TEXT,
        Ставка REAL,
        Максимально_часов REAL,
        Назначено_часов REAL
    )
    ''')

    # Insert data into the table
    for _, row in data.iterrows():
        ФИО = row['Сотрудник']
        Должность = row['Должность']
        Ставка = row['Ставка']
        Максимально_часов = Ставка * 840
        Назначено_часов = None  # Empty field as per requirement

        cursor.execute('''
            INSERT INTO Преподаватели (ФИО, Должность, Ставка, Максимально_часов, Назначено_часов)
            VALUES (?, ?, ?, ?, ?)
        ''', (ФИО, Должность, Ставка, Максимально_часов, Назначено_часов))

    # Commit changes and close the connection
    conn.commit()
    conn.close()

teach_to_sql(data)
