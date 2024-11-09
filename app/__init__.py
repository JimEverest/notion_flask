# app/__init__.py
from flask import Flask
from flask_session import Session

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

from app import minio_helper
from app import routes
from app import color_converter