import sqlite3
conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS staff (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, dept TEXT, subject TEXT)')
cols_students = ['dob', 'parent_name', 'parent_contact', 'parent_occ', 'income', 'course', 'course_id', 'photo_path']
for col in cols_students:
    try: c.execute(f'ALTER TABLE students ADD COLUMN {col} TEXT')
    except sqlite3.OperationalError: pass
cols_fees = ['tuition_fee', 'exam_fee', 'other_fee', 'total_fee', 'paid_amount', 'due_amount']
for col in cols_fees:
    try: c.execute(f'ALTER TABLE fees ADD COLUMN {col} REAL')
    except sqlite3.OperationalError: pass
conn.commit()
conn.close()
print('DB updated')
