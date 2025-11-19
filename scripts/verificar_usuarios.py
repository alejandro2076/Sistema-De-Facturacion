import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy.orm import sessionmaker
from src.main import engine, UsuarioModel

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
