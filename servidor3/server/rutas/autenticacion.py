from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from ..extensiones import mysql
from ..utilidades import paginar_consulta, rol_normalizado
import hashlib
import hmac
import secrets
import re


bp = Blueprint('auth', __name__)

@bp.route('/sso/consume', methods=['POST'])
def sso_consume():
    """Canjea el código de NAVEW y establece una sesión local para Talento Humano."""
    origen = request.headers.get('Origin', '').rstrip('/')
    origen_permitido = current_app.config['NAVEW_FRONTEND_ORIGIN']
    if not origen_permitido or origen != origen_permitido:
        abort(403)

    codigo = request.form.get('code', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', codigo):
        abort(400)

    hash_codigo = hashlib.sha256(codigo.encode('ascii')).hexdigest()
    cursor = mysql.connection.cursor()
    usuario = None
    codigo_valido = False
    try:
        mysql.connection.begin()
        cursor.execute(
            """UPDATE rrhh_sso_codes
               SET consumed_at = UTC_TIMESTAMP()
               WHERE code_hash = %s
                 AND consumed_at IS NULL
                 AND expires_at > UTC_TIMESTAMP()""",
            (hash_codigo,)
        )
        codigo_valido = cursor.rowcount == 1
        if codigo_valido:
            # Recuperar la cuenta vigente dentro de la misma transacción.
            cursor.execute(
                """SELECT u.id, u.email, u.rol, u.estado, u.username, c.NOMBRE
                   FROM rrhh_sso_codes s
                   INNER JOIN usuarios u ON u.id = s.user_id
                   LEFT JOIN Colaboradores c ON c.CEDULA = u.cedula
                   WHERE s.code_hash = %s
                   LIMIT 1""",
                (hash_codigo,)
            )
            usuario = cursor.fetchone()
        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        current_app.logger.error('Falló el canje SSO de Talento Humano')
        abort(503)
    finally:
        cursor.close()

    if not codigo_valido:
        abort(401)
    if not usuario or str(usuario[3] or '').strip().lower() != 'activo':
        abort(403)
    if rol_normalizado(usuario[2]) != 'talentohumano':
        abort(403)

    session.clear()
    session['user_id'] = usuario[0]
    session['username'] = usuario[1]
    session['display_name'] = usuario[5] or usuario[4] or usuario[1]
    session['user_role'] = usuario[2]
    session.permanent = True
    return redirect(url_for('auth.menu'))


@bp.route('/sso/navew/organigrama', methods=['GET'])
def abrir_organigrama_navew():
    """Emite un codigo de un solo uso para abrir NAVEW desde el menu de RRHH."""
    if rol_normalizado(session.get('user_role')) != 'talentohumano':
        abort(403)

    codigo = secrets.token_urlsafe(32)
    hash_codigo = hashlib.sha256(codigo.encode('ascii')).hexdigest()
    cursor = mysql.connection.cursor()
    try:
        cursor.execute(
            """DELETE FROM rrhh_sso_codes
               WHERE expires_at <= UTC_TIMESTAMP() OR consumed_at IS NOT NULL"""
        )
        cursor.execute(
            """INSERT INTO rrhh_sso_codes (code_hash, user_id, expires_at)
               VALUES (%s, %s, DATE_ADD(UTC_TIMESTAMP(), INTERVAL 60 SECOND))""",
            (hash_codigo, session['user_id'])
        )
        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        current_app.logger.error('No se pudo emitir el codigo SSO hacia NAVEW')
        abort(503)
    finally:
        cursor.close()

    destino = f"{current_app.config['NAVEW_FRONTEND_ORIGIN']}/sso/rrhh#code={codigo}"
    return redirect(destino, code=303)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Compatibilidad con enlaces antiguos; el login central está en NAVEW.
    return redirect(current_app.config['NAVEW_LOGIN_URL'])


@bp.route('/menu')
def menu():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('menu.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    # Compatibilidad con enlaces antiguos; las cuentas se administran en NAVEW.
    return redirect(current_app.config['NAVEW_LOGIN_URL'])


@bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(current_app.config['NAVEW_LOGOUT_URL'])


