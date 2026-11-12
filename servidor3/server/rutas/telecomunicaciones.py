from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from ..extensiones import mysql
from ..utilidades import rol_normalizado
from ..filtrosGestion import paginar_gestion
import re


bp = Blueprint('telecom', __name__)

@bp.route('/api/lookups/colaboradores', methods=['GET'])
def api_buscar_colaboradores():
    """Búsqueda acotada para autocompletados; no descarga el directorio completo."""
    termino = (request.args.get('q') or '').strip()
    if len(termino) < 2:
        return jsonify([])
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT c.ID_COLABORADOR, c.NOMBRE, a.ID_AREAS, a.AREA,
                   d.ID_DEPARTAMENTOS, d.DEPARTAMENTO
            FROM Colaboradores c
            LEFT JOIN Cargos cg ON c.CARGO = cg.ID_CARGOS
            LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
            LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
            WHERE c.NOMBRE LIKE %s
            ORDER BY c.NOMBRE ASC, c.ID_COLABORADOR ASC
            LIMIT 20
        """, (f"%{termino}%",))
        filas = cur.fetchall()
    finally:
        cur.close()
    return jsonify([
        {'id': r[0], 'nombre': r[1], 'area_id': r[2] or '', 'area_nombre': r[3] or '',
         'departamento_id': r[4] or '', 'departamento_nombre': r[5] or ''}
        for r in filas
    ])


@bp.route('/api/lookups/cargos', methods=['GET'])
def api_buscar_cargos():
    """Búsqueda acotada de cargos para el formulario de colaboradores."""
    termino = (request.args.get('q') or '').strip()
    if len(termino) < 2:
        return jsonify([])
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT ID_CARGOS, DESCRIPCION, AREA, DEPARTAMENTO
            FROM Cargos
            WHERE DESCRIPCION LIKE %s
            ORDER BY DESCRIPCION ASC, ID_CARGOS ASC
            LIMIT 20
        """, (f"%{termino}%",))
        filas = cur.fetchall()
    finally:
        cur.close()
    return jsonify([{'id': r[0], 'nombre': r[1], 'area': r[2], 'departamento': r[3]} for r in filas])


@bp.route('/extensiones', methods=['GET', 'POST'])
def crud_extensiones():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    # Obtener áreas y departamentos para los selects
    cur.execute("SELECT ID_AREAS, AREA FROM Areas ORDER BY ID_AREAS ASC")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM Departamentos ORDER BY ID_DEPARTAMENTOS ASC")
    departamentos = cur.fetchall()
    # Crear
    if request.method == 'POST':
        id_colaborador = (request.form.get('id_colaborador') or '').strip()
        extension = (request.form.get('extension') or '').strip()
        area = (request.form.get('area') or '').strip()
        departamento = (request.form.get('departamento') or '').strip()

        if not all((id_colaborador, extension, area, departamento)):
            flash('Selecciona un colaborador con área y departamento, e ingresa su extensión.', 'danger')
            cur.close()
            return redirect(url_for('telecom.crud_extensiones'))

        if not all(value.isdigit() for value in (id_colaborador, extension, area, departamento)):
            flash('Colaborador, área, departamento y extensión deben contener valores válidos.', 'danger')
            cur.close()
            return redirect(url_for('telecom.crud_extensiones'))

        id_col, ext_val, area_id, departamento_id = map(int, (id_colaborador, extension, area, departamento))
        cur.execute("""
            SELECT cg.AREA, cg.DEPARTAMENTO
            FROM Colaboradores c
            LEFT JOIN Cargos cg ON c.CARGO = cg.ID_CARGOS
            WHERE c.ID_COLABORADOR = %s
        """, (id_col,))
        asignacion = cur.fetchone()
        if not asignacion or asignacion[0] is None or asignacion[1] is None:
            flash('El colaborador debe tener un cargo con área y departamento asignados.', 'danger')
            cur.close()
            return redirect(url_for('telecom.crud_extensiones'))

        if area_id != asignacion[0] or departamento_id != asignacion[1]:
            flash('El área y el departamento deben coincidir con el cargo del colaborador seleccionado.', 'danger')
            cur.close()
            return redirect(url_for('telecom.crud_extensiones'))

        try:
            cur.execute(
                "INSERT INTO Extensiones (ID_COLABORADOR, EXTENSION, AREA, DEPARTAMENTO) VALUES (%s, %s, %s, %s)",
                (id_col, ext_val, area_id, departamento_id)
            )
            mysql.connection.commit()
            flash('Extensión agregada correctamente.', 'success')
        except Exception as e:
            mysql.connection.rollback()
            current_app.logger.exception('Error al agregar extensión')
            flash('No se pudo agregar la extensión. Revisa los datos e inténtalo de nuevo.', 'danger')
    # Leer: mostrar área y departamento actual del colaborador relacionado
    extensiones, pagination = paginar_gestion(cur, """
        SELECT e.ID_EXTENSIONES, c.NOMBRE, e.EXTENSION, a.AREA, d.DEPARTAMENTO, e.AREA, e.DEPARTAMENTO, e.ID_COLABORADOR
        FROM Extensiones e
        LEFT JOIN Colaboradores c ON e.ID_COLABORADOR = c.ID_COLABORADOR
        LEFT JOIN Areas a ON e.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON e.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY e.ID_EXTENSIONES ASC
    """, (), "SELECT COUNT(*) FROM Extensiones")
    cur.close()
    return render_template('Extensiones/CRUD_Extensiones.html', extensiones=extensiones, areas=areas, departamentos=departamentos, pagination=pagination)


@bp.route('/extensiones/editar/<int:id>', methods=['POST'])
def editar_extension(id):
    # Protección de sesión
    if 'user_id' not in session:
        flash('Debes iniciar sesión para realizar esta acción.', 'warning')
        return redirect(url_for('auth.login'))

    # Obtener valores del formulario
    id_colaborador = (request.form.get('id_colaborador') or '').strip()
    extension = (request.form.get('extension') or '').strip()
    area = (request.form.get('area') or '').strip()
    departamento = (request.form.get('departamento') or '').strip()

    # Validaciones básicas
    if not all((id_colaborador, extension, area, departamento)):
        flash('Selecciona un colaborador con área y departamento, e ingresa su extensión.', 'danger')
        return redirect(url_for('telecom.crud_extensiones'))
    if not all(value.isdigit() for value in (id_colaborador, extension, area, departamento)):
        flash('Colaborador, área, departamento y extensión deben contener valores válidos.', 'danger')
        return redirect(url_for('telecom.crud_extensiones'))

    id_col, ext_val, area_id, departamento_id = map(int, (id_colaborador, extension, area, departamento))

    # Ejecutar actualización
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT cg.AREA, cg.DEPARTAMENTO
            FROM Colaboradores c
            LEFT JOIN Cargos cg ON c.CARGO = cg.ID_CARGOS
            WHERE c.ID_COLABORADOR = %s
        """, (id_col,))
        asignacion = cur.fetchone()
        if not asignacion or asignacion[0] is None or asignacion[1] is None:
            flash('El colaborador debe tener un cargo con área y departamento asignados.', 'danger')
            cur.close()
            return redirect(url_for('telecom.crud_extensiones'))
        if area_id != asignacion[0] or departamento_id != asignacion[1]:
            flash('El área y el departamento deben coincidir con el cargo del colaborador seleccionado.', 'danger')
            cur.close()
            return redirect(url_for('telecom.crud_extensiones'))

        cur.execute(
            "UPDATE Extensiones SET ID_COLABORADOR = %s, EXTENSION = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_EXTENSIONES = %s",
            (id_col, ext_val, area_id, departamento_id, id)
        )
        mysql.connection.commit()
        cur.close()
        flash('Extensión editada correctamente.', 'success')
    except Exception as e:
        try:
            cur.close()
        except Exception:
            pass
        current_app.logger.exception('Error al editar extensión')
        flash('No se pudo editar la extensión. Revisa los datos e inténtalo de nuevo.', 'danger')

    return redirect(url_for('telecom.crud_extensiones'))


@bp.route('/extensiones/eliminar/<int:id>', methods=['POST'])
def eliminar_extension(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM Extensiones WHERE ID_EXTENSIONES = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('telecom.crud_extensiones'))


@bp.route('/celulares', methods=['GET', 'POST'])
def crud_celulares():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    # Obtener áreas y departamentos para los selects
    cur.execute("SELECT ID_AREAS, AREA FROM Areas ORDER BY ID_AREAS ASC")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM Departamentos ORDER BY ID_DEPARTAMENTOS ASC")
    departamentos = cur.fetchall()
    # Crear
    if request.method == 'POST':
        id_colaborador = request.form.get('id_colaborador')
        celular = request.form.get('celular')
        area = request.form.get('area')
        departamento = request.form.get('departamento')
        if id_colaborador and celular and area and departamento:
            try:
                cur.execute("INSERT INTO Celulares (ID_COLABORADOR, CELULAR, AREA, DEPARTAMENTO) VALUES (%s, %s, %s, %s)", (id_colaborador, celular, area, departamento))
                mysql.connection.commit()
                flash('Celular agregado correctamente.', 'success')
            except Exception as e:
                mysql.connection.rollback()
                current_app.logger.exception('Error al agregar celular')
                flash('No se pudo agregar el celular. Revisa los datos e inténtalo de nuevo.', 'danger')
    # Leer: mostrar área y departamento actual del colaborador relacionado
    celulares, pagination = paginar_gestion(cur, """
        SELECT c.ID_CELULARES, col.NOMBRE, c.CELULAR, a.AREA, d.DEPARTAMENTO, cg.AREA, cg.DEPARTAMENTO, c.ID_COLABORADOR
        FROM Celulares c
        LEFT JOIN Colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.ID_CELULARES ASC
    """, (), "SELECT COUNT(*) FROM Celulares")
    cur.close()
    return render_template('Celulares/CRUD_Celulares.html', celulares=celulares, areas=areas, departamentos=departamentos, pagination=pagination)


@bp.route('/celulares/editar/<int:id>', methods=['POST'])
def editar_celular(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    id_colaborador = request.form.get('id_colaborador')
    celular = request.form.get('celular')
    area = request.form.get('area')
    departamento = request.form.get('departamento')
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Celulares SET ID_COLABORADOR = %s, CELULAR = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_CELULARES = %s", (id_colaborador, celular, area, departamento, id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('telecom.crud_celulares'))


@bp.route('/celulares/eliminar/<int:id>', methods=['POST'])
def eliminar_celular(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM Celulares WHERE ID_CELULARES = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('telecom.crud_celulares'))


@bp.route('/correos', methods=['GET', 'POST'])
def crud_correos():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    # Obtener áreas y departamentos para los selects
    cur.execute("SELECT ID_AREAS, AREA FROM Areas ORDER BY ID_AREAS ASC")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM Departamentos ORDER BY ID_DEPARTAMENTOS ASC")
    departamentos = cur.fetchall()
    # Crear
    if request.method == 'POST':
        id_colaborador = request.form.get('id_colaborador')
        correo = request.form.get('correo')
        area = request.form.get('area')
        departamento = request.form.get('departamento')
        import re
        correo_regex = r'^([A-Za-z][A-Za-z0-9_.+-]*)@((farbiopharma|inpelab)\.com)$'
        if not correo or '@' not in correo:
            flash('El correo debe contener el separador @.', 'danger')
        elif correo.partition('@')[0].isdigit():
            flash('El nombre de usuario del correo no puede contener solo números.', 'danger')
        elif correo.partition('@')[2] not in ['farbiopharma.com', 'inpelab.com']:
            flash('El dominio del correo debe ser farbiopharma.com o inpelab.com.', 'danger')
        elif not re.match(correo_regex, correo):
            flash('El formato del correo no es válido.', 'danger')
        elif id_colaborador and correo and area and departamento:
            try:
                cur.execute("INSERT INTO Correos (ID_COLABORADOR, CORREO, AREA, DEPARTAMENTO) VALUES (%s, %s, %s, %s)", (id_colaborador, correo, area, departamento))
                mysql.connection.commit()
                flash('Correo agregado correctamente.', 'success')
            except Exception as e:
                mysql.connection.rollback()
                current_app.logger.exception('Error al agregar correo')
                flash('No se pudo agregar el correo. Revisa los datos e inténtalo de nuevo.', 'danger')
    # Leer: mostrar área y departamento actual del cargo del colaborador relacionado
    correos, pagination = paginar_gestion(cur, """
        SELECT c.ID_CORREOS, col.NOMBRE, c.CORREO, a.AREA, d.DEPARTAMENTO, c.ID_COLABORADOR
        FROM Correos c
        LEFT JOIN Colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.ID_CORREOS ASC
    """, (), "SELECT COUNT(*) FROM Correos")
    cur.close()
    return render_template('Correos/CRUD_Correos.html', correos=correos, areas=areas, departamentos=departamentos, pagination=pagination)


@bp.route('/correos/editar/<int:id>', methods=['POST'])
def editar_correo(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    id_colaborador = request.form.get('id_colaborador')
    correo = request.form.get('correo')
    area = request.form.get('area')
    departamento = request.form.get('departamento')
    import re
    # Validación de formato de correo
    correo_regex = r'^([A-Za-z][A-Za-z0-9_.+-]*)@((farbiopharma|inpelab)\.com)$'
    if not correo or '@' not in correo:
        flash('El correo debe contener el separador @.', 'danger')
        return redirect(url_for('telecom.crud_correos'))
    usuario, sep, dominio = correo.partition('@')
    if usuario.isdigit():
        flash('El nombre de usuario del correo no puede contener solo números.', 'danger')
        return redirect(url_for('telecom.crud_correos'))
    if dominio not in ['farbiopharma.com', 'inpelab.com']:
        flash('El dominio del correo debe ser farbiopharma.com o inpelab.com.', 'danger')
        return redirect(url_for('telecom.crud_correos'))
    # Validación extra con regex
    if not re.match(correo_regex, correo):
        flash('El formato del correo no es válido.', 'danger')
        return redirect(url_for('telecom.crud_correos'))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Correos SET ID_COLABORADOR = %s, CORREO = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_CORREOS = %s", (id_colaborador, correo, area, departamento, id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('telecom.crud_correos'))


@bp.route('/correos/eliminar/<int:id>', methods=['POST'])
def eliminar_correo(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM Correos WHERE ID_CORREOS = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('telecom.crud_correos'))


