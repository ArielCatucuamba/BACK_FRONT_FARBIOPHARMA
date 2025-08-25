

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
app.config['MYSQL_HOST'] = os.getenv("*********", "**********")
app.config['MYSQL_USER'] = os.getenv("********", "********")
app.config['MYSQL_PASSWORD'] = os.getenv("********", "********")
app.config['MYSQL_DB'] = os.getenv("********", "********")
app.config['MYSQL_PORT'] = int(os.getenv("********", 3306))


# Inicializar la base de datos
mysql = MySQL(app)

def wait_for_db():
    """Esperar a que la base de datos esté disponible"""
    max_retries = 30
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
            print(f"⏳ Esperando base de datos... intento {retry_count}/{max_retries}")
            time.sleep(2)
    
    raise Exception("❌ No se pudo conectar a la base de datos después de varios intentos")

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
                AREA VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                NOMBRES VARCHAR(100) NOT NULL,
                APELLIDOS VARCHAR(100) NOT NULL,
                DEPARTAMENTO INT DEFAULT NULL,
                AREA INT DEFAULT NULL,
                CARGO INT DEFAULT NULL,
                UBICACION INT DEFAULT NULL,
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

        # Crear tabla de extensiones relacionada con áreas y departamentos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS extensiones (
                ID_EXTENSIONES INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                NOMBRE VARCHAR(100) NOT NULL,
                EXTENSION INT NOT NULL,
                AREA INT DEFAULT NULL,
                DEPARTAMENTO INT DEFAULT NULL,
                KEY AREA (AREA),
                KEY DEPARTAMENTO (DEPARTAMENTO),
                CONSTRAINT extensiones_ibfk_1 FOREIGN KEY (AREA) REFERENCES areas (ID_AREAS),
                CONSTRAINT extensiones_ibfk_2 FOREIGN KEY (DEPARTAMENTO) REFERENCES departamentos (ID_DEPARTAMENTOS)
            )
        """)

        # Crear tabla de celulares relacionada con áreas y departamentos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS celulares (
                ID_CELULARES INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                NOMBRE VARCHAR(100) NOT NULL,
                CELULAR BIGINT NOT NULL,
                AREA INT NOT NULL,
                DEPARTAMENTO INT NOT NULL,
                KEY AREA (AREA),
                KEY DEPARTAMENTO (DEPARTAMENTO),
                CONSTRAINT celulares_ibfk_1 FOREIGN KEY (AREA) REFERENCES areas (ID_AREAS),
                CONSTRAINT celulares_ibfk_2 FOREIGN KEY (DEPARTAMENTO) REFERENCES departamentos (ID_DEPARTAMENTOS)
            )
        """)

        # Crear tabla de correos relacionada con áreas y departamentos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS correos (
                ID_CORREOS INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                NOMBRE VARCHAR(100) NOT NULL,
                CORREO VARCHAR(50) NOT NULL,
                AREA INT NOT NULL,
                DEPARTAMENTO INT NOT NULL,
                KEY AREA (AREA),
                KEY DEPARTAMENTO (DEPARTAMENTO),
                CONSTRAINT correos_ibfk_1 FOREIGN KEY (AREA) REFERENCES areas (ID_AREAS),
                CONSTRAINT correos_ibfk_2 FOREIGN KEY (DEPARTAMENTO) REFERENCES departamentos (ID_DEPARTAMENTOS)
            )
        """)
        
        
        
        mysql.connection.commit()
        cur.close()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    servidor_info = "Servidor 3"
    return render_template('Areas/CRUD_Areas.html', servidor_info=servidor_info)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
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
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('menu'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    return render_template('Login/login.html')

@app.route('/menu')
def menu():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('menu.html')


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
    
    return render_template('Login/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('login'))




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
            cur.execute("INSERT INTO areas (AREA) VALUES (%s)", (area,))
            mysql.connection.commit()
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
    cur = mysql.connection.cursor()
    cur.execute("UPDATE areas SET AREA = %s WHERE ID_AREAS = %s", (area, id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('crud_areas'))

# Eliminar área
@app.route('/crud_areas/eliminar/<int:id>', methods=['POST'])
def eliminar_area(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM areas WHERE ID_AREAS = %s", (id,))
    mysql.connection.commit()
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
            cur.execute("INSERT INTO departamentos (DEPARTAMENTO) VALUES (%s)", (departamento,))
            mysql.connection.commit()
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
    cur = mysql.connection.cursor()
    cur.execute("UPDATE departamentos SET DEPARTAMENTO = %s WHERE ID_DEPARTAMENTOS = %s", (departamento, id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('departamentos'))

# Eliminar departamento
@app.route('/departamentos/eliminar/<int:id>', methods=['POST'])
def eliminar_departamento(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM departamentos WHERE ID_DEPARTAMENTOS = %s", (id,))
    mysql.connection.commit()
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
    cur.execute("DELETE FROM ubicaciones WHERE ID_UBICACIONES = %s", (id,))
    mysql.connection.commit()
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
        if descripcion and area and departamento:
            cur.execute("INSERT INTO cargos (DESCRIPCION, AREA, DEPARTAMENTO) VALUES (%s, %s, %s)", (descripcion, area, departamento))
            mysql.connection.commit()
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
    cur = mysql.connection.cursor()
    cur.execute("UPDATE cargos SET DESCRIPCION = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_CARGOS = %s", (descripcion, area, departamento, id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('crud_cargos'))

# Eliminar cargo
@app.route('/crud_cargos/eliminar/<int:id>', methods=['POST'])
def eliminar_cargo(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM cargos WHERE ID_CARGOS = %s", (id,))
    mysql.connection.commit()
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
    cur.execute("SELECT ID_CARGOS, DESCRIPCION FROM cargos ORDER BY DESCRIPCION")
    cargos = cur.fetchall()
    cur.execute("SELECT ID_UBICACIONES, DESCRIPCION FROM ubicaciones ORDER BY DESCRIPCION")
    ubicaciones = cur.fetchall()
    # Crear
    if request.method == 'POST':
        nombres = request.form.get('nombres')
        apellidos = request.form.get('apellidos')
        departamento = request.form.get('departamento')
        area = request.form.get('area')
        cargo = request.form.get('cargo')
        ubicacion = request.form.get('ubicacion')
        if nombres and apellidos:
            cur.execute("INSERT INTO colaboradores (NOMBRES, APELLIDOS, DEPARTAMENTO, AREA, CARGO, UBICACION) VALUES (%s, %s, %s, %s, %s, %s)",
                        (nombres, apellidos, departamento, area, cargo, ubicacion))
            mysql.connection.commit()
    # Leer
    cur.execute("""
        SELECT col.ID_COLABORADORES, col.NOMBRES, col.APELLIDOS,
               d.DEPARTAMENTO, a.AREA, c.DESCRIPCION, u.DESCRIPCION,
               col.DEPARTAMENTO, col.AREA, col.CARGO, col.UBICACION
        FROM colaboradores col
        LEFT JOIN departamentos d ON col.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        LEFT JOIN areas a ON col.AREA = a.ID_AREAS
        LEFT JOIN cargos c ON col.CARGO = c.ID_CARGOS
        LEFT JOIN ubicaciones u ON col.UBICACION = u.ID_UBICACIONES
        ORDER BY col.NOMBRES, col.APELLIDOS
    """)
    colaboradores = cur.fetchall()
    cur.close()
    return render_template('Colaboradores/CRUD_Colaboradores.html', colaboradores=colaboradores, areas=areas, departamentos=departamentos, cargos=cargos, ubicaciones=ubicaciones)

# Editar colaborador
@app.route('/crud_colaboradores/editar/<int:id>', methods=['POST'])
def editar_colaborador(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    nombres = request.form.get('nombres')
    apellidos = request.form.get('apellidos')
    departamento = request.form.get('departamento')
    area = request.form.get('area')
    cargo = request.form.get('cargo')
    ubicacion = request.form.get('ubicacion')
    cur = mysql.connection.cursor()
    cur.execute("UPDATE colaboradores SET NOMBRES = %s, APELLIDOS = %s, DEPARTAMENTO = %s, AREA = %s, CARGO = %s, UBICACION = %s WHERE ID_COLABORADORES = %s",
                (nombres, apellidos, departamento, area, cargo, ubicacion, id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('crud_colaboradores'))

# Eliminar colaborador
@app.route('/crud_colaboradores/eliminar/<int:id>', methods=['POST'])
def eliminar_colaborador(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM colaboradores WHERE ID_COLABORADORES = %s", (id,))
    mysql.connection.commit()
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
    # Crear
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        extension = request.form.get('extension')
        area = request.form.get('area')
        departamento = request.form.get('departamento')
        if nombre and extension:
            cur.execute("INSERT INTO extensiones (NOMBRE, EXTENSION, AREA, DEPARTAMENTO) VALUES (%s, %s, %s, %s)", (nombre, extension, area, departamento))
            mysql.connection.commit()
    # Leer
    cur.execute("""
        SELECT e.ID_EXTENSIONES, e.NOMBRE, e.EXTENSION, a.AREA, d.DEPARTAMENTO, e.AREA, e.DEPARTAMENTO
        FROM extensiones e
        LEFT JOIN areas a ON e.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON e.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY e.NOMBRE
    """)
    extensiones = cur.fetchall()
    cur.close()
    return render_template('Extensiones/CRUD_Extensiones.html', extensiones=extensiones, areas=areas, departamentos=departamentos)

# Editar extension
@app.route('/extensiones/editar/<int:id>', methods=['POST'])
def editar_extension(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    nombre = request.form.get('nombre')
    extension = request.form.get('extension')
    area = request.form.get('area')
    departamento = request.form.get('departamento')
    cur = mysql.connection.cursor()
    cur.execute("UPDATE extensiones SET NOMBRE = %s, EXTENSION = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_EXTENSIONES = %s", (nombre, extension, area, departamento, id))
    mysql.connection.commit()
    cur.close()
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
    # Crear
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        celular = request.form.get('celular')
        area = request.form.get('area')
        departamento = request.form.get('departamento')
        if nombre and celular and area and departamento:
            cur.execute("INSERT INTO celulares (NOMBRE, CELULAR, AREA, DEPARTAMENTO) VALUES (%s, %s, %s, %s)", (nombre, celular, area, departamento))
            mysql.connection.commit()
    # Leer
    cur.execute("""
        SELECT c.ID_CELULARES, c.NOMBRE, c.CELULAR, a.AREA, d.DEPARTAMENTO, c.AREA, c.DEPARTAMENTO
        FROM celulares c
        LEFT JOIN areas a ON c.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON c.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.NOMBRE
    """)
    celulares = cur.fetchall()
    cur.close()
    return render_template('Celulares/CRUD_Celulares.html', celulares=celulares, areas=areas, departamentos=departamentos)

# Editar celular
@app.route('/celulares/editar/<int:id>', methods=['POST'])
def editar_celular(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    nombre = request.form.get('nombre')
    celular = request.form.get('celular')
    area = request.form.get('area')
    departamento = request.form.get('departamento')
    cur = mysql.connection.cursor()
    cur.execute("UPDATE celulares SET NOMBRE = %s, CELULAR = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_CELULARES = %s", (nombre, celular, area, departamento, id))
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
    # Crear
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        correo = request.form.get('correo')
        area = request.form.get('area')
        departamento = request.form.get('departamento')
        if nombre and correo and area and departamento:
            cur.execute("INSERT INTO correos (NOMBRE, CORREO, AREA, DEPARTAMENTO) VALUES (%s, %s, %s, %s)", (nombre, correo, area, departamento))
            mysql.connection.commit()
    # Leer
    cur.execute("""
        SELECT c.ID_CORREOS, c.NOMBRE, c.CORREO, a.AREA, d.DEPARTAMENTO, c.AREA, c.DEPARTAMENTO
        FROM correos c
        LEFT JOIN areas a ON c.AREA = a.ID_AREAS
        LEFT JOIN departamentos d ON c.DEPARTAMENTO = d.ID_DEPARTAMENTOS
        ORDER BY c.NOMBRE
    """)
    correos = cur.fetchall()
    cur.close()
    return render_template('Correos/CRUD_Correos.html', correos=correos, areas=areas, departamentos=departamentos)

# Editar correo
@app.route('/correos/editar/<int:id>', methods=['POST'])
def editar_correo(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    nombre = request.form.get('nombre')
    correo = request.form.get('correo')
    area = request.form.get('area')
    departamento = request.form.get('departamento')
    cur = mysql.connection.cursor()
    cur.execute("UPDATE correos SET NOMBRE = %s, CORREO = %s, AREA = %s, DEPARTAMENTO = %s WHERE ID_CORREOS = %s", (nombre, correo, area, departamento, id))
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
