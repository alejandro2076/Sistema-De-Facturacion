from fastapi.testclient import TestClient
import os
os.environ['ELECTROSTORE_DB'] = 'test_electrostore_debug.db'
# ensure src on path
import sys
sys.path.insert(0, 'c:/Users/Usuario/Documents/GitHub/Sistema-De-Facturacion/src')
from api import app, hash_password
from main import SessionLocal, UsuarioModel
# Setup DB user
db = SessionLocal()
db.query(UsuarioModel).delete()
password = hash_password('admin123')
admin = UsuarioModel(username='admin', password=password, rol='admin', nombre='Administrador')
db.add(admin)
db.commit()
db.close()
client = TestClient(app)
# Login
resp = client.post('/login', data={'username':'admin','password':'admin123'})
print('login status', resp.status_code, resp.json())
token = resp.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}
# Create product
producto_data = {
    'codigo_barras':'1234567890123',
    'nombre':'Producto Test',
    'precio':100.0,
    'stock':10,
    'categoria':'Test',
    'numero_serie':'SN-TEST-001'
}
resp2 = client.post('/productos', json=producto_data, headers=headers)
print('create product status', resp2.status_code)
try:
    print('body:', resp2.json())
except Exception as e:
    print('no json body', e)
