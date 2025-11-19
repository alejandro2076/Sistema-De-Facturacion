import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy.orm import sessionmaker
from src.main import engine, UsuarioModel
import psycopg2

PG_CONN = {
    'host': 'localhost',
    'port': 9040,
    'dbname': 'electrostore',
    'user': 'Admin',
    'password': 'password'
}

Session = sessionmaker(bind=engine)
db = Session()
usuarios = db.query(UsuarioModel).all()
if not usuarios:
    print("No hay usuarios en la base de datos.")
else:
    print("Usuarios encontrados:")
    for u in usuarios:
        print(f"- {u.username} | {u.rol} | {u.nombre}")
db.close()

def listar_productos():
    conn = psycopg2.connect(**PG_CONN)
    cur = conn.cursor()
    cur.execute('SELECT id, codigo_barras, nombre, precio, stock, categoria, numero_serie FROM productos')
    productos = cur.fetchall()
    for p in productos:
        print(p)
    cur.close()
    conn.close()

if __name__ == "__main__":
    listar_productos()
