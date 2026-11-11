from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from ..extensiones import mysql
from ..utilidades import paginar_consulta, rol_normalizado

bp = Blueprint('collaborators', __name__)

@bp.route('/crud_colaboradores', methods=['GET', 'POST'])
def crud_colaboradores():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    # Obtener áreas, departamentos, cargos y ubicaciones para los selects
    cur.execute("SELECT ID_AREAS, AREA FROM Areas ORDER BY ID_AREAS ASC")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM Departamentos ORDER BY ID_DEPARTAMENTOS ASC")
    departamentos = cur.fetchall()
    cur.execute("SELECT ID_UBICACIONES, DESCRIPCION FROM Ubicaciones ORDER BY ID_UBICACIONES ASC")
    ubicaciones = cur.fetchall()
    # Crear
    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        cargo = (request.form.get('cargo') or '').strip()
        ubicacion = (request.form.get('ubicacion') or '').strip()
        estado = (request.form.get('estado') or 'ACTIVO').strip().upper()
        if not all([nombre, cargo, ubicacion]):
            flash('Todos los campos son obligatorios.', 'danger')
        elif estado not in ('ACTIVO', 'AUSENTE'):
            flash('El estado del colaborador no es válido.', 'danger')
        else:
            try:
                if not cargo.isdigit():
                    cur.execute("SELECT ID_CARGOS FROM Cargos WHERE DESCRIPCION = %s", (cargo,))
                    cargo_row = cur.fetchone()
                    cargo = str(cargo_row[0]) if cargo_row else ''
                if not cargo.isdigit():
                    raise ValueError('El cargo seleccionado no es válido.')

                cur.execute("SELECT AREA, DEPARTAMENTO FROM Cargos WHERE ID_CARGOS = %s", (cargo,))
                cargo_contexto = cur.fetchone()
                if not cargo_contexto:
                    raise ValueError('El cargo seleccionado no existe.')

                area_form = (request.form.get('area') or '').strip()
                departamento_form = (request.form.get('departamento') or '').strip()
                if ((area_form and area_form.isdigit() and int(area_form) != cargo_contexto[0]) or
                        (departamento_form and departamento_form.isdigit() and int(departamento_form) != cargo_contexto[1])):
                    raise ValueError('El área y departamento deben corresponder al cargo seleccionado.')

                cur.execute(
                    "INSERT INTO Colaboradores (NOMBRE, ESTADO, CARGO, UBICACION) VALUES (%s, %s, %s, %s)",
                    (nombre, estado, int(cargo), int(ubicacion))
                )
                mysql.connection.commit()
                flash('Colaborador agregado exitosamente.', 'success')
            except Exception as e:
                mysql.connection.rollback()
                current_app.logger.exception('Error al agregar colaborador')
                flash('No se pudo agregar el colaborador. Revisa los datos e inténtalo de nuevo.', 'danger')
    # Leer
    colaboradores, pagination = paginar_consulta(cur, """
        SELECT col.ID_COLABORADOR, col.NOMBRE,
               d.DEPARTAMENTO, a.AREA, c.DESCRIPCION, u.DESCRIPCION,
               c.DEPARTAMENTO, c.AREA, col.CARGO, col.UBICACION, col.ESTADO,
               col.CEDULA, empresa.NOMBRE, correo.CORREO
        FROM Colaboradores col
        LEFT JOIN Cargos c ON col.CARGO = c.ID_CARGOS
        LEFT JOIN Areas a ON c.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON c.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        LEFT JOIN Ubicaciones u ON col.UBICACION = u.ID_UBICACIONES
         LEFT JOIN Empresas empresa ON col.EMPRESA = empresa.ID_EMPRESA
         LEFT JOIN Correos correo ON col.ID_CORREO_PRINCIPAL = correo.ID_CORREOS
        ORDER BY col.ID_COLABORADOR ASC
    """, (), "SELECT COUNT(*) FROM Colaboradores")
    cur.close()
    return render_template('Colaboradores/CRUD_Colaboradores.html', colaboradores=colaboradores, areas=areas, departamentos=departamentos, ubicaciones=ubicaciones, pagination=pagination)


@bp.route('/crud_colaboradores/editar/<int:id>', methods=['POST'])
def editar_colaborador(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    nombre = request.form.get('nombre')
    departamento = request.form.get('departamento')
    area = request.form.get('area')
    cargo = request.form.get('cargo')
    ubicacion = request.form.get('ubicacion')
    estado = (request.form.get('estado') or '').strip().upper()

    # Validaciones básicas
    if not all([nombre, cargo, ubicacion, estado]):
        flash('Todos los campos son obligatorios.', 'danger')
        return redirect(url_for('collaborators.crud_colaboradores'))
    if estado not in ('ACTIVO', 'AUSENTE'):
        flash('El estado del colaborador no es válido.', 'danger')
        return redirect(url_for('collaborators.crud_colaboradores'))
    # Validar que el nombre no sea solo números
    if nombre.isdigit():
        flash('El nombre del colaborador no puede ser solo números.', 'danger')
        return redirect(url_for('collaborators.crud_colaboradores'))

    # Si cargo no es un número (ID), buscar el ID por nombre
    if not cargo.isdigit():
        cur = mysql.connection.cursor()
        cur.execute("SELECT ID_CARGOS FROM Cargos WHERE DESCRIPCION = %s", (cargo,))
        cargo_row = cur.fetchone()
        if cargo_row:
            cargo = str(cargo_row[0])
        else:
            cur.close()
            flash('El cargo seleccionado no es válido.', 'danger')
            return redirect(url_for('collaborators.crud_colaboradores'))
        cur.close()

    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT AREA, DEPARTAMENTO FROM Cargos WHERE ID_CARGOS = %s", (int(cargo),))
        cargo_contexto = cur.fetchone()
        if not cargo_contexto:
            raise ValueError('El cargo seleccionado no existe.')
        area_form = (request.form.get('area') or '').strip()
        departamento_form = (request.form.get('departamento') or '').strip()
        if ((area_form and area_form.isdigit() and int(area_form) != cargo_contexto[0]) or
                (departamento_form and departamento_form.isdigit() and int(departamento_form) != cargo_contexto[1])):
            raise ValueError('El área y departamento deben corresponder al cargo seleccionado.')

        # Obtener el nombre anterior del colaborador
        cur.execute("SELECT NOMBRE FROM Colaboradores WHERE ID_COLABORADOR = %s", (id,))
        old_row = cur.fetchone()
        old_nombre = old_row[0] if old_row else None
        # Si el nombre cambió, actualizar en cascada en las tablas relacionadas
        if old_nombre and old_nombre != nombre:
            # Ya no es necesario actualizar NOMBRE en tablas relacionadas, solo en colaboradores
            pass
        # Actualizar colaborador
        cur.execute(
            "UPDATE Colaboradores SET NOMBRE = %s, ESTADO = %s, CARGO = %s, UBICACION = %s WHERE ID_COLABORADOR = %s",
            (nombre, estado, int(cargo), int(ubicacion), id)
        )
        mysql.connection.commit()
        flash('Colaborador editado correctamente.', 'success')
    except Exception as e:
        mysql.connection.rollback()
        current_app.logger.exception('Error al editar colaborador')
        flash('No se pudo editar el colaborador. Revisa los datos e inténtalo de nuevo.', 'danger')
    cur.close()
    return redirect(url_for('collaborators.crud_colaboradores'))


@bp.route('/crud_colaboradores/eliminar/<int:id>', methods=['POST'])
def eliminar_colaborador(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Colaboradores WHERE ID_COLABORADOR = %s", (id,))
        mysql.connection.commit()
        flash('Colaborador eliminado correctamente.', 'success')
    except Exception as e:
        mysql.connection.rollback()
        # Si es un error de integridad (clave foránea), mostrar alerta amigable
        if hasattr(e, 'args') and e.args and 'foreign key constraint fails' in str(e.args[1]).lower():
            flash('No se puede eliminar este colaborador porque está ligado a otros datos.', 'danger')
        else:
            current_app.logger.exception('Error al eliminar colaborador')
            flash('No se pudo eliminar el colaborador porque está relacionado con otros datos.', 'danger')
    cur.close()
    return redirect(url_for('collaborators.crud_colaboradores'))


