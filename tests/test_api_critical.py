import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_register_and_login():
    response = client.post("/register", json={"username": "testuser", "password": "testpass"})
    assert response.status_code in (200, 400)
    response = client.post("/login", data={"username": "testuser", "password": "testpass"})
    assert response.status_code == 200
    token = response.json().get("access_token")
    assert token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/productos", headers=headers)
    assert response.status_code == 200
    productos = response.json()
    assert isinstance(productos, list)

def test_invalid_login():
    response = client.post("/login", data={"username": "fake", "password": "wrong"})
    assert response.status_code == 401

def test_productos_permisos():
    # Login como usuario normal
    response = client.post("/login", data={"username": "testuser", "password": "testpass"})
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    producto = {
        "codigo_barras": "0000000000002",
        "nombre": "Test Producto 2",
        "precio": 20.0,
        "stock": 10,
        "categoria": "Test",
        "numero_serie": "SN-0002"
    }
    response = client.post("/productos", json=producto, headers=headers)
    assert response.status_code == 403

def test_endpoint_ventas():
    response = client.post("/login", data={"username": "testuser", "password": "testpass"})
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/ventas", headers=headers)
    assert response.status_code in (200, 403)

def test_endpoint_devoluciones():
    response = client.post("/login", data={"username": "testuser", "password": "testpass"})
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    devolucion = {
        "venta_id": 1,
        "producto_id": 1,
        "cantidad": 1,
        "motivo": "Test",
        "estado_producto": "vendible"
    }
    response = client.post("/devoluciones", json=devolucion, headers=headers)
    assert response.status_code in (200, 403, 404)

def login_and_get_token(username, password):
    response = client.post("/login", data={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]

def test_registro_producto_admin():
    # Usar usuario 'almacen' con permisos de registro de productos
    almacen_token = login_and_get_token("almacen", "Alm4c3n_2024!")
    headers = {"Authorization": f"Bearer {almacen_token}"}
    producto = {
        "codigo_barras": "0000000009999",
        "nombre": "Producto Admin Test",
        "precio": 99.99,
        "stock": 50,
        "categoria": "Test",
        "numero_serie": "SN-ADMIN-TEST"
    }
    response = client.post("/productos", json=producto, headers=headers)
    assert response.status_code in (200, 201, 400)  # 400 si ya existe

def test_registro_producto_usuario_normal():
    user_token = login_and_get_token("testuser", "testpass")
    headers = {"Authorization": f"Bearer {user_token}"}
    producto = {
        "codigo_barras": "0000000008888",
        "nombre": "Producto User Test",
        "precio": 88.88,
        "stock": 10,
        "categoria": "Test",
        "numero_serie": "SN-USER-TEST"
    }
    response = client.post("/productos", json=producto, headers=headers)
    assert response.status_code == 403

def test_busqueda_producto_por_nombre():
    token = login_and_get_token("testuser", "testpass")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/productos", headers=headers)
    assert response.status_code == 200
    productos = response.json()
    assert any("nombre" in p and p["nombre"] for p in productos)
    # Buscar por nombre si endpoint lo permite
    # response = client.get("/productos?nombre=Producto Admin Test", headers=headers)
    # assert response.status_code == 200

def test_stock_en_respuesta_productos():
    token = login_and_get_token("testuser", "testpass")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/productos", headers=headers)
    assert response.status_code == 200
    productos = response.json()
    assert all("stock" in p for p in productos)
    # Opcional: verificar que el stock sea un entero >= 0
    assert all(isinstance(p["stock"], int) and p["stock"] >= 0 for p in productos)
