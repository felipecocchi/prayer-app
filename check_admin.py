from app import app, db, Admin

with app.app_context():
    admins = Admin.query.all()
    for admin in admins:
        print(f"ID: {admin.id} | Username: {admin.username}")