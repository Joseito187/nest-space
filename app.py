import streamlit as st
import pandas as pd
from extractor import extraer_datos_mensaje, guardar_operacion_db, obtener_conexion

st.set_page_config(page_title="Nest Space - Control de Operaciones", layout="wide")

st.title("Nest Space - Panel de Control de Operaciones Multimoneda")
st.caption("Version Beta")

if "historial_local" not in st.session_state:
    st.session_state["historial_local"] = []



st.markdown("---")
col_izq, col_der = st.columns([1, 1.2])

with col_izq:
    st.subheader("Entrada de Mensajes (Soporta Multitransacción)")
    
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("Cargar Plantilla Estandar"):
            st.session_state["mensaje_texto"]

    mensaje_input = st.text_area(
        "Pega aquí uno o varios mensajes de WhatsApp:",
        value=st.session_state.get("mensaje_texto"),
        height=240
    )
    
    telefono_input = st.text_input("Teléfono del Remitente:", value="+58")
    
    if st.button("Procesar y Guardar Transacción(es)", use_container_width=True):
        datos = extraer_datos_mensaje(mensaje_input, telefono_input)
        exito_db, msg_db = guardar_operacion_db(datos)
        
        lista_ops = datos if isinstance(datos, list) else [datos]
        st.session_state["historial_local"].extend(lista_ops)
        
        if exito_db:
            st.success(f"✅ {msg_db}")
        else:
            st.warning("⚠️ MySQL no conectado. Registros guardados en memoria temporal.")

with col_der:
    st.subheader("Transacciones Detectadas en Tiempo Real")
    
    # Ahora la función siempre devuelve una lista, no necesita conversión
    lista_preview = extraer_datos_mensaje(mensaje_input, telefono_input)
    
    st.info(f"Se han detectado **{len(lista_preview)}** operación(es) en este mensaje.")
    
    for idx, op in enumerate(lista_preview, 1):
        with st.expander(f"Operación #{idx}: **{op['codigo_operacion']}** ({op['pais_origen']} 🌎)", expanded=True):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Código", op["codigo_operacion"])
            m2.metric(f"Monto ({op['moneda']})", f"{op['monto_divisa']:,.2f}")
            m3.metric("Tasa Cambio", f"{op['tasa_cambio']}")
            m4.metric("Total Bolívares", f"{op['monto_bolivares']:,.2f} Bs.")
            st.caption(f"**Modo:** {op['tipo_procesamiento']} | **Moneda:** {op['moneda']}")

st.markdown("---")
st.subheader("Registro General de Transacciones (Base de Datos)")

conn = obtener_conexion()
if conn:
    query = """
        SELECT o.id_operacion AS ID, 
               o.codigo_operacion AS Código, 
               o.monto_divisa AS 'Monto Divisa',
               o.moneda AS Moneda,
               o.tasa_cambio AS Tasa, 
               o.monto_bolivares AS 'Total (Bs)', 
               c.telefono AS Cliente, 
               o.fecha_hora AS Fecha
        FROM operaciones o
        LEFT JOIN clientes c ON o.id_cliente = c.id_cliente
        ORDER BY o.fecha_hora DESC
    """
    try:
        df = pd.read_sql(query, conn)
        conn.close()
    except Exception:
        df = pd.DataFrame(st.session_state["historial_local"])
else:
    df = pd.DataFrame(st.session_state["historial_local"])

if not df.empty:
    st.dataframe(df, use_container_width=True)
    
    st.download_button(
        label="Exportar Reporte a CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name="reporte_operaciones.csv",
        mime="text/csv"
    )
else:
    st.write("No hay transacciones registradas todavía.")
