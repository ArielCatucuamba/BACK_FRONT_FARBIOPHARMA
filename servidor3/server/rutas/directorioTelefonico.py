from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from ..extensiones import mysql
from ..utilidades import paginar_consulta, rol_normalizado

bp = Blueprint('directory', __name__)


def _opciones_filtros(cur):
    cur.execute("SELECT DISTINCT DEPARTAMENTO FROM Departamentos WHERE DEPARTAMENTO IS NOT NULL AND DEPARTAMENTO <> '' ORDER BY DEPARTAMENTO")
    departamentos = [fila[0] for fila in cur.fetchall()]
    departamento = (request.args.get('departamento') or '').strip()
    if departamento:
        cur.execute("""
            SELECT DISTINCT a.AREA FROM Areas a
            WHERE a.AREA IS NOT NULL AND a.AREA <> '' AND (
                EXISTS (SELECT 1 FROM Cargos c
                    JOIN Departamentos d ON d.ID_DEPARTAMENTOS = c.DEPARTAMENTO
                    WHERE c.AREA = a.ID_AREAS AND d.DEPARTAMENTO = %s)
                OR EXISTS (SELECT 1 FROM Extensiones e
                    JOIN Departamentos d ON d.ID_DEPARTAMENTOS = e.DEPARTAMENTO
                    WHERE e.AREA = a.ID_AREAS AND d.DEPARTAMENTO = %s)
            ) ORDER BY a.AREA
        """, (departamento, departamento))
    else:
        cur.execute("SELECT DISTINCT AREA FROM Areas WHERE AREA IS NOT NULL AND AREA <> '' ORDER BY AREA")
    areas = [fila[0] for fila in cur.fetchall()]
    return departamentos, areas


def _crear_filtro(termino, departamento, area, campos_busqueda):
    condiciones = []
    parametros = []
    if termino:
        condiciones.append('(' + ' OR '.join(f'{campo} LIKE %s' for campo in campos_busqueda) + ')')
        parametros.extend([f'%{termino}%'] * len(campos_busqueda))
    if departamento:
        condiciones.append('d.DEPARTAMENTO = %s')
        parametros.append(departamento)
    if area:
        condiciones.append('a.AREA = %s')
        parametros.append(area)
    return ('WHERE ' + ' AND '.join(condiciones) if condiciones else ''), tuple(parametros)

@bp.route('/')
def index():
    cur = mysql.connection.cursor()
    termino = (request.args.get('q') or '').strip()
    departamento = (request.args.get('departamento') or '').strip()
    area = (request.args.get('area') or '').strip()
    departamentos, areas = _opciones_filtros(cur)
    if area not in areas:
        area = ''
    filtro, parametros = _crear_filtro(termino, departamento, area, ('c.NOMBRE', 'CAST(e.EXTENSION AS CHAR)', 'a.AREA', 'd.DEPARTAMENTO'))
    extensiones, pagination = paginar_consulta(cur, """
        SELECT e.ID_EXTENSIONES, c.NOMBRE, e.EXTENSION, a.AREA, d.DEPARTAMENTO, e.AREA, e.DEPARTAMENTO, e.ID_COLABORADOR
        FROM Extensiones e
        LEFT JOIN Colaboradores c ON e.ID_COLABORADOR = c.ID_COLABORADOR
        LEFT JOIN Areas a ON e.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON e.DEPARTAMENTO = d.ID_DEPARTAMENTOS
    """ + filtro + """
        ORDER BY e.ID_EXTENSIONES ASC
    """, parametros, """
        SELECT COUNT(*) FROM Extensiones e
        LEFT JOIN Colaboradores c ON e.ID_COLABORADOR = c.ID_COLABORADOR
        LEFT JOIN Areas a ON e.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON e.DEPARTAMENTO = d.ID_DEPARTAMENTOS
    """ + filtro, parametros)
    if request.args.get('format') == 'json':
        filas = [
            {'nombre': row[1] or '', 'dato': str(row[2] or ''), 'area': row[3] or '', 'departamento': row[4] or ''}
            for row in extensiones
        ]
        cur.close()
        return jsonify(items=filas, pagination=pagination, filters={'departamentos': departamentos, 'areas': areas})
    cur.close()
    return render_template('DTelefonico/VExtensiones/Extensiones.html', extensiones=extensiones, pagination=pagination, search_query=termino, departamentos=departamentos, areas=areas, departamento_seleccionado=departamento, area_seleccionada=area)


@bp.route('/vextensiones')
def vextensiones():
    cur = mysql.connection.cursor()
    termino = (request.args.get('q') or '').strip()
    departamento = (request.args.get('departamento') or '').strip()
    area = (request.args.get('area') or '').strip()
    departamentos, areas = _opciones_filtros(cur)
    if area not in areas:
        area = ''
    filtro, parametros = _crear_filtro(termino, departamento, area, ('col.NOMBRE', 'CAST(e.EXTENSION AS CHAR)', 'a.AREA', 'd.DEPARTAMENTO'))
    extensiones, pagination = paginar_consulta(cur, """
        SELECT e.ID_EXTENSIONES, col.NOMBRE, e.EXTENSION, a.AREA, d.DEPARTAMENTO, e.ID_COLABORADOR
        FROM Extensiones e
        LEFT JOIN Colaboradores col ON e.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Areas a ON e.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON e.DEPARTAMENTO = d.ID_DEPARTAMENTOS
    """ + filtro + """
        ORDER BY e.ID_EXTENSIONES ASC
    """, parametros, """
        SELECT COUNT(*) FROM Extensiones e
        LEFT JOIN Colaboradores col ON e.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Areas a ON e.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON e.DEPARTAMENTO = d.ID_DEPARTAMENTOS
    """ + filtro, parametros)
    if request.args.get('format') == 'json':
        filas = [
            {'nombre': row[1] or '', 'dato': str(row[2] or ''), 'area': row[3] or '', 'departamento': row[4] or ''}
            for row in extensiones
        ]
        cur.close()
        return jsonify(items=filas, pagination=pagination, filters={'departamentos': departamentos, 'areas': areas})
    cur.close()
    return render_template('DTelefonico/VExtensiones/Extensiones.html', extensiones=extensiones, pagination=pagination, search_query=termino, departamentos=departamentos, areas=areas, departamento_seleccionado=departamento, area_seleccionada=area)


@bp.route('/vcelulares')
def vcelulares():
    cur = mysql.connection.cursor()
    termino = (request.args.get('q') or '').strip()
    departamento = (request.args.get('departamento') or '').strip()
    area = (request.args.get('area') or '').strip()
    departamentos, areas = _opciones_filtros(cur)
    if area not in areas:
        area = ''
    filtro, parametros = _crear_filtro(termino, departamento, area, ('col.NOMBRE', 'CAST(c.CELULAR AS CHAR)', 'a.AREA', 'd.DEPARTAMENTO'))
    celulares, pagination = paginar_consulta(cur, """
        SELECT c.ID_CELULARES, col.NOMBRE, c.CELULAR, a.AREA, d.DEPARTAMENTO, c.ID_COLABORADOR
        FROM Celulares c
        LEFT JOIN Colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
    """ + filtro + """
        ORDER BY c.ID_CELULARES ASC
    """, parametros, """
        SELECT COUNT(*) FROM Celulares c
        LEFT JOIN Colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
    """ + filtro, parametros)

    if request.args.get('format') == 'json':
        filas = [
            {'nombre': row[1] or '', 'dato': str(row[2] or ''), 'area': row[3] or '', 'departamento': row[4] or ''}
            for row in celulares
        ]
        cur.close()
        return jsonify(items=filas, pagination=pagination, filters={'departamentos': departamentos, 'areas': areas})
    
    cur.close()
    return render_template('DTelefonico/VCelulares/Celulares.html', celulares=celulares, pagination=pagination, search_query=termino, departamentos=departamentos, areas=areas, departamento_seleccionado=departamento, area_seleccionada=area)


@bp.route('/vcorreos')
def vcorreos():
    cur = mysql.connection.cursor()
    termino = (request.args.get('q') or '').strip()
    departamento = (request.args.get('departamento') or '').strip()
    area = (request.args.get('area') or '').strip()
    departamentos, areas = _opciones_filtros(cur)
    if area not in areas:
        area = ''
    filtro, parametros = _crear_filtro(termino, departamento, area, ('col.NOMBRE', 'c.CORREO', 'a.AREA', 'd.DEPARTAMENTO'))
    correos, pagination = paginar_consulta(cur, """
        SELECT c.ID_CORREOS, col.NOMBRE, c.CORREO, a.AREA, d.DEPARTAMENTO, c.ID_COLABORADOR
        FROM Correos c
        LEFT JOIN Colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
    """ + filtro + """
        ORDER BY c.ID_CORREOS ASC
    """, parametros, """
        SELECT COUNT(*) FROM Correos c
        LEFT JOIN Colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
    """ + filtro, parametros)
    if request.args.get('format') == 'json':
        filas = [
            {'nombre': row[1] or '', 'dato': row[2] or '', 'area': row[3] or '', 'departamento': row[4] or ''}
            for row in correos
        ]
        cur.close()
        return jsonify(items=filas, pagination=pagination, filters={'departamentos': departamentos, 'areas': areas})
    cur.close()
    return render_template('DTelefonico/VCorreos/Correos.html', correos=correos, pagination=pagination, search_query=termino, departamentos=departamentos, areas=areas, departamento_seleccionado=departamento, area_seleccionada=area)


