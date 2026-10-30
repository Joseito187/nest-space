import math
import os
import re
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


DB_PATH = Path(
    os.environ.get("NEST_SPACE_DB_PATH", Path(__file__).with_name("nest_space.db"))
).expanduser().resolve()


@contextmanager
def obtener_conexion() -> Generator[sqlite3.Connection, None, None]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def crear_tablas() -> None:
    with obtener_conexion() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                vendedor TEXT NOT NULL,
                pais TEXT NOT NULL,
                monto_divisa REAL NOT NULL,
                moneda TEXT NOT NULL,
                monto_bs REAL NOT NULL,
                tasa REAL NOT NULL,
                concepto TEXT NOT NULL DEFAULT '',
                usuario_id TEXT NOT NULL DEFAULT 'legacy',
                estado TEXT NOT NULL DEFAULT 'activa',
                modificado_en TIMESTAMP,
                modificado_por TEXT
            )
            """
        )
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(operaciones)")
        }
        if "usuario_id" not in columns:
            conn.execute(
                "ALTER TABLE operaciones "
                "ADD COLUMN usuario_id TEXT NOT NULL DEFAULT 'legacy'"
            )
        migrations = {
            "estado": "TEXT NOT NULL DEFAULT 'activa'",
            "modificado_en": "TIMESTAMP",
            "modificado_por": "TEXT",
        }
        for column, definition in migrations.items():
            if column not in columns:
                conn.execute(
                    f"ALTER TABLE operaciones ADD COLUMN {column} {definition}"
                )


def _validar_importes(
    monto_divisa: float, monto_bs: float, tasa: float
) -> None:
    valores = (monto_divisa, monto_bs, tasa)
    if not all(math.isfinite(float(valor)) for valor in valores):
        raise ValueError("Los importes y la tasa deben ser números finitos.")
    if monto_divisa <= 0 or monto_bs < 0 or tasa < 0:
        raise ValueError("El monto debe ser positivo y la tasa no puede ser negativa.")


def guardar_operacion(
    vendedor: str,
    pais: str,
    monto_divisa: float,
    moneda: str,
    monto_bs: float,
    tasa: float,
    concepto: str = "",
    usuario_id: str = "legacy",
) -> int:
    _validar_importes(monto_divisa, monto_bs, tasa)
    with obtener_conexion() as conn:
        cursor = conn.execute(
            """
            INSERT INTO operaciones
                (vendedor, pais, monto_divisa, moneda, monto_bs, tasa,
                 concepto, usuario_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vendedor.strip(),
                pais.strip(),
                float(monto_divisa),
                moneda.strip().upper(),
                float(monto_bs),
                float(tasa),
                concepto.strip(),
                usuario_id.strip(),
            ),
        )
        return int(cursor.lastrowid)


def obtener_todas_operaciones(
    usuario_id: str | None = None,
) -> list[dict[str, object]]:
    with obtener_conexion() as conn:
        if usuario_id is None:
            filas = conn.execute(
                "SELECT * FROM operaciones ORDER BY fecha DESC, id DESC"
            ).fetchall()
        else:
            filas = conn.execute(
                """
                SELECT * FROM operaciones
                WHERE usuario_id = ?
                ORDER BY fecha DESC, id DESC
                """,
                (usuario_id,),
            ).fetchall()
        return [dict(fila) for fila in filas]


def actualizar_operacion(
    operacion_id: int,
    *,
    vendedor: str,
    pais: str,
    monto_divisa: float,
    moneda: str,
    monto_bs: float,
    tasa: float,
    concepto: str,
    modificado_por: str,
) -> bool:
    _validar_importes(monto_divisa, monto_bs, tasa)
    with obtener_conexion() as conn:
        cursor = conn.execute(
            """
            UPDATE operaciones
            SET vendedor = ?, pais = ?, monto_divisa = ?, moneda = ?,
                monto_bs = ?, tasa = ?, concepto = ?,
                modificado_en = CURRENT_TIMESTAMP, modificado_por = ?
            WHERE id = ? AND estado = 'activa'
            """,
            (
                vendedor.strip(),
                pais.strip(),
                float(monto_divisa),
                moneda.strip().upper(),
                float(monto_bs),
                float(tasa),
                concepto.strip(),
                modificado_por.strip(),
                operacion_id,
            ),
        )
        return cursor.rowcount == 1


def eliminar_operacion(operacion_id: int, usuario_id: str) -> bool:
    with obtener_conexion() as conn:
        cursor = conn.execute(
            """
            UPDATE operaciones
            SET estado = 'anulada', modificado_en = CURRENT_TIMESTAMP,
                modificado_por = ?
            WHERE id = ? AND estado = 'activa'
            """,
            (usuario_id.strip(), operacion_id),
        )
        return cursor.rowcount == 1


def exportar_base_datos() -> bytes:
    with obtener_conexion() as source:
        destination = sqlite3.connect(":memory:")
        try:
            source.backup(destination)
            return destination.serialize()
        finally:
            destination.close()


def restaurar_base_datos(contenido: bytes) -> None:
    if not contenido:
        raise ValueError("El archivo de respaldo está vacío.")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=DB_PATH.parent, suffix=".db", delete=False
        ) as archivo:
            temporal = Path(archivo.name)
            archivo.write(contenido)

        conn = sqlite3.connect(temporal)
        try:
            resultado = conn.execute("PRAGMA integrity_check").fetchone()
            if not resultado or resultado[0] != "ok":
                raise ValueError("La base de datos no pasó la comprobación de integridad.")

            tablas = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            if "operaciones" not in tablas:
                raise ValueError("El archivo no contiene la tabla de operaciones.")

            columnas = {
                row[1] for row in conn.execute("PRAGMA table_info(operaciones)")
            }
            requeridas = {
                "id",
                "fecha",
                "vendedor",
                "pais",
                "monto_divisa",
                "moneda",
                "monto_bs",
                "tasa",
                "concepto",
            }
            if not requeridas.issubset(columnas):
                raise ValueError("La tabla de operaciones tiene un formato incompatible.")
            if "usuario_id" not in columnas:
                conn.execute(
                    "ALTER TABLE operaciones "
                    "ADD COLUMN usuario_id TEXT NOT NULL DEFAULT 'legacy'"
                )
            migrations = {
                "estado": "TEXT NOT NULL DEFAULT 'activa'",
                "modificado_en": "TIMESTAMP",
                "modificado_por": "TEXT",
            }
            for columna, definicion in migrations.items():
                if columna not in columnas:
                    conn.execute(
                        f"ALTER TABLE operaciones ADD COLUMN {columna} {definicion}"
                    )
            conn.commit()
        finally:
            conn.close()

        os.replace(temporal, DB_PATH)
        temporal = None
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


_PAISES = {
    "pe": "Perú",
    "peru": "Perú",
    "perú": "Perú",
    "mexico": "México",
    "méxico": "México",
    "chile": "Chile",
    "colombia": "Colombia",
    "venezuela": "Venezuela",
    "eeuu": "EEUU",
    "españa": "España",
}
_MONEDAS = {
    "soles": "PEN",
    "pen": "PEN",
    "mxn": "MXN",
    "clp": "CLP",
    "usd": "USD",
    "eur": "EUR",
    "cop": "COP",
}


def _parsear_numero(valor: str) -> float:
    valor = valor.strip().replace(" ", "")
    if "." in valor and "," in valor:
        separador_decimal = "." if valor.rfind(".") > valor.rfind(",") else ","
        separador_miles = "," if separador_decimal == "." else "."
        valor = valor.replace(separador_miles, "")
        valor = valor.replace(separador_decimal, ".")
    elif "." in valor or "," in valor:
        separador = "." if "." in valor else ","
        partes = valor.split(separador)
        if len(partes) > 2 or len(partes[-1]) == 3:
            valor = "".join(partes)
        else:
            valor = separador.join(partes[:-1]) + "." + partes[-1]
    return float(valor)


def extraer_datos_de_texto(texto: str, vendedor_default: str = "Admin") -> dict[str, object]:
    limpio = texto.replace("*", "")
    datos: dict[str, object] = {
        "monto_divisa": 0.0,
        "moneda": "USD",
        "pais": "Venezuela",
        "tasa": 0.0,
        "monto_bs": 0.0,
        "vendedor": vendedor_default,
        "concepto": texto,
    }

    lineas = [linea.strip() for linea in limpio.splitlines() if linea.strip()]
    for alias, pais in _PAISES.items():
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", limpio, re.IGNORECASE):
            datos["pais"] = pais
            break

    vendedor_match = re.search(r"\(([^)]+)\)", limpio)
    if vendedor_match:
        datos["vendedor"] = vendedor_match.group(1).strip()
    elif len(lineas) > 1:
        posible_vendedor = lineas[1]
        extras = {
            "bcp",
            "bbva",
            "pago móvil",
            "zelle",
            "m/p",
            "banesco",
            "venezuela",
            "vista",
            "prepago tenpo",
        }
        if (
            not any(char.isdigit() for char in posible_vendedor)
            and posible_vendedor.casefold() not in extras
        ):
            datos["vendedor"] = posible_vendedor

    for alias, moneda in _MONEDAS.items():
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", limpio, re.IGNORECASE):
            datos["moneda"] = moneda
            break

    monto_tasa = re.search(
        r"(\$?\s*[\d.,]+)\s+a\s+([\d.,]+)", limpio, re.IGNORECASE
    )
    if monto_tasa:
        datos["monto_divisa"] = _parsear_numero(
            monto_tasa.group(1).replace("$", "")
        )
        datos["tasa"] = _parsear_numero(monto_tasa.group(2))
    else:
        cantidad_moneda = re.search(
            r"(\d[\d.,]*)\s*(soles|PEN|USD|EUR|COP|CLP|MXN)\b",
            limpio,
            re.IGNORECASE,
        )
        cantidad_dolar = re.search(r"\$\s*(\d[\d.,]*)", limpio)
        if cantidad_moneda:
            datos["monto_divisa"] = _parsear_numero(cantidad_moneda.group(1))
        elif cantidad_dolar:
            datos["monto_divisa"] = _parsear_numero(cantidad_dolar.group(1))

    monto_local = re.search(
        r"(?:\b(?:bs|clp)\.?\s*([\d.,]+)|([\d.,]+)\s*(?:bs|clp)\b)",
        limpio,
        re.IGNORECASE,
    )
    if monto_local:
        datos["monto_bs"] = _parsear_numero(
            monto_local.group(1) or monto_local.group(2)
        )

    monto_divisa = float(datos["monto_divisa"])
    monto_bs = float(datos["monto_bs"])
    tasa = float(datos["tasa"])
    if tasa == 0 and monto_divisa > 0 and monto_bs > 0:
        datos["tasa"] = monto_bs / monto_divisa
    elif monto_bs == 0 and monto_divisa > 0 and tasa > 0:
        datos["monto_bs"] = monto_divisa * tasa
    return datos


crear_tablas()
