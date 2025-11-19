import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlalchemy
from sqlalchemy.orm import sessionmaker
from src.main import Base, engine, SessionLocal, UsuarioModel
from src.api import hash_password

def crear_usuarios_iniciales():
    Session = sessionmaker(bind=engine)
    db = Session()
    usuarios = [
        {"username": "devteam", "password": hash_password("DevTeam_2024!"), "rol": "desarrollo", "nombre": "Equipo Desarrollo"},
        {"username": "superadmin", "password": hash_password("Super@dmin2024!"), "rol": "soporte", "nombre": "Super Soporte"},
        {"username": "gerente", "password": hash_password("G3r3nt3_2024$"), "rol": "gerente", "nombre": "Gerente General"},
        {"username": "cajero", "password": hash_password("C@j3r0_2024!"), "rol": "cajero", "nombre": "Cajero Principal"},
        {"username": "almacen", "password": hash_password("Alm4c3n_2024!"), "rol": "almacen", "nombre": "Encargado Almacén"},
    ]
    for u in usuarios:
        existe = db.query(UsuarioModel).filter(UsuarioModel.username == u["username"]).first()
        if not existe:
            user = UsuarioModel(**u)
            db.add(user)
    db.commit()
    db.close()
    print("Usuarios iniciales creados correctamente.")

if __name__ == "__main__":
    crear_usuarios_iniciales()
