import streamlit as st
import pandas as pd
from extractor import extraer_datos_mensaje, guardar_operacion_db, obtener_conexion

st.set_page_config(page_title="Nest Space - Control de Operaciones", layout="wide")

st.title("Nest Space - Panel de Control de Operaciones Multimoneda")
st.caption("Version Beta")

if "historial_local" not in st.session_state:
    st.session_state["historial_local"] = []

# Plantilla predeterminada sugerida para los operadores
PLANTILLA_ESTANDAR = """REGISTRO DE OPERACIÓN
Código: Chile-23103
Monto: 50000
Tasa: 0.925
Detalle: Pago Móvil Venezuela"""

EJEMPLO_MULTIPLE = """Chile-23103
Pago Móvil 
Venezuela 
50.000 a 0,925
Bs. 46.250

Pe 23102
6.200 bs
*20 soles*

México-23093
100 a 43
Bs. 4.300 Mxn

Chile-23034
1.000 a 255
Clp. 255.000"""

st.markdown("---")
col_izq, col_der = st.columnas([1, 1.2])

con col_izq:
    st.subencabezado("Entrada de Mensajes (Soporta Multitransacción)")
    
    c_btn1, c_btn2 = st.columnas(2)
    con c_btn1:
        si st.botón(„Cargar Plantilla Estandar"):
            st.estado_sesión["mensaje_texto"] = PLANTILLA_ESTANDAR
    con c_btn2:
        si st.botón(„Cargar Ráfaga Múltiple"):
            st.estado_sesión["mensaje_texto"] = EJEMPLO_MULTIPLE

    mensaje_input = st.texto_área(
        "Pega aquí uno o varios mensajes de WhatsApp:",
        valor=st.estado_sesión.get("mensaje_texto", EJEMPLO_MÚLTIPLE),
        alta=240
    )
    
    telefono_input = st.entrada_texto(„Teléfono del Remitente:", valor="+584129048187")
    
    si st.botón("Procesar y Guardar Transacción(es)", use_container_width=Verdadero):
        datos = extraer_datos_mensaje(mensaje_input, telefono_input)
        exito_db, msg_db = guardar_operacion_db(datos)
        
        lista_ops = datos si esinstancia(datos, lista) else [datos]
        st.estado_sesión["historial_local"].extender(lista_ops)
        
        si exito_db:
            st.éxito(f"✅ {msg_db}")
        de lo contrario:
            st.advertencia("⚠️ MySQL no conectado. Registros guardados en memoria temporal.")

con col_der:
    st.subencabezado("Transacciones Detectadas en Tiempo Real")
    
    # Ahora la función siempre devuelve una lista, no es necesaria conversación
    lista_preview = extraer_datos_mensaje(mensaje_input, telefono_input)
    
    st.información(f"Se han detectado **{len(lista_preview)}** operación(es) en este mensaje.")
    
    para idx, op en enumerar(lista_preview, 1):
        con st.expansor(f"Operación #{idx}: **{op['codigo_operacion']}** ({op['pais_origen']} 🌎)", expandido=Verdadero):
            m1, m2, m3, m4=st.columnas(4)
            m1.métrica("Código", op["codigo_operacion"])
            m2.métrica(f"Monto ({op['moneda']})", f"{op['monto_divisa']:,.2f}")
            m3.métrica(„Tasa Cambio", f"{op['tasa_cambio']}")
            m4.métrica(„Total Bolívares", f"{op['monto_bolívares']:,.2f} Bs.")
            st.subtípulo(f"**Modo:** {op['tipo_proceso']} | **Moneda:** {op['moneda']}")

st.markdown("---")
st.subencabezado("Registro General de Transacciones (Base de Datos)")

conn = obtener_conexion()
si conn:
    consulta = """
        SELECCIONE o.id_operacion COMO ID, 
               o.codigo_operacion COMO Código, 
               o.monto_divisa COMO 'Monto Divisa',
               o.moneda COMO Moneda,
               o.tasa_cambio AS Tasa, 
               o.monto_bolívares AS 'Total (Bs)', 
               c.telefono AS Cliente, 
               o.fecha_hora COMO Fecha
        DESDE operaciones o
        ÚNASE A LA IZQUIERDA clientes c ON o.id_cliente = c.id_cliente
        ORDENAR POR o.fecha_hora DESC
    """
    intentar:
        df = pd.leer_sql(consulta, conexión)
        conn.cerrar()
    excepto Excelencia:
        df = pd.Marco de datos(st.estado_sesión["historial_local"])
de lo contrario:
    df = pd.Marco de datos(st.estado_sesión["historial_local"])

si no df.vacío:
    st.marco(df, use_container_width=Verdadero)
    
    st.descargar_botón(
        etiqueta="Exportar Reporte a CSV",
        datos=df.to_csv(índice=Falso).codificar('utf-8'),
        nombre_archivo="reportaje_operaciones.csv",
        mime="texto/csv"
    )
de lo contrario:
    st.escribir("No hay transacciones registradas hoy.")
