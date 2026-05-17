import yaml
import io
import os
from main import app, db, User
from werkzeug.security import generate_password_hash

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

print("\nInstallation complete! You can now launch your Flask app.")