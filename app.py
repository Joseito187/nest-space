import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re
from datetime import datetime, timedelta
from extractor import guardar_operacion, obtener_todas_operaciones, obtener_conexion

st.set_page_config(page_title="Nest Space - Operaciones", layout="wide")

# --- BASE DE DATOS DE USUARIOS ---
USUARIOS = {
    "admin": {"password": "admini", "rol": "Jefe", "nombre": "Administrador Principal"},
    "empleado1": {"password": "emp1", "rol": "Empleado", "nombre": "Juan Pérez"},
    "empleado2": {"password": "emp2", "rol": "María Gómez"}
}

# --- ESTADO DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None
if "rol" not in st.session_state:
    st.session_state["rol"] = None

# --- EXTRACCIÓN INTELIGENTE MULTIFORMATO ---
def extraer_datos_de_texto(texto):
    # Limpiar asteriscos de formato de WhatsApp
    texto_limpio = texto.replace('*', '')
    
    datos = {
        "monto_divisa": 0.0,
        "moneda": "USD",
        "pais": "Venezuela",
        "tasa": 0.0,
        "monto_bs": 0.0,
        "vendedor": st.session_state.get("usuario", "Admin"),
        "concepto": texto
    }
    
    lineas = [l.strip() for l in texto_limpio.split('\n') if l.strip()]
    
    paises_map = {
        "pe": "Perú", "peru": "Perú", "perú": "Perú",
        "mexico": "México", "méxico": "México",
        "chile": "Chile", "colombia": "Colombia", 
        "venezuela": "Venezuela", "eeuu": "EEUU", "españa": "España"
    }
    
    if lineas:
        primer_bloque = lineas[0].split("-")[0].split(" ")[0].lower()
        if primer_bloque in paises_map:
            datos["pais"] = paises_map[primer_bloque]
            
    for clave, nombre_pais in paises_map.items():
        if clave in texto_limpio.lower():
            datos["pais"] = nombre_pais
            break

    vendedor_match = re.search(r'\(([^)]+)\)', texto_limpio)
    if vendedor_match:
        datos["vendedor"] = vendedor_match.group(1).strip()
    elif len(lineas) > 1:
        posible_vendedor = lineas[1] if len(lineas) > 1 else ""
        bancos_o_extras = ["bcp", "bbva", "pago móvil", "zelle", "m/p", "banesco", "venezuela", "vista", "prepago tenpo"]
        if posible_vendedor and not any(char.isdigit() for char in posible_vendedor) and posible_vendedor.lower() not in bancos_o_extras:
            datos["vendedor"] = posible_vendedor

    patron_monto_tasa = re.search(r'(\$?\s*[\d\.,]+)\s+a\s+([\d\.,]+)', texto_limpio, re.IGNORECASE)
    if patron_monto_tasa:
        str_monto = patron_monto_tasa.group(1).replace('$', '').strip()
        str_tasa = patron_monto_tasa.group(2).replace(',', '.').strip()
        
        if '.' in str_monto and len(str_monto.split('.')[-1]) == 3:
            str_monto = str_monto.replace('.', '')
        str_monto = str_monto.replace(',', '.')
        
        try:
            datos["monto_divisa"] = float(str_monto)
        except ValueError:
            datos["monto_divisa"] = 0.0

        try:
            datos["tasa"] = float(str_tasa)
        except ValueError:
            datos["tasa"] = 0.0
    else:
        monto_match = re.search(r'\s*\$(\d+[\.,]?\d*)', texto_limpio)
        if monto_match:
            datos["monto_divisa"] = float(monto_match.group(1).replace(',', '.'))
        else:
            divisa_match = re.search(r'(\d+[\.,]?\d*)\s*(soles|PEN|USD|EUR|COP|CLP|MXN)', texto_limpio, re.IGNORECASE)
            if divisa_match:
                datos["monto_divisa"] = float(divisa_match.group(1).replace(',', '.'))

    monedas_conocidas = ["clp", "mxn", "pen", "soles", "usd", "eur", "cop"]
    for m in monedas_conocidas:
        if m in texto_limpio.lower():
            if m in ["pen", "soles"]:
                datos["moneda"] = "PEN"
            elif m == "mxn":
                datos["moneda"] = "MXN"
            elif m == "clp":
                datos["moneda"] = "CLP"
            else:
                datos["moneda"] = m.upper()
            break

    bs_match = re.search(r'(?:bs\.?|clp\.?)\s*([\d\.,]+)', texto_limpio, re.IGNORECASE) or re.search(r'([\d\.,]+)\s*bs', texto_limpio, re.IGNORECASE)
    if bs_match:
        bs_str = bs_match.group(1)
        if '.' in bs_str and len(bs_str.split('.')[-1]) == 3:
            bs_str = bs_str.replace('.', '')
        bs_str = bs_str.replace(',', '.')
        try:
            datos["monto_bs"] = float(bs_str)
        except ValueError:
            datos["monto_bs"] = 0.0

    if datos["tasa"] == 0 and datos["monto_divisa"] > 0 and datos["monto_bs"] > 0:
        datos["tasa"] = datos["monto_bs"] / datos["monto_divisa"]
    elif datos["monto_bs"] == 0 and datos["monto_divisa"] > 0 and datos["tasa"] > 0:
        datos["monto_bs"] = datos["monto_divisa"] * datos["tasa"]

    return datos

# --- VISTA DE LOGIN ---
def login_view():
    st.markdown("<h1 style='text-align: center;'>Nest Space</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Acceso al Sistema</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            
            if submit:
                if username in USUARIOS and USUARIOS[username]["password"] == password:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario"] = USUARIOS[username]["nombre"]
                    st.session_state["rol"] = USUARIOS[username]["rol"]
                    st.success(f"Bienvenido {USUARIOS[username]['nombre']}")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")

# --- VISTA DE EMPLEADO ---
def empleado_view():
    st.title("Extractor de Operaciones - WhatsApp")
    st.caption(f"Operador activo: **{st.session_state['usuario']}** ({st.session_state['rol']})")

    st.info("Pegue el mensaje completo de WhatsApp para registrar la operación de forma automática.")

    with st.form("form_whatsapp", clear_on_submit=True):
        mensaje_whatsapp = st.text_area(
            "Mensaje de WhatsApp:", 
            placeholder="Ejemplo: Pe 23102 \n Stephane \n Bcp \n 6.200 bs \n *20 soles*",
            height=150
        )
        procesar = st.form_submit_button("Extraer y Registrar Operación", use_container_width=True)

        if procesar:
            if mensaje_whatsapp.strip():
                extracted = extraer_datos_de_texto(mensaje_whatsapp)
                if extracted["monto_divisa"] > 0:
                    exito = guardar_operacion(
                        vendedor=extracted["vendedor"],
                        pais=extracted["pais"],
                        monto_divisa=extracted["monto_divisa"],
                        moneda=extracted["moneda"],
                        monto_bs=extracted["monto_bs"],
                        tasa=extracted["tasa"],
                        concepto=extracted["concepto"]
                    )
                    if exito:
                        st.success(f"✅ Operación registrada con éxito [Vendedor: {extracted['vendedor']} | País: {extracted['pais']} | Monto: {extracted['monto_divisa']} {extracted['moneda']}]")
                    else:
                        st.error("❌ Error al guardar en la base de datos.")
                else:
                    st.warning("⚠️ No se pudo detectar un monto válido en el mensaje. Verifique el formato.")
            else:
                st.warning("⚠️ Por favor ingrese un mensaje para procesar.")

    st.markdown("---")
    st.subheader("Historial Reciente de Operaciones")
    datos = obtener_todas_operaciones()
    if datos:
        df = pd.DataFrame(datos)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay registros en la base de datos todavía.")

# --- VISTA DE JEFE (DASHBOARD Y REPORTES) ---
def jefe_view():
    st.title("Dashboard Gerencial y Reportes")
    st.caption(f"Panel de Control - **{st.session_state['usuario']}**")

    datos = obtener_todas_operaciones()
    if not datos:
        st.info("No hay suficiente información registrada para generar métricas.")
        return

    df = pd.DataFrame(datos)
    df["fecha_dt"] = pd.to_datetime(df["fecha"])
    df["monto_divisa"] = pd.to_numeric(df["monto_divisa"], errors="coerce")
    df["monto_bs"] = pd.to_numeric(df["monto_bs"], errors="coerce")

    # --- BARRA LATERAL DE FILTROS ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtros y Reportes")

    paises_disponibles = ["Todos"] + list(df["pais"].dropna().unique())
    filtro_pais = st.sidebar.selectbox("Filtrar por País", paises_disponibles)

    monedas_disponibles = ["Todas"] + list(df["moneda"].dropna().unique())
    filtro_moneda = st.sidebar.selectbox("Filtrar por Moneda", monedas_disponibles)

    tipo_periodo = st.sidebar.selectbox("Corte Temporal", ["Histórico General", "Cada 15 Días (Quincenal)", "Mensual"])

    # Aplicar Filtros
    df_filtrado = df.copy()
    if filtro_pais != "Todos":
        df_filtrado = df_filtrado[df_filtrado["pais"] == filtro_pais]
    if filtro_moneda != "Todas":
        df_filtrado = df_filtrado[df_filtrado["moneda"] == filtro_moneda]

    if tipo_periodo == "Cada 15 Días (Quincenal)":
        hoy = datetime.now()
        hace_15_dias = hoy - timedelta(days=15)
        df_filtrado = df_filtrado[df_filtrado["fecha_dt"] >= hace_15_dias]
        st.subheader("Reporte: Últimos 15 Días")
    elif tipo_periodo == "Mensual":
        inicio_mes = datetime(datetime.now().year, datetime.now().month, 1)
        df_filtrado = df_filtrado[df_filtrado["fecha_dt"] >= inicio_mes]
        st.subheader("Reporte: Mes en Curso")
    else:
        st.subheader("Reporte: Histórico General Filtrado")

    if df_filtrado.empty:
        st.warning("⚠️ No hay operaciones que coincidan con los filtros seleccionados.")
        return

    # --- KPIs PRINCIPALES ---
    total_divisa = df_filtrado["monto_divisa"].sum()
    total_bs = df_filtrado["monto_bs"].sum()
    vendedor_top = df_filtrado.groupby("vendedor")["monto_divisa"].sum().idxmax() if not df_filtrado.empty else "N/A"
    pais_top = df_filtrado.groupby("pais")["monto_divisa"].sum().idxmax() if not df_filtrado.empty else "N/A"

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Ingresos Divisa", f"${total_divisa:,.2f}")
    kpi2.metric("Equivalente Total", f"{total_bs:,.2f}")
    kpi3.metric("Vendedor Destacado", vendedor_top)
    kpi4.metric("País Líder", pais_top)

    st.markdown("---")

    # --- GRÁFICOS (TORTA Y BARRAS) ---
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("Distribución por Moneda")
        ventas_moneda = df_filtrado.groupby("moneda")["monto_divisa"].sum().reset_index()
        fig_torta = px.pie(ventas_moneda, names="moneda", values="monto_divisa", hole=0.4)
        st.plotly_chart(fig_torta, use_container_width=True)

    with col_chart2:
        st.subheader("Ventas por País")
        ventas_pais = df_filtrado.groupby("pais")["monto_divisa"].sum().reset_index()
        fig_bar = px.bar(ventas_pais, x="pais", y="monto_divisa", color="pais", text_auto=".2s")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # --- TABLA Y DESCARGA A EXCEL ---
    st.subheader("Detalle de Operaciones")
    st.dataframe(df_filtrado.drop(columns=["fecha_dt"]), use_container_width=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_filtrado.drop(columns=["fecha_dt"]).to_excel(writer, index=False, sheet_name='Reporte')
    excel_data = output.getvalue()

    st.download_button(
        label="Descargar Reporte en Excel",
        data=excel_data,
        file_name=f"reporte_nest_space_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    st.markdown("---")
    st.subheader("Gestión de Base de Datos")

    col_exp, col_imp = st.columns(2)
    with col_exp:
        try:
            with open("nest_space.db", "rb") as f:
                db_bytes = f.read()
            st.download_button(
                label="Exportar Base de Datos (.db)",
                data=db_bytes,
                file_name="nest_space_backup.db",
                mime="application/octet-stream",
                use_container_width=True
            )
        except Exception:
            st.info("Aún no hay archivo de base de datos generado.")

    with col_imp:
        archivo_subido = st.file_uploader("Importar Base de Datos (.db)", type=["db"])
        if archivo_subido is not None:
            if st.button("Restaurar Base de Datos", use_container_width=True):
                with open("nest_space.db", "wb") as f:
                    f.write(archivo_subido.getbuffer())
                st.success("✅ Base de datos importada con éxito. Recargue la página.")
                st.rerun()

# --- CONTROL DE NAVEGACIÓN Y ROLES ---
if not st.session_state["autenticado"]:
    login_view()
else:
    with st.sidebar:
        st.write(f"**Usuario:** {st.session_state['usuario']}")
        st.write(f"**Rol:** {st.session_state['rol']}")
        
        if st.session_state["rol"] == "Jefe":
            modo = st.radio("Navegación", ["Métricas y Dashboard", "Extractor de WhatsApp"])
        else:
            modo = "Extractor de WhatsApp"

        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()

    if st.session_state["rol"] == "Jefe":
        if modo == "Métricas y Dashboard":
            jefe_view()
        else:
            empleado_view()
    else:
        empleado_view()
