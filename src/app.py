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

        cursor.execute("""
            SELECT * 
            FROM usuarios 
            WHERE nombre_usuario=%s AND contrasena=%s
        """, (usuario, contrasena))

        user = cursor.fetchone()

        cursor.close()
        conexion.close()

        if user:
            session['usuario'] = user['nombre_usuario']
            session['rol'] = user['rol']

            # REDIRECCIÓN SEGÚN EL ROL
            if user['rol'] == 'cliente':
                return redirect(url_for('panel_cliente'))

            elif user['rol'] == 'admin':
                return redirect(url_for('panel_admin'))

            elif user['rol'] == 'superadmin':
                return redirect(url_for('panel_superadmin'))

            else:
                error = "Rol no válido"

        else:
            error = "Usuario o contraseña incorrectos"

    return render_template('login.html', error=error)
# rutas para roles
# PANEL CLIENTE
@app.route('/cliente')
def panel_cliente():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if session['rol'] != 'cliente':
        return redirect(url_for('login'))

    return render_template('cliente.html')


# PANEL ADMIN
# PANEL ADMIN
@app.route('/admin')
def panel_admin():

    if 'usuario' not in session:
        return redirect(url_for('login'))

    if session['rol'] != 'admin':
        return redirect(url_for('login'))

    return render_template('admin.html')


# PANEL SUPER ADMIN
@app.route('/superadmin')
def panel_superadmin():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if session['rol'] != 'superadmin':
        return redirect(url_for('login'))

    return render_template('superadmin.html')


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
# pedido cliente
@app.route('/pedido_cliente')
def pedido_cliente():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if session['rol'] != 'cliente':
        return redirect(url_for('login'))

    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    # Mostrar solo productos con stock disponible
    cursor.execute("""
        SELECT id_producto, nombre, precio, stock
        FROM productos
        WHERE stock > 0
    """)
    productos = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("pedido_cliente.html", productos=productos)


#guardar pedido cliente
@app.route('/guardar_pedido', methods=['POST'])
def guardar_pedido():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if session['rol'] != 'cliente':
        return redirect(url_for('login'))

    conexion = conectar()
    cursor = conexion.cursor()

    productos = request.form.getlist('producto[]')
    cantidades = request.form.getlist('cantidad[]')

    # Buscar cliente según usuario logueado
    cursor.execute("""
        SELECT id_cliente 
        FROM clientes 
        WHERE nombre = %s
    """, (session['usuario'],))

    cliente = cursor.fetchone()

    if not cliente:
        cursor.close()
        conexion.close()
        return "El cliente no existe en la tabla clientes"

    id_cliente = cliente[0]

    # Crear pedido principal
    cursor.execute("""
        INSERT INTO pedidos (id_cliente, estado)
        VALUES (%s, %s)
    """, (id_cliente, 'pendiente'))

    id_pedido = cursor.lastrowid

    # Guardar detalle del pedido
    for i in range(len(productos)):
        id_producto = productos[i]
        cantidad = cantidades[i]

        cursor.execute("""
            INSERT INTO detalle_pedidos (id_pedido, id_producto, cantidad)
            VALUES (%s, %s, %s)
        """, (id_pedido, id_producto, cantidad))

    conexion.commit()
    cursor.close()
    conexion.close()

    return redirect(url_for('panel_cliente'))

#catalogo cliente
@app.route('/catalogo')
def catalogo():
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT id_producto, nombre, descripcion, precio, stock
        FROM productos
        WHERE stock > 0
    """)

    productos = cursor.fetchall()

    conexion.close()

    return render_template("catalogo.html", productos=productos)

@app.route("/ventas")
def ventas():
    # validar sesión
    if 'usuario' not in session:
        return redirect(url_for('login'))

    # validar roles permitidos
    if session['rol'] not in ['admin', 'superadmin']:
        return redirect(url_for('login'))

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

    # 🔥 VALIDAR TODO ANTES DE VENDER
    for i in range(len(productos)):
        id_producto = productos[i]
        cantidad = int(cantidades[i])

        cursor.execute("""
            SELECT precio, stock, estado 
            FROM productos 
            WHERE id_producto = %s
        """, (id_producto,))
        
        producto = cursor.fetchone()

        if not producto:
            conexion.close()
            return "ERROR: Producto no existe"

        precio = producto[0]
        stock = producto[1]
        estado = producto[2]

        # 🚫 VALIDACIONES IMPORTANTES
        if estado != 'disponible':
            conexion.close()
            return f"ERROR: Producto ID {id_producto} no disponible"

        if stock <= 0:
            conexion.close()
            return f"ERROR: Producto ID {id_producto} sin stock"

        if cantidad > stock:
            conexion.close()
            return f"ERROR: No hay suficiente stock del producto ID {id_producto}"

        total_venta += precio * cantidad

    # ✅ INSERTAR VENTA
    cursor.execute("""
        INSERT INTO ventas (fecha, id_cliente, total)
        VALUES (%s, %s, %s)
    """, (fecha, cliente_id if cliente_id else None, total_venta))

    id_venta = cursor.lastrowid

    # 🔥 INSERTAR DETALLE + ACTUALIZAR STOCK
    for i in range(len(productos)):
        id_producto = productos[i]
        cantidad = int(cantidades[i])

        cursor.execute("SELECT precio, stock FROM productos WHERE id_producto = %s", (id_producto,))
        producto = cursor.fetchone()

        precio = producto[0]
        stock_actual = producto[1]

        subtotal = precio * cantidad
        nuevo_stock = stock_actual - cantidad

        cursor.execute("""
            INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, precio_unitario, subtotal)
            VALUES (%s, %s, %s, %s, %s)
        """, (id_venta, id_producto, cantidad, precio, subtotal))

        # 🔄 actualizar stock
        cursor.execute("""
            UPDATE productos 
            SET stock = %s 
            WHERE id_producto = %s
        """, (nuevo_stock, id_producto))

        # 🔥 CAMBIO AUTOMÁTICO DE ESTADO
        if nuevo_stock == 0:
            cursor.execute("""
                UPDATE productos 
                SET estado = 'agotado' 
                WHERE id_producto = %s
            """, (id_producto,))

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

    # validar sesión
    if 'usuario' not in session:
        return redirect(url_for('login'))

    # validar roles permitidos
    if session['rol'] not in ['admin', 'superadmin']:
        return redirect(url_for('login'))

    # conexión BD
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    # obtener productos
    cursor.execute("""
        SELECT p.id_producto, 
               p.nombre, 
               p.descripcion, 
               p.precio, 
               p.stock,
               p.estado,
               p.lote,
               p.fecha_vencimiento,
               pr.nombre AS proveedor
        FROM productos p
        LEFT JOIN proveedores pr 
        ON p.proveedor_id = pr.id_proveedor
    """)

    productos = cursor.fetchall()

    # obtener proveedores
    cursor.execute("SELECT * FROM proveedores")
    proveedores = cursor.fetchall()

    conexion.close()

    return render_template(
        "productos.html",
        productos=productos,
        proveedores=proveedores
    )

# Registrar un producto nuevo
@app.route('/agregar_producto', methods=['POST'])
def agregar_producto():
    nombre = request.form['nombre']
    descripcion = request.form['descripcion']
    precio = request.form['precio']
    stock = request.form['stock']
    proveedor_id = request.form['proveedor_id']
    lote = request.form['lote']
    fecha_vencimiento = request.form['fecha_vencimiento']

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO productos (
            nombre,
            descripcion,
            precio,
            stock,
            proveedor_id,
            lote,
            fecha_vencimiento
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        nombre,
        descripcion,
        precio,
        stock,
        proveedor_id,
        lote,
        fecha_vencimiento
    ))

    conexion.commit()
    cursor.close()
    conexion.close()

    flash("Producto registrado correctamente")
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


#estado de los productos (activo o inactivo)
@app.route('/cambiar_estado/<int:id>')
def cambiar_estado(id):
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("SELECT estado FROM productos WHERE id_producto = %s", (id,))
    producto = cursor.fetchone()

    estado_actual = producto['estado']

    if estado_actual == 'disponible':
        nuevo_estado = 'agotado'
    else:
        nuevo_estado = 'disponible'

    cursor.execute("""
        UPDATE productos 
        SET estado = %s 
        WHERE id_producto = %s
    """, (nuevo_estado, id))

    conexion.commit()
    conexion.close()

    return redirect(url_for('productos'))


#productos a vencer 
from datetime import date

@app.route('/vencimientos')
def vencimientos():
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM productos
    """)
    
    productos = cursor.fetchall()

    hoy = date.today()

    for p in productos:
        fecha = p['fecha_vencimiento']
        
        if fecha:
            dias = (fecha - hoy).days

            if dias > 180:
                p['estado'] = 'verde'
            elif dias > 0:
                p['estado'] = 'amarillo'
            else:
                p['estado'] = 'rojo'

    cursor.close()
    conexion.close()

    return render_template("vencimientos.html", productos=productos)




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
    
#admin pedidos
@app.route('/ver_pedidos')
def ver_pedidos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if session['rol'] not in ['admin', 'superadmin']:
        return redirect(url_for('login'))

    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.id_pedido,
               p.fecha,
               p.estado,
               c.nombre AS cliente
        FROM pedidos p
        INNER JOIN clientes c 
            ON p.id_cliente = c.id_cliente
        ORDER BY p.id_pedido DESC
    """)

    pedidos = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("ver_pedidos.html", pedidos=pedidos)







# Proveedores

# Mostrar lista de proveedores
@app.route('/proveedores')
def proveedores():

    # validar sesión
    if 'usuario' not in session:
        return redirect(url_for('login'))

    # validar roles permitidos
    if session['rol'] not in ['admin', 'superadmin']:
        return redirect(url_for('login'))

    # conexión BD
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    # obtener proveedores
    cursor.execute("""
        SELECT p.*, 
               COUNT(v.id_venta) AS ventas_relacionadas
        FROM proveedores p
        LEFT JOIN productos prod 
            ON p.id_proveedor = prod.proveedor_id
        LEFT JOIN detalle_ventas dv 
            ON prod.id_producto = dv.id_producto
        LEFT JOIN ventas v 
            ON dv.id_venta = v.id_venta
        GROUP BY p.id_proveedor
    """)

    proveedores = cursor.fetchall()

    conexion.close()

    return render_template(
        'proveedores.html',
        proveedores=proveedores
    )
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

