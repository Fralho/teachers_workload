import pandas as pd
import sqlite3
from flask import jsonify

DATABASE = 'database.db'

def load_excel_file(df, stop_marker_1, stop_marker_2):
  
  columns_to_drop = [i for i in range(1, 14)] + [15, 17, 19, 22, 23, 25, 27, 29, 30, 31, 33, 35, 37, 39, 41, 43, 45, 47, 49, 50, 51]
    
  num_rows = df.shape[0]
  formatted_rows = [] # Список для хранения отформатированных строк
  
  in_block = False # Начало блока
  is_marker = False
  
  for index in range(num_rows):
   
    current_row = df.iloc[index]
    current_value = current_row[df.columns[0]] # Значение в первом столбце

    if current_value == 'Осенний семестр':
      in_block = True # Начало блока
      if is_marker == False:
        formatted_rows.append(current_row.tolist()) # Добавляем строку с start_marker
        is_marker = True
      continue

    if current_value in stop_marker_1:
      in_block = False # Конец блока
      continue # Пропускаем строку с stop_marker или пустую строку

    if in_block: # Записываем строку, если находимся в блоке
      if pd.isnull(current_value):
        continue
      formatted_rows.append(current_row.tolist())
  
  in_block = False
  is_marker = False
  
  for index in range(num_rows):
   
    current_row = df.iloc[index]
    current_value = current_row[df.columns[0]] # Значение в первом столбце

    if current_value == 'Весенний семестр':
      in_block = True # Начало блока
      if is_marker == False:
        formatted_rows.append(current_row.tolist()) # Добавляем строку с start_marker
        is_marker = True
      continue

    if current_value in stop_marker_2:
      in_block = False # Конец блока
      continue # Пропускаем строку с stop_marker или пустую строку

    if in_block: # Записываем строку, если находимся в блоке
      if pd.isnull(current_value):
        continue
      formatted_rows.append(current_row.tolist())
      

  # Создание DataFrame из отформатированных данных
  formatted_df = pd.DataFrame(formatted_rows, columns=df.columns) 
      
  find_issues(formatted_df)
  
  formatted_df.drop(df.columns[columns_to_drop], axis=1, inplace=True)

  return formatted_df

def find_issues(formatted_df):
  for index, row in formatted_df.iterrows():
    # Assuming group names have a specific format (with hyphens) and are not NaN
        if isinstance(row['Unnamed: 0'], str) and row['Unnamed: 0'].count('-') >= 2:
        # Check the conditions: column 15 > 20 and column 25 < 20
            if row[formatted_df.columns[14]] > 20 and row[formatted_df.columns[24]] < 20:
                print(f"Ошибка несоотсвие нагрузки лабораторных в {index+2} строке. Проверить на несоответсвие количества нагрузки у лабораторных работ")
          
          
  column_17 = formatted_df.columns[16]  # 17th column (index 16 in Python)
  # Initialize variables
  current_discipline = None
  first_group_value = None

  # Loop through the data to process each block of groups
  for index, row in formatted_df.iterrows():
    first_column_value = row['Unnamed: 0']
    
    # Check if the row is a new semester or discipline
    if isinstance(first_column_value, str) and ("семестр" in first_column_value.lower() or first_column_value.count('-') < 2):
        # Reset discipline and first group value for a new block
        current_discipline = first_column_value
        first_group_value = None  # Reset the comparison value for a new block
    
    # Process group rows within the same discipline
    elif current_discipline and isinstance(first_column_value, str) and first_column_value.count('-') >= 2:
        # Capture the first group's value in column 17 as the comparison reference
        if first_group_value is None:
            first_group_value = row[column_17]  # Store the first group's 17th column value for comparison
        
        # Compare subsequent group's column 17 values within the same block
        elif pd.notna(row[column_17]) and row[column_17] != first_group_value:
          print(f"Ошибка, непраивльное разделение потоков. Проверьте {index + 2} строку")
  return 0

def format_excel(data):
  semesters = []
  disciplines = []
  other_columns = []
  group_list = []

# Variables to store current semester and discipline
  current_semester = None
  current_discipline = None
  discipline_row_values = None
  current_groups = []

  # Loop through the data to structure it in the required format
  for index, row in data.iterrows():
      value = row.iloc[0]

      # If it's a semester
      if "семестр" in str(value).lower():
          current_semester = value  # Update current semester

      # If it's a discipline name (identified by having fewer than two hyphens)
      elif isinstance(value, str) and (value.count('-') < 2 or not any(char.isdigit() for char in value)):
          # If there's a previous discipline with groups collected, add to the formatted data
          if current_discipline and current_groups:
              semesters.append(current_semester)
              disciplines.append(current_discipline)
              group_list.append(', '.join(current_groups))
              other_columns.append(discipline_row_values)  # Use values from the discipline row

          # Update current discipline and capture its row values
          current_discipline = value
          discipline_row_values = row[1:].tolist()  # Store values for this discipline row
          current_groups = []  # Reset groups list

      # Otherwise, it's a group name row, so add it to the current discipline's groups
      elif current_discipline:
          group_name = row['Unnamed: 0']
          if pd.notna(group_name):  # Ensure the group name is valid
              current_groups.append(group_name)

  # Add the last collected discipline to formatted data
  if current_discipline and current_groups:
      semesters.append(current_semester)
      disciplines.append(current_discipline)
      group_list.append(', '.join(current_groups))
      other_columns.append(discipline_row_values)

  # Create a DataFrame with the desired structure
  output_data = pd.DataFrame({
      'Семестр': semesters,
      'Дисциплина': disciplines,
      'Группы': group_list
  })

  # Add remaining columns from discipline row values
  for i, column_name in enumerate(data.columns[1:]):  # Iterate over remaining columns
      output_data[column_name] = [row[i] for row in other_columns]  # Add each column

  
  # Переименовываем нужные столбцы
  output_data.rename(columns={output_data.columns[4]: 'Noname',
                              output_data.columns[5]: 'Лекции', 
                              output_data.columns[7]: 'Практические', 
                              output_data.columns[8]: 'Лабы'}, inplace=True)

  # Удаляем 5 и 7 столбцы
  output_data.drop(columns=[output_data.columns[4], output_data.columns[6]], inplace=True)
  
  return output_data

def excel_to_sql(DATABASE, output_data):
  
  conn = sqlite3.connect(DATABASE)
  cursor = conn.cursor()

  # Drop tables if they already exist to reset them
  cursor.execute('DROP TABLE IF EXISTS Семестры')
  cursor.execute('DROP TABLE IF EXISTS Группы')
  cursor.execute('DROP TABLE IF EXISTS Дисциплины')

  # Step 1: Create the "Семестры" table with IDs
  cursor.execute('''
  CREATE TABLE IF NOT EXISTS Семестры (
      id_семестра INTEGER PRIMARY KEY AUTOINCREMENT,
      название_семестра TEXT UNIQUE
  )
  ''')
  unique_semesters = output_data['Семестр'].unique()
  for semester in unique_semesters:
      cursor.execute('INSERT OR IGNORE INTO Семестры (название_семестра) VALUES (?)', (semester,))

  # Step 2: Create the "Группы" table with unique group names
  cursor.execute('''
  CREATE TABLE IF NOT EXISTS Группы (
      id_группы INTEGER PRIMARY KEY AUTOINCREMENT,
      название_группы TEXT UNIQUE
  )
  ''')

  # Insert unique group names into "Группы"
  all_groups_corrected = set()
  for groups in output_data['Группы']:
      group_names = [group.strip() for group in groups.split(', ') if group.strip()]
      all_groups_corrected.update(group_names)

  for group in all_groups_corrected:
      cursor.execute('INSERT OR IGNORE INTO Группы (название_группы) VALUES (?)', (group,))

  # Step 3: Create the "Дисциплины" table with additional columns, handling special characters in column names
  # Properly format column names with quotes for SQL command
  formatted_discipline_columns = ", ".join([f'"{col}" TEXT' for col in output_data.columns[3:]])
  cursor.execute(f'''
  CREATE TABLE IF NOT EXISTS Дисциплины (
      id_дисциплины INTEGER PRIMARY KEY AUTOINCREMENT,
      название_дисциплины TEXT,
      id_семестра INTEGER,
      id_группы TEXT,
      {formatted_discipline_columns},
      FOREIGN KEY (id_семестра) REFERENCES Семестры(id_семестра)
  )
  ''')

  # Insert data into "Дисциплины" with references to "Семестры" and "Группы" and additional columns
  for _, row in output_data.iterrows():
      # Get semester ID
      cursor.execute('SELECT id_семестра FROM Семестры WHERE название_семестра = ?', (row['Семестр'],))
      id_семестра = cursor.fetchone()[0]

      # Get group IDs as a comma-separated string from corrected groups
      group_names = row['Группы'].split(', ')
      group_ids = []
      for group in group_names:
          cursor.execute('SELECT id_группы FROM Группы WHERE название_группы = ?', (group,))
          group_id = cursor.fetchone()[0]
          group_ids.append(str(group_id))
      id_группы_str = ','.join(group_ids)

      # Insert discipline and additional columns into "Дисциплины"
      discipline_values = (row['Дисциплина'], id_семестра, id_группы_str) + tuple(row[3:].fillna("").tolist())
      cursor.execute(f'''
      INSERT INTO Дисциплины (название_дисциплины, id_семестра, id_группы, {", ".join([f'"{col}"' for col in output_data.columns[3:]])})
      VALUES ({", ".join(["?"] * len(discipline_values))})
      ''', discipline_values)

  # Commit changes and close the database connection
  conn.commit()
  # Возвращаем список преподавателей для отображения
  cursor.execute("SELECT название_дисциплины, id_семестра, id_группы, 'Сту\nден\nтов', Лекции, Практические, Лабы, 'В\nс\nе\nг\nо'  FROM Дисциплины")
  disciplines = [{'название_дисциплины': row[0], 'id_семестра': row[1], 'id_группы': row[2], 'Сту\nден\nтов': row[3], 'Лекции': row[4], 'Практические': row[5], 'Лабы': row[6], 'В\nс\nе\nг\nо': row[7] or 0} for row in cursor.fetchall()]
    
  conn.close()
    
  return jsonify({'disciplines': disciplines})


stop_marker_1 = [ 'Факультет 1', 'очная форма обучения, Бакалавриат', 'очная форма обучения, Специализированное высшее образование', 'очная форма обучения, Специалитет', 'Факультет 3', 'очная форма обучения, Аспирантура', 'очная форма обучения, Базовое высшее образование', 'Факультет 6', 'Факультет 7', 'очно-заочная форма обучения, Специалитет', 'Факультет 9', 'Весенний семестр' ]
stop_marker_2 = [ 'Факультет 1', 'очная форма обучения, Бакалавриат', 'очная форма обучения, Специализированное высшее образование', 'очная форма обучения, Специалитет', 'Факультет 3', 'очная форма обучения, Аспирантура', 'очная форма обучения, Базовое высшее образование', 'Факультет 6', 'Факультет 7', 'очно-заочная форма обучения, Специалитет', 'Факультет 9', 'Осенний семестр' ]

filename = '/Users/kalek/Desktop/Учеба/Информатика/Проект АЯП/Нагрузка кафедра.xlsx'

#Загрузка Excel файла в DataFrame
df = pd.read_excel(filename, skiprows = 6)

if "__main__" == __name__:
  
  formatted_df = load_excel_file(df, stop_marker_1, stop_marker_2 )
  output_data = format_excel(formatted_df)
  excel_to_sql(DATABASE, output_data)
  
  print('Файл удачно загружен')