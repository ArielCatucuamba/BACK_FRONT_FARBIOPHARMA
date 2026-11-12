from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for, send_file
from datetime import datetime
from Colaboradores.exportarColaboradores import generar_excel_colaboradores
from Colaboradores.validarColaborador import validar_colaborador, ESTADOS_COLABORADOR
from ..extensiones import mysql
from ..utilidades import rol_normalizado
from ..filtrosGestion import paginar_gestion

bp = Blueprint('collaborators', __name__)


@bp.route('/crud_colaboradores/descargar-excel', methods=['GET'])
def descargar_excel_colaboradores():
    # register_security aplica la sesión y el rol de Talento Humano/Administrador.
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        archivo = generar_excel_colaboradores(cursor)
        respuesta = send_file(
            archivo,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'colaboradores_{datetime.now():%Y%m%d_%H%M%S}.xlsx',
        )
        respuesta.headers['Cache-Control'] = 'no-store, private'
        respuesta.headers['X-Content-Type-Options'] = 'nosniff'
        return respuesta
    except Exception:
        current_app.logger.exception('No se pudo exportar el padrón de colaboradores')
        flash('No se pudo generar el Excel. Inténtalo nuevamente.', 'danger')
        return redirect(url_for('collaborators.crud_colaboradores'))
    finally:
        if cursor is not None:
            cursor.close()

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
    cur.execute("SELECT ID_EMPRESA, NOMBRE FROM Empresas ORDER BY NOMBRE ASC")
    empresas = cur.fetchall()
    # Crear
    if request.method == 'POST':
        try:
            datos = validar_colaborador(request.form, cur)
            cur.execute(
                "INSERT INTO Colaboradores (CEDULA, NOMBRE, EMPRESA, ESTADO, CARGO, UBICACION) VALUES (%s, %s, %s, %s, %s, %s)",
                tuple(datos[campo] for campo in ('cedula', 'nombre', 'empresa', 'estado', 'cargo', 'ubicacion')),
            )
            mysql.connection.commit()
            flash('Colaborador agregado exitosamente.', 'success')
        except ValueError as error:
            mysql.connection.rollback()
            flash(str(error), 'danger')
        except Exception as error:
            mysql.connection.rollback()
            if getattr(error, 'args', ()) and error.args[0] == 1062:
                flash('La cédula ya está registrada en otro colaborador.', 'danger')
            else:
                current_app.logger.exception('Error al agregar colaborador')
                flash('No se pudo agregar el colaborador. Revisa los datos e inténtalo de nuevo.', 'danger')
        finally:
            cur.close()
        return redirect(url_for('collaborators.crud_colaboradores'))
    # Leer
    colaboradores, pagination = paginar_gestion(cur, """
        SELECT col.ID_COLABORADOR, col.NOMBRE,
               d.DEPARTAMENTO, a.AREA, c.DESCRIPCION, u.DESCRIPCION,
               c.DEPARTAMENTO, c.AREA, col.CARGO, col.UBICACION, col.ESTADO,
               col.CEDULA, empresa.NOMBRE, correo.CORREO, col.EMPRESA
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
    return render_template('Colaboradores/CRUD_Colaboradores.html', colaboradores=colaboradores, areas=areas, departamentos=departamentos, ubicaciones=ubicaciones, empresas=empresas, estados_colaborador=ESTADOS_COLABORADOR, pagination=pagination)


@bp.route('/crud_colaboradores/editar/<int:id>', methods=['POST'])
def editar_colaborador(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    try:
        cur.execute('SELECT ID_COLABORADOR FROM Colaboradores WHERE ID_COLABORADOR = %s FOR UPDATE', (id,))
        if not cur.fetchone():
            raise ValueError('El colaborador ya no existe.')
        datos = validar_colaborador(request.form, cur, colaborador_id=id)
        cur.execute(
            "UPDATE Colaboradores SET CEDULA = %s, NOMBRE = %s, EMPRESA = %s, ESTADO = %s, CARGO = %s, UBICACION = %s WHERE ID_COLABORADOR = %s",
            tuple(datos[campo] for campo in ('cedula', 'nombre', 'empresa', 'estado', 'cargo', 'ubicacion')) + (id,),
        )
        # La FK de usuarios.cedula usa ON UPDATE CASCADE en la base compartida.
        mysql.connection.commit()
        flash('Colaborador editado correctamente.', 'success')
    except ValueError as error:
        mysql.connection.rollback()
        flash(str(error), 'danger')
    except Exception as error:
        mysql.connection.rollback()
        if getattr(error, 'args', ()) and error.args[0] == 1062:
            flash('La cédula ya está registrada en otro colaborador.', 'danger')
        else:
            current_app.logger.exception('Error al editar colaborador')
            flash('No se pudo editar el colaborador. Revisa los datos e inténtalo de nuevo.', 'danger')
    finally:
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


