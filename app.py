from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key'

DB_FILE = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT)''')
    
    # New students table
    c.execute('''CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, reg TEXT UNIQUE, password TEXT, dept TEXT, year INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (student_id INTEGER PRIMARY KEY, percentage INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS marks (student_id INTEGER, subject TEXT, mark INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS internal_marks (id INTEGER PRIMARY KEY AUTOINCREMENT, reg TEXT, subject TEXT, marks_obtained INTEGER, max_marks INTEGER, percentage REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS fees (student_id INTEGER PRIMARY KEY, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS timetable (day TEXT, subject TEXT)''')
    
    # New leave requests table linked via reg
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, reg TEXT, type TEXT, from_date TEXT, to_date TEXT, reason TEXT, document_path TEXT, staff_remark TEXT, reviewed_by TEXT, reviewed_at TEXT, status TEXT)''')

    # Insert defaults
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
        c.execute("INSERT INTO users (username, password, role) VALUES ('staff', 'staff123', 'staff')")

    c.execute('SELECT COUNT(*) FROM students')
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO students (name, reg, password, dept, year) VALUES ('John Doe', '1029384756', 'student123', 'Computer Science', 3)")
        c.execute("INSERT INTO attendance (student_id, percentage) VALUES (1, 85)")
        c.execute("INSERT INTO marks (student_id, subject, mark) VALUES (1, 'Data Structures', 90)")
        c.execute("INSERT INTO marks (student_id, subject, mark) VALUES (1, 'Algorithms', 88)")
        c.execute("INSERT INTO fees (student_id, status) VALUES (1, 'Paid')")
        c.execute("INSERT INTO timetable (day, subject) VALUES ('Monday', 'Data Structures')")
        c.execute("INSERT INTO timetable (day, subject) VALUES ('Tuesday', 'Algorithms')")
        
        c.execute("INSERT INTO leave_requests (reg, type, from_date, to_date, reason, status) VALUES ('1029384756', 'Leave', '2023-10-15', '2023-10-16', 'Sick leave', 'Approved')")
        c.execute("INSERT INTO leave_requests (reg, type, from_date, to_date, reason, status) VALUES ('1029384756', 'OD', '2023-11-05', '2023-11-06', 'Hackathon', 'Pending')")
        c.execute("INSERT INTO leave_requests (reg, type, from_date, to_date, reason, status) VALUES ('1029384756', 'Leave', '2023-12-01', '2023-12-02', 'Family function', 'Rejected')")
        
    conn.commit()
    conn.close()

@app.route('/')
def index():
    if 'role' in session:
        if session['role'] == 'student':
            return redirect(url_for('student_dashboard'))
        return redirect(url_for(session['role'] + '_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        
        # Check if Admin or Staff
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            conn.close()
            return redirect(url_for(user['role'] + '_dashboard'))
            
        # Check if Student (via Register Number)
        student = conn.execute('SELECT * FROM students WHERE reg = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        
        if student:
            session['student_id'] = student['id']
            session['name'] = student['name']
            session['reg'] = student['reg']
            session['role'] = 'student'
            return redirect(url_for('student_dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students').fetchall()
    conn.close()
    return render_template('admin.html', students=students)

@app.route('/admin/add_student', methods=['POST'])
def add_student():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    username = request.form['username']
    password = request.form['password']
    name = request.form['name']
    dept = request.form['dept']
    year = request.form['year']
    
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO students (name, reg, password, dept, year) VALUES (?, ?, ?, ?, ?)", (name, username, password, dept, year))
        conn.commit()
    except:
        pass
    finally:
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_fees', methods=['POST'])
def update_fees():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    student_id = request.form['student_id']
    status = request.form['status']
    
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO fees (student_id, status) VALUES (?, ?)", (student_id, status))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/staff')
def staff_dashboard():
    if session.get('role') != 'staff':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    requests_raw = conn.execute('''
        SELECT lr.id, lr.reg, s.name, s.dept, lr.type, lr.from_date, lr.to_date, 
               lr.reason, lr.document_path, lr.status, lr.staff_remark, lr.reviewed_by, lr.reviewed_at
        FROM leave_requests lr
        JOIN students s ON lr.reg = s.reg
        ORDER BY lr.id DESC
    ''').fetchall()
    conn.close()
    
    requests_list = [tuple(r) for r in requests_raw]
    return render_template('staff.html', requests=requests_list)

@app.route('/staff/update_request', methods=['POST'])
def update_request():
    if session.get('role') != 'staff':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    data = request.json
    req_id = data.get('request_id')
    action = data.get('action') # 'Approved' or 'Rejected'
    remark = data.get('remark', '')
    staff_username = session.get('username')
    
    from datetime import datetime
    reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE leave_requests 
        SET status = ?, staff_remark = ?, reviewed_by = ?, reviewed_at = ?
        WHERE id = ?
    ''', (action, remark, staff_username, reviewed_at, req_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/staff/add_student_api', methods=['POST'])
def add_student_api():
    if session.get('role') != 'staff': return jsonify({'success': False, 'message': 'Unauthorized'})
    data = request.json
    reg = data.get('reg')
    name = data.get('name')
    dept = data.get('dept')
    year = data.get('year')
    conn = get_db_connection()
    existing = conn.execute('SELECT * FROM students WHERE reg = ?', (reg,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'success': False, 'message': 'Register Number already exists.'})
    
    conn.execute("INSERT INTO students (name, reg, password, dept, year) VALUES (?, ?, 'student123', ?, ?)", (name, reg, dept, year))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Student added successfully!'})

@app.route('/staff/add_marks', methods=['POST'])
def add_marks():
    if session.get('role') != 'staff': return jsonify({'success': False, 'message': 'Unauthorized'})
    data = request.json
    reg = data.get('reg')
    subject = data.get('subject')
    try:
        obtained = float(data.get('marks_obtained'))
        maximum = float(data.get('max_marks'))
        percentage = (obtained / maximum) * 100 if maximum > 0 else 0
    except:
        return jsonify({'success': False, 'message': 'Invalid mark values.'})

    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE reg = ?', (reg,)).fetchone()
    if not student:
        conn.close()
        return jsonify({'success': False, 'message': 'Student not found.'})
    
    conn.execute("INSERT INTO internal_marks (reg, subject, marks_obtained, max_marks, percentage) VALUES (?, ?, ?, ?, ?)", (reg, subject, obtained, maximum, percentage))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Marks uploaded successfully!'})

@app.route('/staff/update_attendance_api', methods=['POST'])
def update_attendance_api():
    if session.get('role') != 'staff': return jsonify({'success': False, 'message': 'Unauthorized'})
    data = request.json
    reg = data.get('reg')
    try:
        percentage = float(data.get('percentage'))
    except:
        return jsonify({'success': False, 'message': 'Invalid percentage.'})
    
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE reg = ?', (reg,)).fetchone()
    if not student:
        conn.close()
        return jsonify({'success': False, 'message': 'Student not found.'})
        
    student_id = student['id']
    conn.execute("INSERT OR REPLACE INTO attendance (student_id, percentage) VALUES (?, ?)", (student_id, percentage))
    conn.commit()
    conn.close()
    
    msg = 'Attendance updated successfully!'
    defaulter = percentage < 75
    if defaulter:
        msg = 'Attendance updated. Alert: Student is a Defaulter (<75%).'
        
    return jsonify({'success': True, 'message': msg, 'defaulter': defaulter})

@app.route('/student')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
        
    student_id = session.get('student_id')
    if not student_id:
        return redirect(url_for('logout'))
        
    conn = get_db_connection()
    stu_row = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    if not stu_row:
        conn.close()
        return redirect(url_for('logout'))
        
    student_tuple = tuple(stu_row)
    
    attendance = conn.execute('SELECT * FROM attendance WHERE student_id = ?', (student_id,)).fetchone()
    marks = conn.execute('SELECT * FROM marks WHERE student_id = ?', (student_id,)).fetchall()
    fees = conn.execute('SELECT * FROM fees WHERE student_id = ?', (student_id,)).fetchone()
    timetable = conn.execute('SELECT * FROM timetable').fetchall()
    
    reg = session.get('reg')
    requests_raw = conn.execute('SELECT * FROM leave_requests WHERE reg = ?', (reg,)).fetchall()
    leave_requests = [tuple(req) for req in requests_raw]
    
    # Internal Marks
    internal_marks_raw = conn.execute('SELECT * FROM internal_marks WHERE reg = ?', (reg,)).fetchall()
    internal_marks = [tuple(m) for m in internal_marks_raw]
    
    conn.close()
    
    return render_template('student.html', student=student_tuple, attendance=attendance, marks=marks, fees=fees, timetable=timetable, leave_requests=leave_requests, internal_marks=internal_marks)

@app.route('/chat', methods=['POST'])
def chat():
    if session.get('role') != 'student':
        return jsonify({'response': 'Unauthorized'})
        
    student_id = session.get('student_id')
    if not student_id:
        return jsonify({'response': 'No student profile linked.'})
        
    data = request.json
    message = data.get('message', '').lower()
    
    conn = get_db_connection()
    response = "I'm sorry, I didn't understand that. Try asking about 'attendance', 'marks', 'fees', or 'timetable'."
    
    if 'attendance' in message:
        att = conn.execute('SELECT percentage FROM attendance WHERE student_id = ?', (student_id,)).fetchone()
        response = f"Your attendance is {att['percentage']}%." if att else "Attendance record not found."
    elif 'mark' in message:
        marks = conn.execute('SELECT subject, mark FROM marks WHERE student_id = ?', (student_id,)).fetchall()
        if marks:
            response = "Your marks are: " + ", ".join([f"{m['subject']}: {m['mark']}" for m in marks]) + "."
        else:
            response = "No marks found."
    elif 'fee' in message:
        fees = conn.execute('SELECT status FROM fees WHERE student_id = ?', (student_id,)).fetchone()
        response = f"Your fee status is: {fees['status']}." if fees else "Fee record not found."
    elif 'timetable' in message:
        tt = conn.execute('SELECT day, subject FROM timetable').fetchall()
        if tt:
            response = "Timetable: " + ", ".join([f"{t['day']}: {t['subject']}" for t in tt]) + "."
        else:
            response = "Timetable not available."
            
    conn.close()
    return jsonify({'response': response})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
