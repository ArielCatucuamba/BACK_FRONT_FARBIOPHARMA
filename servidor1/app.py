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
app.config['MYSQL_PASSWORD'] = os.getenv("MYSQL_PASSWORD", "root")
app.config['MYSQL_DB'] = os.getenv("MYSQL_DB", "db_informacion")
app.config['MYSQL_PORT'] = int(os.getenv("MYSQL_PORT", 3306))

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
        
        # Crear tabla de productos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                codigo VARCHAR(50) UNIQUE NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT,
                unidad VARCHAR(20) NOT NULL,
                categoria VARCHAR(50) NOT NULL,
                stock INT DEFAULT 0,
                precio DECIMAL(10,2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        mysql.connection.commit()
        cur.close()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    servidor_info = "Servidor 1"
    return render_template('index.html', servidor_info=servidor_info)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor, complete todos los campos', 'error')
            return render_template('login.html')
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, username, password_hash FROM usuarios WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([username, email, password, confirm_password]):
            flash('Por favor, complete todos los campos', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('register.html')
        
        # Verificar si el usuario ya existe
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM usuarios WHERE username = %s OR email = %s", (username, email))
        existing_user = cur.fetchone()
        
        if existing_user:
            flash('El usuario o email ya existe', 'error')
            cur.close()
            return render_template('register.html')
        
        # Crear hash de la contraseña
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insertar nuevo usuario
        cur.execute("INSERT INTO usuarios (username, email, password_hash) VALUES (%s, %s, %s)", 
                   (username, email, password_hash))
        mysql.connection.commit()
        cur.close()
        
        flash('Usuario registrado exitosamente', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

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
    
    servidor_info = "Servidor 1"
    return render_template('productos.html', productos=productos, servidor_info=servidor_info)

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
            return render_template('agregar_producto.html')
        
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
    
    servidor_info = "Servidor 1"
    return render_template('agregar_producto.html', servidor_info=servidor_info)

@app.route('/api/producto/<codigo>')
def api_producto_disponibilidad(codigo):
    """API para consultar disponibilidad de producto en tiempo real"""
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT codigo, nombre, stock, categoria FROM productos WHERE codigo = %s", (codigo,))
    producto = cur.fetchone()
    cur.close()
    
    if producto:
        return jsonify({
            'codigo': producto[0],
            'nombre': producto[1],
            'stock': producto[2],
            'categoria': producto[3],
            'disponible': producto[2] > 0,
            'servidor': "Servidor 1"
        })
    else:
        return jsonify({'error': 'Producto no encontrado'}), 404

@app.route('/consultar_disponibilidad')
def consultar_disponibilidad():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    servidor_info = "Servidor 1"
    return render_template('consultar_disponibilidad.html', servidor_info=servidor_info)

if __name__ == "__main__":
    print("🚀 Iniciando servidor Flask...")
    wait_for_db()
    init_db()
    print("✅ Servidor listo para recibir conexiones")
    app.run(host='0.0.0.0', debug=True)

