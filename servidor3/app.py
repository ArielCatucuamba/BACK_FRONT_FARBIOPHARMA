"""
Shim: some Python versions (very new ones) remove or change
`pkgutil.get_loader`. Older Flask releases call that function.
If the running Python's `pkgutil` module doesn't provide
`get_loader`, provide a small compatibility shim that uses
importlib to emulate the behavior. This must run before
importing Flask so Flask's internal imports work.
"""
import pkgutil
import importlib.util
if not hasattr(pkgutil, "get_loader"):
    def _get_loader(module_name):
        try:
            spec = importlib.util.find_spec(module_name)
            return spec.loader if spec is not None else None
        except Exception:
            return None
    pkgutil.get_loader = _get_loader

from flask import Flask, abort, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from datetime import timedelta
import hashlib
import os
import re
import socket
import time

app = Flask(__name__)

# Configuración de la aplicación
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "").strip()
if not app.config['SECRET_KEY']:
    raise RuntimeError("SECRET_KEY debe configurarse antes de iniciar Flask")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
app.config['NAVEW_FRONTEND_ORIGIN'] = os.getenv('NAVEW_FRONTEND_ORIGIN', '').strip().rstrip('/')
if not app.config['NAVEW_FRONTEND_ORIGIN']:
    raise RuntimeError("NAVEW_FRONTEND_ORIGIN debe configurarse antes de iniciar Flask")
app.config['NAVEW_LOGIN_URL'] = f"{app.config['NAVEW_FRONTEND_ORIGIN']}/login"
app.config['NAVEW_LOGOUT_URL'] = f"{app.config['NAVEW_FRONTEND_ORIGIN']}/logout"
app.config['MAX_CONTENT_LENGTH'] = 4096

# Configuración de la base de datos MySQL
app.config['MYSQL_HOST'] = os.getenv("DB_HOST") or os.getenv("MYSQL_HOST", "127.0.0.1")
app.config['MYSQL_USER'] = os.getenv("DB_USER") or os.getenv("MYSQL_USER", "")
app.config['MYSQL_PASSWORD'] = os.getenv("DB_PASSWORD") or os.getenv("MYSQL_PASSWORD", "")
app.config['MYSQL_DB'] = os.getenv("DB_NAME") or os.getenv("MYSQL_DB", "")
app.config['MYSQL_PORT'] = int(os.getenv("DB_PORT") or os.getenv("MYSQL_PORT", 3306))

# Inicializar la base de datos
mysql = MySQL(app)


def rol_normalizado(rol):
    return ''.join(str(rol or '').strip().lower().split())


@app.before_request
def proteger_panel_recursos_humanos():
    # El directorio telefónico y las pantallas de autenticación siguen siendo públicas.
    publicas = {
        'static', 'index', 'login', 'register', 'logout',
        'vextensiones', 'vcelulares', 'vcorreos', 'sso_consume'
    }
    if request.endpoint in publicas:
        return None

    if 'user_id' not in session:
        return redirect(url_for('login'))

    if rol_normalizado(session.get('user_role')) not in {'talentohumano', 'administrador'}:
        abort(403)


@app.route('/sso/consume', methods=['POST'])
def sso_consume():
    """Canjea el código de NAVEW y establece una sesión local para Talento Humano."""
    origen = request.headers.get('Origin', '').rstrip('/')
    origen_permitido = app.config['NAVEW_FRONTEND_ORIGIN']
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
                """SELECT u.id, u.email, u.rol, u.estado
                   FROM rrhh_sso_codes s
                   INNER JOIN usuarios u ON u.id = s.user_id
                   WHERE s.code_hash = %s
                   LIMIT 1""",
                (hash_codigo,)
            )
            usuario = cursor.fetchone()
        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        app.logger.error('Falló el canje SSO de Talento Humano')
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
    session['user_role'] = usuario[2]
    session.permanent = True
    return redirect(url_for('menu'))

def wait_for_db():
    """Esperar a que la base de datos esté disponible"""
    # Aumentamos tolerancia: algunas inicializaciones de MySQL tardan más.
    max_retries = 60
    retry_count = 0

    while retry_count < max_retries:
        try:
            with app.app_context():
                cur = mysql.connection.cursor()
                cur.execute("SELECT 1")
                cur.close()
                print("✅ Conexión a la base de datos establecida")
                return True
        except Exception as e:
            retry_count += 1
            # Mostrar error completo en cada intento para facilitar diagnóstico.
            print(f"⏳ Esperando base de datos... intento {retry_count}/{max_retries} - error: {e!r}")
            # Espera ligeramente mayor para no saturar logs ni CPU
            time.sleep(3)

    # Si no pudimos conectar, lanzar excepción con contexto
    raise Exception(f"❌ No se pudo conectar a la base de datos después de {max_retries} intentos")

@app.route('/')
def index():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT e.ID_EXTENSIONES, c.NOMBRE, e.EXTENSION, a.AREA, d.DEPARTAMENTO, e.AREA, e.DEPARTAMENTO, e.ID_COLABORADOR
        FROM Extensiones e
        LEFT JOIN Colaboradores c ON e.ID_COLABORADOR = c.ID_COLABORADOR
        LEFT JOIN Areas a ON e.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON e.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY e.ID_EXTENSIONES ASC
    """)
    extensiones = cur.fetchall()
    cur.close()
    return render_template('DTelefonico/VExtensiones/Extensiones.html', extensiones=extensiones)
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Compatibilidad con enlaces antiguos; el login central está en NAVEW.
    return redirect(app.config['NAVEW_LOGIN_URL'])

@app.route('/menu')
def menu():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('menu.html')
    


 # --------------------------------------Registro----------------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Compatibilidad con enlaces antiguos; las cuentas se administran en NAVEW.
    return redirect(app.config['NAVEW_LOGIN_URL'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(app.config['NAVEW_LOGOUT_URL'])

@app.route('/vextensiones')
def vextensiones():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT e.ID_EXTENSIONES, col.NOMBRE, e.EXTENSION, a.AREA, d.DEPARTAMENTO, e.ID_COLABORADOR
        FROM Extensiones e
        LEFT JOIN Colaboradores col ON e.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Areas a ON e.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON e.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY e.ID_EXTENSIONES ASC
    """)
    extensiones = cur.fetchall()
    cur.close()
    return render_template('DTelefonico/VExtensiones/Extensiones.html', extensiones=extensiones)

# Ruta para mostrar la vista de celulares
@app.route('/vcelulares')
def vcelulares():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.ID_CELULARES, col.NOMBRE, c.CELULAR, a.AREA, d.DEPARTAMENTO, c.ID_COLABORADOR
        FROM Celulares c
        LEFT JOIN Colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.ID_CELULARES ASC
    """)
    celulares = cur.fetchall()
    cur.close()
    return render_template('DTelefonico/VCelulares/Celulares.html', celulares=celulares)

@app.route('/vcorreos')
def vcorreos():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.ID_CORREOS, col.NOMBRE, c.CORREO, a.AREA, d.DEPARTAMENTO, c.ID_COLABORADOR
        FROM Correos c
        LEFT JOIN Colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.ID_CORREOS ASC
    """)
    correos = cur.fetchall()
    cur.close()
    return render_template('DTelefonico/VCorreos/Correos.html', correos=correos)






 # --------------------------------------CRUD de áreas----------------------------------------------------------------------

@app.route('/crud_areas', methods=['GET', 'POST'])
def crud_areas():
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
    cur.execute("SELECT ID_AREAS, AREA FROM Areas ORDER BY ID_AREAS ASC")
    areas = cur.fetchall()
    cur.close()
    return render_template('Areas/CRUD_Areas.html', areas=areas)

# Editar área
@app.route('/crud_areas/editar/<int:id>', methods=['POST'])
def editar_area(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    area = request.form.get('area')
    if not area:
        flash('El campo área es obligatorio.', 'danger')
        return redirect(url_for('crud_areas'))
    if area.isdigit():
        flash('El nombre del área no puede ser solo números.', 'danger')
        return redirect(url_for('crud_areas'))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Areas SET AREA = %s WHERE ID_AREAS = %s", (area, id))
    mysql.connection.commit()
    cur.close()
    flash('Área editada correctamente.', 'success')
    return redirect(url_for('crud_areas'))

# Eliminar área
@app.route('/crud_areas/eliminar/<int:id>', methods=['POST'])
def eliminar_area(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Areas WHERE ID_AREAS = %s", (id,))
        mysql.connection.commit()
        flash('Área eliminada exitosamente.', 'success')
    except Exception as e:
        flash('No se puede eliminar esta área porque está ligada a otros datos.', 'danger')
    cur.close()
    return redirect(url_for('crud_areas'))


# --------------------------------------CRUD de departamentos----------------------------------------------------------------------

@app.route('/departamentos', methods=['GET', 'POST'])
def departamentos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM Departamentos ORDER BY ID_DEPARTAMENTOS ASC")
    departamentos = cur.fetchall()
    cur.close()
    return render_template('Departamentos/CRUD_Departamentos.html', departamentos=departamentos)

# Editar departamento
@app.route('/departamentos/editar/<int:id>', methods=['POST'])
def editar_departamento(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    departamento = request.form.get('departamento')
    if not departamento:
        flash('El campo departamento es obligatorio.', 'danger')
        return redirect(url_for('departamentos'))
    if departamento.isdigit():
        flash('El nombre del departamento no puede ser solo números.', 'danger')
        return redirect(url_for('departamentos'))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Departamentos SET DEPARTAMENTO = %s WHERE ID_DEPARTAMENTOS = %s", (departamento, id))
    mysql.connection.commit()
    cur.close()
    flash('Departamento editado correctamente.', 'success')
    return redirect(url_for('departamentos'))

# Eliminar departamento
@app.route('/departamentos/eliminar/<int:id>', methods=['POST'])
def eliminar_departamento(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Departamentos WHERE ID_DEPARTAMENTOS = %s", (id,))
        mysql.connection.commit()
        flash('Departamento eliminado exitosamente.', 'success')
    except Exception as e:
        flash('No se puede eliminar este departamento porque está ligado a otros datos.', 'danger')
    cur.close()
    return redirect(url_for('departamentos'))


# --------------------------------------CRUD de ubicaciones----------------------------------------------------------------------
@app.route('/ubicaciones', methods=['GET', 'POST'])
def ubicaciones():
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
    cur.execute("SELECT ID_UBICACIONES, DESCRIPCION, GEOLOCALIZACION, DIRECCION FROM Ubicaciones ORDER BY ID_UBICACIONES ASC")
    ubicaciones = cur.fetchall()
    cur.close()
    return render_template('Ubicaciones/CRUD_Ubicaciones.html', ubicaciones=ubicaciones)

# Editar ubicacion
@app.route('/ubicaciones/editar/<int:id>', methods=['POST'])
def editar_ubicacion(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    descripcion = request.form.get('descripcion')
    geolocalizacion = request.form.get('geolocalizacion')
    direccion = request.form.get('direccion')
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Ubicaciones SET DESCRIPCION = %s, GEOLOCALIZACION = %s, DIRECCION = %s WHERE ID_UBICACIONES = %s", (descripcion, geolocalizacion, direccion, id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('ubicaciones'))

# Eliminar ubicacion
@app.route('/ubicaciones/eliminar/<int:id>', methods=['POST'])
def eliminar_ubicacion(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Ubicaciones WHERE ID_UBICACIONES = %s", (id,))
        mysql.connection.commit()
        flash('Ubicación eliminada exitosamente.', 'success')
    except Exception as e:
        flash('No se puede eliminar esta ubicación porque está ligada a otros datos.', 'danger')
    cur.close()
    return redirect(url_for('ubicaciones'))


# --------------------------------------CRUD de cargos----------------------------------------------------------------------
@app.route('/crud_cargos', methods=['GET', 'POST'])
def crud_cargos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
    cur.execute("""
        SELECT c.ID_CARGOS, c.DESCRIPCION, a.AREA, d.DEPARTAMENTO, c.AREA, c.DEPARTAMENTO
        FROM Cargos c
        LEFT JOIN Areas a ON c.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON c.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.ID_CARGOS ASC
    """)
    cargos = cur.fetchall()
    cur.close()
    return render_template('Cargos/CRUD_Cargos.html', cargos=cargos, areas=areas, departamentos=departamentos)

# Editar cargo
@app.route('/crud_cargos/editar/<int:id>', methods=['POST'])
def editar_cargo(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    descripcion = request.form.get('descripcion')
    area = request.form.get('area')
    departamento = request.form.get('departamento')
    if not descripcion or not area or not departamento:
        flash('Todos los campos son obligatorios.', 'danger')
        return redirect(url_for('crud_cargos'))
    if descripcion.isdigit():
        flash('El nombre del cargo no puede ser solo números.', 'danger')
        return redirect(url_for('crud_cargos'))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Cargos SET DESCRIPCION = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_CARGOS = %s", (descripcion, area, departamento, id))
    mysql.connection.commit()
    cur.close()
    flash('Cargo editado correctamente.', 'success')
    return redirect(url_for('crud_cargos'))

# Eliminar cargo
@app.route('/crud_cargos/eliminar/<int:id>', methods=['POST'])
def eliminar_cargo(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM Cargos WHERE ID_CARGOS = %s", (id,))
        mysql.connection.commit()
        flash('Cargo eliminado exitosamente.', 'success')
    except Exception as e:
        flash('No se puede eliminar este cargo porque está ligado a otros datos.', 'danger')
    cur.close()
    return redirect(url_for('crud_cargos'))


# --------------------------------------CRUD de jerarquía----------------------------------------------------------------------
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


@app.route('/api/colaboradores/<int:colaborador_id>/aprobador', methods=['GET'])
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


@app.route('/jerarquia', methods=['GET', 'POST'])
def crud_jerarquia():
    if 'user_id' not in session:
        return redirect(url_for('login'))

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
    cur.execute("""
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
    """)
    jerarquias = cur.fetchall()
    cur.close()
    return render_template(
        'Jerarquia/CRUD_Jerarquia.html',
        jerarquias=jerarquias,
        cargos=cargos,
        areas=areas,
        departamentos=departamentos,
        plantas=plantas
    )


@app.route('/jerarquia/editar/<int:id>', methods=['POST'])
def editar_jerarquia(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cargo = (request.form.get('cargo') or '').strip()
    superior = (request.form.get('superior_jerarquico') or '').strip()
    departamento = (request.form.get('departamento') or '').strip()
    area = (request.form.get('area') or '').strip()
    planta = (request.form.get('planta') or '').strip()

    if not all([cargo, departamento, area, planta]):
        flash('Cargo, departamento, área y planta son obligatorios.', 'danger')
        return redirect(url_for('crud_jerarquia'))

    try:
        cargo_id = int(cargo)
        departamento_id = int(departamento)
        area_id = int(area)
        superior_id = int(superior) if superior else None
    except ValueError:
        flash('Selecciona opciones válidas para cargo, superior, departamento y área.', 'danger')
        return redirect(url_for('crud_jerarquia'))

    cur = mysql.connection.cursor()
    if superior_id == cargo_id:
        cur.close()
        flash('Un cargo no puede ser su propio superior jerárquico.', 'danger')
        return redirect(url_for('crud_jerarquia'))
    if superior_id is not None and jerarquia_crea_ciclo(
        cur, cargo_id, superior_id, departamento_id, area_id, planta, excluir_id=id
    ):
        cur.close()
        flash('La relación crearía un ciclo en la jerarquía.', 'danger')
        return redirect(url_for('crud_jerarquia'))

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
    return redirect(url_for('crud_jerarquia'))


@app.route('/jerarquia/eliminar/<int:id>', methods=['POST'])
def eliminar_jerarquia(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

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
    return redirect(url_for('crud_jerarquia'))


# --------------------------------------CRUD de colaboradores----------------------------------------------------------------------
@app.route('/crud_colaboradores', methods=['GET', 'POST'])
def crud_colaboradores():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    # Obtener áreas, departamentos, cargos y ubicaciones para los selects
    cur.execute("SELECT ID_AREAS, AREA FROM Areas ORDER BY ID_AREAS ASC")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM Departamentos ORDER BY ID_DEPARTAMENTOS ASC")
    departamentos = cur.fetchall()
    cur.execute("SELECT ID_CARGOS, DESCRIPCION, AREA, DEPARTAMENTO FROM Cargos ORDER BY ID_CARGOS ASC")
    cargos = cur.fetchall()
    # Para JS: lista de objetos {id, nombre, area, departamento}
    cargos_info = [
        {"id": c[0], "nombre": c[1], "area": c[2], "departamento": c[3]} for c in cargos
    ]
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
                flash('Error al agregar colaborador: ' + str(e), 'danger')
    # Leer
    cur.execute("""
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
    """)
    colaboradores = cur.fetchall()
    cur.close()
    return render_template('Colaboradores/CRUD_Colaboradores.html', colaboradores=colaboradores, areas=areas, departamentos=departamentos, cargos=cargos, ubicaciones=ubicaciones, cargos_info=cargos_info)

# Editar colaborador
@app.route('/crud_colaboradores/editar/<int:id>', methods=['POST'])
def editar_colaborador(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    nombre = request.form.get('nombre')
    departamento = request.form.get('departamento')
    area = request.form.get('area')
    cargo = request.form.get('cargo')
    ubicacion = request.form.get('ubicacion')
    estado = (request.form.get('estado') or '').strip().upper()

    # Validaciones básicas
    if not all([nombre, cargo, ubicacion, estado]):
        flash('Todos los campos son obligatorios.', 'danger')
        return redirect(url_for('crud_colaboradores'))
    if estado not in ('ACTIVO', 'AUSENTE'):
        flash('El estado del colaborador no es válido.', 'danger')
        return redirect(url_for('crud_colaboradores'))
    # Validar que el nombre no sea solo números
    if nombre.isdigit():
        flash('El nombre del colaborador no puede ser solo números.', 'danger')
        return redirect(url_for('crud_colaboradores'))

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
            return redirect(url_for('crud_colaboradores'))
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
        flash('Error al editar colaborador: ' + str(e), 'danger')
    cur.close()
    return redirect(url_for('crud_colaboradores'))

# Eliminar colaborador
@app.route('/crud_colaboradores/eliminar/<int:id>', methods=['POST'])
def eliminar_colaborador(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
            flash('Error al eliminar colaborador: ' + str(e), 'danger')
    cur.close()
    return redirect(url_for('crud_colaboradores'))

# --------------------------------------CRUD de extensiones----------------------------------------------------------------------
@app.route('/extensiones', methods=['GET', 'POST'])
def crud_extensiones():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    # Obtener áreas y departamentos para los selects
    cur.execute("SELECT ID_AREAS, AREA FROM Areas ORDER BY ID_AREAS ASC")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM Departamentos ORDER BY ID_DEPARTAMENTOS ASC")
    departamentos = cur.fetchall()
    # Obtener colaboradores para el autocompletado y su info de área y departamento
    cur.execute("""
        SELECT c.ID_COLABORADOR, c.NOMBRE, a.ID_AREAS, a.AREA, d.ID_DEPARTAMENTOS, d.DEPARTAMENTO
        FROM Colaboradores c
        LEFT JOIN Cargos cg ON c.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.ID_COLABORADOR ASC
    """)
    colaboradores_info = []
    colaboradores = []
    for row in cur.fetchall():
        col_id, nombre, area_id, area_nombre, dep_id, dep_nombre = row
        colaboradores.append({'id': col_id, 'nombre': nombre})
        colaboradores_info.append({
            'id': col_id,
            'nombre': nombre,
            'area_id': area_id if area_id is not None else '',
            'area_nombre': area_nombre if area_nombre is not None else '',
            'departamento_id': dep_id if dep_id is not None else '',
            'departamento_nombre': dep_nombre if dep_nombre is not None else ''
        })
    # Crear
    if request.method == 'POST':
        id_colaborador = (request.form.get('id_colaborador') or '').strip()
        extension = (request.form.get('extension') or '').strip()
        area = (request.form.get('area') or '').strip()
        departamento = (request.form.get('departamento') or '').strip()

        if not all((id_colaborador, extension, area, departamento)):
            flash('Selecciona un colaborador con área y departamento, e ingresa su extensión.', 'danger')
            cur.close()
            return redirect(url_for('crud_extensiones'))

        if not all(value.isdigit() for value in (id_colaborador, extension, area, departamento)):
            flash('Colaborador, área, departamento y extensión deben contener valores válidos.', 'danger')
            cur.close()
            return redirect(url_for('crud_extensiones'))

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
            return redirect(url_for('crud_extensiones'))

        if area_id != asignacion[0] or departamento_id != asignacion[1]:
            flash('El área y el departamento deben coincidir con el cargo del colaborador seleccionado.', 'danger')
            cur.close()
            return redirect(url_for('crud_extensiones'))

        try:
            cur.execute(
                "INSERT INTO Extensiones (ID_COLABORADOR, EXTENSION, AREA, DEPARTAMENTO) VALUES (%s, %s, %s, %s)",
                (id_col, ext_val, area_id, departamento_id)
            )
            mysql.connection.commit()
            flash('Extensión agregada correctamente.', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash('Error al agregar la extensión: ' + str(e), 'danger')
    # Leer: mostrar área y departamento actual del colaborador relacionado
    cur.execute("""
        SELECT e.ID_EXTENSIONES, c.NOMBRE, e.EXTENSION, a.AREA, d.DEPARTAMENTO, e.AREA, e.DEPARTAMENTO, e.ID_COLABORADOR
        FROM Extensiones e
        LEFT JOIN Colaboradores c ON e.ID_COLABORADOR = c.ID_COLABORADOR
        LEFT JOIN Areas a ON e.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON e.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY e.ID_EXTENSIONES ASC
    """)
    extensiones = cur.fetchall()
    cur.close()
    return render_template('Extensiones/CRUD_Extensiones.html', extensiones=extensiones, areas=areas, departamentos=departamentos, colaboradores=colaboradores, colaboradores_info=colaboradores_info)

# Editar extension
@app.route('/extensiones/editar/<int:id>', methods=['POST'])
def editar_extension(id):
    # Protección de sesión
    if 'user_id' not in session:
        flash('Debes iniciar sesión para realizar esta acción.', 'warning')
        return redirect(url_for('login'))

    # Obtener valores del formulario
    id_colaborador = (request.form.get('id_colaborador') or '').strip()
    extension = (request.form.get('extension') or '').strip()
    area = (request.form.get('area') or '').strip()
    departamento = (request.form.get('departamento') or '').strip()

    # Validaciones básicas
    if not all((id_colaborador, extension, area, departamento)):
        flash('Selecciona un colaborador con área y departamento, e ingresa su extensión.', 'danger')
        return redirect(url_for('crud_extensiones'))
    if not all(value.isdigit() for value in (id_colaborador, extension, area, departamento)):
        flash('Colaborador, área, departamento y extensión deben contener valores válidos.', 'danger')
        return redirect(url_for('crud_extensiones'))

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
            return redirect(url_for('crud_extensiones'))
        if area_id != asignacion[0] or departamento_id != asignacion[1]:
            flash('El área y el departamento deben coincidir con el cargo del colaborador seleccionado.', 'danger')
            cur.close()
            return redirect(url_for('crud_extensiones'))

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
        flash(f'Ocurrió un error al editar la extensión: {e}', 'danger')

    return redirect(url_for('crud_extensiones'))

# Eliminar extension
@app.route('/extensiones/eliminar/<int:id>', methods=['POST'])
def eliminar_extension(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM Extensiones WHERE ID_EXTENSIONES = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('crud_extensiones'))

# --------------------------------------CRUD de celulares----------------------------------------------------------------------
@app.route('/celulares', methods=['GET', 'POST'])
def crud_celulares():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    # Obtener áreas y departamentos para los selects
    cur.execute("SELECT ID_AREAS, AREA FROM Areas ORDER BY ID_AREAS ASC")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM Departamentos ORDER BY ID_DEPARTAMENTOS ASC")
    departamentos = cur.fetchall()
    # Obtener colaboradores para el autocompletado y su info de área y departamento
    cur.execute("""
        SELECT c.ID_COLABORADOR, c.NOMBRE, a.ID_AREAS, a.AREA, d.ID_DEPARTAMENTOS, d.DEPARTAMENTO
        FROM Colaboradores c
        LEFT JOIN Cargos cg ON c.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.ID_COLABORADOR ASC
    """)
    colaboradores_info = []
    colaboradores = []
    for row in cur.fetchall():
        col_id, nombre, area_id, area_nombre, dep_id, dep_nombre = row
        colaboradores.append({'id': col_id, 'nombre': nombre})
        colaboradores_info.append({
            'id': col_id,
            'nombre': nombre,
            'area_id': area_id if area_id is not None else '',
            'area_nombre': area_nombre if area_nombre is not None else '',
            'departamento_id': dep_id if dep_id is not None else '',
            'departamento_nombre': dep_nombre if dep_nombre is not None else ''
        })
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
                flash('Error al agregar celular: ' + str(e), 'danger')
    # Leer: mostrar área y departamento actual del colaborador relacionado
    cur.execute("""
        SELECT c.ID_CELULARES, col.NOMBRE, c.CELULAR, a.AREA, d.DEPARTAMENTO, cg.AREA, cg.DEPARTAMENTO, c.ID_COLABORADOR
        FROM Celulares c
        LEFT JOIN Colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.ID_CELULARES ASC
    """)
    celulares = cur.fetchall()
    cur.close()
    return render_template('Celulares/CRUD_Celulares.html', celulares=celulares, areas=areas, departamentos=departamentos, colaboradores=colaboradores, colaboradores_info=colaboradores_info)

# Editar celular
@app.route('/celulares/editar/<int:id>', methods=['POST'])
def editar_celular(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    id_colaborador = request.form.get('id_colaborador')
    celular = request.form.get('celular')
    area = request.form.get('area')
    departamento = request.form.get('departamento')
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Celulares SET ID_COLABORADOR = %s, CELULAR = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_CELULARES = %s", (id_colaborador, celular, area, departamento, id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('crud_celulares'))

# Eliminar celular
@app.route('/celulares/eliminar/<int:id>', methods=['POST'])
def eliminar_celular(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM Celulares WHERE ID_CELULARES = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('crud_celulares'))


# --------------------------------------CRUD de correos----------------------------------------------------------------------
@app.route('/correos', methods=['GET', 'POST'])
def crud_correos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    # Obtener áreas y departamentos para los selects
    cur.execute("SELECT ID_AREAS, AREA FROM Areas ORDER BY ID_AREAS ASC")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM Departamentos ORDER BY ID_DEPARTAMENTOS ASC")
    departamentos = cur.fetchall()
    # Obtener colaboradores para el autocompletado y su info de área y departamento
    cur.execute("""
        SELECT c.ID_COLABORADOR, c.NOMBRE, a.ID_AREAS, a.AREA, d.ID_DEPARTAMENTOS, d.DEPARTAMENTO
        FROM Colaboradores c
        LEFT JOIN Cargos cg ON c.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.ID_COLABORADOR ASC
    """)
    colaboradores_info = []
    colaboradores = []
    for row in cur.fetchall():
        col_id, nombre, area_id, area_nombre, dep_id, dep_nombre = row
        colaboradores.append({'id': col_id, 'nombre': nombre})
        colaboradores_info.append({
            'id': col_id,
            'nombre': nombre,
            'area_id': area_id if area_id is not None else '',
            'area_nombre': area_nombre if area_nombre is not None else '',
            'departamento_id': dep_id if dep_id is not None else '',
            'departamento_nombre': dep_nombre if dep_nombre is not None else ''
        })
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
                flash('Error al agregar correo: ' + str(e), 'danger')
    # Leer: mostrar área y departamento actual del cargo del colaborador relacionado
    cur.execute("""
        SELECT c.ID_CORREOS, col.NOMBRE, c.CORREO, a.AREA, d.DEPARTAMENTO, c.ID_COLABORADOR
        FROM Correos c
        LEFT JOIN Colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADOR
        LEFT JOIN Cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN Areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN Departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.ID_CORREOS ASC
    """)
    correos = cur.fetchall()
    cur.close()
    return render_template('Correos/CRUD_Correos.html', correos=correos, areas=areas, departamentos=departamentos, colaboradores=colaboradores, colaboradores_info=colaboradores_info)

# Editar correo
@app.route('/correos/editar/<int:id>', methods=['POST'])
def editar_correo(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    id_colaborador = request.form.get('id_colaborador')
    correo = request.form.get('correo')
    area = request.form.get('area')
    departamento = request.form.get('departamento')
    import re
    # Validación de formato de correo
    correo_regex = r'^([A-Za-z][A-Za-z0-9_.+-]*)@((farbiopharma|inpelab)\.com)$'
    if not correo or '@' not in correo:
        flash('El correo debe contener el separador @.', 'danger')
        return redirect(url_for('crud_correos'))
    usuario, sep, dominio = correo.partition('@')
    if usuario.isdigit():
        flash('El nombre de usuario del correo no puede contener solo números.', 'danger')
        return redirect(url_for('crud_correos'))
    if dominio not in ['farbiopharma.com', 'inpelab.com']:
        flash('El dominio del correo debe ser farbiopharma.com o inpelab.com.', 'danger')
        return redirect(url_for('crud_correos'))
    # Validación extra con regex
    if not re.match(correo_regex, correo):
        flash('El formato del correo no es válido.', 'danger')
        return redirect(url_for('crud_correos'))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Correos SET ID_COLABORADOR = %s, CORREO = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_CORREOS = %s", (id_colaborador, correo, area, departamento, id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('crud_correos'))

# Eliminar correo
@app.route('/correos/eliminar/<int:id>', methods=['POST'])
def eliminar_correo(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM Correos WHERE ID_CORREOS = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('crud_correos'))


# --------------------------------------CRUD de empresas----------------------------------------------------------------------
@app.route('/empresas', methods=['GET', 'POST'])
def crud_empresas():
    if 'user_id' not in session:
        return redirect(url_for('login'))

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

    cur.execute("SELECT ID_EMPRESA, NOMBRE FROM Empresas ORDER BY ID_EMPRESA ASC")
    empresas = cur.fetchall()
    cur.close()
    return render_template('Empresas/CRUD_Empresas.html', empresas=empresas)


@app.route('/empresas/editar/<int:id>', methods=['POST'])
def editar_empresa(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    nombre = (request.form.get('nombre') or '').strip()
    if not nombre:
        flash('El nombre de la empresa es obligatorio.', 'danger')
        return redirect(url_for('crud_empresas'))

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
    return redirect(url_for('crud_empresas'))


@app.route('/empresas/eliminar/<int:id>', methods=['POST'])
def eliminar_empresa(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

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
    return redirect(url_for('crud_empresas'))


# --------------------------------------CRUD de vehículos----------------------------------------------------------------------
@app.route('/vehiculos', methods=['GET', 'POST'])
def crud_vehiculos():
    if 'user_id' not in session:
        return redirect(url_for('login'))

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
    cur.execute("""
        SELECT ID_VEHICULOS, PLACA, MARCA, MODELO, COLOR, CONDUCTOR_ASIGNADO
        FROM Vehiculos
        ORDER BY ID_VEHICULOS ASC
    """)
    vehiculos = cur.fetchall()
    cur.close()
    return render_template('Vehiculos/CRUD_Vehiculos.html', vehiculos=vehiculos)


@app.route('/vehiculos/editar/<int:id>', methods=['POST'])
def editar_vehiculo(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    placa = (request.form.get('placa') or '').strip().upper()
    marca = (request.form.get('marca') or '').strip()
    modelo = (request.form.get('modelo') or '').strip()
    color = (request.form.get('color') or '').strip()
    conductor = (request.form.get('conductor_asignado') or '').strip() or None

    if not all([placa, marca, modelo, color]):
        flash('Placa, marca, modelo y color son obligatorios.', 'danger')
        return redirect(url_for('crud_vehiculos'))

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
    return redirect(url_for('crud_vehiculos'))


@app.route('/vehiculos/eliminar/<int:id>', methods=['POST'])
def eliminar_vehiculo(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

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
    return redirect(url_for('crud_vehiculos'))




if __name__ == "__main__":
    print("🚀 Iniciando servidor Flask...")
    wait_for_db()
    print("✅ Servidor listo para recibir conexiones")
    app.run(host='0.0.0.0', debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')
