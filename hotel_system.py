import sqlite3
import datetime
import os
import time
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ==========================================
# CONFIGURATION & SETUP
# ==========================================
app = Flask(__name__)
app.secret_key = 'fahsai_resort_secret_key'
DB_NAME = 'hotel_database.db'

# ตั้งค่าการอัปโหลดไฟล์
UPLOAD_FOLDER = 'static/uploads' # โฟลเดอร์สำหรับเก็บไฟล์สลิป
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# สร้างโฟลเดอร์เก็บรูปถ้ายังไม่มี
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==========================================
# DATABASE MANAGEMENT (SQLite)
# ==========================================
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # D1 Customer
    c.execute('''CREATE TABLE IF NOT EXISTS Customer (
        Member_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        F_name TEXT NOT NULL,
        Lname TEXT NOT NULL,
        Address TEXT,
        Phonenumber TEXT,
        Reg_date TEXT,
        Email TEXT UNIQUE NOT NULL,
        Password TEXT NOT NULL
    )''')

    # D2 RoomType
    c.execute('''CREATE TABLE IF NOT EXISTS RoomType (
        Type_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Type_Name TEXT NOT NULL,
        Price_Night REAL NOT NULL,
        Max_Guest INTEGER,
        Description TEXT,
        Image_URL TEXT
    )''')

    # D3 Room
    c.execute('''CREATE TABLE IF NOT EXISTS Room (
        Room_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Type_ID INTEGER,
        Room_Number TEXT NOT NULL,
        Room_Status TEXT DEFAULT 'Available',
        FOREIGN KEY (Type_ID) REFERENCES RoomType (Type_ID)
    )''')

    # D4 Booking
    c.execute('''CREATE TABLE IF NOT EXISTS Booking (
        Booking_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Member_ID INTEGER,
        Room_ID INTEGER,
        Check_In TEXT NOT NULL,
        Check_Out TEXT NOT NULL,
        Total_Price REAL,
        Booking_Status TEXT DEFAULT 'Waiting Payment',
        Book_Date TEXT,
        FOREIGN KEY (Member_ID) REFERENCES Customer (Member_ID),
        FOREIGN KEY (Room_ID) REFERENCES Room (Room_ID)
    )''')

    # D5 Payment
    c.execute('''CREATE TABLE IF NOT EXISTS Payment (
        Pay_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Booking_ID INTEGER,
        Pay_Amount REAL,
        Pay_Method TEXT,
        Pay_Date TEXT,
        Pay_Slip TEXT,
        Pay_Status TEXT DEFAULT 'Pending',
        FOREIGN KEY (Booking_ID) REFERENCES Booking (Booking_ID)
    )''')

    # D6 SystemAdmin
    c.execute('''CREATE TABLE IF NOT EXISTS SystemAdmin (
        Email TEXT PRIMARY KEY
    )''')

    # --- Seed Data ---
    c.execute('SELECT count(*) FROM RoomType')
    if c.fetchone()[0] == 0:
        room_types = [
            ('Sea View Deluxe', 3500, 2, 'ห้องพักหรูวิวทะเลพาโนรามา พร้อมระเบียงส่วนตัว', 'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?auto=format&fit=crop&w=800&q=80'),
            ('Garden Villa', 5500, 4, 'วิลล่าส่วนตัวท่ามกลางสวนทรอปิคอล เหมาะสำหรับครอบครัว', 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80'),
            ('Pool Suite', 8500, 2, 'ห้องสวีทพร้อมสระว่ายน้ำส่วนตัว สุดโรแมนติก', 'https://images.unsplash.com/photo-1591088398332-8a7791972843?auto=format&fit=crop&w=800&q=80')
        ]
        c.executemany('INSERT INTO RoomType (Type_Name, Price_Night, Max_Guest, Description, Image_URL) VALUES (?,?,?,?,?)', room_types)
        
        rooms = [
            (1, '101'), (1, '102'), (1, '103'),
            (2, '201'), (2, '202'),
            (3, '301')
        ]
        c.executemany('INSERT INTO Room (Type_ID, Room_Number) VALUES (?,?)', rooms)

    default_admins = [
        ('System', 'Admin', 'admin@hotel.com', 'admin123'),
        ('Resort', 'Owner', 'owner@hotel.com', 'owner123')
    ]
    for f_name, l_name, email, pwd in default_admins:
        check_cust = c.execute("SELECT * FROM Customer WHERE Email = ?", (email,)).fetchone()
        if not check_cust:
            hashed_pw = generate_password_hash(pwd)
            c.execute('INSERT INTO Customer (F_name, Lname, Email, Password, Phonenumber) VALUES (?,?,?,?,?)', 
                      (f_name, l_name, email, hashed_pw, '0000000000'))
        c.execute('INSERT OR IGNORE INTO SystemAdmin (Email) VALUES (?)', (email,))

    conn.commit()
    conn.close()

init_db()

# ==========================================
# ROUTES & LOGIC
# ==========================================

@app.route('/')
def index():
    conn = get_db_connection()
    room_types = conn.execute('SELECT * FROM RoomType').fetchall()
    conn.close()
    return render_template('index.html', room_types=room_types)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        f_name = request.form['f_name']
        l_name = request.form['l_name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        phone = request.form['phone']
        # Address removed
        reg_date = datetime.datetime.now().strftime("%Y-%m-%d")

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO Customer (F_name, Lname, Email, Password, Phonenumber, Reg_date) VALUES (?, ?, ?, ?, ?, ?)',
                         (f_name, l_name, email, password, phone, reg_date))
            conn.commit()
            flash('สมัครสมาชิกเรียบร้อยแล้ว ยินดีต้อนรับสู่ครอบครัวฟ้าทราย', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('อีเมลนี้มีผู้ใช้งานแล้ว', 'danger')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Customer WHERE Email = ?', (email,)).fetchone()
        
        if user and check_password_hash(user['Password'], password):
            session['user_id'] = user['Member_ID']
            session['user_name'] = user['F_name']
            
            is_admin = conn.execute('SELECT 1 FROM SystemAdmin WHERE Email = ?', (email,)).fetchone()
            conn.close()

            if is_admin:
                session['is_admin'] = True
                return redirect(url_for('admin_dashboard'))
            
            flash(f'ยินดีต้อนรับกลับ, {user["F_name"]}', 'success')
            return redirect(url_for('index'))
        else:
            conn.close()
            flash('อีเมลหรือรหัสผ่านไม่ถูกต้อง', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
    return redirect(url_for('index'))

@app.route('/room/<int:type_id>', methods=['GET', 'POST'])
def room_detail(type_id):
    if 'user_id' not in session:
        flash('กรุณาเข้าสู่ระบบเพื่อทำการจองห้องพัก', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    room_type = conn.execute('SELECT * FROM RoomType WHERE Type_ID = ?', (type_id,)).fetchone()
    
    if request.method == 'POST':
        check_in = request.form['check_in']
        check_out = request.form['check_out']
        
        try:
            d1 = datetime.datetime.strptime(check_in, "%Y-%m-%d")
            d2 = datetime.datetime.strptime(check_out, "%Y-%m-%d")
            delta = d2 - d1
            nights = delta.days
            
            if nights <= 0:
                flash('วันที่เช็คเอาท์ต้องหลังจากวันที่เช็คอิน', 'danger')
            else:
                total_price = nights * room_type['Price_Night']
                available_room = conn.execute("SELECT Room_ID FROM Room WHERE Type_ID = ? AND Room_Status = 'Available' LIMIT 1", (type_id,)).fetchone()
                
                if available_room:
                    conn.execute('''INSERT INTO Booking (Member_ID, Room_ID, Check_In, Check_Out, Total_Price, Book_Date, Booking_Status) 
                                    VALUES (?, ?, ?, ?, ?, ?, 'Waiting Payment')''',
                                (session['user_id'], available_room['Room_ID'], check_in, check_out, total_price, datetime.datetime.now().strftime("%Y-%m-%d")))
                    
                    conn.execute("UPDATE Room SET Room_Status = 'Booked' WHERE Room_ID = ?", (available_room['Room_ID'],))
                    
                    conn.commit()
                    flash(f'จองสำเร็จ! ยอดรวม {total_price:,.0f} บาท กรุณาชำระเงินเพื่อยืนยันสิทธิ์', 'success')
                    return redirect(url_for('my_bookings'))
                else:
                    flash('ขออภัย ห้องพักประเภทนี้เต็มในช่วงเวลาดังกล่าว', 'danger')
        except ValueError:
             flash('รูปแบบวันที่ไม่ถูกต้อง', 'danger')
    
    conn.close()
    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    return render_template('room_detail.html', room=room_type, today=today_date)

@app.route('/my_bookings')
def my_bookings():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    bookings = conn.execute('''
        SELECT b.*, r.Room_Number, t.Type_Name, t.Image_URL
        FROM Booking b 
        JOIN Room r ON b.Room_ID = r.Room_ID 
        JOIN RoomType t ON r.Type_ID = t.Type_ID 
        WHERE b.Member_ID = ? ORDER BY b.Booking_ID DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    booking = conn.execute('SELECT * FROM Booking WHERE Booking_ID = ? AND Member_ID = ?', (booking_id, session['user_id'])).fetchone()
    
    if booking:
        if booking['Booking_Status'] == 'Waiting Payment':
            conn.execute("UPDATE Booking SET Booking_Status = 'Cancelled' WHERE Booking_ID = ?", (booking_id,))
            conn.execute("UPDATE Room SET Room_Status = 'Available' WHERE Room_ID = ?", (booking['Room_ID'],))
            conn.commit()
            flash('ยกเลิกการจองเรียบร้อยแล้ว', 'success')
        else:
            flash('รายการนี้ชำระเงินแล้วหรือไม่สามารถยกเลิกได้', 'danger')
    else:
        flash('เกิดข้อผิดพลาด ไม่พบรายการจอง', 'danger')
        
    conn.close()
    return redirect(url_for('my_bookings'))

@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
def payment(booking_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    booking = conn.execute('SELECT * FROM Booking WHERE Booking_ID = ?', (booking_id,)).fetchone()
    
    if request.method == 'POST':
        amount = request.form['amount']
        method = request.form['method']
        
        # รับไฟล์จากฟอร์ม
        if 'slip_image' not in request.files:
            flash('กรุณาเลือกไฟล์รูปภาพสลิปการโอน', 'danger')
            return redirect(request.url)
            
        file = request.files['slip_image']
        
        if file.filename == '':
            flash('ไม่ได้เลือกไฟล์', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            # ตั้งชื่อไฟล์ใหม่: slip_bookingID_timestamp.extension
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            new_filename = f"slip_{booking_id}_{int(time.time())}.{file_ext}"
            filename = secure_filename(new_filename)
            
            # บันทึกไฟล์
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # สร้าง URL เพื่อเก็บลง DB (เช่น /static/uploads/slip_1_12345.jpg)
            slip_url = f"/{UPLOAD_FOLDER}/{filename}"
            pay_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn.execute('''INSERT INTO Payment (Booking_ID, Pay_Amount, Pay_Method, Pay_Date, Pay_Slip, Pay_Status)
                            VALUES (?, ?, ?, ?, ?, 'Pending')''', 
                         (booking_id, amount, method, pay_date, slip_url))
            
            conn.execute("UPDATE Booking SET Booking_Status = 'Verifying' WHERE Booking_ID = ?", (booking_id,))
            
            conn.commit()
            conn.close()
            flash('อัปโหลดสลิปเรียบร้อย รอการตรวจสอบสักครู่', 'success')
            return redirect(url_for('my_bookings'))
        else:
            flash('รองรับเฉพาะไฟล์รูปภาพ (png, jpg, jpeg, gif) เท่านั้น', 'danger')

    conn.close()
    return render_template('payment.html', booking=booking)

@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        flash('เข้าถึงได้เฉพาะผู้ดูแลระบบเท่านั้น', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    total_sales = conn.execute("SELECT SUM(Total_Price) FROM Booking WHERE Booking_Status = 'Paid'").fetchone()[0] or 0
    
    pending_payments = conn.execute('''
        SELECT p.*, b.Total_Price, c.F_name, c.Lname 
        FROM Payment p 
        JOIN Booking b ON p.Booking_ID = b.Booking_ID
        JOIN Customer c ON b.Member_ID = c.Member_ID
        WHERE p.Pay_Status = 'Pending'
    ''').fetchall()
    
    admins = conn.execute('''
        SELECT c.F_name, c.Lname, c.Email 
        FROM Customer c
        JOIN SystemAdmin s ON c.Email = s.Email
    ''').fetchall()
    
    booked_rooms = conn.execute('''
        SELECT r.Room_Number, t.Type_Name, b.Check_In, b.Check_Out, c.F_name, c.Lname, b.Booking_Status
        FROM Room r
        JOIN Booking b ON r.Room_ID = b.Room_ID
        JOIN Customer c ON b.Member_ID = c.Member_ID
        JOIN RoomType t ON r.Type_ID = t.Type_ID
        WHERE r.Room_Status = 'Booked'
        AND b.Booking_Status IN ('Waiting Payment', 'Verifying', 'Paid')
        GROUP BY r.Room_ID
    ''').fetchall()
    
    available_rooms = conn.execute('''
        SELECT r.Room_Number, t.Type_Name, t.Price_Night
        FROM Room r
        JOIN RoomType t ON r.Type_ID = t.Type_ID
        WHERE r.Room_Status = 'Available'
    ''').fetchall()
    
    conn.close()
    return render_template('admin_dashboard.html', 
                           total_sales=total_sales, 
                           payments=pending_payments, 
                           admins=admins,
                           booked_rooms=booked_rooms,
                           available_rooms=available_rooms)

@app.route('/admin/add_admin', methods=['POST'])
def add_admin():
    if not session.get('is_admin'): return redirect(url_for('index'))
    
    f_name = request.form['f_name']
    l_name = request.form['l_name']
    email = request.form['email']
    password = generate_password_hash(request.form['password'])
    phone = request.form['phone']
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO Customer (F_name, Lname, Email, Password, Phonenumber, Reg_date) VALUES (?, ?, ?, ?, ?, ?)',
                     (f_name, l_name, email, password, phone, datetime.datetime.now().strftime("%Y-%m-%d")))
        conn.execute('INSERT INTO SystemAdmin (Email) VALUES (?)', (email,))
        conn.commit()
        flash(f'เพิ่มผู้ดูแลระบบ {f_name} เรียบร้อยแล้ว', 'success')
    except sqlite3.IntegrityError:
        flash('อีเมลนี้มีอยู่ในระบบแล้ว', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_admin', methods=['POST'])
def delete_admin():
    if not session.get('is_admin'): return redirect(url_for('index'))
    
    email_to_delete = request.form['email']
    
    if email_to_delete == 'owner@hotel.com':
        flash('ไม่สามารถลบบัญชีเจ้าของ (Owner) ได้', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM SystemAdmin WHERE Email = ?', (email_to_delete,))
    conn.commit()
    conn.close()
    
    flash(f'ลบสิทธิ์ผู้ดูแลระบบของ {email_to_delete} เรียบร้อยแล้ว', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve/<int:pay_id>')
def approve_payment(pay_id):
    if not session.get('is_admin'): return redirect(url_for('index'))
    
    conn = get_db_connection()
    conn.execute("UPDATE Payment SET Pay_Status = 'Completed' WHERE Pay_ID = ?", (pay_id,))
    pay_data = conn.execute("SELECT Booking_ID FROM Payment WHERE Pay_ID = ?", (pay_id,)).fetchone()
    if pay_data:
        conn.execute("UPDATE Booking SET Booking_Status = 'Paid' WHERE Booking_ID = ?", (pay_data['Booking_ID'],))
    
    conn.commit()
    conn.close()
    flash('อนุมัติการชำระเงินเรียบร้อย', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)