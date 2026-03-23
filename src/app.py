from flask import Flask, render_template, request, redirect, url_for, session, flash
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

@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
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
            error = "Usuario o contraseña incorrectos"

    return render_template('login.html', error=error)


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

@app.route("/detalle_venta/<int:id>")
def detalle_venta(id):
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    # Obtener info de la venta
    cursor.execute("""
        SELECT v.id_venta, v.fecha, v.total,
               c.nombre AS cliente
        FROM ventas v
        LEFT JOIN clientes c ON v.id_cliente = c.id_cliente
        WHERE v.id_venta = %s
    """, (id,))
    venta = cursor.fetchone()

    # Obtener detalles de la venta
    cursor.execute("""
        SELECT p.nombre AS producto,
               d.cantidad,
               d.precio_unitario,
               (d.cantidad * d.precio_unitario) AS subtotal
        FROM detalle_ventas d
        JOIN productos p ON d.id_producto = p.id_producto
        WHERE d.id_venta = %s
    """, (id,))
    detalles = cursor.fetchall()

    conexion.close()

    return render_template("detalle_venta.html", venta=venta, detalles=detalles)

@app.route("/ventas")
def ventas():
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    # Obtener clientes
    cursor.execute("SELECT * FROM clientes")
    clientes = cursor.fetchall()

    # Obtener productos (SE NECESITA para el formulario)
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()

    # Obtener ventas (SIN producto directo)
    cursor.execute("""
        SELECT v.id_venta, v.fecha,
               c.nombre AS cliente,
               v.total
        FROM ventas v
        LEFT JOIN clientes c ON v.id_cliente = c.id_cliente
        ORDER BY v.id_venta DESC
    """)
    ventas = cursor.fetchall()

    conexion.close()

    return render_template("ventas.html", clientes=clientes, productos=productos, ventas=ventas)
@app.route('/agregar_venta', methods=['POST'])
def agregar_venta():
    fecha = request.form['fecha']
    cliente_id = request.form.get('cliente')

    productos = request.form.getlist('producto[]')
    cantidades = request.form.getlist('cantidad[]')

    conexion = conectar()
    cursor = conexion.cursor()

    total_venta = 0

    # calcular total
    for i in range(len(productos)):
        id_producto = productos[i]
        cantidad = int(cantidades[i])

        cursor.execute("SELECT precio FROM productos WHERE id_producto = %s", (id_producto,))
        precio = cursor.fetchone()[0]

        total_venta += precio * cantidad

    # insertar venta
    cursor.execute("""
        INSERT INTO ventas (fecha, cliente_id, total)
        VALUES (%s, %s, %s)
    """, (fecha, cliente_id if cliente_id else None, total_venta))

    id_venta = cursor.lastrowid

    # insertar detalle + actualizar stock
    for i in range(len(productos)):
        id_producto = productos[i]
        cantidad = int(cantidades[i])

        cursor.execute("SELECT precio FROM productos WHERE id_producto = %s", (id_producto,))
        precio = cursor.fetchone()[0]

        subtotal = precio * cantidad

        cursor.execute("""
            INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, precio_unitario, subtotal)
            VALUES (%s, %s, %s, %s, %s)
        """, (id_venta, id_producto, cantidad, precio, subtotal))

        cursor.execute("""
            UPDATE productos 
            SET stock = stock - %s 
            WHERE id_producto = %s
        """, (cantidad, id_producto))

    conexion.commit()
    cursor.close()
    conexion.close()

    return redirect(url_for('generar_factura', id=id_venta))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# Mostrar productos
@app.route('/productos')
def productos():
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    # Obtener lista de productos con proveedor
    cursor.execute("""
        SELECT p.id_producto, p.nombre, p.descripcion, p.precio, p.stock, 
               pr.nombre AS proveedor 
        FROM productos p 
        LEFT JOIN proveedores pr ON p.proveedor_id = pr.id_proveedor
    """)
    productos = cursor.fetchall()

    # Obtener lista de proveedores (para el formulario)
    cursor.execute("SELECT * FROM proveedores")
    proveedores = cursor.fetchall()

    # Detectar productos con ventas
    cursor.execute("SELECT DISTINCT id_producto FROM detalle_ventas")
    productos_con_ventas = [row['id_producto'] for row in cursor.fetchall()]
    conexion.close()

    return render_template("productos.html",
                           productos=productos,
                           proveedores=proveedores,
                           productos_con_ventas=productos_con_ventas)


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

@app.route('/eliminar_producto/<int:id>')
def eliminar_producto(id):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM productos WHERE id_producto = %s", (id,))
        conn.commit()
        flash("Producto eliminado correctamente.", "success")
    except mysql.connector.errors.IntegrityError as e:
        # Código 1451 -> existe FK en ventas u otra tabla
        flash("❌ No se puede eliminar este producto porque tiene registros relacionados (ventas).", "error")
    except Exception as e:
        # error inesperado
        flash("❌ Error al eliminar el producto.", "error")
    finally:
        conn.close()
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
@app.route('/actualizar_producto/<int:id_producto>', methods=['POST'])
def actualizar_producto(id_producto):
    id = id_producto

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

# Proveedores
@app.route('/proveedores') #
# Mostrar lista de proveedores
def proveedores():

    # Obtener proveedores con conteo de ventas relacionadas
    conexion = conectar()

    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
    SELECT p.*, 
           COUNT(v.id_venta) AS ventas_relacionadas
    FROM proveedores p
    LEFT JOIN productos prod ON p.id_proveedor = prod.proveedor_id
    LEFT JOIN detalle_ventas dv ON prod.id_producto = dv.id_producto
    LEFT JOIN ventas v ON dv.id_venta = v.id_venta
    GROUP BY p.id_proveedor
""")

    # Obtener todos los proveedores
    proveedores = cursor.fetchall()
    conexion.close()
    return render_template('proveedores.html', proveedores=proveedores)
# Agregar nuevo proveedor
@app.route('/agregar_proveedor', methods=['POST'])
def agregar_proveedor():
    # Obtener datos del formulario
    nombre = request.form['nombre']
    telefono = request.form['telefono']
    correo = request.form['correo']
    direccion = request.form['direccion']
   # Insertar en la base de datos
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO proveedores (nombre, telefono, correo, direccion) VALUES (%s, %s, %s, %s)",
        (nombre, telefono, correo, direccion)
    )
    
    conexion.commit()
    conexion.close()
# Redirigir de vuelta a la página de proveedores
    return redirect(url_for('proveedores'))
# Eliminar proveedor
@app.route('/proveedores/eliminar/<int:id>')
# Eliminar un proveedor por su ID
def eliminar_proveedor(id):
    # Conectar a la base de datos
    try:
        conexion = conectar()
        cursor = conexion.cursor()

        cursor.execute("DELETE FROM proveedores WHERE id_proveedor = %s", (id,))
        conexion.commit()

    except mysql.connector.IntegrityError:
        flash("No se puede eliminar este proveedor, tiene productos asociados.", "error")
    
    finally:
        cursor.close()
        conexion.close()

    return redirect(url_for('proveedores'))


# Editar proveedor (mostrar formulario)
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

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import send_file
import os

@app.route("/factura/<int:id>")
def generar_factura(id):
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    # Obtener venta
    cursor.execute("""
        SELECT v.id_venta, v.fecha, v.total,
               c.nombre AS cliente
        FROM ventas v
        LEFT JOIN clientes c ON v.id_cliente = c.id_cliente
        WHERE v.id_venta = %s
    """, (id,))
    venta = cursor.fetchone()

    # Obtener detalles
    cursor.execute("""
        SELECT p.nombre AS producto,
               d.cantidad,
               d.precio_unitario,
               d.subtotal
        FROM detalle_ventas d
        JOIN productos p ON d.id_producto = p.id_producto
        WHERE d.id_venta = %s
    """, (id,))
    detalles = cursor.fetchall()

    conexion.close()
   #funcion para generar factura en PDF usando ReportLab
    # Crear PDF
    nombre_archivo = f"factura_{id}.pdf"
    ruta = os.path.join("static", nombre_archivo)

    c = canvas.Canvas(ruta, pagesize=letter)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, "FACTURA DE VENTA")

    c.setFont("Helvetica", 10)
    c.drawString(50, 730, f"ID Venta: {venta['id_venta']}")
    c.drawString(50, 715, f"Fecha: {venta['fecha']}")
    c.drawString(50, 700, f"Cliente: {venta['cliente'] if venta['cliente'] else 'Consumidor final'}")

    y = 670
    for d in detalles:
        c.drawString(50, y, d['producto'])
        c.drawString(250, y, str(d['cantidad']))
        c.drawString(300, y, f"${d['precio_unitario']}")
        c.drawString(380, y, f"${d['subtotal']}")
        y -= 20

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"TOTAL: ${venta['total']}")

    c.save()

    return send_file(ruta)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

