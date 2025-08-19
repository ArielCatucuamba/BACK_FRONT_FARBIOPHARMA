
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
                DESCRIPCION VARCHAR(150) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Crear tabla de departamentos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS departamentos (
                ID_DEPARTAMENTOS INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                DEPARTAMENTO VARCHAR(100) NOT NULL,
                DESCRIPCION VARCHAR(150) NOT NULL
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
        descripcion = request.form.get('descripcion')
        if area and descripcion:
            cur.execute("INSERT INTO areas (AREA, DESCRIPCION) VALUES (%s, %s)", (area, descripcion))
            mysql.connection.commit()
    # Leer
    cur.execute("SELECT ID_AREAS, AREA, DESCRIPCION FROM areas ORDER BY AREA")
    areas = cur.fetchall()
    cur.close()
    return render_template('Areas/CRUD_Areas.html', areas=areas)

# Editar área
@app.route('/crud_areas/editar/<int:id>', methods=['POST'])
def editar_area(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    area = request.form.get('area')
    descripcion = request.form.get('descripcion')
    cur = mysql.connection.cursor()
    cur.execute("UPDATE areas SET AREA = %s, DESCRIPCION = %s WHERE ID_AREAS = %s", (area, descripcion, id))
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
        descripcion = request.form.get('descripcion')
        if departamento and descripcion:
            cur.execute("INSERT INTO departamentos (DEPARTAMENTO, DESCRIPCION) VALUES (%s, %s)", (departamento, descripcion))
            mysql.connection.commit()
    # Leer
    cur.execute("SELECT ID_DEPARTAMENTOS, DEPARTAMENTO, DESCRIPCION FROM departamentos ORDER BY DEPARTAMENTO")
    departamentos = cur.fetchall()
    cur.close()
    return render_template('Departamentos/CRUD_Departamentos.html', departamentos=departamentos)

# Editar departamento
@app.route('/departamentos/editar/<int:id>', methods=['POST'])
def editar_departamento(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    departamento = request.form.get('departamento')
    descripcion = request.form.get('descripcion')
    cur = mysql.connection.cursor()
    cur.execute("UPDATE departamentos SET DEPARTAMENTO = %s, DESCRIPCION = %s WHERE ID_DEPARTAMENTOS = %s", (departamento, descripcion, id))
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


if __name__ == "__main__":
    print("🚀 Iniciando servidor Flask...")
    wait_for_db()
    init_db()
    print("✅ Servidor listo para recibir conexiones")
    app.run(host='0.0.0.0', debug=True)
