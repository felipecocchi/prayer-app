import os
from app import app, db

db_path = "instance/prayer.db"

with app.app_context():
    if not os.path.exists(db_path):
        db.create_all()
        print("Banco criado com sucesso.")
    else:
        print("Banco já existe — nada foi feito.")