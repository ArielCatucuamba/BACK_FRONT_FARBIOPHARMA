
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
        
        mysql.connection.commit()
        cur.close()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    servidor_info = "Servidor 3"
    return render_template('Areas/index.html', servidor_info=servidor_info)

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

@app.route('/areas')
def areas():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    servidor_info = "Servidor 3"
    return render_template('Areas/index.html', servidor_info=servidor_info)

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

@app.route('/productos')
def productos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM productos ORDER BY nombre")
    productos = cur.fetchall()
    cur.close()
    
    servidor_info = "Servidor 3"
    return render_template('Areas/productos.html', productos=productos, servidor_info=servidor_info)

@app.route('/agregar_producto', methods=['GET', 'POST'])
def agregar_producto():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        unidad = request.form.get('unidad')
        categoria = request.form.get('categoria')
        stock = request.form.get('stock', 0)
        precio = request.form.get('precio', 0.00)
        
        if not all([codigo, nombre, unidad, categoria]):
            flash('Por favor, complete todos los campos obligatorios', 'error')
            return render_template('Areas/agregar_producto.html')
        
        # Verificar si el código ya existe
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM productos WHERE codigo = %s", (codigo,))
        existing_product = cur.fetchone()
        
        if existing_product:
            flash('El código de producto ya existe', 'error')
            cur.close()
            return render_template('agregar_producto.html')
        
        # Insertar nuevo producto
        cur.execute("""
            INSERT INTO productos (codigo, nombre, descripcion, unidad, categoria, stock, precio) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (codigo, nombre, descripcion, unidad, categoria, stock, precio))
        mysql.connection.commit()
        cur.close()
        
        flash('Producto agregado exitosamente', 'success')
        return redirect(url_for('productos'))
    
    servidor_info = "Servidor 3"
    return render_template('Areas/agregar_producto.html', servidor_info=servidor_info)


# API para consultar área por ID
@app.route('/api/area/<int:id_area>')
def api_area(id_area):
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    cur = mysql.connection.cursor()
    cur.execute("SELECT ID_AREAS, DESCRIPCION FROM areas WHERE ID_AREAS = %s", (id_area,))
    area = cur.fetchone()
    cur.close()
    if area:
        return jsonify({
            'ID_AREAS': area[0],
            'DESCRIPCION': area[1],
            'servidor': "Servidor 3"
        })
    else:
        return jsonify({'error': 'Área no encontrada'}), 404

# Vista para consultar disponibilidad de áreas
@app.route('/consultar_disponibilidad')
def consultar_disponibilidad():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    servidor_info = "Servidor 3"
    # Obtener todas las áreas para mostrar en la vista
    cur = mysql.connection.cursor()
    cur.execute("SELECT ID_AREAS, DESCRIPCION FROM areas ORDER BY DESCRIPCION")
    areas = cur.fetchall()
    cur.close()
    return render_template('Areas/consultar_disponibilidad.html', servidor_info=servidor_info, areas=areas)


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

if __name__ == "__main__":
    print("🚀 Iniciando servidor Flask...")
    wait_for_db()
    init_db()
    print("✅ Servidor listo para recibir conexiones")
    app.run(host='0.0.0.0', debug=True)
