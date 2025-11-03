import pytest
from fastapi.testclient import TestClient
from api import app, hash_password
from main import SessionLocal, UsuarioModel
import sqlite3
import os
import bcrypt

# Forzar el uso de la base de datos de test
os.environ["ELECTROSTORE_DB"] = "test_electrostore.db"

@pytest.fixture
def client():
    import os
    os.environ["ELECTROSTORE_DB"] = "test_electrostore.db"
    # Crear base de datos y usuario admin con ORM
    db = SessionLocal()
    db.query(UsuarioModel).delete()  # Limpiar usuarios
    password = hash_password("admin123")
    admin = UsuarioModel(username="admin", password=password, rol="admin", nombre="Administrador")
    db.add(admin)
    db.commit()
    db.close()
    yield TestClient(app)
    # Eliminar la base de datos después de las pruebas
    test_db = "test_electrostore.db"
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except PermissionError:
            pass

def get_auth_header(client):
    login_data = {"username": "admin", "password": "admin123"}
    response = client.post("/login", data=login_data)
    print("LOGIN RESPONSE:", response.json())  # Depuración
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_venta_flujo_completo(client):
    headers = get_auth_header(client)
    producto_data = {
        "codigo_barras": "1234567890123",
        "nombre": "Producto Test",
        "precio": 100.0,
        "stock": 10,
        "categoria": "Test",
        "numero_serie": "SN-TEST-001"
    }
    response = client.post("/productos", json=producto_data, headers=headers)
    assert response.status_code == 200
    producto_id = response.json()["id"]
    response = client.get(f"/productos/{producto_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["stock"] == 10
    venta_data = {
        "productos": [{"id": producto_id, "cantidad": 2, "precio": 100.0}],
        "metodo_pago": "Efectivo"
    }
    response = client.post("/ventas", json=venta_data, headers=headers)
    assert response.status_code == 200
    venta_id = response.json()["id"]
    response = client.get(f"/productos/{producto_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["stock"] == 8
    devolucion_data = {
        "venta_id": venta_id,
        "producto_id": producto_id,
        "cantidad": 1,
        "motivo": "Defectuoso",
        "estado_producto": "defectuoso"
    }
    response = client.post("/devoluciones", json=devolucion_data, headers=headers)
    assert response.status_code == 200
    response = client.get(f"/productos/{producto_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["stock"] == 9  # Corregido: el stock debe ser 9 tras la devolución

def test_venta_sin_stock(client):
    headers = get_auth_header(client)
    producto_data = {
        "codigo_barras": "1234567890124",
        "nombre": "Producto Test 2",
        "precio": 50.0,
        "stock": 1,
        "categoria": "Test",
        "numero_serie": "SN-TEST-002"
    }
    response = client.post("/productos", json=producto_data, headers=headers)
    assert response.status_code == 200
    producto_id = response.json()["id"]
    venta_data = {
        "productos": [{"id": producto_id, "cantidad": 2, "precio": 50.0}],
        "metodo_pago": "Efectivo"
    }
    response = client.post("/ventas", json=venta_data, headers=headers)
    assert response.status_code == 500
    response = client.get(f"/productos/{producto_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["stock"] == 1
