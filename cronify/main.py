from flask import Flask,render_template,send_file,request,redirect,url_for,flash
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

print(f"database path : {config["cronify_folder"]}/database.db")
if os.path.isfile(os.path.join(config["cronify_folder"],"database.db")):
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
@app.route('/dashboard')
@login_required  
def dashboard():
    return render_template('index.html')
        
#redirect to /dashboard
@app.route("/")
def route():
    return redirect("/dashboard",302)

@app.route("/api/cron", methods=['GET', 'POST'])
@login_required
def api_cron():
    if request.method == 'POST':
        pass


@app.route("/api/handshake", methods=['POST'])
def handshake():
    data = request.get_json()
    if not data or 'agent_id' not in data:
        return "Missing agent_id", 400
        
    agent_id = data['agent_id']
    
    # Record the current time for this unique agent
    ACTIVE_AGENTS[agent_id] = time.time()
    
    return "OK", 200
@app.route("/api/agents")
@login_required
def api_agents():
    current_time = time.time()
    active_count = 0
    for agent_id, last_seen in list(ACTIVE_AGENTS.items()):
        if current_time - last_seen < 45:
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