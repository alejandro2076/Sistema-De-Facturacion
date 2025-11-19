import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
from fastapi.testclient import TestClient
from src.api import app

logging.basicConfig(filename="../validation_report.log", level=logging.INFO, format='%(levelname)s: %(message)s')

def critical_check():
    client = TestClient(app)
    print("[INFO] Iniciando validación crítica de la API...")
    # Prueba registro/login
    r = client.post("/register", json={"username": "audit", "password": "audit"})
    if r.status_code not in (200, 400):
        logging.error(f"Registro falló: {r.text}")
        print(f"[ERROR] Registro falló: {r.text}")
    r = client.post("/login", data={"username": "audit", "password": "audit"})
    if r.status_code != 200:
        logging.critical(f"Login falló: {r.text}")
        print(f"[CRITICAL] Login falló: {r.text}")
        return
    else:
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        # Prueba acceso a productos
        r = client.get("/productos", headers=headers)
        if r.status_code != 200:
            logging.critical(f"Acceso a productos falló: {r.text}")
            print(f"[CRITICAL] Acceso a productos falló: {r.text}")
        else:
            print("[OK] Acceso a productos exitoso.")
            productos = r.json()
            if not isinstance(productos, list):
                logging.warning("La respuesta de productos no es una lista.")
                print("[WARNING] La respuesta de productos no es una lista.")
            elif len(productos) == 0:
                logging.warning("No hay productos registrados en el sistema.")
                print("[WARNING] No hay productos registrados en el sistema.")
        # Prueba creación de producto (requiere rol admin/gerente, aquí solo se valida error de permisos)
        producto = {
            "codigo_barras": "0000000000001",
            "nombre": "Test Producto",
            "precio": 10.0,
            "stock": 5,
            "categoria": "Test",
            "numero_serie": "SN-0001"
        }
        r = client.post("/productos", json=producto, headers=headers)
        if r.status_code == 403:
            logging.info("Intento de creación de producto sin permisos correctamente bloqueado.")
            print("[OK] Creación de producto sin permisos bloqueada.")
        elif r.status_code == 200:
            logging.critical("Se pudo crear un producto sin permisos de admin/gerente.")
            print("[CRITICAL] Se pudo crear un producto sin permisos de admin/gerente.")
        # Prueba endpoint de ventas (debería devolver lista o error de permisos)
        r = client.get("/ventas", headers=headers)
        if r.status_code == 200:
            print("[OK] Acceso a ventas exitoso.")
        elif r.status_code == 403:
            print("[OK] Acceso a ventas correctamente restringido por permisos.")
        else:
            logging.warning(f"Respuesta inesperada en /ventas: {r.status_code}")
            print(f"[WARNING] Respuesta inesperada en /ventas: {r.status_code}")
        # Prueba endpoint de devoluciones (debería devolver lista o error de permisos)
        r = client.post("/devoluciones", json={
            "venta_id": 1,
            "producto_id": 1,
            "cantidad": 1,
            "motivo": "Test",
            "estado_producto": "vendible"
        }, headers=headers)
        if r.status_code in (200, 403, 404):
            print(f"[OK] Respuesta esperada en /devoluciones: {r.status_code}")
        else:
            logging.warning(f"Respuesta inesperada en /devoluciones: {r.status_code}")
            print(f"[WARNING] Respuesta inesperada en /devoluciones: {r.status_code}")

if __name__ == "__main__":
    critical_check()
    print("[INFO] Validación completa. Revisa validation_report.log para advertencias y errores.")
