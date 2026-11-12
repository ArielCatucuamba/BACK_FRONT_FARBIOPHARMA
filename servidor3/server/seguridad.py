"""Autenticación de sesión, autorización de RR. HH. y protección CSRF."""
import hmac
import secrets

from flask import abort, current_app, jsonify, redirect, render_template, request, session, url_for

from .utilidades import rol_normalizado
from .extensiones import mysql


PUBLIC_ENDPOINTS = {
    'static', 'index', 'login', 'register', 'logout',
    'vextensiones', 'vcelulares', 'vcorreos', 'sso_consume', 'estado_sesion',
}


def respuesta_sin_sesion():
    destino = current_app.config['NAVEW_LOGIN_URL']
    if request.headers.get('Sec-Fetch-Dest') == 'empty' or request.accept_mimetypes.best == 'application/json':
        return jsonify(error='sesion_expirada'), 401
    if request.headers.get('Sec-Fetch-Dest') == 'iframe':
        return render_template('sesionRequerida.html', destino_login=destino), 401
    return redirect(destino)


def register_security(app):
    @app.after_request
    def evitar_cache_de_paginas(response):
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store, no-cache, private, max-age=0, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response

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
        if endpoint not in PUBLIC_ENDPOINTS:
            if 'user_id' not in session:
                return respuesta_sin_sesion()
            if rol_normalizado(session.get('user_role')) not in {'talentohumano', 'administrador'}:
                abort(403)
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and endpoint != 'sso_consume':
            expected = session.get('_csrf_token', '')
            received = request.form.get('csrf_token', '') or request.headers.get('X-CSRF-Token', '')
            if not expected or not received or not hmac.compare_digest(expected, received):
                abort(400, description='Token CSRF ausente o inválido.')

        if endpoint in PUBLIC_ENDPOINTS:
            return None
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
