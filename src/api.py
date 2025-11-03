# ...existing code from api.py...
from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from typing import List, Optional
import sqlite3
import jwt
from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler
import os
from fastapi.responses import JSONResponse
import bcrypt
from logging_config import audit_logger
from prometheus_fastapi_instrumentator import Instrumentator
from main import SessionLocal, ProductoModel, VentaModel, DetalleVentaModel, DevolucionModel, UsuarioModel, ProductoSchema

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Configuración de la aplicación FastAPI
app = FastAPI(
    title="ElectroStore API",
    description="API REST para el sistema ERP/POS ElectroStore",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

Instrumentator().instrument(app).expose(app)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de seguridad
security = OAuth2PasswordBearer(tokenUrl="/login")
SECRET_KEY = os.environ.get("SECRET_KEY", "electrostore_secret_key")
ALGORITHM = "HS256"

# Modelos de datos para la API
class Producto(BaseModel):
    id: Optional[int] = None
    codigo_barras: str
    nombre: str
    precio: float
    stock: int
    categoria: str
    numero_serie: str

class Venta(BaseModel):
    id: Optional[int] = None
    fecha: str
    total: float
    estado_caja: str
    metodo_pago: str
    cliente_id: Optional[int] = None

class VentaCreate(BaseModel):
    productos: List[dict]
    metodo_pago: str
    cliente_id: Optional[int] = None

class Devolucion(BaseModel):
    id: Optional[int] = None
    venta_id: int
    producto_id: int
    cantidad: int
    motivo: str
    estado_producto: str
    fecha: Optional[str] = None  # Ahora es opcional
    autorizado_por: Optional[str] = None

class Usuario(BaseModel):
    id: Optional[int] = None
    username: str
    rol: str
    nombre: str

class LoginRequest(BaseModel):
    username: str
    password: str

# Utilidades de base de datos
def get_db_connection():
    db_path = os.environ.get('ELECTROSTORE_DB', 'electrostore.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Utilidades de autenticación

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def crear_token(usuario: dict):
    payload = {
        "sub": usuario["username"],
        "rol": usuario["rol"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verificar_token(token: str = Depends(security)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

# Endpoints de autenticación
@app.post("/register", response_model=Usuario)
def register_user(user: LoginRequest):
    db = SessionLocal()
    hashed_password = hash_password(user.password)
    nuevo_usuario = UsuarioModel(
        username=user.username,
        password=hashed_password,
        rol="vendedor",
        nombre=user.username
    )
    db.add(nuevo_usuario)
    try:
        db.commit()
        db.refresh(nuevo_usuario)
        audit_logger.info(f"Usuario registrado: {user.username}")
        return Usuario(id=nuevo_usuario.id, username=user.username, rol="vendedor", nombre=user.username)
    except Exception:
        db.rollback()
        audit_logger.info(f"Intento de registro fallido para usuario existente: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe"
        )
    finally:
        db.close()

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    usuario = db.query(UsuarioModel).filter(UsuarioModel.username == form_data.username).first()
    db.close()
    if not usuario or not verify_password(form_data.password, usuario.password):
        audit_logger.info(f"Intento de login fallido: usuario no encontrado o contraseña incorrecta {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    token = crear_token(usuario.__dict__)
    logger.info(f"Usuario {form_data.username} ha iniciado sesión")
    audit_logger.info(f"Login exitoso: {form_data.username}")
    return {"access_token": token, "token_type": "bearer"}

# Endpoints de productos
@app.get("/productos", response_model=List[Producto])
def obtener_productos(skip: int = 0, limit: int = 100, payload: dict = Depends(verificar_token)):
    db = SessionLocal()
    productos = db.query(ProductoModel).order_by(ProductoModel.nombre).offset(skip).limit(limit).all()
    db.close()
    return [producto.__dict__ for producto in productos]

@app.get("/productos/{producto_id}", response_model=Producto)
def obtener_producto(producto_id: int, payload: dict = Depends(verificar_token)):
    db = SessionLocal()
    producto = db.query(ProductoModel).filter(ProductoModel.id == producto_id).first()
    db.close()
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    return producto.__dict__

@app.post("/productos", response_model=Producto)
def crear_producto(producto: Producto, payload: dict = Depends(verificar_token)):
    if payload["rol"] not in ["admin", "gerente"]:
        audit_logger.info(f"Intento de creación de producto sin permisos por {payload['sub']}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para realizar esta acción"
        )
    # Validar con Pydantic antes de guardar
    try:
        validated = ProductoSchema(**producto.dict())
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    db = SessionLocal()
    nuevo_producto = ProductoModel(
        codigo_barras=validated.codigo_barras,
        nombre=validated.nombre,
        precio=validated.precio,
        stock=validated.stock,
        categoria=validated.categoria,
        numero_serie=validated.numero_serie
    )
    db.add(nuevo_producto)
    try:
        db.commit()
        db.refresh(nuevo_producto)
        producto.id = nuevo_producto.id
        logger.info(f"Producto {producto.nombre} creado por {payload['sub']}")
        audit_logger.info(f"Producto creado: {producto.nombre} por {payload['sub']}")
        return producto
    except Exception:
        db.rollback()
        audit_logger.info(f"Intento de creación de producto fallido: código o serie duplicado por {payload['sub']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código de barras o número de serie ya existe"
        )
    finally:
        db.close()

# Endpoints de ventas
@app.get("/ventas", response_model=List[Venta])
def obtener_ventas(skip: int = 0, limit: int = 100, payload: dict = Depends(verificar_token)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ventas ORDER BY fecha DESC LIMIT ? OFFSET ?", (limit, skip))
    ventas = cursor.fetchall()
    return [dict(venta) for venta in ventas]

@app.post("/ventas", response_model=Venta)
def crear_venta(venta: VentaCreate, payload: dict = Depends(verificar_token)):
    db = SessionLocal()
    try:
        # Validar stock antes de procesar la venta
        for producto in venta.productos:
            prod = db.query(ProductoModel).filter(ProductoModel.id == producto["id"]).first()
            if not prod or prod.stock < producto["cantidad"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Stock insuficiente para el producto {producto['id']}"
                )
        # Calcular total
        total = 0
        for producto in venta.productos:
            prod = db.query(ProductoModel).filter(ProductoModel.id == producto["id"]).first()
            total += prod.precio * producto["cantidad"]
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nueva_venta = VentaModel(
            fecha=fecha,
            total=total,
            estado_caja="abierta",
            metodo_pago=venta.metodo_pago,
            cliente_id=venta.cliente_id
        )
        db.add(nueva_venta)
        db.commit()
        db.refresh(nueva_venta)
        # Registrar detalles de venta y actualizar stock
        for producto in venta.productos:
            prod = db.query(ProductoModel).filter(ProductoModel.id == producto["id"]).first()
            detalle = DetalleVentaModel(
                venta_id=nueva_venta.id,
                producto_id=prod.id,
                cantidad=producto["cantidad"],
                precio=prod.precio,
                numero_serie=prod.numero_serie
            )
            db.add(detalle)
            prod.stock -= producto["cantidad"]
        db.commit()
        return {
            "id": nueva_venta.id,
            "fecha": fecha,
            "total": total,
            "estado_caja": "abierta",
            "metodo_pago": venta.metodo_pago,
            "cliente_id": venta.cliente_id
        }
    except HTTPException as e:
        db.rollback()
        logger.error(f"Error al crear venta: {str(e)}")
        audit_logger.info(f"Error al crear venta por {payload['sub']}: {str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al crear venta: {str(e)}")
        audit_logger.info(f"Error al crear venta por {payload['sub']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar la venta"
        )
    finally:
        db.close()

# Endpoints de devoluciones
@app.post("/devoluciones", response_model=Devolucion)
def crear_devolucion(devolucion: Devolucion, payload: dict = Depends(verificar_token)):
    db = SessionLocal()
    try:
        prod = db.query(ProductoModel).filter(ProductoModel.id == devolucion.producto_id).first()
        if not prod:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        precio = prod.precio
        if precio * devolucion.cantidad >= 500 and payload["rol"] not in ["gerente", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta devolución requiere autorización de un gerente"
            )
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        autorizado_por = payload["sub"] if precio * devolucion.cantidad >= 500 else None
        nueva_devolucion = DevolucionModel(
            venta_id=devolucion.venta_id,
            producto_id=devolucion.producto_id,
            cantidad=devolucion.cantidad,
            motivo=devolucion.motivo,
            estado_producto=devolucion.estado_producto,
            fecha=fecha,
            autorizado_por=autorizado_por
        )
        db.add(nueva_devolucion)
        prod.stock += devolucion.cantidad
        db.commit()
        db.refresh(nueva_devolucion)
        logger.info(f"Devolución {nueva_devolucion.id} procesada por {payload['sub']}")
        audit_logger.info(f"Devolución procesada: {nueva_devolucion.id} por {payload['sub']}")
        return {
            "id": nueva_devolucion.id,
            "venta_id": devolucion.venta_id,
            "producto_id": devolucion.producto_id,
            "cantidad": devolucion.cantidad,
            "motivo": devolucion.motivo,
            "estado_producto": devolucion.estado_producto,
            "fecha": fecha,
            "autorizado_por": autorizado_por
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error al procesar devolución: {str(e)}")
        audit_logger.info(f"Error al procesar devolución por {payload['sub']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar la devolución"
        )
    finally:
        db.close()

# Manejo global de errores
@app.exception_handler(Exception)
def global_exception_handler(request, exc):
    logger.error(f"Error no manejado: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
