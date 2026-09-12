import email

from zoneinfo import ZoneInfo
from flask import Flask,render_template, request, redirect, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from helpers import admin_required, region_required, auth_required, send_notification
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

db = SQLAlchemy(app)

class Region(db.Model):
    __tablename__ = "regions"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True)


class PrayerRequest(db.Model):
    __tablename__ = "prayer_requests"

    id = db.Column(db.Integer, primary_key=True)
    anonymous = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    request = db.Column(db.Text, nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"), nullable=True)
    region = db.relationship("Region", backref="prayer_requests")
    status = db.Column(db.String(20), default="pending")
    token = db.Column(db.String(100), unique=True, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())


class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == "GET":
        regions = Region.query.filter_by(active=True).all()
        return render_template('index.html', regions=regions)
    else:
        anonymous = request.form.get("anonymous") == "on"
        name = request.form.get("name") if not anonymous else None
        email = request.form.get("email")
        title = request.form.get("title")
        request_text = request.form.get("request")
        region_id = request.form.get("region_id") or None

        if not email or not title or not request_text:
            flash("Por favor, preencha todos os campos obrigatórios.", "error")
            return redirect('/')

        token = os.urandom(16).hex()

        new_request = PrayerRequest(
            anonymous=anonymous,
            name=name,
            email=email,
            title=title,
            request=request_text,
            region_id=region_id,
            token=token
        )
        db.session.add(new_request)
        db.session.commit()

        send_notification(
            to_email=email,
            subject="Confirmação de Pedido de Oração",
            body=f"<p>Olá! Recebemos seu pedido de oração sobre <strong>{title}</strong>.</p><p>Alguém irá orar por você em breve.</p>"
            )
        flash("Pedido de oração enviado com sucesso!", "success")
        return redirect('/')

   
        

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        return render_template('login.html')
    
    else:
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash("Por favor, preencha todos os campos.", "error")
            return redirect('/login')
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_id'] = admin.id
            return redirect('/admin')
                
        region = Region.query.filter_by(username=username).first()
        if region and check_password_hash(region.password_hash, password):
            session['region_id'] = region.id
            return redirect('/region/dashboard')
        
        flash("Login ou senha inválidos.", "error")
        return redirect('/login')

    
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
        

@app.route("/admin")
@admin_required
def admin():
    pending_requests = PrayerRequest.query.filter_by(status='pending').all()
    return render_template('admin.html', requests=pending_requests)


@app.route("/admin/team", methods=['GET', 'POST'])
@admin_required
def admin_team():
    if request.method == "GET":
        regions = Region.query.all()
        return render_template('admin_team.html', regions=regions)
    
    else:
        if request.form.get("action") == "delete":
            region_id = request.form.get("id")
            region_to_delete = Region.query.filter_by(id=region_id).first()
            if region_to_delete:
                db.session.delete(region_to_delete)
                db.session.commit()
            return redirect('/admin/team')

        elif request.form.get("action") == "toggle":
            region_id = request.form.get("id")
            region_to_toggle = Region.query.filter_by(id=region_id).first()
            if region_to_toggle:
                region_to_toggle.active = not region_to_toggle.active
                db.session.commit()
            return redirect('/admin/team')

        name = request.form.get("name")
        username = request.form.get("username")
        password = request.form.get("password")

        if not name or not username or not password:
            flash("Por favor, preencha todos os campos.", "error")
            return redirect('/admin/team')

        password_hash = generate_password_hash(password)
        new_region = Region(name=name, username=username, password_hash=password_hash)
        db.session.add(new_region)
        db.session.commit()
        flash("Região adicionada com sucesso!", "success")

        return redirect('/admin/team')


@app.route("/admin/history")
@admin_required
def admin_history():
    completed_requests = PrayerRequest.query.filter_by(status='done').all()
    return render_template('admin_history.html', requests=completed_requests)


@app.route("/admin/history/delete", methods=['POST'])
@admin_required
def admin_history_delete():
    id = request.form.get("id")
    request_to_delete = PrayerRequest.query.filter_by(id=id).first()
    if request_to_delete:
        db.session.delete(request_to_delete)
        db.session.commit()
        flash("Pedido de oração deletado!", "success")
    return redirect(request.referrer or '/admin')


@app.route("/region/dashboard")
@region_required
def region_dashboard():
    pending_requests = PrayerRequest.query.filter_by(status='pending', 
                                                     region_id=session['region_id']).all()
    return render_template('region_dashboard.html', requests=pending_requests)


@app.route("/pray", methods=['POST'])
@auth_required
def pray():
    id = request.form.get("id")
    prayer = PrayerRequest.query.filter_by(id=id).first()
    prayer.status = 'done'
    db.session.commit()
    
    send_notification(
        to_email=prayer.email,
        subject="Oração realizada",
        body=f"<p>Olá! Sua oração sobre <strong>{prayer.title}</strong> foi realizada.</p>"
)
    if 'admin_id' in session:
        return redirect('/admin')
    
    return redirect('/region/dashboard')


@app.template_filter('horario_atlanta')
def horario_atlanta(utc_dt):
    if utc_dt is None:
        return ''
    utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
    local_dt = utc_dt.astimezone(ZoneInfo("America/New_York"))
    return local_dt.strftime('%d/%m/%Y %H:%M')

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
