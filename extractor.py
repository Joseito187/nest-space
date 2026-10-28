import sqlite3

DB_NAME = "nest_space.db"

def obtener_conexion():
    """Establece conexión con la base de datos local SQLite."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row  # Para manejar resultados como diccionarios
        return conn
    except Exception as e:
        print(f"Error al conectar con SQLite: {e}")
        return None

def crear_tablas():
    """Crea la tabla de operaciones si no existe."""
    conn = obtener_conexion()
    if conn:
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS operaciones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        vendedor TEXT,
                        pais TEXT,
                        monto_divisa REAL,
                        moneda TEXT,
                        monto_bs REAL,
                        tasa REAL,
                        concepto TEXT
                    );
                """)
        except Exception as e:
            print(f"Error al crear tablas: {e}")
        finally:
            conn.close()

def guardar_operacion(vendedor, pais, monto_divisa, moneda, monto_bs, tasa, concepto=""):
    """Inserta un registro de operación en SQLite local."""
    conn = obtener_conexion()
    if not conn:
        return False
    try:
        with conn:
            conn.execute("""
                INSERT INTO operaciones (vendedor, pais, monto_divisa, moneda, monto_bs, tasa, concepto)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (vendedor, pais, monto_divisa, moneda, monto_bs, tasa, concepto))
            return True
    except Exception as e:
        print(f"Error al guardar operación: {e}")
        return False
    finally:
        conn.close()

def obtener_todas_operaciones():
    """Recupera todas las operaciones registradas ordenadas por fecha."""
    conn = obtener_conexion()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM operaciones ORDER BY fecha DESC;")
        filas = cursor.fetchall()
        # Convertir a lista de diccionarios para que Streamlit/Pandas lo lea perfecto
        return [dict(fila) for fila in filas]
    except Exception as e:
        print(f"Error al consultar operaciones: {e}")
        return []
    finally:
        conn.close()

# Ejecutamos la creación automática de tablas al importar
crear_tablas()
