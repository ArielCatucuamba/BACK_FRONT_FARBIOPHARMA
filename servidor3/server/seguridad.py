"""Autenticación de sesión, autorización de RR. HH. y protección CSRF."""
import hmac
import secrets

from flask import abort, redirect, request, session, url_for

from .utilidades import rol_normalizado
from .extensiones import mysql


PUBLIC_ENDPOINTS = {
    'static', 'index', 'login', 'register', 'logout',
    'vextensiones', 'vcelulares', 'vcorreos', 'sso_consume',
}


def register_security(app):
    @app.context_processor
    def inject_csrf_token():
        token = session.get('_csrf_token')
        if not token:
            token = secrets.token_urlsafe(32)
            session['_csrf_token'] = token
        return {'csrf_token_value': token}

    @app.before_request
    def protect_hr_pages():
        endpoint = (request.endpoint or '').rsplit('.', 1)[-1]
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and endpoint != 'sso_consume':
            expected = session.get('_csrf_token', '')
            received = request.form.get('csrf_token', '') or request.headers.get('X-CSRF-Token', '')
            if not expected or not received or not hmac.compare_digest(expected, received):
                abort(400, description='Token CSRF ausente o inválido.')

        if endpoint in PUBLIC_ENDPOINTS:
            return None
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        if rol_normalizado(session.get('user_role')) not in {'talentohumano', 'administrador'}:
            abort(403)

        if not session.get('display_name'):
            cursor = None
            try:
                cursor = mysql.connection.cursor()
                cursor.execute(
                    """SELECT COALESCE(NULLIF(c.NOMBRE, ''), NULLIF(u.username, ''), u.email)
                       FROM usuarios u LEFT JOIN Colaboradores c ON c.CEDULA = u.cedula
                       WHERE u.id = %s LIMIT 1""",
                    (session['user_id'],),
                )
                usuario = cursor.fetchone()
                if usuario and usuario[0]:
                    session['display_name'] = usuario[0]
            except Exception:
                app.logger.warning('No se pudo recuperar el nombre visible de la sesión')
            finally:
                if cursor:
                    cursor.close()
