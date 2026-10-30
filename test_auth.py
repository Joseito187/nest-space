import os
import unittest
from unittest.mock import patch

from auth import cargar_usuarios, crear_hash_contrasena, verificar_contrasena


class AuthTests(unittest.TestCase):
    def test_password_hash_verifies_without_storing_plaintext(self) -> None:
        password = "una-clave-larga-de-prueba"
        password_hash = crear_hash_contrasena(password)

        self.assertNotIn(password, password_hash)
        self.assertTrue(verificar_contrasena(password, password_hash))
        self.assertFalse(verificar_contrasena("incorrecta", password_hash))

    def test_password_hash_requires_a_long_password(self) -> None:
        with self.assertRaises(ValueError):
            crear_hash_contrasena("corta")

    def test_user_configuration_is_loaded_from_environment(self) -> None:
        password_hash = crear_hash_contrasena("clave-de-prueba")
        configuration = (
            '{"admin":{"nombre":"Administración","rol":"Jefe",'
            f'"password_hash":"{password_hash}"' + "}}"
        )
        with patch.dict(os.environ, {"NEST_SPACE_USERS_JSON": configuration}):
            usuarios = cargar_usuarios()

        self.assertEqual(usuarios["admin"]["rol"], "Jefe")

    def test_missing_users_uses_default_configuration(self) -> None:
        with patch.dict(os.environ):
            os.environ.pop("NEST_SPACE_USERS_JSON", None)
            usuarios = cargar_usuarios()
            self.assertEqual(set(usuarios), {"admin", "Jose"})
            self.assertEqual(usuarios["Jose"]["nombre"], "Jose Arguelles")
            self.assertEqual(usuarios["Jose"]["rol"], "Empleado")

    def test_malformed_user_configuration_is_rejected(self) -> None:
        with patch.dict(os.environ, {"NEST_SPACE_USERS_JSON": "not-json"}):
            with self.assertRaises(ValueError):
                cargar_usuarios()


if __name__ == "__main__":
    unittest.main()
