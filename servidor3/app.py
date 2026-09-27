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

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
import bcrypt
import os
import socket
import time

app = Flask(__name__)

# Configuración de la aplicación
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "tu_clave_secreta_aqui")

# Configuración de la base de datos MySQL
app.config['MYSQL_HOST'] = os.getenv("MYSQL_HOST", "maestro1")
app.config['MYSQL_USER'] = os.getenv("MYSQL_USER", "root")
app.config['MYSQL_PASSWORD'] = os.getenv("MYSQL_PASSWORD", "F4rb10PH4rm4")
app.config['MYSQL_DB'] = os.getenv("MYSQL_DB", "db_informacion")
app.config['MYSQL_PORT'] = int(os.getenv("MYSQL_PORT", 3306))

# Inicializar la base de datos
mysql = MySQL(app)

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

def init_db():
    """Inicializar las tablas de la base de datos"""
    with app.app_context():
        cur = mysql.connection.cursor()
        
        # Crear tabla de usuarios
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Crear tabla de áreas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS areas (
                ID_AREAS INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                AREA VARCHAR(100) NOT NULL
            )
        """)

        # Crear tabla de departamentos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS departamentos (
                ID_DEPARTAMENTOS INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                DEPARTAMENTO VARCHAR(100) NOT NULL
            )
        """)

        # Crear tabla de ubicaciones
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ubicaciones (
                ID_UBICACIONES INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                DESCRIPCION VARCHAR(150) NOT NULL,
                GEOLOCALIZACION VARCHAR(100) NOT NULL,
                DIRECCION VARCHAR(100) NOT NULL
            )
        """)

        # Crear tabla de cargos relacionada con áreas y departamentos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cargos (
                ID_CARGOS INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                DESCRIPCION VARCHAR(150) NOT NULL,
                AREA INT DEFAULT NULL,
                DEPARTAMENTO INT DEFAULT NULL,
                KEY AREA (AREA),
                KEY DEPARTAMENTO (DEPARTAMENTO),
                CONSTRAINT cargos_ibfk_1 FOREIGN KEY (AREA) REFERENCES areas (ID_AREAS),
                CONSTRAINT cargos_ibfk_2 FOREIGN KEY (DEPARTAMENTO) REFERENCES departamentos (ID_DEPARTAMENTOS)
            )
        """)

        # Crear tabla de colaboradores relacionada con áreas, departamentos, cargos y ubicaciones
        cur.execute("""
            CREATE TABLE IF NOT EXISTS colaboradores (
                ID_COLABORADORES INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                NOMBRE VARCHAR(100) NOT NULL,
                DEPARTAMENTO INT DEFAULT NULL,
                AREA INT DEFAULT NULL,
                CARGO INT DEFAULT NULL,
                UBICACION INT DEFAULT NULL,
                KEY NOMBRE (NOMBRE),
                KEY DEPARTAMENTO (DEPARTAMENTO),
                KEY AREA (AREA),
                KEY CARGO (CARGO),
                KEY UBICACION (UBICACION),
                CONSTRAINT colaboradores_ibfk_1 FOREIGN KEY (DEPARTAMENTO) REFERENCES departamentos (ID_DEPARTAMENTOS),
                CONSTRAINT colaboradores_ibfk_2 FOREIGN KEY (AREA) REFERENCES areas (ID_AREAS),
                CONSTRAINT colaboradores_ibfk_3 FOREIGN KEY (CARGO) REFERENCES cargos (ID_CARGOS),
                CONSTRAINT colaboradores_ibfk_4 FOREIGN KEY (UBICACION) REFERENCES ubicaciones (ID_UBICACIONES)
            )
        """)


        # Crear tabla de extensiones relacionada con áreas, departamentos y colaboradores (por ID)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS extensiones (
                ID_EXTENSIONES INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                ID_COLABORADOR INT NOT NULL,
                EXTENSION INT NOT NULL,
                AREA INT DEFAULT NULL,
                DEPARTAMENTO INT DEFAULT NULL,
                KEY AREA (AREA),
                KEY DEPARTAMENTO (DEPARTAMENTO),
                KEY ID_COLABORADOR (ID_COLABORADOR),
                CONSTRAINT extensiones_ibfk_1 FOREIGN KEY (AREA) REFERENCES areas (ID_AREAS),
                CONSTRAINT extensiones_ibfk_2 FOREIGN KEY (DEPARTAMENTO) REFERENCES departamentos (ID_DEPARTAMENTOS),
                CONSTRAINT extensiones_ibfk_3 FOREIGN KEY (ID_COLABORADOR) REFERENCES colaboradores (ID_COLABORADORES)
            )
        """)

        # Crear tabla de celulares relacionada con áreas, departamentos y colaboradores (por ID)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS celulares (
                ID_CELULARES INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                ID_COLABORADOR INT NOT NULL,
                CELULAR BIGINT NOT NULL,
                AREA INT NOT NULL,
                DEPARTAMENTO INT NOT NULL,
                KEY AREA (AREA),
                KEY DEPARTAMENTO (DEPARTAMENTO),
                KEY ID_COLABORADOR (ID_COLABORADOR),
                CONSTRAINT celulares_ibfk_1 FOREIGN KEY (AREA) REFERENCES areas (ID_AREAS),
                CONSTRAINT celulares_ibfk_2 FOREIGN KEY (DEPARTAMENTO) REFERENCES departamentos (ID_DEPARTAMENTOS),
                CONSTRAINT celulares_ibfk_3 FOREIGN KEY (ID_COLABORADOR) REFERENCES colaboradores (ID_COLABORADORES)
            )
        """)

        # Crear tabla de correos relacionada con áreas, departamentos y colaboradores (por ID)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS correos (
                ID_CORREOS INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                ID_COLABORADOR INT NOT NULL,
                CORREO VARCHAR(50) NOT NULL,
                AREA INT NOT NULL,
                DEPARTAMENTO INT NOT NULL,
                KEY AREA (AREA),
                KEY DEPARTAMENTO (DEPARTAMENTO),
                KEY ID_COLABORADOR (ID_COLABORADOR),
                CONSTRAINT correos_ibfk_1 FOREIGN KEY (AREA) REFERENCES areas (ID_AREAS),
                CONSTRAINT correos_ibfk_2 FOREIGN KEY (DEPARTAMENTO) REFERENCES departamentos (ID_DEPARTAMENTOS),
                CONSTRAINT correos_ibfk_3 FOREIGN KEY (ID_COLABORADOR) REFERENCES colaboradores (ID_COLABORADORES)
            )
        """)
        
        
        
        mysql.connection.commit()
        cur.close()

@app.route('/')
def index():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT e.ID_EXTENSIONES, c.NOMBRE, e.EXTENSION, a.AREA, d.DEPARTAMENTO, e.AREA, e.DEPARTAMENTO, e.ID_COLABORADOR
        FROM extensiones e
        LEFT JOIN colaboradores c ON e.ID_COLABORADOR = c.ID_COLABORADORES
        LEFT JOIN areas a ON e.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON e.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.NOMBRE
    """)
    extensiones = cur.fetchall()
    cur.close()
    return render_template('DTelefonico/VExtensiones/Extensiones.html', extensiones=extensiones)
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Límite de intentos por sesión
        if 'login_attempts' not in session:
            session['login_attempts'] = 0
        import time
        bloqueado = False
        if session.get('login_blocked_until'):
            if time.time() < session['login_blocked_until']:
                bloqueado = True
        if session['login_attempts'] >= 5 or bloqueado:
            if not bloqueado:
                session['login_blocked_until'] = time.time() + 5*60
            restante = int(session['login_blocked_until'] - time.time())
            minutos = restante // 60
            segundos = restante % 60
            flash(f'Has superado el límite de intentos. Intenta nuevamente en {minutos}m {segundos}s.', 'danger')
            return render_template('Login/login.html')
        if not username or not password:
            flash('Por favor, complete todos los campos', 'error')
            return render_template('Login/login.html')
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, username, password_hash FROM usuarios WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['login_attempts'] = 0
            session.pop('login_blocked_until', None)
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('menu'))
        else:
            session['login_attempts'] += 1
            intentos_restantes = 5 - session['login_attempts']
            flash(f'Usuario o contraseña incorrectos. Intentos restantes: {intentos_restantes}', 'error')
        return render_template('Login/login.html')
    # Limpiar mensajes flash previos (de otras vistas) al mostrar el login
    session.pop('_flashes', None)
    return render_template('Login/login.html')

@app.route('/menu')
def menu():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('menu.html')
    


 # --------------------------------------Registro----------------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([username, email, password, confirm_password]):
            flash('Por favor, complete todos los campos', 'error')
            return render_template('Login/register.html')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('Login/register.html')
        
        # Verificar si el usuario ya existe
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM usuarios WHERE username = %s OR email = %s", (username, email))
        existing_user = cur.fetchone()
        
        if existing_user:
            flash('El usuario o email ya existe', 'error')
            cur.close()
            return render_template('Login/register.html')
        
        # Crear hash de la contraseña
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insertar nuevo usuario
        cur.execute("INSERT INTO usuarios (username, email, password_hash) VALUES (%s, %s, %s)", 
                   (username, email, password_hash))
        mysql.connection.commit()
        cur.close()
        
        flash('Usuario registrado exitosamente', 'success')
        return redirect(url_for('login'))
    
    # Limpiar mensajes flash previos (por ejemplo, de login)
    session.pop('_flashes', None)
    return render_template('Login/register.html')

 # --------------------------------------Cerrar sesión----------------------------------------------------------------------

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('login'))



 # --------------------------------------Directorio Telefonico----------------------------------------------------------------------

# Ruta para mostrar la vista de extensiones
@app.route('/vextensiones')
def vextensiones():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT e.ID_EXTENSIONES, col.NOMBRE, e.EXTENSION, a.AREA, d.DEPARTAMENTO, e.ID_COLABORADOR
        FROM extensiones e
        LEFT JOIN colaboradores col ON e.ID_COLABORADOR = col.ID_COLABORADORES
        LEFT JOIN areas a ON col.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON col.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY col.NOMBRE
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
        FROM celulares c
        LEFT JOIN colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADORES
        LEFT JOIN cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY col.NOMBRE
    """)
    celulares = cur.fetchall()
    cur.close()
    return render_template('DTelefonico/VCelulares/Celulares.html', celulares=celulares)

@app.route('/vcorreos')
def vcorreos():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.ID_CORREOS, col.NOMBRE, c.CORREO, a.AREA, d.DEPARTAMENTO, c.ID_COLABORADOR
        FROM correos c
        LEFT JOIN colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADORES
        LEFT JOIN cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY col.NOMBRE
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
                cur.execute("INSERT INTO areas (AREA) VALUES (%s)", (area,))
                mysql.connection.commit()
                flash('Área agregada correctamente.', 'success')
        else:
            flash('El campo área es obligatorio.', 'danger')
    # Leer
    cur.execute("SELECT ID_AREAS, AREA FROM areas ORDER BY AREA")
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
    cur.execute("UPDATE areas SET AREA = %s WHERE ID_AREAS = %s", (area, id))
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
        cur.execute("DELETE FROM areas WHERE ID_AREAS = %s", (id,))
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
                cur.execute("INSERT INTO departamentos (DEPARTAMENTO) VALUES (%s)", (departamento,))
                mysql.connection.commit()
                flash('Departamento agregado correctamente.', 'success')
        else:
            flash('El campo departamento es obligatorio.', 'danger')
    # Leer
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM departamentos ORDER BY DEPARTAMENTO")
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
    cur.execute("UPDATE departamentos SET DEPARTAMENTO = %s WHERE ID_DEPARTAMENTOS = %s", (departamento, id))
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
        cur.execute("DELETE FROM departamentos WHERE ID_DEPARTAMENTOS = %s", (id,))
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
            cur.execute("INSERT INTO ubicaciones (DESCRIPCION, GEOLOCALIZACION, DIRECCION) VALUES (%s, %s, %s)", (descripcion, geolocalizacion, direccion))
            mysql.connection.commit()
    # Leer
    cur.execute("SELECT ID_UBICACIONES, DESCRIPCION, GEOLOCALIZACION, DIRECCION FROM ubicaciones ORDER BY DESCRIPCION")
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
    cur.execute("UPDATE ubicaciones SET DESCRIPCION = %s, GEOLOCALIZACION = %s, DIRECCION = %s WHERE ID_UBICACIONES = %s", (descripcion, geolocalizacion, direccion, id))
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
        cur.execute("DELETE FROM ubicaciones WHERE ID_UBICACIONES = %s", (id,))
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
    cur.execute("SELECT ID_AREAS, AREA FROM areas ORDER BY AREA")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM departamentos ORDER BY DEPARTAMENTO")
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
            cur.execute("INSERT INTO cargos (DESCRIPCION, AREA, DEPARTAMENTO) VALUES (%s, %s, %s)", (descripcion, area, departamento))
            mysql.connection.commit()
            flash('Cargo agregado correctamente.', 'success')
    # Leer
    cur.execute("""
        SELECT c.ID_CARGOS, c.DESCRIPCION, a.AREA, d.DEPARTAMENTO, c.AREA, c.DEPARTAMENTO
        FROM cargos c
        LEFT JOIN areas a ON c.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON c.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.DESCRIPCION
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
    cur.execute("UPDATE cargos SET DESCRIPCION = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_CARGOS = %s", (descripcion, area, departamento, id))
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
        cur.execute("DELETE FROM cargos WHERE ID_CARGOS = %s", (id,))
        mysql.connection.commit()
        flash('Cargo eliminado exitosamente.', 'success')
    except Exception as e:
        flash('No se puede eliminar este cargo porque está ligado a otros datos.', 'danger')
    cur.close()
    return redirect(url_for('crud_cargos'))


# --------------------------------------CRUD de colaboradores----------------------------------------------------------------------
@app.route('/crud_colaboradores', methods=['GET', 'POST'])
def crud_colaboradores():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    # Obtener áreas, departamentos, cargos y ubicaciones para los selects
    cur.execute("SELECT ID_AREAS, AREA FROM areas ORDER BY AREA")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM departamentos ORDER BY DEPARTAMENTO")
    departamentos = cur.fetchall()
    cur.execute("SELECT ID_CARGOS, DESCRIPCION, AREA, DEPARTAMENTO FROM cargos ORDER BY DESCRIPCION")
    cargos = cur.fetchall()
    # Para JS: lista de objetos {id, nombre, area, departamento}
    cargos_info = [
        {"id": c[0], "nombre": c[1], "area": c[2], "departamento": c[3]} for c in cargos
    ]
    cur.execute("SELECT ID_UBICACIONES, DESCRIPCION FROM ubicaciones ORDER BY DESCRIPCION")
    ubicaciones = cur.fetchall()
    # Crear
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        departamento = request.form.get('departamento')
        area = request.form.get('area')
        cargo = request.form.get('cargo')
        ubicacion = request.form.get('ubicacion')
        if not all([nombre, departamento, area, cargo, ubicacion]):
            flash('Todos los campos son obligatorios.', 'danger')
        else:
            try:
                cur.execute("INSERT INTO colaboradores (NOMBRE, DEPARTAMENTO, AREA, CARGO, UBICACION) VALUES (%s, %s, %s, %s, %s)",
                            (nombre, departamento, area, cargo, ubicacion))
                mysql.connection.commit()
                flash('Colaborador agregado exitosamente.', 'success')
            except Exception as e:
                mysql.connection.rollback()
                flash('Error al agregar colaborador: ' + str(e), 'danger')
    # Leer
    cur.execute("""
        SELECT col.ID_COLABORADORES, col.NOMBRE,
               d.DEPARTAMENTO, a.AREA, c.DESCRIPCION, u.DESCRIPCION,
               c.DEPARTAMENTO, c.AREA, col.CARGO, col.UBICACION
        FROM colaboradores col
        LEFT JOIN cargos c ON col.CARGO = c.ID_CARGOS
        LEFT JOIN areas a ON c.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON c.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        LEFT JOIN ubicaciones u ON col.UBICACION = u.ID_UBICACIONES
        ORDER BY col.NOMBRE
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

    # Validaciones básicas
    if not all([nombre, departamento, area, cargo, ubicacion]):
        flash('Todos los campos son obligatorios.', 'danger')
        return redirect(url_for('crud_colaboradores'))
    # Validar que el nombre no sea solo números
    if nombre.isdigit():
        flash('El nombre del colaborador no puede ser solo números.', 'danger')
        return redirect(url_for('crud_colaboradores'))

    # Si cargo no es un número (ID), buscar el ID por nombre
    if not cargo.isdigit():
        cur = mysql.connection.cursor()
        cur.execute("SELECT ID_CARGOS FROM cargos WHERE DESCRIPCION = %s", (cargo,))
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
        # Obtener el nombre anterior del colaborador
        cur.execute("SELECT NOMBRE FROM colaboradores WHERE ID_COLABORADORES = %s", (id,))
        old_row = cur.fetchone()
        old_nombre = old_row[0] if old_row else None
        # Si el nombre cambió, actualizar en cascada en las tablas relacionadas
        if old_nombre and old_nombre != nombre:
            # Ya no es necesario actualizar NOMBRE en tablas relacionadas, solo en colaboradores
            pass
        # Actualizar colaborador
        cur.execute("UPDATE colaboradores SET NOMBRE = %s, DEPARTAMENTO = %s, AREA = %s, CARGO = %s, UBICACION = %s WHERE ID_COLABORADORES = %s",
                    (nombre, departamento, area, cargo, ubicacion, id))
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
        cur.execute("DELETE FROM colaboradores WHERE ID_COLABORADORES = %s", (id,))
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
    cur.execute("SELECT ID_AREAS, AREA FROM areas ORDER BY AREA")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM departamentos ORDER BY DEPARTAMENTO")
    departamentos = cur.fetchall()
    # Obtener colaboradores para el autocompletado y su info de área y departamento
    cur.execute("""
        SELECT c.ID_COLABORADORES, c.NOMBRE, a.ID_AREAS, a.AREA, d.ID_DEPARTAMENTOS, d.DEPARTAMENTO
        FROM colaboradores c
        LEFT JOIN cargos cg ON c.CARGO = cg.ID_CARGOS
        LEFT JOIN areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.NOMBRE
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

        # Validaciones y normalizaciones: convertir cadenas vacías a None para insert NULL
        if not id_colaborador:
            flash('Debes seleccionar un colaborador válido antes de agregar la extensión.', 'danger')
            cur.close()
            return redirect(url_for('crud_extensiones'))

        try:
            id_col = int(id_colaborador)
        except Exception:
            flash('ID de colaborador inválido.', 'danger')
            cur.close()
            return redirect(url_for('crud_extensiones'))

        try:
            ext_val = int(extension)
        except Exception:
            flash('La extensión debe ser un número válido.', 'danger')
            cur.close()
            return redirect(url_for('crud_extensiones'))

        area_val = None
        if area != '':
            try:
                area_val = int(area)
            except Exception:
                # si no es un entero válido, lo ignoramos y lo dejamos NULL
                area_val = None

        departamento_val = None
        if departamento != '':
            try:
                departamento_val = int(departamento)
            except Exception:
                departamento_val = None

        try:
            cur.execute(
                "INSERT INTO extensiones (ID_COLABORADOR, EXTENSION, AREA, DEPARTAMENTO) VALUES (%s, %s, %s, %s)",
                (id_col, ext_val, area_val, departamento_val)
            )
            mysql.connection.commit()
            flash('Extensión agregada correctamente.', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash('Error al agregar la extensión: ' + str(e), 'danger')
    # Leer: mostrar área y departamento actual del colaborador relacionado
    cur.execute("""
        SELECT e.ID_EXTENSIONES, c.NOMBRE, e.EXTENSION, a.AREA, d.DEPARTAMENTO, cg.AREA, cg.DEPARTAMENTO, e.ID_COLABORADOR
        FROM extensiones e
        LEFT JOIN colaboradores c ON e.ID_COLABORADOR = c.ID_COLABORADORES
        LEFT JOIN cargos cg ON c.CARGO = cg.ID_CARGOS
        LEFT JOIN areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.NOMBRE
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
    id_colaborador = request.form.get('id_colaborador', '').strip()
    extension = request.form.get('extension', '').strip()
    area = request.form.get('area', '').strip()
    departamento = request.form.get('departamento', '').strip()

    # Validaciones básicas
    if not extension:
        flash('La extensión no puede estar vacía.', 'danger')
        return redirect(url_for('crud_extensiones'))
    if not extension.isdigit():
        flash('La extensión debe ser un número válido.', 'danger')
        return redirect(url_for('crud_extensiones'))

    # Si el id_colaborador viene vacío o no numérico, conservar el actual de la fila
    if not id_colaborador or not id_colaborador.isdigit():
        cur = mysql.connection.cursor()
        cur.execute("SELECT ID_COLABORADOR FROM extensiones WHERE ID_EXTENSIONES = %s", (id,))
        row = cur.fetchone()
        cur.close()
        if row and row[0] is not None:
            id_colaborador = row[0]
        else:
            flash('No se pudo determinar el colaborador asociado a la extensión.', 'danger')
            return redirect(url_for('crud_extensiones'))

    # Normalizar valores opcionales (usar NULL en BD si vacío)
    area_val = area if area != '' else None
    dep_val = departamento if departamento != '' else None

    # Ejecutar actualización
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE extensiones SET ID_COLABORADOR = %s, EXTENSION = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_EXTENSIONES = %s",
            (id_colaborador, int(extension), area_val, dep_val, id)
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
    cur.execute("DELETE FROM extensiones WHERE ID_EXTENSIONES = %s", (id,))
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
    cur.execute("SELECT ID_AREAS, AREA FROM areas ORDER BY AREA")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM departamentos ORDER BY DEPARTAMENTO")
    departamentos = cur.fetchall()
    # Obtener colaboradores para el autocompletado y su info de área y departamento
    cur.execute("""
        SELECT c.ID_COLABORADORES, c.NOMBRE, a.ID_AREAS, a.AREA, d.ID_DEPARTAMENTOS, d.DEPARTAMENTO
        FROM colaboradores c
        LEFT JOIN cargos cg ON c.CARGO = cg.ID_CARGOS
        LEFT JOIN areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.NOMBRE
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
                cur.execute("INSERT INTO celulares (ID_COLABORADOR, CELULAR, AREA, DEPARTAMENTO) VALUES (%s, %s, %s, %s)", (id_colaborador, celular, area, departamento))
                mysql.connection.commit()
                flash('Celular agregado correctamente.', 'success')
            except Exception as e:
                mysql.connection.rollback()
                flash('Error al agregar celular: ' + str(e), 'danger')
    # Leer: mostrar área y departamento actual del colaborador relacionado
    cur.execute("""
        SELECT c.ID_CELULARES, col.NOMBRE, c.CELULAR, a.AREA, d.DEPARTAMENTO, cg.AREA, cg.DEPARTAMENTO, c.ID_COLABORADOR
        FROM celulares c
        LEFT JOIN colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADORES
        LEFT JOIN cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY col.NOMBRE
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
    cur.execute("UPDATE celulares SET ID_COLABORADOR = %s, CELULAR = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_CELULARES = %s", (id_colaborador, celular, area, departamento, id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('crud_celulares'))

# Eliminar celular
@app.route('/celulares/eliminar/<int:id>', methods=['POST'])
def eliminar_celular(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM celulares WHERE ID_CELULARES = %s", (id,))
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
    cur.execute("SELECT ID_AREAS, AREA FROM areas ORDER BY AREA")
    areas = cur.fetchall()
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO FROM departamentos ORDER BY DEPARTAMENTO")
    departamentos = cur.fetchall()
    # Obtener colaboradores para el autocompletado y su info de área y departamento
    cur.execute("""
        SELECT c.ID_COLABORADORES, c.NOMBRE, a.ID_AREAS, a.AREA, d.ID_DEPARTAMENTOS, d.DEPARTAMENTO
        FROM colaboradores c
        LEFT JOIN cargos cg ON c.CARGO = cg.ID_CARGOS
        LEFT JOIN areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.NOMBRE
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
                cur.execute("INSERT INTO correos (ID_COLABORADOR, CORREO, AREA, DEPARTAMENTO) VALUES (%s, %s, %s, %s)", (id_colaborador, correo, area, departamento))
                mysql.connection.commit()
                flash('Correo agregado correctamente.', 'success')
            except Exception as e:
                mysql.connection.rollback()
                flash('Error al agregar correo: ' + str(e), 'danger')
    # Leer: mostrar área y departamento actual del cargo del colaborador relacionado
    cur.execute("""
        SELECT c.ID_CORREOS, col.NOMBRE, c.CORREO, a.AREA, d.DEPARTAMENTO, c.ID_COLABORADOR
        FROM correos c
        LEFT JOIN colaboradores col ON c.ID_COLABORADOR = col.ID_COLABORADORES
        LEFT JOIN cargos cg ON col.CARGO = cg.ID_CARGOS
        LEFT JOIN areas a ON cg.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON cg.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY col.NOMBRE
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
    cur.execute("UPDATE correos SET ID_COLABORADOR = %s, CORREO = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_CORREOS = %s", (id_colaborador, correo, area, departamento, id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('crud_correos'))

# Eliminar correo
@app.route('/correos/eliminar/<int:id>', methods=['POST'])
def eliminar_correo(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM correos WHERE ID_CORREOS = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('crud_correos'))




if __name__ == "__main__":
    print("🚀 Iniciando servidor Flask...")
    wait_for_db()
    init_db()
    print("✅ Servidor listo para recibir conexiones")
    app.run(host='0.0.0.0', debug=True)
