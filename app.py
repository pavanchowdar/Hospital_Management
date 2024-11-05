
import sqlite3
import random
from flask import Flask, render_template, request, redirect, url_for, session, g,flash as curses_flash
from db_helpers import query_db, modify_db, get_db_connection
from models import create_tables
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'hospital_secret_key'

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)

# Home route for the main page
@app.route('/')
def home():
    return render_template('index.html')

# Doctor Registration Route
@app.route('/doctor_register', methods=['GET', 'POST'])
def doctor_register():
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        loginid = request.form['loginid']
        password = request.form['password']
        email = request.form['email']

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Insert the doctor into the database
            cursor.execute("INSERT INTO doctors (name, specialization, loginid, password, email) VALUES (?, ?, ?, ?, ?)", 
                           (name, specialization, loginid, password, email))
            conn.commit()
            curses_flash('Doctor registration successful.')
        except sqlite3.IntegrityError as e:
            conn.rollback()
            curses_flash(f"Registration failed: {str(e)}", "error")
        finally:
            conn.close()

        return redirect(url_for('doctor_register'))
    return render_template('doctor_register.html')

# Patient Registration Route
@app.route('/patient_register', methods=['GET', 'POST'])
def patient_register():
    if request.method == 'POST':
        name = request.form['name']
        loginid = request.form['loginid']
        password = request.form['password']
        email = request.form['email']
        age = request.form['age']
        gender=request.form['gender']

        if not name or not loginid or not password or not email or not age or not gender:
            curses_flash('All fields are required!', 'error')
            return redirect(url_for('patient_register'))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO patients (name, loginid, password, email, age, gender) VALUES (?, ?, ?, ?, ?,?)",
                           (name, loginid, password, email, age, gender))
            conn.commit()
            conn.close()

            curses_flash('Patient registration successful.', 'success')
            return redirect(url_for('patient_register'))
        except sqlite3.IntegrityError as e:
            curses_flash(f'Registration failed. Error: {str(e)}', 'error')
            return redirect(url_for('patient_register'))
    return render_template('patient_register.html')

# Admin Login
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        loginid = request.form['loginid']
        password = request.form['password']
        admin = query_db('SELECT * FROM admins WHERE loginid = ? AND password = ?', (loginid, password), one=True)

        if admin:
            session['admin_id'] = admin['id']
            return redirect(url_for('admin_dashboard'))
        else:
            curses_flash("Invalid login credentials", "error")
            return redirect(url_for('admin_login'))
    
    return render_template('admin_login.html')

# Admin Dashboard (Protected Route)
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    # Fetch appointments along with their payment statuses
    appointments = query_db('''
        SELECT a.id AS appointment_id, 
               p.name AS patient_name, 
               d.name AS doctor_name, 
               a.appointment_date, 
               COALESCE(b.payment_status, 'Pending') AS payment_status, 
               b.id AS billing_id
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        LEFT JOIN billing b ON a.patient_id = b.patient_id AND a.doctor_id = b.doctor_id
        ORDER BY a.appointment_date
    ''')

    return render_template('admin_dashboard.html', appointments=appointments)





# View Doctors
@app.route('/view_doctors')
def view_doctors():
    doctors = query_db('SELECT id, name, specialization, email FROM doctors')
    return render_template('view_doctors.html', doctors=doctors)

# Edit Doctor
@app.route('/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
def edit_doctor(doctor_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    doctor = query_db('SELECT * FROM doctors WHERE id = ?', [doctor_id], one=True)
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        email = request.form['email']
        modify_db('UPDATE doctors SET name = ?, specialization = ?, email = ? WHERE id = ?',
                  (name, specialization, email, doctor_id))
        return redirect(url_for('view_doctors'))

    return render_template('edit_doctor.html', doctor=doctor)

# Delete Doctor
@app.route('/delete_doctor/<int:doctor_id>')
def delete_doctor(doctor_id):
    try:
        modify_db('DELETE FROM doctors WHERE id = ?', [doctor_id])
        curses_flash('Doctor deleted successfully.', 'success')
    except sqlite3.IntegrityError:
        curses_flash('Cannot delete doctor, existing references in appointments.', 'error')
    return redirect(url_for('view_doctors'))

# View Patients
@app.route('/view_patients')
def view_patients():
    patients = query_db('SELECT * FROM patients')
    return render_template('view_patients.html', patients=patients)

# Edit Patient
@app.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    patient = query_db('SELECT * FROM patients WHERE id = ?', [patient_id], one=True)
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        email = request.form['email']
        modify_db('UPDATE patients SET name = ?, age = ?, email = ? WHERE id = ?',
                  (name, age, email, patient_id))
        return redirect(url_for('view_patients'))

    return render_template('edit_patient.html', patient=patient)

#delete_patient
@app.route('/delete_patient/<int:patient_id>', methods=['GET'])
def delete_patient(patient_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    # First, delete all related appointments and billing records
    modify_db('DELETE FROM appointments WHERE patient_id = ?', [patient_id])
    modify_db('DELETE FROM billing WHERE patient_id = ?', [patient_id])

    # Now delete the patient
    modify_db('DELETE FROM patients WHERE id = ?', [patient_id])
    
    return redirect(url_for('view_patients'))


# View Billing
@app.route('/view_billing/<int:patient_id>', methods=['GET'])
def view_billing(patient_id):
    # Fetch the billing information for this patient
    billing_info = query_db('''
        SELECT b.id, p.name AS patient_name, d.name AS doctor_name, b.total_amount, b.payment_status, b.payment_date
        FROM billing b
        JOIN patients p ON b.patient_id = p.id
        JOIN doctors d ON b.doctor_id = d.id
        WHERE b.patient_id = ?
    ''', [patient_id])

    return render_template('view_billing.html', billing_info=billing_info)


# Edit Billing
@app.route('/edit_billing/<int:billing_id>', methods=['GET', 'POST'])
def edit_billing(billing_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    billing = query_db('SELECT * FROM billing WHERE id = ?', [billing_id], one=True)
    if request.method == 'POST':
        total_amount = request.form['total_amount']
        payment_status = request.form['payment_status']
        modify_db('UPDATE billing SET total_amount = ?, payment_status = ? WHERE id = ?',
                  (total_amount, payment_status, billing_id))
        return redirect(url_for('view_billing'))

    return render_template('edit_billing.html', billing=billing)

# Patient Login
@app.route('/patient_login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        loginid = request.form['loginid']
        password = request.form['password']
        patient = query_db('SELECT * FROM patients WHERE loginid = ? AND password = ?', (loginid, password), one=True)
        if patient:
            session['patient_id'] = patient['id']
            return redirect(url_for('patient_dashboard'))
        else:
            return "Invalid credentials!"
    return render_template('patient_login.html')

# Doctor Login
@app.route('/doctor_login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        loginid = request.form['loginid']
        password = request.form['password']
        doctor = query_db('SELECT * FROM doctors WHERE loginid = ? AND password = ?', (loginid, password), one=True)
        if doctor:
            session['doctor_id'] = doctor['id']
            return redirect(url_for('doctor_dashboard'))
        else:
            return "Invalid credentials!"
    return render_template('doctor_login.html')

@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if 'patient_id' not in session:
        return redirect(url_for('patient_login'))

    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        appointment_date = request.form['appointment_date']
        
        patient_id = session['patient_id']

        # Insert the appointment into the database
        modify_db('INSERT INTO appointments (patient_id, doctor_id, appointment_date) VALUES (?, ?, ?)',
                  (patient_id, doctor_id, appointment_date))

        # Fetch doctor info and store in the session for billing
        doctor = query_db('SELECT * FROM doctors WHERE id = ?', [doctor_id], one=True)
        session['doctor_id'] = doctor_id
        session['doctor_name'] = doctor['name']  # Store doctor's name for billing

        # Redirect to payment page
        return redirect(url_for('billing', patient_id=patient_id))

    # Render the form to book an appointment
    doctors = query_db('SELECT * FROM doctors')
    return render_template('book_appointment.html', doctors=doctors)



@app.route('/view_appointments')
def view_appointments():
    try:
        patient_id = session['patient_id']  # Assuming the patient is logged in
        appointments = query_db('''
            SELECT a.id AS appointment_id, d.name AS doctor_name, a.appointment_date, b.payment_status
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            LEFT JOIN billing b ON a.patient_id = b.patient_id AND a.doctor_id = b.doctor_id
            WHERE a.patient_id = ?
        ''', [patient_id])
        return render_template('view_appointments.html', appointments=appointments)
    except Exception as e:
        curses_flash(f'Error fetching appointments: {e}', 'error')
        return redirect(url_for('patient_dashboard'))




@app.route('/patient_dashboard')
def patient_dashboard():
    return render_template('patient_dashboard.html')

@app.route('/patient_logout')
def patient_logout():
    session.pop('patient_id', None)
    curses_flash('You have successfully logged out.')
    return redirect(url_for('patient_login'))

# Admin Logout Route
@app.route('/admin_logout')
def admin_logout():
    # Clear the admin session
    session.pop('admin_id', None)
    # Redirect to the admin login page
    return redirect(url_for('admin_login'))

# Doctor Dashboard (Protected Route)
@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_login'))

    doctor_id = session['doctor_id']
    # Fetch appointments for this doctor
    appointments = query_db('''
        SELECT a.appointment_date, p.name AS patient_name, p.age, p.gender, p.email
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = ?
    ''', [doctor_id])

    return render_template('doctor_dashboard.html', appointments=appointments)

# Doctor Logout
@app.route('/doctor_logout')
def doctor_logout():
    session.pop('doctor_id', None)  # Remove doctor ID from session
    return redirect(url_for('doctor_login'))  # Redirect to the login page

@app.route('/billing/<int:patient_id>', methods=['GET', 'POST'])
def billing(patient_id):
    if request.method == 'POST':
        # Retrieve doctor_id from the session
        doctor_id = session.get('doctor_id')
        if not doctor_id:
            curses_flash("Doctor not found. Please book an appointment first.", 'error')
            return redirect(url_for('book_appointment'))

        # Get payment method from form submission
        payment_method = request.form['payment_method']
        total_amount = 100.00  # Fixed total amount
        payment_status = 'Pending'  # Default status for walk-in
        payment_date = datetime.now().strftime('%Y-%m-%d')

        # Process payment based on the method
        if payment_method == 'Online Card Payment':
            # Collect card details
            card_number = request.form.get('card_number')
            card_expiry = request.form.get('card_expiry')
            card_cvv = request.form.get('card_cvv')

            if card_number and card_expiry and card_cvv:
                payment_status = 'Paid'  # Mark as paid if valid card details are provided
                curses_flash('Payment successful. Your card was charged $100.', 'success')
            else:
                curses_flash('Payment failed. Please check your card details.', 'error')
                return redirect(url_for('billing', patient_id=patient_id))
        elif payment_method == 'Walk-in':
            # Keep the payment status as 'Pending' for walk-in payments
            curses_flash('Payment will be collected at the hospital.', 'info')

        # Insert or update billing record into the database
        modify_db('''
            INSERT INTO billing (patient_id, doctor_id, total_amount, payment_status, payment_date)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(patient_id, doctor_id) DO UPDATE 
            SET payment_status = excluded.payment_status, 
                payment_date = excluded.payment_date
        ''', (patient_id, doctor_id, total_amount, payment_status, payment_date))



        return redirect(url_for('patient_dashboard'))

    # Fetch the doctor and billing information
    billing_info = query_db('''
        SELECT b.total_amount, b.payment_status, b.payment_date, d.name AS doctor_name
        FROM billing b
        JOIN doctors d ON b.doctor_id = d.id
        WHERE b.patient_id = ?
    ''', [patient_id])

    doctor_name = query_db('SELECT name FROM doctors WHERE id = ?', [session.get('doctor_id')], one=True)['name']
    
    return render_template('billing.html', billing_info=billing_info, doctor_name=doctor_name, patient_id=patient_id)



    # Fetch the doctor and billing information
    billing_info = query_db('''
        SELECT b.total_amount, b.payment_status, b.payment_date, d.name AS doctor_name
        FROM billing b
        JOIN doctors d ON b.doctor_id = d.id
        WHERE b.patient_id = ?
    ''', [patient_id])

    doctor_info = query_db('SELECT name FROM doctors WHERE id = ?', [session.get('doctor_id')], one=True)

    # Ensure patient_id is passed to the template
    return render_template('billing.html', billing_info=billing_info, doctor=doctor_info, patient_id=patient_id)





@app.route('/view_billing', methods=['GET'])
def admin_view_billing():
    # Fetch all billing records for admin
    billing_info = query_db('''
        SELECT b.id, p.name AS patient_name, d.name AS doctor_name, b.total_amount, b.payment_status, b.payment_date
        FROM billing b
        JOIN patients p ON b.patient_id = p.id
        JOIN doctors d ON b.doctor_id = d.id
    ''')

    return render_template('admin_billing.html', billing_info=billing_info)


@app.route('/admin_billing', methods=['GET'])
def admin_billing():
    if 'admin_id' not in session:  # Ensure that only admins access this route
        return redirect(url_for('admin_login'))

    # Fetch all billing records for all patients
    billing_info = query_db('''
        SELECT b.id, p.name AS patient_name, d.name AS doctor_name, b.total_amount, b.payment_status, b.payment_date
        FROM billing b
        JOIN patients p ON b.patient_id = p.id
        JOIN doctors d ON b.doctor_id = d.id
    ''')

    return render_template('admin_billing.html', billing_info=billing_info)




# Helper function to generate a 6-digit unique billing ID
def generate_unique_billing_id():
    while True:
        billing_id = random.randint(100000, 999999)
        existing_id = query_db('SELECT id FROM billing WHERE id = ?', [billing_id], one=True)
        if existing_id is None:
            return billing_id


    # Retrieve doctor information
    doctors = query_db('SELECT id, name FROM doctors')
    
    # Retrieve billing info for the patient
    billing_info = query_db('''
        SELECT b.total_amount, b.payment_status, b.payment_date, d.name as doctor_name
        FROM billing b
        JOIN doctors d ON b.doctor_id = d.id
        WHERE b.patient_id = ?
    ''', (patient_id,))
    
    return render_template('billing.html', billing_info=billing_info, doctors=doctors, patient_id=patient_id)


    doctors = query_db('SELECT id, name FROM doctors')
    billing_info = query_db('SELECT * FROM billing WHERE patient_id = ?', [patient_id])
    
    return render_template('billing.html', billing_info=billing_info, doctors=doctors, patient_id=patient_id)

@app.route('/delete_appointment/<int:appointment_id>', methods=['GET'])
def delete_appointment(appointment_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    # Delete the specific appointment using the appointment_id
    modify_db('DELETE FROM appointments WHERE id = ?', [appointment_id])
    
    return redirect(url_for('admin_dashboard'))


# Admin route to update payment status (only for walk-ins)


@app.route('/update_payment_status/<int:billing_id>', methods=['GET', 'POST'])
def update_payment_status(billing_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    billing = query_db('SELECT * FROM billing WHERE id = ?', [billing_id], one=True)

    if request.method == 'POST':
        payment_status = request.form['payment_status']
        modify_db('UPDATE billing SET payment_status = ?, payment_date = ? WHERE id = ?',
                  [payment_status, datetime.now().strftime('%Y-%m-%d'), billing_id])
        curses_flash(f'Payment status updated to {payment_status}.', 'success')

        return redirect(url_for('admin_view_billing'))

    return render_template('update_payment_status.html', billing=billing)

@app.route('/delete_patient_appointments/<int:patient_id>', methods=['POST'])
def delete_patient_appointments(patient_id):
    if 'admin_id' not in session:  # Ensure that only admins can access this route
        return redirect(url_for('admin_login'))

    try:
        # Delete all appointments for the given patient
        modify_db('DELETE FROM appointments WHERE patient_id = ?', [patient_id])
        curses_flash(f"All appointments for patient ID {patient_id} have been deleted.", 'success')
    except Exception as e:
        curses_flash(f"Error deleting appointments: {str(e)}", 'error')

    return redirect(url_for('view_patients'))  # Redirect back to the patients view or dashboard

