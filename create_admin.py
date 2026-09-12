from app import app, db, Admin
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = Admin(
        username="admin",
        password_hash=generate_password_hash("@dmin!23")
    )
    db.session.add(admin)
    db.session.commit()
    print("Admin criado!")
