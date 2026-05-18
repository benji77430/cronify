import yaml
import io
import os
import subprocess
import shutil
from pathlib import Path
from flask import Flask,render_template,send_file,request,redirect,url_for,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash
if os.geteuid() != 0:
    exit("You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting.")

with open("cronify/config.yml", 'r') as stream:
    config = yaml.safe_load(stream)

print(config["cronify_folder"])
shutil.move("cronify","/var/www/cronify")
if not os.path.isdir(config["cronify_folder"]):
    os.makedirs(config["cronify_folder"], exist_ok=True)
if Path(config["cronify_folder"]).owner() != config["user"]:
    subprocess.run(f"chown -R {config["user"]} {config["cronify_folder"]}", shell=True, check=True)
    print(f"user '{config["user"]}' now own the folder: {config["cronify_folder"]}")

app = Flask("cronify")
app.config['SECRET_KEY'] = config["secret_key"]
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{config["cronify_folder"]}/database.db'
print(f"database path : {config["cronify_folder"]}/database.db")

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

#User db init
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

while True:
    username=input("enter the username of the admin account you want to create > ") or "admin"
    if not "n" in input(f"is the username correct '{username}' (Y/n) "):
        break
while True:
    password=input("enter a password > ") or None
    if not password == None:
        if not "n" in input(f"is the password correct '{password}' (Y/n) ").lower():
            break
with app.app_context():
    db.create_all()

    #if no admin account create one 
    if not User.query.filter_by(username=username).first():
        print(f"Creating default '{username}' account...")
        hashed_password = generate_password_hash(password)
        admin = User(username=username, password_hash=hashed_password)
        
        db.session.add(admin)
        db.session.commit()
        print(f"account '{username}' created successfully!")
    else:
        print(f"'{username}' account already exists. Skipping provisioning.")

shutil.copy("cronify.service","/etc/systemd/system/cronify.service")
subprocess.run("systemctl enable cronify", shell=True, check=True)
subprocess.run("systemctl start cronify", shell=True, check=True)
print(f"cronify service created and started !")

print("\nInstallation complete! You can now launch your Flask app.")
