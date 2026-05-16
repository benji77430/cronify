from flask import Flask,render_template,send_file,request,redirect,url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import os,subprocess,time,sqlite3,random,string,yaml,io

#cronify web interface port

port=2766

with open("config.yml", 'r') as stream:
    config = yaml.safe_load(stream)

app = Flask("cronify")
app.config['SECRET_KEY'] = config["secret_key"]
print(f"Secret KEY : {app.config['SECRET_KEY']}")

#path to the db
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{config["cronify_folder"]}/database.db'

print(f"database path : {config["cronify_folder"]}/database.db")
if os.path.isfile(os.path.join(config["cronify_folder"],"database.db")):
    print("database exists !")

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


if not os.path.isdir(config["cronify_folder"]):
    print("Cronify config folder does not exist consider running \"sudo /usr/bin/python3 install.py\" or check the config.yaml !")


#User db init
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
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

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=port)