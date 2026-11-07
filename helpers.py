import os
from dotenv import load_dotenv
from functools import wraps
from flask import session, redirect
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def region_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "region_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_id" not in session and "region_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def send_notification(to_email, subject, body):
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        print(f"[email disabled] To: {to_email} | Subject: {subject}")
        return

    message = Mail(
        from_email=os.getenv("MAIL_USERNAME"),
        to_emails=to_email,
        subject=subject,
        html_content=body,
    )
    try:
        sg = SendGridAPIClient(api_key)
        sg.send(message)
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        print(f"Tipo do erro: {type(e)}")
        if hasattr(e, "body"):
            print(f"Detalhes: {e.body}")
