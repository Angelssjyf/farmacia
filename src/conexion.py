import mysql.connector

def conectar():
    try:
        conexion = mysql.connector.connect(
            host="localhost",
            port=3307,  # usa 3307 si tu MySQL corre en ese puerto
            user="root",
            password="",  # deja vacío si no tiene contraseña
            database="farmacia"
        )
        if conexion.is_connected():
            print("✅ Conexión exitosa a la base de datos farmacia")
        return conexion
    except mysql.connector.Error as e:
        print(f"❌ Error al conectar: {e}")
        return None

# Prueba directa
if __name__ == "__main__":
    conectar()
