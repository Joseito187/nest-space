import logging
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from auth import cargar_usuarios, verificar_contrasena
from extractor import (
    actualizar_operacion,
    eliminar_operacion,
    exportar_base_datos,
    extraer_datos_de_texto,
    guardar_operacion,
    obtener_todas_operaciones,
    restaurar_base_datos,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Nest Space - Operaciones", layout="wide")

MONEDAS = ["USD", "PEN", "MXN", "CLP", "EUR", "COP"]
PAISES = ["Venezuela", "Perú", "México", "Chile", "Colombia", "EEUU", "España"]


def aplicar_estilo() -> None:
    st.markdown(
        """
        <style>
            :root {
                --bg: #0b1220;
                --bg-soft: #111827;
                --panel: rgba(17, 24, 39, 0.9);
                --panel-strong: #111827;
                --primary: #7c9cff;
                --primary-strong: #5377ff;
                --accent: #36d399;
                --text: #e5eefb;
                --muted: #a7b5d0;
                --border: rgba(148, 163, 184, 0.18);
                --shadow: 0 18px 40px rgba(2, 6, 23, 0.42);
            }

            .stApp {
                background: radial-gradient(circle at top left, #111d2f 0%, #0b1220 35%, #070d17 100%);
                color: var(--text);
            }

            .block-container {
                max-width: 1280px;
                padding-top: 2.2rem;
                padding-bottom: 3rem;
            }

            div[data-testid="stSidebar"] {
                background: linear-gradient(180deg, rgba(15, 23, 42, 0.97), rgba(2, 6, 23, 0.99));
                border-right: 1px solid rgba(148, 163, 184, 0.14);
            }

            div[data-testid="stSidebar"] * {
                color: #edf2ff !important;
            }

            div[data-testid="stSidebarNav"] {
                padding-top: 1rem;
            }

            [data-testid="stForm"] {
                background: rgba(17, 24, 39, 0.87);
                border: 1px solid rgba(148, 163, 184, 0.18);
                border-radius: 22px;
                box-shadow: 0 18px 40px rgba(2, 6, 23, 0.38);
                padding: 1.4rem;
            }

            .stButton > button {
                border: none;
                border-radius: 12px;
                background: linear-gradient(135deg, #7c9cff, #4f73ff);
                color: white;
                font-weight: 700;
                padding: 0.7rem 1.3rem;
                box-shadow: 0 10px 22px rgba(124, 156, 255, 0.25);
            }

            .stButton > button:hover {
                background: linear-gradient(135deg, #6d8efb, #3d63ea);
                transform: translateY(-1px);
            }

            .stButton button[kind="secondary"] {
                background: linear-gradient(135deg, #1e293b, #0f172a);
                color: var(--text);
                box-shadow: none;
            }

            .stSuccess {
                background: rgba(54, 211, 153, 0.12);
                border: 1px solid rgba(54, 211, 153, 0.28);
                border-radius: 12px;
                color: #d1fae5;
            }

            .stError {
                background: rgba(248, 113, 113, 0.12);
                border: 1px solid rgba(248, 113, 113, 0.28);
                border-radius: 12px;
                color: #fee2e2;
            }

            .stInfo {
                background: rgba(96, 165, 250, 0.12);
                border: 1px solid rgba(96, 165, 250, 0.22);
                border-radius: 12px;
                color: #dbeafe;
            }

            .stWarning {
                background: rgba(245, 158, 11, 0.12);
                border: 1px solid rgba(245, 158, 11, 0.24);
                border-radius: 12px;
                color: #fef3c7;
            }

            h1, h2, h3 {
                color: #f8fbff;
                letter-spacing: -0.03em;
            }

            .metric-container {
                background: rgba(15, 23, 42, 0.9);
                border: 1px solid rgba(148, 163, 184, 0.18);
                border-radius: 18px;
                box-shadow: 0 12px 28px rgba(2, 6, 23, 0.34);
                padding: 1rem;
            }

            [data-testid="stMetricLabel"] {
                color: var(--muted) !important;
            }

            [data-testid="stMetricValue"] {
                color: var(--text) !important;
            }

            .stDataFrame {
                border-radius: 16px;
                overflow: hidden;
                border: 1px solid rgba(148, 163, 184, 0.18);
            }

            div[data-testid="stAlert"] {
                border-radius: 12px;
            }

            .stTextInput > div > div > input,
            .stTextArea > div > div > textarea,
            .stSelectbox > div > div,
            .stNumberInput > div > div,
            .stDateInput > div > div {
                background: rgba(15, 23, 42, 0.9);
                color: var(--text);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 10px;
            }

            .stTextInput label,
            .stTextArea label,
            .stSelectbox label,
            .stNumberInput label,
            .stDateInput label {
                color: var(--muted) !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


aplicar_estilo()


def login_view() -> None:
    st.markdown("<h1 style='text-align: center; margin-bottom: 0.2rem;'>Nest Space</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #475569;'>Acceso al Sistema</h3>", unsafe_allow_html=True)

    try:
        usuarios = cargar_usuarios()
    except ValueError:
        logger.exception("Configuración de usuarios inválida")
        st.error("La configuración de usuarios es inválida. Revise NEST_SPACE_USERS_JSON.")
        return

    if not usuarios:
        st.warning(
            "No hay cuentas configuradas. Consulte README.md para crear usuarios "
            "y definir NEST_SPACE_USERS_JSON."
        )

    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("<div style='text-align: center; margin-bottom: 1rem;'><strong>Ingresa tus credenciales</strong></div>", unsafe_allow_html=True)
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Iniciar Sesión", width="stretch")

            if submit:
                usuario = usuarios.get(username)
                if usuario and verificar_contrasena(password, usuario["password_hash"]):
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_id"] = username
                    st.session_state["usuario"] = usuario["nombre"]
                    st.session_state["rol"] = usuario["rol"]
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")


def registrar_operacion_view() -> None:
    if "mensaje_exito_registro" in st.session_state:
        st.success(st.session_state.pop("mensaje_exito_registro"))

    st.title("Registrar operación")
    st.caption(
        f"Operador activo: **{st.session_state['usuario']}** "
        f"({st.session_state['rol']})"
    )
    st.info("Pegue el mensaje de WhatsApp. Revise y corrija los datos extraídos antes de guardar.")

    with st.form("form_extraer"):
        mensaje = st.text_area(
            "Mensaje de WhatsApp",
            placeholder="Ejemplo: Pe 23102\nStephane\nBcp\n6.200 bs\n*20 soles*",
            height=150,
        )
        procesar = st.form_submit_button("Extraer datos", width="stretch")

    if procesar:
        if not mensaje.strip():
            st.warning("Ingrese un mensaje para procesar.")
        else:
            try:
                borrador = extraer_datos_de_texto(
                    mensaje, st.session_state["usuario_id"]
                )
                borrador["form_id"] = uuid.uuid4().hex
                st.session_state["borrador_operacion"] = borrador
                st.rerun()
            except ValueError:
                logger.exception("No se pudo interpretar el mensaje")
                st.error("No se pudo interpretar un número del mensaje. Revise su formato.")

    borrador = st.session_state.get("borrador_operacion")
    if borrador is None:
        return

    st.subheader("Revisar datos extraídos")
    st.caption("El monto local conserva la unidad indicada en el mensaje; no se convierte.")
    form_id = borrador["form_id"]
    with st.form(f"form_confirmar_{form_id}"):
        vendedor = st.text_input("Vendedor / contraparte", value=str(borrador["vendedor"]))
        pais = st.selectbox(
            "País",
            PAISES,
            index=PAISES.index(borrador["pais"])
            if borrador["pais"] in PAISES
            else 0,
        )
        moneda = st.selectbox(
            "Moneda del monto",
            MONEDAS,
            index=MONEDAS.index(borrador["moneda"])
            if borrador["moneda"] in MONEDAS
            else 0,
        )
        monto_divisa = st.number_input(
            "Monto en moneda seleccionada",
            min_value=0.0,
            value=float(borrador["monto_divisa"]),
            format="%.4f",
        )
        monto_local = st.number_input(
            "Monto local (unidad indicada en el mensaje)",
            min_value=0.0,
            value=float(borrador["monto_bs"]),
            format="%.4f",
        )
        tasa = st.number_input(
            "Tasa indicada o calculada",
            min_value=0.0,
            value=float(borrador["tasa"]),
            format="%.6f",
        )
        concepto = st.text_area("Mensaje original", value=str(borrador["concepto"]))
        guardar = st.form_submit_button("Confirmar y registrar", width="stretch")

    if guardar:
        if not vendedor.strip() or not pais:
            st.error("El vendedor y el país son obligatorios.")
            return
        try:
            operacion_id = guardar_operacion(
                vendedor=vendedor,
                pais=pais,
                monto_divisa=monto_divisa,
                moneda=moneda,
                monto_bs=monto_local,
                tasa=tasa,
                concepto=concepto,
                usuario_id=st.session_state["usuario_id"],
            )
        except (sqlite3.Error, ValueError):
            logger.exception("No se pudo registrar la operación")
            st.error("No se pudo registrar la operación. Revise los datos e inténtelo de nuevo.")
            return
        st.session_state.pop("borrador_operacion", None)
        st.session_state["mensaje_exito_registro"] = (
            f"Operación #{operacion_id} registrada correctamente."
        )
        st.rerun()


def _cargar_operaciones(usuario_id: str | None = None) -> pd.DataFrame | None:
    try:
        datos = obtener_todas_operaciones(usuario_id)
    except sqlite3.Error:
        logger.exception("No se pudieron consultar las operaciones")
        st.error("No se pudieron cargar las operaciones por un error de base de datos.")
        return None
    if not datos:
        return pd.DataFrame()
    df = pd.DataFrame(datos)
    df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
    for columna in ("monto_divisa", "monto_bs", "tasa"):
        df[columna] = pd.to_numeric(df[columna], errors="coerce")
    return df


def _filtrar_operaciones(df: pd.DataFrame, clave: str) -> pd.DataFrame:
    if df.empty:
        return df
    columnas = st.columns(4)
    busqueda = columnas[0].text_input("Buscar vendedor o concepto", key=f"{clave}_buscar")
    paises = ["Todos", *sorted(df["pais"].dropna().astype(str).unique())]
    pais = columnas[1].selectbox("País", paises, key=f"{clave}_pais")
    monedas = ["Todas", *sorted(df["moneda"].dropna().astype(str).unique())]
    moneda = columnas[2].selectbox("Moneda", monedas, key=f"{clave}_moneda")
    periodo = columnas[3].selectbox(
        "Período",
        ["Histórico", "Últimos 15 días", "Mes actual", "Personalizado"],
        key=f"{clave}_periodo",
    )

    filtrado = df.copy()
    if busqueda:
        coincidencia = (
            filtrado["vendedor"]
            .fillna("")
            .astype(str)
            .str.contains(busqueda, case=False, regex=False)
            | filtrado["concepto"]
            .fillna("")
            .astype(str)
            .str.contains(busqueda, case=False, regex=False)
        )
        filtrado = filtrado[coincidencia]
    if pais != "Todos":
        filtrado = filtrado[filtrado["pais"] == pais]
    if moneda != "Todas":
        filtrado = filtrado[filtrado["moneda"] == moneda]

    hoy = date.today()
    if periodo == "Últimos 15 días":
        filtrado = filtrado[filtrado["fecha_dt"] >= pd.Timestamp(hoy - timedelta(days=14))]
    elif periodo == "Mes actual":
        inicio_mes = date(hoy.year, hoy.month, 1)
        filtrado = filtrado[filtrado["fecha_dt"] >= pd.Timestamp(inicio_mes)]
    elif periodo == "Personalizado":
        validas = filtrado["fecha_dt"].dropna()
        if not validas.empty:
            col_desde, col_hasta = st.columns(2)
            minimo = validas.min().date()
            maximo = max(validas.max().date(), hoy)
            desde = col_desde.date_input(
                "Desde", value=minimo, min_value=minimo, max_value=maximo, key=f"{clave}_desde"
            )
            hasta = col_hasta.date_input(
                "Hasta", value=maximo, min_value=minimo, max_value=maximo, key=f"{clave}_hasta"
            )
            if desde > hasta:
                st.warning("La fecha inicial debe ser anterior a la fecha final.")
                return filtrado.iloc[0:0]
            filtrado = filtrado[
                (filtrado["fecha_dt"] >= pd.Timestamp(desde))
                & (filtrado["fecha_dt"] < pd.Timestamp(hasta + timedelta(days=1)))
            ]
    return filtrado


def _tabla_operaciones(df: pd.DataFrame) -> None:
    visibles = df.drop(columns=["fecha_dt"], errors="ignore").rename(
        columns={
            "id": "ID",
            "fecha": "Fecha",
            "vendedor": "Vendedor",
            "pais": "País",
            "monto_divisa": "Monto",
            "moneda": "Moneda",
            "monto_bs": "Monto local (sin conversión)",
            "tasa": "Tasa",
            "concepto": "Concepto",
            "usuario_id": "Usuario que registró",
            "estado": "Estado",
            "modificado_en": "Última modificación",
            "modificado_por": "Modificado por",
        }
    )
    st.dataframe(visibles, width="stretch", hide_index=True)


def operaciones_view(usuario_id: str | None = None, editable: bool = False) -> None:
    st.title("Gestión de operaciones" if editable else "Mis operaciones")
    df = _cargar_operaciones(usuario_id)
    if df is None:
        return
    if df.empty:
        st.info("Todavía no hay operaciones para mostrar.")
        return

    filtrado = _filtrar_operaciones(df, "operaciones")
    if filtrado.empty:
        st.info("No hay operaciones que coincidan con los filtros.")
        return
    _tabla_operaciones(filtrado)
    st.download_button(
        "Descargar operaciones filtradas (CSV)",
        data=filtrado.drop(columns=["fecha_dt"]).to_csv(index=False).encode("utf-8-sig"),
        file_name=f"operaciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

    if not editable:
        return

    st.markdown("---")
    st.subheader("Corregir o anular una operación")
    registros_activos = filtrado[filtrado["estado"] == "activa"].to_dict("records")
    if not registros_activos:
        st.info("No hay operaciones activas para corregir o anular.")
        return
    operaciones_por_id = {int(fila["id"]): fila for fila in registros_activos}
    seleccion_id = st.selectbox(
        "Operación",
        list(operaciones_por_id),
        format_func=lambda operacion_id: (
            f"#{operacion_id} · "
            f"{operaciones_por_id[operacion_id]['fecha']} · "
            f"{operaciones_por_id[operacion_id]['monto_divisa']} "
            f"{operaciones_por_id[operacion_id]['moneda']} · "
            f"{operaciones_por_id[operacion_id]['vendedor']}"
        ),
        key="operacion_seleccionada",
    )
    seleccion = operaciones_por_id[seleccion_id]
    with st.form(f"editar_operacion_{seleccion_id}"):
        vendedor = st.text_input("Vendedor", value=str(seleccion["vendedor"]))
        paises = sorted(set(PAISES + [str(seleccion["pais"])]))
        pais = st.selectbox("País", paises, index=paises.index(seleccion["pais"]))
        monedas = sorted(set(MONEDAS + [str(seleccion["moneda"])]))
        moneda = st.selectbox(
            "Moneda", monedas, index=monedas.index(seleccion["moneda"])
        )
        monto_divisa = st.number_input(
            "Monto", min_value=0.0, value=float(seleccion["monto_divisa"]), format="%.4f"
        )
        monto_local = st.number_input(
            "Monto local (sin conversión)",
            min_value=0.0,
            value=float(seleccion["monto_bs"]),
            format="%.4f",
        )
        tasa = st.number_input(
            "Tasa", min_value=0.0, value=float(seleccion["tasa"]), format="%.6f"
        )
        concepto = st.text_area("Concepto", value=str(seleccion["concepto"]))
        actualizar = st.form_submit_button("Guardar cambios")
    if actualizar:
        try:
            actualizado = actualizar_operacion(
                int(seleccion_id),
                vendedor=vendedor,
                pais=pais,
                monto_divisa=monto_divisa,
                moneda=moneda,
                monto_bs=monto_local,
                tasa=tasa,
                concepto=concepto,
                modificado_por=st.session_state["usuario_id"],
            )
        except (sqlite3.Error, ValueError):
            logger.exception("No se pudo actualizar la operación")
            st.error("No se pudo actualizar la operación.")
            return
        if actualizado:
            st.success("Operación actualizada.")
            st.rerun()
        st.error("La operación seleccionada ya no está activa.")

    confirmar = st.checkbox(
        f"Confirmo que deseo anular la operación #{seleccion_id}",
        key=f"confirmar_borrado_{seleccion_id}",
    )
    if st.button(
        "Anular operación",
        disabled=not confirmar,
        type="secondary",
        key=f"borrar_{seleccion_id}",
    ):
        try:
            anulada = eliminar_operacion(
                int(seleccion_id), st.session_state["usuario_id"]
            )
        except sqlite3.Error:
            logger.exception("No se pudo anular la operación")
            st.error("No se pudo anular la operación.")
            return
        if anulada:
            st.success("Operación anulada. El registro queda conservado en el historial.")
            st.rerun()
        st.error("La operación seleccionada ya no está activa.")


def dashboard_view() -> None:
    st.title("Dashboard gerencial")
    df = _cargar_operaciones()
    if df is None:
        return
    if df.empty:
        st.info("No hay operaciones registradas todavía.")
        return

    df = df[df["estado"] == "activa"]
    if df.empty:
        st.info("No hay operaciones activas para generar métricas.")
        return

    filtrado = _filtrar_operaciones(df, "dashboard")
    if filtrado.empty:
        st.warning("No hay operaciones que coincidan con los filtros.")
        return

    top_vendedor = (
        filtrado.groupby("vendedor").size().idxmax()
        if filtrado["vendedor"].notna().any()
        else "N/A"
    )
    top_pais = (
        filtrado.groupby("pais").size().idxmax()
        if filtrado["pais"].notna().any()
        else "N/A"
    )
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Operaciones", f"{len(filtrado):,}")
    kpi2.metric("Vendedor con más operaciones", str(top_vendedor))
    kpi3.metric("País con más operaciones", str(top_pais))

    st.subheader("Montos por moneda (sin conversión)")
    resumen_moneda = (
        filtrado.groupby("moneda", dropna=False)
        .agg(operaciones=("id", "count"), monto_total=("monto_divisa", "sum"))
        .reset_index()
        .sort_values("moneda")
    )
    st.dataframe(resumen_moneda, width="stretch", hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Operaciones por moneda")
        por_moneda = (
            filtrado.groupby("moneda").size().rename("operaciones").reset_index()
        )
        st.plotly_chart(
            px.bar(por_moneda, x="moneda", y="operaciones", color="moneda"),
            width="stretch",
        )
    with col2:
        st.subheader("Operaciones por país")
        por_pais = filtrado.groupby("pais").size().rename("operaciones").reset_index()
        st.plotly_chart(
            px.bar(por_pais, x="pais", y="operaciones", color="pais"),
            width="stretch",
        )

    st.subheader("Detalle de operaciones")
    _tabla_operaciones(filtrado)

    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        filtrado.drop(columns=["fecha_dt"]).to_excel(
            writer, index=False, sheet_name="Operaciones"
        )
    st.download_button(
        "Descargar reporte en Excel",
        data=salida.getvalue(),
        file_name=f"reporte_nest_space_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def respaldo_view() -> None:
    st.title("Respaldo de base de datos")
    st.caption("La restauración reemplaza la base actual solo después de validar el archivo.")

    try:
        respaldo = exportar_base_datos()
    except sqlite3.Error:
        logger.exception("No se pudo crear el respaldo de la base de datos")
        st.error("No se pudo crear el respaldo.")
    else:
        st.download_button(
            "Descargar respaldo (.db)",
            data=respaldo,
            file_name=f"nest_space_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
            mime="application/octet-stream",
            width="stretch",
        )

    st.markdown("---")
    st.subheader("Restaurar base de datos")
    archivo = st.file_uploader("Seleccionar archivo de respaldo", type=["db"])
    confirmar = st.checkbox(
        "Entiendo que restaurar reemplazará las operaciones actuales."
    )
    if archivo is not None and st.button(
        "Validar y restaurar respaldo", disabled=not confirmar
    ):
        try:
            restaurar_base_datos(archivo.getvalue())
        except (OSError, sqlite3.Error, ValueError):
            logger.exception("No se pudo restaurar el respaldo")
            st.error("El respaldo no es válido o no se pudo restaurar; la base actual se conserva.")
        else:
            st.success("Respaldo restaurado correctamente.")
            st.rerun()


if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    login_view()
else:
    with st.sidebar:
        st.write(f"**Usuario:** {st.session_state['usuario']}")
        st.write(f"**Rol:** {st.session_state['rol']}")
        if st.session_state["rol"] == "Jefe":
            opciones = [
                "Dashboard",
                "Registrar operación",
                "Gestión de operaciones",
                "Respaldos",
            ]
        else:
            opciones = ["Registrar operación", "Mis operaciones"]
        modo = st.radio("Navegación", opciones)
        if st.button("Cerrar sesión", width="stretch"):
            for clave in ("autenticado", "usuario_id", "usuario", "rol", "borrador_operacion"):
                st.session_state.pop(clave, None)
            st.rerun()

    if modo == "Dashboard":
        dashboard_view()
    elif modo == "Registrar operación":
        registrar_operacion_view()
    elif modo == "Gestión de operaciones":
        operaciones_view(editable=True)
    elif modo == "Mis operaciones":
        operaciones_view(usuario_id=st.session_state["usuario_id"])
    else:
        respaldo_view()
