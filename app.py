from flask import Flask, render_template, request, redirect, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from db import get_connection
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "super_secret_key"

app.config['JWT_SECRET_KEY'] = 'super_secret'
jwt = JWTManager(app)

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT']=587
app.config['MAIL_USERNAME']='your_email@gmail.com'
app.config['MAIL_PASSWORD']='your_app_password'
app.config['MAIL_USE_TLS']=True

mail = Mail(app)

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email=%s",(email,))
        user = cur.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user'] = user['id']
            return redirect("/dashboard")
    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users(name,email,password_hash) VALUES(%s,%s,%s)",
                    (name,email,password))
        conn.commit()
        return redirect("/")
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if 'user' not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM applications WHERE user_id=%s",(session['user'],))
    apps = cur.fetchall()

    cur.execute("""
        SELECT MONTH(applied_date) m, COUNT(*) t 
        FROM applications WHERE user_id=%s 
        GROUP BY m
    """,(session['user'],))
    monthly = cur.fetchall()

    cur.execute("""
        SELECT status, COUNT(*) t 
        FROM applications WHERE user_id=%s 
        GROUP BY status
    """,(session['user'],))
    status_data = cur.fetchall()

    return render_template(
        "dashboard.html",
        apps=apps,
        monthly=monthly,
        status_data=status_data
    )
@app.route("/add", methods=["GET","POST"])
def add():
    if request.method=="POST":
        data = (
            session['user'],
            request.form['company'],
            request.form['role'],
            request.form['platform'],
            request.form['applied_date'],
            request.form['status'],
            request.form['follow_up'],
            request.form['notes']
        )

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO applications
            (user_id,company,role,platform,applied_date,status,follow_up_date,notes)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
        """, data)
        conn.commit()
        return redirect("/dashboard")
    return render_template("add.html")

@app.route("/export")
def export():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM applications", conn)
    path = "exports/applications.xlsx"
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True)

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json

    name = data.get('name')
    email = data.get('email')
    password = generate_password_hash(data.get('password'))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users(name,email,password_hash) VALUES(%s,%s,%s)",
                (name,email,password))
    conn.commit()

    return {"message": "User registered successfully"}, 201

@app.route('/api/applications', methods=['GET'])
@app.route('/api/apps', methods=['GET'])
@jwt_required()
def api_get_apps():
    user_id = get_jwt_identity()

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM applications WHERE user_id=%s", (user_id,))
    return {"data": cur.fetchall()}

@app.route('/api/applications', methods=['POST'])
@jwt_required()
def api_add_app():
    user_id = get_jwt_identity()
    data = request.json

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO applications
        (user_id,company,role,platform,applied_date,status,follow_up_date,notes)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        user_id,
        data['company'],
        data['role'],
        data['platform'],
        data['applied_date'],
        data['status'],
        data['follow_up_date'],
        data['notes']
    ))
    conn.commit()
    return {"message": "Application added successfully"}, 201

@app.route('/send_reminders')
def send_reminders():
    send_followup_reminders()
    return {"message": "Reminders sent successfully"}, 200

def send_followup_reminders():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT u.email, a.company, a.role
        FROM applications a
        JOIN users u ON a.user_id=u.id
        WHERE a.follow_up_date = CURDATE()
    """)

    data = cur.fetchall()

    for d in data:
        msg = Message(
            subject="Follow-up Reminder",
            sender="your_email@gmail.com",
            recipients=[d['email']]
        )
        msg.body = f"""
Reminder:
Follow up today with {d['company']} for {d['role']} role.
"""
        mail.send(msg)
        
@app.route('/api/apps/<int:id>', methods=['PUT'])
@jwt_required()
def api_update_app(id):
    user_id = get_jwt_identity()
    data = request.json

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE applications 
        SET company=%s, role=%s, platform=%s, status=%s, follow_up_date=%s, notes=%s
        WHERE id=%s AND user_id=%s
    """, (
        data['company'],
        data['role'],
        data['platform'],
        data['status'],
        data['follow_up_date'],
        data['notes'],
        id,
        user_id
    ))

    conn.commit()
    return {"message":"Updated successfully"}
    return {"message":"Application not found"},404

@app.route('/api/apps/<int:id>', methods=['DELETE'])
@jwt_required()
def api_delete_app(id):
    user_id = get_jwt_identity()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM applications WHERE id=%s AND user_id=%s", (id,user_id))
    conn.commit()

    return {"message":"Deleted successfully"}
 
if __name__ == "__main__":
    app.run(debug=True)