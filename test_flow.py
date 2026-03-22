import app
client = app.app.test_client()

# login as student
res1 = client.post('/login', data={'username': '1029384756', 'password': 'student123'})
print('Login Student Status:', res1.status_code)

# submit request
res2 = client.post('/submit_request', json={'request_type': 'Leave', 'reason': 'Test Reason', 'from_date': '2024-01-01', 'to_date': '2024-01-02'})
print('Submit Response:', res2.json)

# login as staff
res3 = client.post('/login', data={'username': 'staff', 'password': 'staff123'})
print('Login Staff Status:', res3.status_code)

# get staff requests
res4 = client.get('/staff_requests')
print('Staff Dashboard OK:', res4.status_code == 200)

# check if request is in db directly
import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM leave_requests ORDER BY id DESC LIMIT 1")
row = cursor.fetchone()
print('Latest DB Row:', row)
conn.close()
