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
    
    staff = conn.execute('SELECT * FROM staff').fetchall()
    
    fees = conn.execute('''
        SELECT s.name, s.reg, f.* FROM fees f
        JOIN students s ON s.id = f.student_id
    ''').fetchall()
    
    total_students = len(students)
    total_staff = len(staff)
    
    dept_counts = conn.execute('SELECT dept, COUNT(*) as count FROM students GROUP BY dept').fetchall()
    dept_labels = [d['dept'] for d in dept_counts] if dept_counts else ["None"]
    dept_data = [d['count'] for d in dept_counts] if dept_counts else [0]
    
    conn.close()
    return render_template('admin.html', students=students, staff=staff, fees=fees, 
                           total_students=total_students, total_staff=total_staff,
                           dept_labels=dept_labels, dept_data=dept_data)

@app.route('/admin/add_student_full', methods=['POST'])
def add_student_full():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    data = request.form
    photo_path = ""
    if 'photo' in request.files:
        photo = request.files['photo']
        if photo.filename != '':
            photo_path = 'static/uploads/' + photo.filename
            import os
            os.makedirs('static/uploads', exist_ok=True)
            photo.save(photo_path)
            
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO students (name, reg, password, dept, year, dob, parent_name, parent_contact, parent_occ, income, course, course_id, photo_path)
            VALUES (?, ?, 'student123', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data.get('name'), data.get('roll_number'), data.get('dept'), data.get('year'),
              data.get('dob'), data.get('parent_name'), data.get('parent_contact'), data.get('parent_occ'),
              data.get('income'), data.get('course'), data.get('course_id'), photo_path))
        conn.commit()
    except Exception as e:
        print("Error inserting student:", e)
    finally:
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_staff', methods=['POST'])
def add_staff():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO staff (name, dept, subject) VALUES (?, ?, ?)", 
                     (request.form.get('name'), request.form.get('dept'), request.form.get('subject')))
        conn.commit()
    except: pass
    finally: conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/manage_fees', methods=['POST'])
def manage_fees():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    data = request.form
    student_reg = data.get('student_reg')
    
    conn = get_db_connection()
    student = conn.execute('SELECT id FROM students WHERE reg = ?', (student_reg,)).fetchone()
    if not student:
        conn.close()
        return redirect(url_for('admin_dashboard'))
        
    stu_id = student['id']
    tuition = float(data.get('tuition_fee', 0) or 0)
    exam = float(data.get('exam_fee', 0) or 0)
    other = float(data.get('other_fee', 0) or 0)
    paid = float(data.get('paid_amount', 0) or 0)
    
    total = tuition + exam + other
    due = total - paid
    status = "Paid" if due <= 0 else "Pending"
    
    conn.execute('''
        INSERT OR REPLACE INTO fees (student_id, status, tuition_fee, exam_fee, other_fee, total_fee, paid_amount, due_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (stu_id, status, tuition, exam, other, total, paid, due))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/staff')
@app.route('/staff_requests')
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

@app.route('/update_request/<int:req_id>', methods=['POST'])
def update_request(req_id):
    if session.get('role') != 'staff':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    data = request.json
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
    requests_raw = conn.execute('SELECT * FROM leave_requests WHERE reg = ? ORDER BY id DESC', (reg,)).fetchall()
    leave_requests = [tuple(req) for req in requests_raw]
    
    # Internal Marks
    internal_marks_raw = conn.execute('SELECT * FROM internal_marks WHERE reg = ?', (reg,)).fetchall()
    internal_marks = [tuple(m) for m in internal_marks_raw]
    
    conn.close()
    
    return render_template('student.html', student=student_tuple, attendance=attendance, marks=marks, fees=fees, timetable=timetable, leave_requests=leave_requests, internal_marks=internal_marks)

@app.route('/submit_request', methods=['POST'])
def submit_request():
    if session.get('role') != 'student':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    reg = session.get('reg')
    if not reg:
        return jsonify({'success': False, 'message': 'Registration number not found'}), 400
        
    data = request.json
    req_type = data.get('request_type') # 'Leave' or 'OD'
    reason = data.get('reason')
    from_date = data.get('from_date')
    to_date = data.get('to_date')
    
    if not all([req_type, reason, from_date, to_date]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO leave_requests (reg, type, from_date, to_date, reason, status) 
        VALUES (?, ?, ?, ?, ?, 'Pending')
    ''', (reg, req_type, from_date, to_date, reason))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Request submitted successfully'})

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
        response = f"Your attendance is {att['percentage']}%." if att else "Your attendance has not been updated by the staff yet."
    elif 'mark' in message:
        reg = session.get('reg')
        internal = conn.execute('SELECT subject, percentage FROM internal_marks WHERE reg = ?', (reg,)).fetchall()
        marks = conn.execute('SELECT subject, mark FROM marks WHERE student_id = ?', (student_id,)).fetchall()
        
        if internal or marks:
            parts = []
            for m in internal:
                parts.append(f"{m['subject']}: {m['percentage']:.1f}%")
            for m in marks:
                parts.append(f"{m['subject']}: {m['mark']}%")
            response = "Your marks are: " + ", ".join(parts) + "."
        else:
            response = "No marks found. Your internal marks have not been uploaded yet."
    elif 'fee' in message:
        fees = conn.execute('SELECT * FROM fees WHERE student_id = ?', (student_id,)).fetchone()
        if fees:
            due = fees['due_amount'] if 'due_amount' in fees.keys() and fees['due_amount'] is not None else 0
            paid = fees['paid_amount'] if 'paid_amount' in fees.keys() and fees['paid_amount'] is not None else 0
            response = f"Your fee status is: {fees['status']}. Total Due: ${due:,.2f} (Paid: ${paid:,.2f})."
        else:
            response = "No fee data found for your profile."
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
