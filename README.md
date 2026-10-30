# Nest Space

Aplicación local de Streamlit para registrar y consultar operaciones. La base SQLite
predeterminada es `nest_space.db`, junto a `extractor.py`. Se puede elegir otra ruta
con `NEST_SPACE_DB_PATH`.

## Configurar cuentas

La aplicación incluye dos cuentas predeterminadas para arrancar sin configuración
extra: `admin` y `Jose`. Si desea personalizar o ampliar usuarios, puede definir
`NEST_SPACE_USERS_JSON` en el entorno donde ejecuta Streamlit. Cada contraseña debe
tener al menos 12 caracteres y guardarse como hash PBKDF2, no como texto plano.

Usuarios por defecto:

- `admin` / `Admin1234567` (rol `Jefe`)
- `Jose` / `Joseito12345` (nombre `Jose Arguelles`, rol `Empleado`)

Si desea generar otro hash localmente:

```sh
./.venv/bin/python -c 'from getpass import getpass; from auth import crear_hash_contrasena; print(crear_hash_contrasena(getpass("Contraseña nueva: ")))'
```

Configure el JSON con el hash obtenido (reemplace `HASH_PBKDF2`):

```json
{
  "admin": {
    "nombre": "Administrador",
    "rol": "Jefe",
    "password_hash": "HASH_PBKDF2"
  },
  "Jose": {
    "nombre": "Jose Arguelles",
    "rol": "Empleado",
    "password_hash": "HASH_PBKDF2"
  }
}
```

Los únicos roles aceptados son `Jefe` y `Empleado`. Si se define
`NEST_SPACE_USERS_JSON`, ese valor tiene prioridad sobre las cuentas por defecto.
Evite poner contraseñas, hashes o el JSON en el código, en archivos versionados o
en comandos guardados en el historial del shell.

## Ejecutar

Con las dependencias de `requirements.txt` instaladas y `NEST_SPACE_USERS_JSON`
configurado en el entorno:

```sh
streamlit run app.py
```

## Probar

```sh
./.venv/bin/python -m unittest discover -v
```

## Notas de datos

- Los importes se resumen por moneda y **no se convierten ni se suman entre monedas**.
- `monto_bs` es un campo histórico; algunos mensajes lo usan para un importe local
  expresado en unidades diferentes. La interfaz lo etiqueta como monto local y no
  lo agrega en los indicadores.
- Las operaciones se atribuyen al usuario que las registra. Las correcciones y
  anulaciones quedan marcadas con su estado y el usuario que las modificó; no se
  borran físicamente. El dashboard excluye las anuladas.
- Las operaciones existentes se conservan al migrar la base. Como no tenían usuario
  asociado, se atribuyen a `legacy` y solo aparecen en la vista del rol `Jefe`.
- La restauración comprueba la integridad y el esquema antes de reemplazar la base.
- Si una contraseña real estuvo en un archivo o se compartió, cámbiela también en
  el servicio correspondiente. Retirar el archivo no revoca la credencial ni elimina
  posibles copias de historiales de Git.
