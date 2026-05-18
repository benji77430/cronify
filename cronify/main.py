from flask import Flask,render_template,send_file,request,redirect,url_for,flash,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import os,subprocess,time,sqlite3,random,string,yaml,io,grp,pwd,sys,threading




#cronify web interface port

port=2766

with open("config.yml", 'r') as stream:
    config = yaml.safe_load(stream)

#privilege dropping
if os.getuid() == 0:
    parent_dir=os.path.dirname(os.path.abspath(sys.argv[0]))
    print(f"parent dir : {parent_dir}")
    subprocess.run(f"chown -R {config["user"]}:{config["user"]} {parent_dir}", shell=True, check=True)
    print(f"user '{config["user"]}' now own the folder: {parent_dir}")
    os.setgroups([])
    os.setgid(pwd.getpwnam(config["user"]).pw_gid)
    os.setuid(pwd.getpwnam(config["user"]).pw_uid)
    print(f"privilege dropped to '{config["user"]}' !")
app = Flask("cronify")
app.config['SECRET_KEY'] = config["secret_key"]

#path to the db
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{config["cronify_folder"]}/database.db'

print(f"users database path : {config["cronify_folder"]}/database.db")
if os.path.isfile(os.path.join(config["cronify_folder"],"database.db")):
    print("database exists !")
print(f"cron jobs database path : {config["cronify_folder"]}/crons.db")
if os.path.isfile(os.path.join(config["cronify_folder"],"crons.db")):
    print("database exists !")
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'




#User db init
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
ACTIVE_AGENTS = {}

#cookie user loader
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

#login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password')
    return render_template('login.html')


#dashboard
@app.route('/dashboard',methods=['GET','POST'])
@login_required  
def dashboard():
    jobs=[]
    conn = sqlite3.connect(os.path.join(config["cronify_folder"],"crons.db"))
    cursor = conn.cursor()
    sql_query = f"""
        SELECT * FROM cronjobs
        ORDER BY id DESC
    """
    
    try:
        cursor.execute(sql_query)
        
        results = cursor.fetchall()
        for result in results:
            jobs.append([result[0],result[1],result[2],result[3],result[4],result[5],result[6],result[7]])
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    if request.method == 'POST':
        minute=request.form.get('minute')
        hour=request.form.get('hour')
        day=request.form.get('day')
        month=request.form.get('month')
        weekday=request.form.get('weekday')
        user=request.form.get('user')
        command=request.form.get('command')
        if not minute or not hour or not day or not month or not weekday or not command or not user:
            flash("ALL FIELDS ARE REQUIRED !","error")
            return render_template('index.html',jobs=jobs)
        conn = sqlite3.connect(os.path.join(config["cronify_folder"],"crons.db"))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cronjobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                minute TEXT NOT NULL,
                hour TEXT NOT NULL,
                day TEXT NOT NULL,
                month TEXT NOT NULL,
                weekday TEXT NOT NULL,
                user TEXT NOT NULL,
                command TEXT NOT NULL
            )
        ''')
    
        try:
            cursor.execute(
                "INSERT INTO cronjobs (minute, hour, day, month, weekday, user, command) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (minute, hour, day, month, weekday, user,command)
            )
            conn.commit()
            print("Data logged successfully.")
            flash("Succes !","success")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            conn.close()
    return render_template('index.html',jobs=jobs)

@app.route('/delete', methods=['POST'])
@login_required
def delete_job():
    # Grab the parsed JSON dictionary from the JS request body
    data = request.get_json() 
    
    job_id = data.get('id')
    print(f"Flask received request to delete job: {job_id}")
    conn = sqlite3.connect(os.path.join(config["cronify_folder"],"crons.db"))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cronjobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            minute TEXT NOT NULL,
            hour TEXT NOT NULL,
            day TEXT NOT NULL,
            month TEXT NOT NULL,
            weekday TEXT NOT NULL,
            user TEXT NOT NULL,
            command TEXT NOT NULL
        )
    ''')

    try:
        cursor.execute(
            "DELETE FROM cronjobs WHERE id = ?",
            (job_id,) # Note: SQLite expects a tuple, so keep that trailing comma!
        )
        conn.commit()
        print(f"Job {job_id} deleted successfully.")
        flash("Job deleted successfully!", "success")
        return jsonify({"status": "success", "message": "Job deleted successfully"})
    except Exception as e:
        print(f"An error occurred: {e}")
        flash(f"Database Error: {e}", "error")
        
    finally:
        conn.close()
#redirect to /dashboard
@app.route("/")
def route():
    return redirect("/dashboard",302)

@app.route("/api/cron")
def api_cron():
    jobs=[]
    conn = sqlite3.connect(os.path.join(config["cronify_folder"],"crons.db"))
    cursor = conn.cursor()
    sql_query = f"""
        SELECT * FROM cronjobs
        ORDER BY id DESC
    """
    try:
        cursor.execute(sql_query)
        
        results = cursor.fetchall()
        for result in results:
            jobs.append({"id": result[0],"minute": result[1],"hour":  result[2],"day":  result[3],"month":  result[4],"weekday":  result[5],"user":  result[6],"command":  result[7]})
        if len(results) < 1:
            return jsonify({"status": "error", "message": "No jobs found"})
        return jsonify({"jobs": jobs})
    except Exception as e:
        print(f"An error occurred: {e}")
        flash(f"Database Error: {e}", "error")
        
    finally:
        conn.close()

@app.route("/api/handshake", methods=['POST'])
def handshake():
    data = request.get_json()
    if not data or 'agent_id' not in data:
        return "Missing agent_id", 400
        
    agent_id = data['agent_id']
    agent_name = data['agent_name']
    # Record the current time for this unique agent
    ACTIVE_AGENTS[agent_id] = [time.time(),agent_name]
    
    return "OK", 200
@app.route("/api/agents")
@login_required
def api_agents():
    current_time = time.time()
    active_count = 0
    for agent_id, last_seen in list(ACTIVE_AGENTS.items()):
        if current_time - last_seen[0] < 45:
            active_count += 1
        else:
            del ACTIVE_AGENTS[agent_id]
    return str(active_count), 200
def agents():
    pass
if __name__ == "__main__":
    if not os.path.isdir(config["cronify_folder"]):
        print("Cronify config folder does not exist consider running \"sudo /usr/bin/python3 install.py\" or check the config.yaml !")
        exit(1)
    print(f"debug mode : {config["debug_mode"]}")
    threading.Thread(target=agents).start()
    app.run(host="0.0.0.0",port=port,debug=bool(config["debug_mode"]))