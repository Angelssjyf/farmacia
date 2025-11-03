from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# Conexión a la base de datos
def conectar():
    return mysql.connector.connect(
        host="localhost",
        port=3307,  # cambia si usas 3307
        user="root",
        password="",
        database="farmacia"
    )

@app.route('/')
def index():
    return render_template('index.html')

# Mostrar productos
@app.route('/productos')
def productos():
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    conexion.close()
    return render_template('productos.html', productos=productos)

# Registrar un producto nuevo
@app.route('/agregar_producto', methods=['POST'])
def agregar_producto():
    nombre = request.form['nombre']
    descripcion = request.form['descripcion']
    precio = request.form['precio']
    stock = request.form['stock']

    conexion = conectar()
    cursor = conexion.cursor()
    sql = "INSERT INTO productos (nombre, descripcion, precio, stock) VALUES (%s, %s, %s, %s)"
    valores = (nombre, descripcion, precio, stock)
    cursor.execute(sql, valores)
    conexion.commit()
    conexion.close()

    return redirect(url_for('productos'))

if __name__ == '__main__':
    app.run(debug=True)
