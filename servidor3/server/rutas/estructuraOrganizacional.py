from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from ..extensiones import mysql
from ..utilidades import paginar_consulta, rol_normalizado

bp = Blueprint('structure', __name__)

@bp.route('/crud_areas', methods=['GET', 'POST'])
def crud_areas():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    # Crear
    if request.method == 'POST':
        area = request.form.get('area')
        if area:
            if area.isdigit():
                flash('El nombre del área no puede ser solo números.', 'danger')
            else:
                cur.execute("INSERT INTO Areas (AREA) VALUES (%s)", (area,))
                mysql.connection.commit()
                flash('Área agregada correctamente.', 'success')
        else:
            flash('El campo área es obligatorio.', 'danger')
    # Leer
    areas, pagination = paginar_consulta(cur, "SELECT ID_AREAS, AREA FROM Areas ORDER BY ID_AREAS ASC", (), "SELECT COUNT(*) FROM Areas")
    cur.close()
    return render_template('Areas/CRUD_Areas.html', areas=areas, pagination=pagination)


@bp.route('/crud_areas/editar/<int:id>', methods=['POST'])
def editar_area(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    area = request.form.get('area')
    if not area:
        flash('El campo área es obligatorio.', 'danger')
        return redirect(url_for('structure.crud_areas'))
    if area.isdigit():
        flash('El nombre del área no puede ser solo números.', 'danger')
        return redirect(url_for('structure.crud_areas'))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Areas SET AREA = %s WHERE ID_AREAS = %s", (area, id))
    mysql.connection.commit()
    cur.close()
    flash('Área editada correctamente.', 'success')
    return redirect(url_for('structure.crud_areas'))


@bp.route('/crud_areas/eliminar/<int:id>', methods=['POST'])
def eliminar_area(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Areas WHERE ID_AREAS = %s", (id,))
        mysql.connection.commit()
        flash('Área eliminada exitosamente.', 'success')
    except Exception as e:
        flash('No se puede eliminar esta área porque está ligada a otros datos.', 'danger')
    cur.close()
    return redirect(url_for('structure.crud_areas'))


@bp.route('/departamentos', methods=['GET', 'POST'])
def departamentos():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    # Crear
    if request.method == 'POST':
        departamento = request.form.get('departamento')
        if departamento:
            if departamento.isdigit():
                flash('El nombre del departamento no puede ser solo números.', 'danger')
            else:
                cur.execute("INSERT INTO Departamentos (DEPARTAMENTO) VALUES (%s)", (departamento,))
                mysql.connection.commit()
                flash('Departamento agregado correctamente.', 'success')
        else:
            flash('El campo departamento es obligatorio.', 'danger')
    # Leer
    departamentos, pagination = paginar_consulta(cur, "SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM Departamentos ORDER BY ID_DEPARTAMENTOS ASC", (), "SELECT COUNT(*) FROM Departamentos")
    cur.close()
    return render_template('Departamentos/CRUD_Departamentos.html', departamentos=departamentos, pagination=pagination)


@bp.route('/departamentos/editar/<int:id>', methods=['POST'])
def editar_departamento(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    departamento = request.form.get('departamento')
    if not departamento:
        flash('El campo departamento es obligatorio.', 'danger')
        return redirect(url_for('structure.departamentos'))
    if departamento.isdigit():
        flash('El nombre del departamento no puede ser solo números.', 'danger')
        return redirect(url_for('structure.departamentos'))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Departamentos SET DEPARTAMENTO = %s WHERE ID_DEPARTAMENTOS = %s", (departamento, id))
    mysql.connection.commit()
    cur.close()
    flash('Departamento editado correctamente.', 'success')
    return redirect(url_for('structure.departamentos'))


@bp.route('/departamentos/eliminar/<int:id>', methods=['POST'])
def eliminar_departamento(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Departamentos WHERE ID_DEPARTAMENTOS = %s", (id,))
        mysql.connection.commit()
        flash('Departamento eliminado exitosamente.', 'success')
    except Exception as e:
        flash('No se puede eliminar este departamento porque está ligado a otros datos.', 'danger')
    cur.close()
    return redirect(url_for('structure.departamentos'))


@bp.route('/ubicaciones', methods=['GET', 'POST'])
def ubicaciones():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    # Crear
    if request.method == 'POST':
        descripcion = request.form.get('descripcion')
        geolocalizacion = request.form.get('geolocalizacion')
        direccion = request.form.get('direccion')
        if descripcion and geolocalizacion and direccion:
            cur.execute("INSERT INTO Ubicaciones (DESCRIPCION, GEOLOCALIZACION, DIRECCION) VALUES (%s, %s, %s)", (descripcion, geolocalizacion, direccion))
            mysql.connection.commit()
    # Leer
    ubicaciones, pagination = paginar_consulta(cur, "SELECT ID_UBICACIONES, DESCRIPCION, GEOLOCALIZACION, DIRECCION FROM Ubicaciones ORDER BY ID_UBICACIONES ASC", (), "SELECT COUNT(*) FROM Ubicaciones")
    cur.close()
    return render_template('Ubicaciones/CRUD_Ubicaciones.html', ubicaciones=ubicaciones, pagination=pagination)


@bp.route('/ubicaciones/editar/<int:id>', methods=['POST'])
def editar_ubicacion(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    descripcion = request.form.get('descripcion')
    geolocalizacion = request.form.get('geolocalizacion')
    direccion = request.form.get('direccion')
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Ubicaciones SET DESCRIPCION = %s, GEOLOCALIZACION = %s, DIRECCION = %s WHERE ID_UBICACIONES = %s", (descripcion, geolocalizacion, direccion, id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('structure.ubicaciones'))


@bp.route('/ubicaciones/eliminar/<int:id>', methods=['POST'])
def eliminar_ubicacion(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Ubicaciones WHERE ID_UBICACIONES = %s", (id,))
        mysql.connection.commit()
        flash('Ubicación eliminada exitosamente.', 'success')
    except Exception as e:
        flash('No se puede eliminar esta ubicación porque está ligada a otros datos.', 'danger')
    cur.close()
    return redirect(url_for('structure.ubicaciones'))


@bp.route('/crud_cargos', methods=['GET', 'POST'])
def crud_cargos():
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
        descripcion = request.form.get('descripcion')
        area = request.form.get('area')
        departamento = request.form.get('departamento')
        if not descripcion or not area or not departamento:
            flash('Todos los campos son obligatorios.', 'danger')
        elif descripcion.isdigit():
            flash('El nombre del cargo no puede ser solo números.', 'danger')
        else:
            cur.execute("INSERT INTO Cargos (DESCRIPCION, AREA, DEPARTAMENTO) VALUES (%s, %s, %s)", (descripcion, area, departamento))
            mysql.connection.commit()
            flash('Cargo agregado correctamente.', 'success')
    # Leer
    cargos, pagination = paginar_consulta(cur, """
        SELECT c.ID_CARGOS, c.DESCRIPCION, a.AREA, d.DEPARTAMENTO, c.AREA, c.DEPARTAMENTO
        FROM Cargos c
        LEFT JOIN Areas a ON c.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON c.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.ID_CARGOS ASC
    """, (), "SELECT COUNT(*) FROM Cargos")
    cur.close()
    return render_template('Cargos/CRUD_Cargos.html', cargos=cargos, areas=areas, departamentos=departamentos, pagination=pagination)


@bp.route('/crud_cargos/editar/<int:id>', methods=['POST'])
def editar_cargo(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    descripcion = request.form.get('descripcion')
    area = request.form.get('area')
    departamento = request.form.get('departamento')
    if not descripcion or not area or not departamento:
        flash('Todos los campos son obligatorios.', 'danger')
        return redirect(url_for('structure.crud_cargos'))
    if descripcion.isdigit():
        flash('El nombre del cargo no puede ser solo números.', 'danger')
        return redirect(url_for('structure.crud_cargos'))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Cargos SET DESCRIPCION = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_CARGOS = %s", (descripcion, area, departamento, id))
    mysql.connection.commit()
    cur.close()
    flash('Cargo editado correctamente.', 'success')
    return redirect(url_for('structure.crud_cargos'))


@bp.route('/crud_cargos/eliminar/<int:id>', methods=['POST'])
def eliminar_cargo(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Cargos WHERE ID_CARGOS = %s", (id,))
        mysql.connection.commit()
        flash('Cargo eliminado exitosamente.', 'success')
    except Exception as e:
        flash('No se puede eliminar este cargo porque está ligado a otros datos.', 'danger')
    cur.close()
    return redirect(url_for('structure.crud_cargos'))


