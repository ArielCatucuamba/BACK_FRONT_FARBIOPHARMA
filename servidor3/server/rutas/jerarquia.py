from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from ..extensiones import mysql
from ..utilidades import paginar_consulta, rol_normalizado
import re

def jerarquia_crea_ciclo(cur, cargo_id, superior_id, departamento_id, area_id, planta, excluir_id=None):
    """Comprueba si asignar superior_id al cargo_id cerraría un ciclo jerárquico."""
    query = (
        "SELECT CARGO, SUPERIOR_JERARQUICO FROM Jerarquia "
        "WHERE DEPARTAMENTO = %s AND AREA = %s AND PLANTA = %s"
    )
    params = (departamento_id, area_id, planta)
    if excluir_id is not None:
        query += " AND ID_JERARQUIA <> %s"
        params += (excluir_id,)
    cur.execute(query, params)

    superiores_por_cargo = {}
    for cargo, superior in cur.fetchall():
        if superior is not None:
            superiores_por_cargo.setdefault(cargo, []).append(superior)

    pendientes = [superior_id]
    visitados = set()
    while pendientes:
        actual = pendientes.pop()
        if actual == cargo_id:
            return True
        if actual in visitados:
            continue
        visitados.add(actual)
        pendientes.extend(superiores_por_cargo.get(actual, []))
    return False

def resolver_aprobador_efectivo(cur, colaborador_id):
    """Busca el primer ocupante activo sobre el colaborador dentro de su contexto."""
    cur.execute("""
         SELECT col.ID_COLABORADOR, col.NOMBRE, col.CARGO, cargo.DEPARTAMENTO,
             cargo.AREA, ubic.DESCRIPCION
        FROM Colaboradores col
         LEFT JOIN Cargos cargo ON col.CARGO = cargo.ID_CARGOS
        LEFT JOIN Ubicaciones ubic ON col.UBICACION = ubic.ID_UBICACIONES
        WHERE col.ID_COLABORADOR = %s
    """, (colaborador_id,))
    colaborador = cur.fetchone()
    if not colaborador:
        return {'aprobadores': [], 'heredado': False, 'saltados': [], 'error': 'Colaborador no encontrado.'}

    _, nombre_solicitante, cargo_actual, departamento, area, planta = colaborador
    resultado = {
        'solicitante': nombre_solicitante,
        'aprobadores': [],
        'heredado': False,
        'saltados': [],
        'error': None
    }
    if not all([cargo_actual, departamento, area, planta]):
        resultado['error'] = 'El colaborador no tiene cargo, área, departamento y ubicación necesarios para resolver la jerarquía.'
        return resultado

    visitados = {cargo_actual}
    while cargo_actual is not None:
        cur.execute("""
            SELECT j.SUPERIOR_JERARQUICO, superior.DESCRIPCION
            FROM Jerarquia j
            LEFT JOIN Cargos superior ON superior.ID_CARGOS = j.SUPERIOR_JERARQUICO
            WHERE j.CARGO = %s AND j.DEPARTAMENTO = %s AND j.AREA = %s AND j.PLANTA = %s
        """, (cargo_actual, departamento, area, planta))
        relacion = cur.fetchone()
        if not relacion or relacion[0] is None:
            break

        superior_id, nombre_cargo_superior = relacion
        if superior_id in visitados:
            resultado['error'] = 'Se detectó un ciclo en la jerarquía; revisa su configuración.'
            return resultado
        visitados.add(superior_id)

        cur.execute("""
                        SELECT ocupante.ID_COLABORADOR, ocupante.NOMBRE
                        FROM Colaboradores ocupante
                        INNER JOIN Cargos cargo_ocupante ON ocupante.CARGO = cargo_ocupante.ID_CARGOS
                        WHERE ocupante.CARGO = %s
                            AND cargo_ocupante.DEPARTAMENTO = %s
                            AND cargo_ocupante.AREA = %s
                            AND ocupante.ID_COLABORADOR <> %s
                            AND ocupante.UBICACION = (
                  SELECT ID_UBICACIONES FROM Ubicaciones WHERE DESCRIPCION = %s LIMIT 1
              )
                            AND ocupante.ESTADO = 'ACTIVO'
                        ORDER BY ocupante.NOMBRE
                """, (superior_id, departamento, area, colaborador_id, planta))
        ocupantes_activos = cur.fetchall()
        if ocupantes_activos:
            resultado['aprobadores'] = [
                {'id': ocupante[0], 'nombre': ocupante[1], 'cargo': nombre_cargo_superior}
                for ocupante in ocupantes_activos
            ]
            return resultado

        cur.execute("""
                        SELECT COUNT(*)
                        FROM Colaboradores ocupante
                        INNER JOIN Cargos cargo_ocupante ON ocupante.CARGO = cargo_ocupante.ID_CARGOS
                        WHERE ocupante.CARGO = %s
                            AND cargo_ocupante.DEPARTAMENTO = %s
                            AND cargo_ocupante.AREA = %s
                            AND ocupante.UBICACION = (
                  SELECT ID_UBICACIONES FROM Ubicaciones WHERE DESCRIPCION = %s LIMIT 1
              )
        """, (superior_id, departamento, area, planta))
        tiene_ocupantes = cur.fetchone()[0] > 0
        resultado['saltados'].append({
            'cargo': nombre_cargo_superior,
            'motivo': 'ocupante(s) ausente(s)' if tiene_ocupantes else 'cargo sin ocupante asignado'
        })
        resultado['heredado'] = True
        cargo_actual = superior_id

    if not resultado['error']:
        resultado['error'] = 'No se encontró un superior activo en la jerarquía configurada.'
    return resultado


bp = Blueprint('hierarchy', __name__)

@bp.route('/api/colaboradores/<int:colaborador_id>/aprobador', methods=['GET'])
def api_aprobador_efectivo(colaborador_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Autenticación requerida.'}), 401

    cur = mysql.connection.cursor()
    try:
        resultado = resolver_aprobador_efectivo(cur, colaborador_id)
    finally:
        cur.close()
    status = 404 if resultado.get('error') == 'Colaborador no encontrado.' else 200
    return jsonify(resultado), status


@bp.route('/jerarquia', methods=['GET', 'POST'])
def crud_jerarquia():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()
    if request.method == 'POST':
        cargo = (request.form.get('cargo') or '').strip()
        superior = (request.form.get('superior_jerarquico') or '').strip()
        departamento = (request.form.get('departamento') or '').strip()
        area = (request.form.get('area') or '').strip()
        planta = (request.form.get('planta') or '').strip()

        if not all([cargo, departamento, area, planta]):
            flash('Cargo, departamento, área y planta son obligatorios.', 'danger')
        else:
            try:
                cargo_id = int(cargo)
                departamento_id = int(departamento)
                area_id = int(area)
                superior_id = int(superior) if superior else None
            except ValueError:
                flash('Selecciona opciones válidas para cargo, superior, departamento y área.', 'danger')
            else:
                if superior_id == cargo_id:
                    flash('Un cargo no puede ser su propio superior jerárquico.', 'danger')
                elif superior_id is not None and jerarquia_crea_ciclo(
                    cur, cargo_id, superior_id, departamento_id, area_id, planta
                ):
                    flash('La relación crearía un ciclo en la jerarquía.', 'danger')
                else:
                    try:
                        cur.execute(
                            "INSERT INTO Jerarquia (CARGO, SUPERIOR_JERARQUICO, DEPARTAMENTO, AREA, PLANTA) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (cargo_id, superior_id, departamento_id, area_id, planta)
                        )
                        mysql.connection.commit()
                        flash('Relación jerárquica agregada correctamente.', 'success')
                    except Exception:
                        mysql.connection.rollback()
                        flash('No se pudo guardar. Verifica que los cargos, el área y el departamento existan y que no esté duplicada la relación.', 'danger')

    cur.execute("SELECT ID_CARGOS, DESCRIPCION FROM Cargos ORDER BY ID_CARGOS ASC")
    cargos = cur.fetchall()
    cur.execute("SELECT ID_AREAS, AREA FROM Areas ORDER BY ID_AREAS ASC")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM Departamentos ORDER BY ID_DEPARTAMENTOS ASC")
    departamentos = cur.fetchall()
    cur.execute("SELECT ID_UBICACIONES, DESCRIPCION FROM Ubicaciones ORDER BY ID_UBICACIONES ASC")
    plantas = cur.fetchall()
    jerarquias, pagination = paginar_consulta(cur, """
        SELECT j.ID_JERARQUIA, j.CARGO, c.DESCRIPCION,
               j.SUPERIOR_JERARQUICO, s.DESCRIPCION,
               j.DEPARTAMENTO, d.DEPARTAMENTO,
               j.AREA, a.AREA, j.PLANTA
        FROM Jerarquia j
        INNER JOIN Cargos c ON j.CARGO = c.ID_CARGOS
        LEFT JOIN Cargos s ON j.SUPERIOR_JERARQUICO = s.ID_CARGOS
        INNER JOIN Departamentos d ON j.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        INNER JOIN Areas a ON j.AREA = a.ID_AREAS
        ORDER BY j.ID_JERARQUIA ASC
    """, (), "SELECT COUNT(*) FROM Jerarquia")
    cur.close()
    return render_template(
        'Jerarquia/CRUD_Jerarquia.html',
        jerarquias=jerarquias,
        pagination=pagination,
        cargos=cargos,
        areas=areas,
        departamentos=departamentos,
        plantas=plantas
    )


@bp.route('/jerarquia/editar/<int:id>', methods=['POST'])
def editar_jerarquia(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cargo = (request.form.get('cargo') or '').strip()
    superior = (request.form.get('superior_jerarquico') or '').strip()
    departamento = (request.form.get('departamento') or '').strip()
    area = (request.form.get('area') or '').strip()
    planta = (request.form.get('planta') or '').strip()

    if not all([cargo, departamento, area, planta]):
        flash('Cargo, departamento, área y planta son obligatorios.', 'danger')
        return redirect(url_for('hierarchy.crud_jerarquia'))

    try:
        cargo_id = int(cargo)
        departamento_id = int(departamento)
        area_id = int(area)
        superior_id = int(superior) if superior else None
    except ValueError:
        flash('Selecciona opciones válidas para cargo, superior, departamento y área.', 'danger')
        return redirect(url_for('hierarchy.crud_jerarquia'))

    cur = mysql.connection.cursor()
    if superior_id == cargo_id:
        cur.close()
        flash('Un cargo no puede ser su propio superior jerárquico.', 'danger')
        return redirect(url_for('hierarchy.crud_jerarquia'))
    if superior_id is not None and jerarquia_crea_ciclo(
        cur, cargo_id, superior_id, departamento_id, area_id, planta, excluir_id=id
    ):
        cur.close()
        flash('La relación crearía un ciclo en la jerarquía.', 'danger')
        return redirect(url_for('hierarchy.crud_jerarquia'))

    try:
        cur.execute(
            "UPDATE Jerarquia SET CARGO = %s, SUPERIOR_JERARQUICO = %s, DEPARTAMENTO = %s, "
            "AREA = %s, PLANTA = %s WHERE ID_JERARQUIA = %s",
            (cargo_id, superior_id, departamento_id, area_id, planta, id)
        )
        mysql.connection.commit()
        flash('Relación jerárquica actualizada correctamente.', 'success')
    except Exception:
        mysql.connection.rollback()
        flash('No se pudo actualizar. Verifica que los cargos, el área y el departamento existan y que no esté duplicada la relación.', 'danger')
    finally:
        cur.close()
    return redirect(url_for('hierarchy.crud_jerarquia'))


@bp.route('/jerarquia/eliminar/<int:id>', methods=['POST'])
def eliminar_jerarquia(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Jerarquia WHERE ID_JERARQUIA = %s", (id,))
        mysql.connection.commit()
        flash('Relación jerárquica eliminada correctamente.', 'success')
    except Exception:
        mysql.connection.rollback()
        flash('No se pudo eliminar la relación jerárquica.', 'danger')
    finally:
        cur.close()
    return redirect(url_for('hierarchy.crud_jerarquia'))


