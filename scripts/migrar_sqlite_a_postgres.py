import sqlite3
import psycopg2
from psycopg2.extras import execute_values

# Configuración origen (SQLite)
SQLITE_DB = '../electrostore.db'
# Configuración destino (PostgreSQL)
PG_CONN = {
    'host': 'localhost',
    'port': 9040,
    'dbname': 'electrostore',
    'user': 'Admin',
    'password': 'password'
}

def migrar_tabla(tabla):
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cur = sqlite_conn.cursor()
    pg_conn = psycopg2.connect(**PG_CONN)
    pg_cur = pg_conn.cursor()
    sqlite_cur.execute(f'SELECT * FROM {tabla}')
    rows = sqlite_cur.fetchall()
    columnas = [desc[0] for desc in sqlite_cur.description]
    values_str = ','.join(['%s'] * len(columnas))
    insert_query = f'INSERT INTO {tabla} ({", ".join(columnas)}) VALUES ({values_str}) ON CONFLICT DO NOTHING'
    for row in rows:
        try:
            pg_cur.execute(insert_query, row)
        except Exception as e:
            print(f"Error insertando en {tabla}: {e}")
    pg_conn.commit()
    sqlite_conn.close()
    pg_conn.close()
    print(f"Migración de {tabla} completada.")

def main():
    tablas = ['usuarios', 'productos', 'ventas', 'detalle_venta', 'devoluciones', 'empresa', 'secuencia_factura']
    for tabla in tablas:
        migrar_tabla(tabla)

if __name__ == "__main__":
    main()
