from flask_mail import Message
from flask import render_template
from app import mail

def send_email(subject, to, template, **kwargs):
    msg = Message(subject, recipients=[to])
    msg.html = render_template(template, **kwargs)
    mail.send(msg)
