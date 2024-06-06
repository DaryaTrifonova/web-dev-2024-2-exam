from flask import Blueprint, render_template, request, flash, redirect, url_for, Flask, send_from_directory
from auth import bp as auth_bp, init_login_manager
from flask_migrate import Migrate
from models import db

app = Flask(__name__)
application = app

app.config.from_pyfile('config.py')

db.init_app(app)
migrate = Migrate(app, db)

init_login_manager(app)

app.register_blueprint(auth_bp)

@app.route('/')
def index():
    return render_template('index.html')

