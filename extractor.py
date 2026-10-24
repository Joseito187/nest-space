import re
import mysql.connector
from datetime import datetime

# Configuración de conexión a MySQL local (XAMPP)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'nest_space_db'
}

def obtener_conexion():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception:
        return None

def identificar_pais_y_moneda(codigo, texto_bloque):
    """
    Identifica el país de origen y la moneda según el código de operación o palabras clave.
    """
    texto_upper = (codigo + " " + texto_bloque).upper()
    
    if "CHILE" in texto_upper or "CLP" in texto_upper:
        return "Chile", "CLP"
    elif "PE " in texto_upper or "PERÚ" in texto_upper or "PERU" in texto_upper or "SOLES" in texto_upper or "PEN" in texto_upper:
        return "Perú", "PEN"
    elif "MÉXICO" in texto_upper or "MEXICO" in texto_upper or "MXN" in texto_upper:
        return "México", "MXN"
    elif "USA" in texto_upper or "ZELLE" in texto_upper or "USD" in texto_upper:
        return "Estados Unidos", "USD"
    elif "EUR" in texto_upper or "ESPAÑA" in texto_upper or "EUROPA" in texto_upper:
        return "Europa", "EUR"
    elif "VEN" in texto_upper or "BS" in texto_upper:
        return "Venezuela", "VES"
    else:
        return "Internacional", "USD"

def procesar_bloque_individual(texto_bloque, telefono_remitente):
    """
    Procesa una única transacción (sea por plantilla o formato informal).
    """
    texto = texto_bloque.strip()
    
    # 1. DETECCIÓN DE CÓDIGO DE OPERACIÓN
    patron_codigo = r'(?i)\b(Chile|Pe|Perú|México|Mexico|Usa|USA|Ven|EUR)[-:]?\s*\d+\b'
    match_codigo = re.search(patron_codigo, texto)
    codigo = match_codigo.group(0) if match_codigo else "S/C"

    # Identificar País y Moneda de la operación
    pais, moneda = identificar_pais_y_moneda(codigo, texto)

    # 2. ESTRATEGIA A: PLANTILLA ESTANDARIZADA
    if "CÓDIGO:" in texto.upper() or "CODIGO:" in texto.upper() or "REGISTRO" in texto.upper():
        monto_match = re.search(r'(?i)(?:monto|monto\s*\(\$\))\s*:\s*([^\n]+)', texto)
        tasa_match = re.search(r'(?i)tasa\s*:\s*([^\n]+)', texto)
        
        m_val = float(re.sub(r'[^\d\.,]', '', monto_match.group(1)).replace('.', '').replace(',', '.')) if monto_match else 0.0
        t_val = float(re.sub(r'[^\d\.,]', '', tasa_match.group(1)).replace('.', '').replace(',', '.')) if tasa_match else 0.0
        
        monto_bs = round(m_val * t_val, 2) if m_val > 0 and t_val > 0 else 0.0

        return {
            "codigo_operacion": codigo.upper(),
            "pais_origen": pais,
            "moneda": moneda,
            "monto_divisa": m_val,
            "tasa_cambio": t_val,
            "monto_bolivares": monto_bs,
            "telefono_cliente": telefono_remitente,
            "mensaje_original": texto_bloque,
            "tipo_procesamiento": "Plantilla Estandarizada",
            "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # 3. ESTRATEGIA B: FORMATO INFORMAL (EXTRACTOR FLEXIBLE)
    patron_a = r'(?i)([\d\.,]+)\s*a\s*([\d\.,]+)'
    match_a = re.search(patron_a, texto)

    monto_divisa = 0.0
    tasa = 0.0
    monto_bs = 0.0

    if match_a:
        str_m1 = match_a.group(1).replace('.', '').replace(',', '.')
        str_m2 = match_a.group(2).replace('.', '').replace(',', '.')
        v1 = float(str_m1) if str_m1 else 0.0
        v2 = float(str_m2) if str_m2 else 0.0

        monto_divisa = v1
        tasa = v2
        monto_bs = round(monto_divisa * tasa, 2)
    else:
        # Búsqueda especial para casos como "*20 soles*" -> "6.200 bs"
        match_soles = re.search(r'(?i)\*?(\d+(?:[\.,]\d+)?)\s*soles\*?', texto)
        match_bs = re.search(r'(?i)([\d\.,]+)\s*bs', texto)

        if match_soles:
            monto_divisa = float(match_soles.group(1).replace('.', '').replace(',', '.'))
        if match_bs:
            monto_bs = float(match_bs.group(1).replace('.', '').replace(',', '.'))
        
        if monto_divisa > 0 and monto_bs > 0:
            tasa = round(monto_bs / monto_divisa, 2)

    return {
        "codigo_operacion": codigo,
        "pais_origen": pais,
        "moneda": moneda,
        "monto_divisa": monto_divisa,
        "tasa_cambio": tasa,
        "monto_bolivares": monto_bs,
        "telefono_cliente": telefono_remitente,
        "mensaje_original": texto_bloque,
        "tipo_procesamiento": "Informal / Auto-Detección",
        "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def extraer_datos_mensaje(texto_mensaje, telefono_remitente="+584120000000"):
    """
    Función principal: Procesa el mensaje y devuelve SIEMPRE una lista de operaciones.
    """
    if not texto_mensaje or not texto_mensaje.strip():
        return [{
            "codigo_operacion": "S/C",
            "pais_origen": "N/A",
            "moneda": "USD",
            "monto_divisa": 0.0,
            "tasa_cambio": 0.0,
            "monto_bolivares": 0.0,
            "telefono_cliente": telefono_remitente,
            "mensaje_original": "",
            "tipo_procesamiento": "Sin datos",
            "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }]

    # Separa bloques por inicio de países/códigos
    patron_separador = r'(?=(?:Chile|Chile-|Pe|Perú|México|México-|Usa|USA-|Ven|Ven-)\s*[-:]?\s*\d+)'
    bloques = re.split(patron_separador, texto_mensaje, flags=re.IGNORECASE)
    bloques = [b.strip() for b in bloques if b.strip()]

    resultados = []
    for b in bloques:
        res = procesar_bloque_individual(b, telefono_remitente)
        resultados.append(res)

    # Si no se pudo dividir en bloques con el patrón anterior, procesa el texto entero
    if not resultados:
        resultados.append(procesar_bloque_individual(texto_mensaje, telefono_remitente))

    return resultados

def guardar_operacion_db(datos):
    """
    Guarda una lista de operaciones en la base de datos MySQL.
    """
    conn = obtener_conexion()
    if not conn:
        return False, "No se pudo conectar a la base de datos MySQL local."

    try:
        cursor = conn.cursor()
        lista_operaciones = datos if isinstance(datos, list) else [datos]

        for op in lista_operaciones:
            if op['codigo_operacion'] == "S/C" and op['monto_divisa'] == 0:
                continue # Evitar guardar registros vacíos
                
            sql_cliente = "INSERT IGNORE INTO clientes (telefono) VALUES (%s)"
            cursor.execute(sql_cliente, (op['telefono_cliente'],))
            
            sql_get_cliente = "SELECT id_cliente FROM clientes WHERE telefono = %s"
            cursor.execute(sql_get_cliente, (op['telefono_cliente'],))
            row = cursor.fetchone()
            id_cliente = row[0] if row else 1

            sql_operacion = """
                INSERT INTO operaciones 
                (codigo_operacion, monto_divisa, moneda, tasa_cambio, monto_bolivares, id_cliente, mensaje_original)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            valores = (
                op['codigo_operacion'],
                op['monto_divisa'],
                op['moneda'],
                op['tasa_cambio'],
                op['monto_bolivares'],
                id_cliente,
                op['mensaje_original']
            )
            cursor.execute(sql_operacion, valores)

        conn.commit()
        cursor.close()
        conn.close()
        return True, f"Procesado(s) {len(lista_operaciones)} registro(s) correctamente."
    except Exception as e:
        return False, f"Error en BD: {str(e)}"