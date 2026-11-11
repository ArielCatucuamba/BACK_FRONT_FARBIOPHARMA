from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from ..extensiones import mysql
from ..utilidades import paginar_consulta, rol_normalizado

bp = Blueprint('fleet', __name__)

@bp.route('/empresas', methods=['GET', 'POST'])
def crud_empresas():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()
    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        if not nombre:
            flash('El nombre de la empresa es obligatorio.', 'danger')
        else:
            try:
                cur.execute("INSERT INTO Empresas (NOMBRE) VALUES (%s)", (nombre,))
                mysql.connection.commit()
                flash('Empresa agregada correctamente.', 'success')
            except Exception:
                mysql.connection.rollback()
                flash('No se pudo agregar la empresa. Verifica que el nombre no esté duplicado.', 'danger')

    empresas, pagination = paginar_consulta(cur, "SELECT ID_EMPRESA, NOMBRE FROM Empresas ORDER BY ID_EMPRESA ASC", (), "SELECT COUNT(*) FROM Empresas")
    cur.close()
    return render_template('Empresas/CRUD_Empresas.html', empresas=empresas, pagination=pagination)


@bp.route('/empresas/editar/<int:id>', methods=['POST'])
def editar_empresa(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    nombre = (request.form.get('nombre') or '').strip()
    if not nombre:
        flash('El nombre de la empresa es obligatorio.', 'danger')
        return redirect(url_for('fleet.crud_empresas'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("UPDATE Empresas SET NOMBRE = %s WHERE ID_EMPRESA = %s", (nombre, id))
        mysql.connection.commit()
        flash('Empresa actualizada correctamente.', 'success')
    except Exception:
        mysql.connection.rollback()
        flash('No se pudo actualizar la empresa. Verifica que el nombre no esté duplicado.', 'danger')
    finally:
        cur.close()
    return redirect(url_for('fleet.crud_empresas'))


@bp.route('/empresas/eliminar/<int:id>', methods=['POST'])
def eliminar_empresa(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Empresas WHERE ID_EMPRESA = %s", (id,))
        mysql.connection.commit()
        flash('Empresa eliminada correctamente.', 'success')
    except Exception:
        mysql.connection.rollback()
        flash('No se puede eliminar esta empresa porque está relacionada con otros datos.', 'danger')
    finally:
        cur.close()
    return redirect(url_for('fleet.crud_empresas'))


@bp.route('/vehiculos', methods=['GET', 'POST'])
def crud_vehiculos():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        placa = (request.form.get('placa') or '').strip().upper()
        marca = (request.form.get('marca') or '').strip()
        modelo = (request.form.get('modelo') or '').strip()
        color = (request.form.get('color') or '').strip()
        conductor = (request.form.get('conductor_asignado') or '').strip() or None

        if not all([placa, marca, modelo, color]):
            flash('Placa, marca, modelo y color son obligatorios.', 'danger')
        else:
            cur = mysql.connection.cursor()
            try:
                cur.execute(
                    "INSERT INTO Vehiculos (PLACA, MARCA, MODELO, COLOR, CONDUCTOR_ASIGNADO) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (placa, marca, modelo, color, conductor)
                )
                mysql.connection.commit()
                flash('Vehículo agregado correctamente.', 'success')
            except Exception:
                mysql.connection.rollback()
                flash('No se pudo agregar el vehículo. Verifica que la placa no esté registrada.', 'danger')
            finally:
                cur.close()

    cur = mysql.connection.cursor()
    vehiculos, pagination = paginar_consulta(cur, """
        SELECT ID_VEHICULOS, PLACA, MARCA, MODELO, COLOR, CONDUCTOR_ASIGNADO
        FROM Vehiculos
        ORDER BY ID_VEHICULOS ASC
    """, (), "SELECT COUNT(*) FROM Vehiculos")
    cur.close()
    return render_template('Vehiculos/CRUD_Vehiculos.html', vehiculos=vehiculos, pagination=pagination)


@bp.route('/vehiculos/editar/<int:id>', methods=['POST'])
def editar_vehiculo(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    placa = (request.form.get('placa') or '').strip().upper()
    marca = (request.form.get('marca') or '').strip()
    modelo = (request.form.get('modelo') or '').strip()
    color = (request.form.get('color') or '').strip()
    conductor = (request.form.get('conductor_asignado') or '').strip() or None

    if not all([placa, marca, modelo, color]):
        flash('Placa, marca, modelo y color son obligatorios.', 'danger')
        return redirect(url_for('fleet.crud_vehiculos'))

    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "UPDATE Vehiculos SET PLACA = %s, MARCA = %s, MODELO = %s, COLOR = %s, "
            "CONDUCTOR_ASIGNADO = %s WHERE ID_VEHICULOS = %s",
            (placa, marca, modelo, color, conductor, id)
        )
        mysql.connection.commit()
        flash('Vehículo actualizado correctamente.', 'success')
    except Exception:
        mysql.connection.rollback()
        flash('No se pudo actualizar el vehículo. Verifica que la placa no esté registrada.', 'danger')
    finally:
        cur.close()
    return redirect(url_for('fleet.crud_vehiculos'))


@bp.route('/vehiculos/eliminar/<int:id>', methods=['POST'])
def eliminar_vehiculo(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Vehiculos WHERE ID_VEHICULOS = %s", (id,))
        mysql.connection.commit()
        flash('Vehículo eliminado correctamente.', 'success')
    except Exception:
        mysql.connection.rollback()
        flash('No se pudo eliminar el vehículo.', 'danger')
    finally:
        cur.close()
    return redirect(url_for('fleet.crud_vehiculos'))


