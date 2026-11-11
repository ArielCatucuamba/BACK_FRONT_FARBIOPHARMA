"""Fábrica Flask del monolito modular de Talento Humano."""
import pkgutil
import importlib.util

if not hasattr(pkgutil, 'get_loader'):
    def _get_loader(module_name):
        try:
            spec = importlib.util.find_spec(module_name)
            return spec.loader if spec is not None else None
        except Exception:
            return None
    pkgutil.get_loader = _get_loader

from datetime import timedelta
import os

from flask import Flask

from .extensiones import mysql
from .rutas import BLUEPRINTS
from .seguridad import register_security


def create_app(test_config=None):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', '').strip(),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=4096,
        MYSQL_HOST=os.getenv('DB_HOST') or os.getenv('MYSQL_HOST', '127.0.0.1'),
        MYSQL_USER=os.getenv('DB_USER') or os.getenv('MYSQL_USER', ''),
        MYSQL_PASSWORD=os.getenv('DB_PASSWORD') or os.getenv('MYSQL_PASSWORD', ''),
        MYSQL_DB=os.getenv('DB_NAME') or os.getenv('MYSQL_DB', ''),
        MYSQL_PORT=int(os.getenv('DB_PORT') or os.getenv('MYSQL_PORT', 3306)),
        NAVEW_FRONTEND_ORIGIN=os.getenv('NAVEW_FRONTEND_ORIGIN', '').strip().rstrip('/'),
    )
    if test_config:
        app.config.update(test_config)
    if not app.config['SECRET_KEY']:
        raise RuntimeError('SECRET_KEY debe configurarse antes de iniciar Flask')
    if not app.config['NAVEW_FRONTEND_ORIGIN']:
        raise RuntimeError('NAVEW_FRONTEND_ORIGIN debe configurarse antes de iniciar Flask')
    app.config['NAVEW_LOGIN_URL'] = f"{app.config['NAVEW_FRONTEND_ORIGIN']}/login"
    app.config['NAVEW_LOGOUT_URL'] = f"{app.config['NAVEW_FRONTEND_ORIGIN']}/logout"

    mysql.init_app(app)
    register_security(app)
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
    return app
