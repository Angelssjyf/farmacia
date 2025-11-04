from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "clave_secreta_segura"

def conectar():
    return mysql.connector.connect(
        host="localhost",
        port=3307,
        user="root",
        password="",
        database="farmacia"
    )

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    usuario = request.form['usuario']
    contrasena = request.form['password']

    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM usuarios WHERE nombre_usuario=%s AND contrasena=%s",
        (usuario, contrasena)
    )
    user = cursor.fetchone()
    conexion.close()

    if user:
        session['usuario'] = user['nombre_usuario']
        session['rol'] = user['rol']
        return redirect(url_for('menu'))
    else:
        return render_template('login.html', error="Usuario o contraseña incorrectos")

# ============================================================
# REGISTRO DE USUARIOS
# ============================================================
@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']
        rol = request.form['rol']

        conexion = conectar()
        cursor = conexion.cursor()
        sql = "INSERT INTO usuarios (nombre_usuario, contrasena, rol) VALUES (%s, %s, %s)"
        valores = (usuario, contrasena, rol)
        cursor.execute(sql, valores)
        conexion.commit()
        conexion.close()

        return redirect(url_for('login'))

    return render_template('registrar.html')


@app.route('/menu')
def menu():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('menu.html', usuario=session['usuario'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# Mostrar productos
@app.route('/productos')
@app.route('/productos')
def productos():
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.id_producto, p.nombre, p.descripcion, p.precio, p.stock,
               pr.nombre AS proveedor
        FROM productos p
        LEFT JOIN proveedores pr ON p.proveedor_id = pr.id_proveedor
    """)
    productos = cursor.fetchall()

    # Traer lista de proveedores para el formulario de agregar producto
    cursor.execute("SELECT id_proveedor, nombre FROM proveedores")
    proveedores = cursor.fetchall()

    conexion.close()
    return render_template('productos.html', productos=productos, proveedores=proveedores)

# Registrar un producto nuevo
@app.route('/agregar_producto', methods=['POST'])
def agregar_producto():
    nombre = request.form['nombre']
    descripcion = request.form['descripcion']
    precio = request.form['precio']
    stock = request.form['stock']
    proveedor_id = request.form['proveedor_id']

    conexion = conectar()
    cursor = conexion.cursor()
    sql = """
        INSERT INTO productos (nombre, descripcion, precio, stock, proveedor_id)
        VALUES (%s, %s, %s, %s, %s)
    """
    valores = (nombre, descripcion, precio, stock, proveedor_id)
    cursor.execute(sql, valores)
    conexion.commit()
    conexion.close()

    return redirect(url_for('productos'))

# Eliminar producto
@app.route('/eliminar_producto/<int:id>')
def eliminar_producto(id):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM productos WHERE id_producto = %s", (id,))
    conexion.commit()
    conexion.close()
    return redirect(url_for('productos'))

# Editar producto (mostrar formulario)
@app.route('/editar_producto/<int:id>')
def editar_producto(id):
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos WHERE id_producto = %s", (id,))
    producto = cursor.fetchone()
    conexion.close()
    return render_template('editar_producto.html', producto=producto)

# Actualizar producto (guardar cambios)
@app.route('/actualizar_producto/<int:id>', methods=['POST'])
def actualizar_producto(id):
    nombre = request.form['nombre']
    descripcion = request.form['descripcion']
    precio = request.form['precio']
    stock = request.form['stock']

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE productos 
        SET nombre=%s, descripcion=%s, precio=%s, stock=%s 
        WHERE id_producto=%s
    """, (nombre, descripcion, precio, stock, id))
    conexion.commit()
    conexion.close()
    return redirect(url_for('productos'))

# ============================================================
# MÓDULO DE PROVEEDORES
# ============================================================

@app.route('/proveedores')
def proveedores():
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM proveedores")
    proveedores = cursor.fetchall()
    conexion.close()
    return render_template('proveedores.html', proveedores=proveedores)

@app.route('/agregar_proveedor', methods=['POST'])
def agregar_proveedor():
    nombre = request.form['nombre']
    telefono = request.form['telefono']
    correo = request.form['correo']
    direccion = request.form['direccion']

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO proveedores (nombre, telefono, correo, direccion) VALUES (%s, %s, %s, %s)",
        (nombre, telefono, correo, direccion)
    )
    conexion.commit()
    conexion.close()

    return redirect(url_for('proveedores'))

@app.route('/eliminar_proveedor/<int:id>')
def eliminar_proveedor(id):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM proveedores WHERE id_proveedor = %s", (id,))
    conexion.commit()
    conexion.close()
    return redirect(url_for('proveedores'))

@app.route('/editar_proveedor/<int:id>')
def editar_proveedor(id):
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM proveedores WHERE id_proveedor = %s", (id,))
    proveedor = cursor.fetchone()
    conexion.close()
    return render_template('editar_proveedor.html', proveedor=proveedor)

@app.route('/actualizar_proveedor/<int:id>', methods=['POST'])
def actualizar_proveedor(id):
    nombre = request.form['nombre']
    telefono = request.form['telefono']
    correo = request.form['correo']
    direccion = request.form['direccion']

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE proveedores 
        SET nombre=%s, telefono=%s, correo=%s, direccion=%s 
        WHERE id_proveedor=%s
    """, (nombre, telefono, correo, direccion, id))
    conexion.commit()
    conexion.close()
    return redirect(url_for('proveedores'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

