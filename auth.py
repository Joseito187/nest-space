import hashlib
import hmac
import json
import os
import secrets
from typing import TypedDict


_ITERACIONES = 310_000

_DEFAULT_USERS = {
    "admin": {
        "nombre": "Administrador",
        "rol": "Jefe",
        "password_hash": "pbkdf2_sha256$310000$9118fb6e556d0b93584ee03dbe09e209$41ac706dccf6b2fdab5832e9c24c3402fff44b7ccc0e4f35942a686ff877a14a",
    },
    "Jose": {
        "nombre": "Jose Arguelles",
        "rol": "Empleado",
        "password_hash": "pbkdf2_sha256$310000$78c5b07e85578914338f17f98534e152$396a17db9b4521574bd62a064a65112e0352bcd7f83b2119c8b564654586ee29",
    },
}


class Usuario(TypedDict):
    nombre: str
    rol: str
    password_hash: str


def crear_hash_contrasena(contrasena: str) -> str:
    if len(contrasena) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", contrasena.encode("utf-8"), salt, _ITERACIONES
    )
    return f"pbkdf2_sha256${_ITERACIONES}${salt.hex()}${digest.hex()}"


def verificar_contrasena(contrasena: str, password_hash: str) -> bool:
    try:
        algoritmo, iteraciones_texto, salt_hex, digest_hex = password_hash.split("$")
        iteraciones = int(iteraciones_texto)
        if algoritmo != "pbkdf2_sha256" or not 100_000 <= iteraciones <= 2_000_000:
            return False
        salt = bytes.fromhex(salt_hex)
        digest_esperado = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256", contrasena.encode("utf-8"), salt, iteraciones
    )
    return hmac.compare_digest(digest, digest_esperado)


def _formato_hash_valido(password_hash: str) -> bool:
    try:
        algoritmo, iteraciones_texto, salt_hex, digest_hex = password_hash.split("$")
        iteraciones = int(iteraciones_texto)
        salt = bytes.fromhex(salt_hex)
        digest = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    return (
        algoritmo == "pbkdf2_sha256"
        and 100_000 <= iteraciones <= 2_000_000
        and len(salt) >= 16
        and len(digest) == hashlib.sha256().digest_size
    )


def cargar_usuarios() -> dict[str, Usuario]:
    configuracion = os.environ.get("NEST_SPACE_USERS_JSON")
    if not configuracion:
        return {
            username: {
                "nombre": usuario["nombre"],
                "rol": usuario["rol"],
                "password_hash": usuario["password_hash"],
            }
            for username, usuario in _DEFAULT_USERS.items()
        }
    try:
        usuarios_raw = json.loads(configuracion)
    except json.JSONDecodeError as exc:
        raise ValueError("NEST_SPACE_USERS_JSON debe contener JSON válido.") from exc
    if not isinstance(usuarios_raw, dict):
        raise ValueError("La configuración de usuarios debe ser un objeto JSON.")

    usuarios: dict[str, Usuario] = {}
    for username, usuario in usuarios_raw.items():
        if (
            not isinstance(username, str)
            or not username.strip()
            or not isinstance(usuario, dict)
        ):
            raise ValueError("Cada cuenta debe tener un nombre y una configuración.")
        nombre = usuario.get("nombre")
        rol = usuario.get("rol")
        password_hash = usuario.get("password_hash")
        if (
            not isinstance(nombre, str)
            or not nombre.strip()
            or rol not in {"Jefe", "Empleado"}
            or not isinstance(password_hash, str)
            or not _formato_hash_valido(password_hash)
        ):
            raise ValueError(
                f"La configuración de la cuenta «{username}» no es válida."
            )
        usuarios[username] = {
            "nombre": nombre.strip(),
            "rol": rol,
            "password_hash": password_hash,
        }
    return usuarios
