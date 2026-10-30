import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import extractor


class ExtractionTests(unittest.TestCase):
    def test_extracts_whatsapp_example_with_thousands_separator(self) -> None:
        result = extractor.extraer_datos_de_texto(
            "Pe 23102\nStephane\nBcp\n6.200 bs\n*20 soles*",
            vendedor_default="empleado1",
        )

        self.assertEqual(result["pais"], "Perú")
        self.assertEqual(result["vendedor"], "Stephane")
        self.assertEqual(result["monto_divisa"], 20)
        self.assertEqual(result["moneda"], "PEN")
        self.assertEqual(result["monto_bs"], 6200)
        self.assertEqual(result["tasa"], 310)

    def test_extracts_decimal_values_and_avoids_country_substring_match(self) -> None:
        result = extractor.extraer_datos_de_texto(
            "Colombia\n$1.234,56 a 36,5\nPago de 45.000 bs"
        )

        self.assertEqual(result["pais"], "Colombia")
        self.assertEqual(result["monto_divisa"], 1234.56)
        self.assertEqual(result["tasa"], 36.5)
        self.assertEqual(result["monto_bs"], 45000)

    def test_currency_aliases_match_whole_words(self) -> None:
        result = extractor.extraer_datos_de_texto("México\n30 EUR")

        self.assertEqual(result["pais"], "México")
        self.assertEqual(result["moneda"], "EUR")
        self.assertEqual(result["monto_divisa"], 30)


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "nest_space.db"
        self.db_patch = patch.object(extractor, "DB_PATH", self.db_path)
        self.db_patch.start()
        extractor.crear_tablas()

    def tearDown(self) -> None:
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def _insert(self, usuario_id: str = "empleado1") -> int:
        return extractor.guardar_operacion(
            vendedor="Cliente",
            pais="Perú",
            monto_divisa=20,
            moneda="PEN",
            monto_bs=6200,
            tasa=310,
            concepto="Operación de prueba",
            usuario_id=usuario_id,
        )

    def test_records_are_scoped_by_user_and_can_be_updated_or_deleted(self) -> None:
        operacion_id = self._insert()
        self._insert("empleado2")

        self.assertEqual(len(extractor.obtener_todas_operaciones("empleado1")), 1)
        self.assertEqual(len(extractor.obtener_todas_operaciones()), 2)
        self.assertTrue(
            extractor.actualizar_operacion(
                operacion_id,
                vendedor="Cliente editado",
                pais="Chile",
                monto_divisa=25,
                moneda="PEN",
                monto_bs=0,
                tasa=0,
                concepto="Corregido",
                modificado_por="admin",
            )
        )
        self.assertEqual(
            extractor.obtener_todas_operaciones("empleado1")[0]["vendedor"],
            "Cliente editado",
        )
        self.assertTrue(extractor.eliminar_operacion(operacion_id, "admin"))
        self.assertFalse(extractor.eliminar_operacion(operacion_id, "admin"))
        anulada = next(
            fila
            for fila in extractor.obtener_todas_operaciones("empleado1")
            if fila["id"] == operacion_id
        )
        self.assertEqual(anulada["estado"], "anulada")
        self.assertEqual(anulada["modificado_por"], "admin")

    def test_invalid_amount_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            extractor.guardar_operacion(
                vendedor="Cliente",
                pais="Perú",
                monto_divisa=float("nan"),
                moneda="PEN",
                monto_bs=0,
                tasa=0,
                usuario_id="empleado1",
            )

    def test_legacy_schema_is_migrated_without_losing_records(self) -> None:
        legacy_path = Path(self.temp_dir.name) / "legacy.db"
        with sqlite3.connect(legacy_path) as conn:
            conn.execute(
                """
                CREATE TABLE operaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    vendedor TEXT,
                    pais TEXT,
                    monto_divisa REAL,
                    moneda TEXT,
                    monto_bs REAL,
                    tasa REAL,
                    concepto TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO operaciones
                    (vendedor, pais, monto_divisa, moneda, monto_bs, tasa, concepto)
                VALUES ('Cliente viejo', 'Perú', 20, 'PEN', 6200, 310, 'Histórico')
                """
            )

        with patch.object(extractor, "DB_PATH", legacy_path):
            extractor.crear_tablas()
            registro = extractor.obtener_todas_operaciones()[0]

        self.assertEqual(registro["vendedor"], "Cliente viejo")
        self.assertEqual(registro["usuario_id"], "legacy")

    def test_invalid_restore_keeps_current_database(self) -> None:
        self._insert()
        with self.assertRaises((ValueError, sqlite3.Error)):
            extractor.restaurar_base_datos(b"not a database")
        self.assertEqual(len(extractor.obtener_todas_operaciones()), 1)

    def test_backup_can_be_restored(self) -> None:
        self._insert()
        backup = extractor.exportar_base_datos()
        self._insert("empleado2")

        extractor.restaurar_base_datos(backup)

        self.assertEqual(len(extractor.obtener_todas_operaciones()), 1)


if __name__ == "__main__":
    unittest.main()
