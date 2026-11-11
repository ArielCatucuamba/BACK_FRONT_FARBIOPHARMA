from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from ..extensiones import mysql
from ..utilidades import paginar_consulta, rol_normalizado

bp = Blueprint('directory', __name__)

@bp.route('/')
def index():
    cur = mysql.connection.cursor()
    extensiones, pagination = paginar_consulta(cur, """
        SELECT e.ID_EXTENSIONES, c.NOMBRE, e.EXTENSION, a.AREA, d.DEPARTAMENTO, e.AREA, e.DEPARTAMENTO, e.ID_COLABORADOR
        FROM Extensiones e
        LEFT JOIN Colaboradores c ON e.ID_COLABORADOR = c.ID_COLABORADOR
        LEFT JOIN Areas a ON e.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON e.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY e.ID_EXTENSIONES ASC
    """, (), "SELECT COUNT(*) FROM Extensiones")
    cur.close()
    return render_template('DTelefonico/VExtensiones/Extensiones.html', extensiones=extensiones, pagination=pagination)


@bp.route('/vextensiones')
def vextensiones():
    cur = mysql.connection.cursor()
    extensiones, pagination = paginar_consulta(cur, """
        SELECT e.ID_EXTENSIONES, col.NOMBRE, e.EXTENSION, a.AREA, d.DEPARTAMENTO, e.ID_COLABORADOR
        FROM Extensiones e
        LEFT JOIN Colaboradores col ON e.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Areas a ON e.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON e.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY e.ID_EXTENSIONES ASC
    """, (), "SELECT COUNT(*) FROM Extensiones")
    cur.close()
    return render_template('DTelefonico/VExtensiones/Extensiones.html', extensiones=extensiones, pagination=pagination)


@bp.route('/vcelulares')
def vcelulares():
    cur = mysql.connection.cursor()
    celulares, pagination = paginar_consulta(cur, """
        SELECT c.ID_CELULARES, col.NOMBRE, c.CELULAR, a.AREA, d.DEPARTAMENTO, c.ID_COLABORADOR
        FROM Celulares c
        LEFT JOIN Colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.ID_CELULARES ASC
    """, (), "SELECT COUNT(*) FROM Celulares")
    
    cur.close()
    return render_template('DTelefonico/VCelulares/Celulares.html', celulares=celulares, pagination=pagination)


@bp.route('/vcorreos')
def vcorreos():
    cur = mysql.connection.cursor()
    correos, pagination = paginar_consulta(cur, """
        SELECT c.ID_CORREOS, col.NOMBRE, c.CORREO, a.AREA, d.DEPARTAMENTO, c.ID_COLABORADOR
        FROM Correos c
        LEFT JOIN Colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.ID_CORREOS ASC
    """, (), "SELECT COUNT(*) FROM Correos")
    cur.close()
    return render_template('DTelefonico/VCorreos/Correos.html', correos=correos, pagination=pagination)


