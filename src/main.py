import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox, scrolledtext
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
import sqlite3
from datetime import datetime, timedelta
import random
import string
import hashlib
import json
import threading
import time
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, ValidationError
import functools
import os

# Decorador para manejo automático de errores
def manejar_errores(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error en {func.__name__}: {str(e)}")
            messagebox.showerror("Error", f"Ocurrió un error: {str(e)}")
            return None
    return wrapper

# Configuración básica de SQLAlchemy
# Preferir la variable ELECTROSTORE_DB para pruebas (ruta a archivo sqlite),
# si no está, usar DATABASE_URL o el valor por defecto.
db_file = os.environ.get("ELECTROSTORE_DB")
if db_file:
    DATABASE_URL = f"sqlite:///{db_file}"
else:
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///electrostore.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()  # Corregido para SQLAlchemy 2.0

# Modelo de datos para Producto
class ProductoModel(Base):
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo_barras = Column(String, unique=True, index=True)
    nombre = Column(String)
    precio = Column(Float)
    stock = Column(Integer)
    categoria = Column(String)
    numero_serie = Column(String, unique=True)

class VentaModel(Base):
    __tablename__ = "ventas"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(String)
    total = Column(Float)
    estado_caja = Column(String)
    metodo_pago = Column(String)
    cliente_id = Column(Integer, nullable=True)

class DetalleVentaModel(Base):
    __tablename__ = "detalle_venta"
    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer)
    producto_id = Column(Integer)
    cantidad = Column(Integer)
    precio = Column(Float)
    numero_serie = Column(String)

class DevolucionModel(Base):
    __tablename__ = "devoluciones"
    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer)
    producto_id = Column(Integer)
    cantidad = Column(Integer)
    motivo = Column(String)
    estado_producto = Column(String)
    fecha = Column(String)
    autorizado_por = Column(String, nullable=True)

class UsuarioModel(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    rol = Column(String)
    nombre = Column(String)

class EmpresaModel(Base):
    __tablename__ = "empresa"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    rif = Column(String, nullable=False)
    direccion = Column(String, nullable=False)
    telefono = Column(String)
    email = Column(String)

class SecuenciaFacturaModel(Base):
    __tablename__ = "secuencia_factura"
    id = Column(Integer, primary_key=True, autoincrement=True)
    prefijo = Column(String, nullable=False)
    siguiente_numero = Column(Integer, nullable=False, default=1)
    tipo = Column(String, nullable=False)  # 'factura', 'nota_credito', etc.

# Crear tablas en la base de datos si no existen (útil para tests y entornos nuevos)
Base.metadata.create_all(bind=engine)
# Simulación de servicios externos
class Microservicio(ABC):
    @abstractmethod
    def procesar_evento(self, evento):
        pass

class ServicioInventario(Microservicio):
    def __init__(self, conn):
        self.conn = conn
        self.alertas_stock_bajo = []
    
    @manejar_errores
    def procesar_evento(self, evento):
        if evento['tipo'] == 'VENTA':
            cursor = self.conn.cursor()
            for producto in evento['productos']:
                cursor.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", 
                              (producto['cantidad'], producto['id']))
            cursor.execute("SELECT nombre, stock FROM productos WHERE stock <= 5")
            productos_bajos = cursor.fetchall()
            for producto in productos_bajos:
                if producto not in self.alertas_stock_bajo:
                    self.alertas_stock_bajo.append(producto)
                    print(f"ALERTA: Stock bajo de {producto[0]} - {producto[1]} unidades")
            self.conn.commit()
        elif evento['tipo'] == 'DEVOLUCION' and evento['estado_producto'] == 'vendible':
            cursor = self.conn.cursor()
            cursor.execute("UPDATE productos SET stock = stock + ? WHERE id = ?", 
                          (evento['cantidad'], evento['producto_id']))
            self.conn.commit()

class ServicioContabilidad(Microservicio):
    def __init__(self):
        self.ingresos = 0
        self.egresos = 0
        self.transacciones = []
    
    def procesar_evento(self, evento):
        if evento['tipo'] == 'VENTA':
            self.ingresos += evento['monto']
            self.transacciones.append(evento)
            print(f"Registrado ingreso de ${evento['monto']} en contabilidad")
            
        elif evento['tipo'] == 'DEVOLUCION':
            self.egresos += evento['monto']
            self.transacciones.append(evento)
            print(f"Registrado egreso de ${evento['monto']} en contabilidad")

class ServicioAutorizaciones(Microservicio):
    def __init__(self, conn):
        self.conn = conn
        self.gerentes = []
        self.cargar_gerentes()
    
    def cargar_gerentes(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT username FROM usuarios WHERE rol = 'gerente'")
        self.gerentes = [row[0] for row in cursor.fetchall()]
    
    def procesar_evento(self, evento):
        if evento['tipo'] == 'AUTORIZACION_REQUERIDA':
            # Simular proceso de autorización
            print(f"Solicitud de autorización para {evento['operacion']} por valor de ${evento['monto']}")
            return random.choice([True, False])  # Simulación aleatoria

# Simulador de Apache Kafka para comunicación entre microservicios
class KafkaSimulator:
    def __init__(self):
        self.suscriptores = {}
        self.eventos = []
    def suscribir(self, topico, microservicio):
        if topico not in self.suscriptores:
            self.suscriptores[topico] = []
        self.suscriptores[topico].append(microservicio)
    publicar = lambda self, topico, evento: threading.Thread(target=self._procesar_evento, args=(topico, evento)).start()
    def _procesar_evento(self, topico, evento):
        evento['timestamp'] = datetime.now().isoformat()
        self.eventos.append(evento)
        print(f"Evento publicado en {topico}: {evento['tipo']}")
        if topico in self.suscriptores:
            for suscriptor in self.suscriptores[topico]:
                try:
                    suscriptor.procesar_evento(evento)
                except Exception as e:
                    print(f"Error procesando evento en {suscriptor.__class__.__name__}: {str(e)}")

class SistemaElectrodomesticos:
    def __init__(self, root):
        self.root = root
        self.root.title("ElectroStore - Sistema de Gestión")
        self.root.geometry("1400x900")
        # use a dark ttkbootstrap theme for a dark UI
        # possible dark themes: 'darkly', 'cyborg' (ttkbootstrap built-ins)
        self.style = ttk.Style(theme="darkly")

        # Variables de estado usadas globalmente (inicializadas temprano para evitar errores
        # cuando se llaman métodos que las referencian antes de que los widgets específicos
        # de la vista de caja se creen).
        self.estado_caja_var = tk.StringVar(value="Estado: CERRADA")
        self.monto_inicial_var = tk.StringVar(value="Monto inicial: $0.00")
        self.ventas_hoy_var = tk.StringVar(value="Ventas hoy: $0.00")
        
        # Estado de la caja (cerrada por defecto)
        self.caja_abierta = False
        self.monto_inicial = 0.0
        self.ventas_dia = 0.0
        
        # Conectar a la base de datos
        self.conn = sqlite3.connect('electrostore.db')
        self.create_tables()
        
        # Cargar datos iniciales si la base de datos está vacía
        self.load_initial_data()
        
        # Configurar sistema de microservicios
        self.kafka = KafkaSimulator()
        self.inventario_service = ServicioInventario(self.conn)
        self.contabilidad_service = ServicioContabilidad()
        self.autorizaciones_service = ServicioAutorizaciones(self.conn)
        
        # Suscribir microservicios a topics
        self.kafka.suscribir('inventario', self.inventario_service)
        self.kafka.suscribir('contabilidad', self.contabilidad_service)
        self.kafka.suscribir('autorizaciones', self.autorizaciones_service)
        
        # Crear la nueva interfaz con el diseño de la imagen
        self.create_new_interface()
        
        # Cargar productos
        self.load_products()
        
        # Actualizar estado de la caja
        self.actualizar_estado_caja()
        
        # Iniciar monitoreo de alertas
        self.monitorear_alertas()
        
        # Mostrar pantalla inicial por defecto (sin dashboard)
        self.mostrar_home()
        
    def create_new_interface(self):
        # Crear contenedor principal
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # HEADER SUPERIOR
        self.create_header()
        
        # CONTENEDOR PRINCIPAL (Sidebar + Content)
        self.content_container = ttk.Frame(self.main_container)
        self.content_container.pack(fill=tk.BOTH, expand=True)
        # Main container (fills root). We'll use grid inside content_container
        # header on top
        self.create_header()

        # content container holds sidebar and main content using grid so layout
        # can be responsive (column weight configuration)
        try:
            self.content_container.columnconfigure(0, weight=0, minsize=200)
            self.content_container.columnconfigure(1, weight=1)
            self.content_container.rowconfigure(0, weight=1)
        except Exception:
            # Algunos backends no usan grid; esta configuración es segura si existe
            pass

        # Estado para controlar la visibilidad del sidebar
        self.sidebar_visible = True

        # SIDEBAR IZQUIERDO
        self.create_sidebar()

        # CONTENIDO PRINCIPAL
        self.create_main_content()

        # Inicializar carrito
        self.carrito = []
        
    def create_header(self):
        header_frame = ttk.Frame(self.main_container, bootstyle="dark")
        header_frame.pack(fill=tk.X, padx=10, pady=5)

        # Logo y departamento
        left_header = ttk.Frame(header_frame)
        left_header.pack(side=tk.LEFT)

        # Cabecera más acorde al sistema de facturación
        ttk.Label(left_header, text="🏢 ElectroStore - Sistema de Facturación", 
                 font=("Arial", 12, "bold"), bootstyle="primary").pack(side=tk.LEFT)

        # Usuario a la derecha
        right_header = ttk.Frame(header_frame)
        right_header.pack(side=tk.RIGHT)

        # Botón para toggle del sidebar (útil en pantallas pequeñas)
        toggle_btn = ttk.Button(right_header, text="☰", command=self.toggle_sidebar, bootstyle="secondary")
        toggle_btn.pack(side=tk.RIGHT, padx=(0, 8))

        ttk.Label(right_header, text="👤 Admin", 
                 font=("Arial", 10), bootstyle="secondary").pack(side=tk.RIGHT)
        
    def create_sidebar(self):
        # Hacemos que el sidebar sea accesible como atributo para poder mostrar/ocultar
        self.sidebar_frame = ttk.Frame(self.content_container, width=250, bootstyle="secondary")
        # Usamos grid dentro de content_container para permitir comportamiento responsive
        try:
            self.sidebar_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W), padx=(0, 5))
            self.sidebar_frame.grid_propagate(False)
        except Exception:
            # Si por alguna razón grid no está disponible, fallback a pack
            self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
            self.sidebar_frame.pack_propagate(False)

        # Información compacta de la tienda (se eliminó el bloque "Espacios de Trabajo")
        shop_frame = ttk.Frame(self.sidebar_frame, padding=8)
        shop_frame.pack(fill=tk.X, padx=5, pady=6)
        ttk.Label(shop_frame, text="ElectroStore", font=("Arial", 11, "bold"), bootstyle="primary").pack(anchor=tk.W)
        ttk.Label(shop_frame, text="Sistema de Facturación", font=("Arial", 9), bootstyle="secondary").pack(anchor=tk.W)
        ttk.Separator(self.sidebar_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=8)

        # Navegación
        nav_frame = ttk.Frame(self.sidebar_frame)
        nav_frame.pack(fill=tk.X, padx=5)

        # Botones de navegación con íconos (se eliminaron Dashboard y Vista Kanban)
        nav_buttons = [
            ("📅 Calendario", self.mostrar_calendario),
            ("💰 Punto de Venta", self.mostrar_ventas),
            ("📦 Inventario", self.mostrar_inventario),
            ("💵 Control de Caja", self.mostrar_caja),
            ("🔄 Devoluciones", self.mostrar_devoluciones),
            ("📈 Reportes", self.mostrar_reportes),
            ("⚙️ Microservicios", self.mostrar_microservicios)
        ]

        for text, command in nav_buttons:
            btn = ttk.Button(nav_frame, text=text, command=command,
                              bootstyle="primary", width=20)
            btn.pack(fill=tk.X, pady=6)
            
    def create_main_content(self):
        self.main_content = ttk.Frame(self.content_container)
        try:
            # Ubicar main_content en la columna 1 (la columna 0 es el sidebar)
            self.main_content.grid(row=0, column=1, sticky=(tk.N, tk.E, tk.S, tk.W))
        except Exception:
            # Fallback a pack si grid no funciona
            self.main_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Frame para el contenido dinámico
        self.content_frame = ttk.Frame(self.main_content)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def toggle_sidebar(self):
        """Mostrar/ocultar la barra lateral. Útil para pantallas pequeñas."""
        try:
            if getattr(self, 'sidebar_visible', True):
                # ocultar
                self.sidebar_frame.grid_remove()
                self.sidebar_visible = False
            else:
                # mostrar (asegurarse de reubicarla)
                self.sidebar_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W), padx=(0, 5))
                self.sidebar_visible = True
        except Exception:
            # fallback: pack/unpack
            try:
                if self.sidebar_visible:
                    self.sidebar_frame.pack_forget()
                    self.sidebar_visible = False
                else:
                    self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
                    self.sidebar_visible = True
            except Exception:
                # Si falla, no hacemos nada
                pass
        
    def mostrar_dashboard(self):
        # Mantener por compatibilidad: mostrar home simple
        self.mostrar_home()

    def mostrar_home(self):
        """Pantalla inicial simple para el sistema de facturación."""
        self.limpiar_contenido()
        title_frame = ttk.Frame(self.content_frame)
        title_frame.pack(fill=tk.X, pady=(10, 20))
        ttk.Label(title_frame, text="Sistema de Facturación - ElectroStore", 
                 font=("Arial", 18, "bold"), bootstyle="primary").pack(side=tk.LEFT)

        subtitle = ttk.Frame(self.content_frame)
        subtitle.pack(fill=tk.X)
        ttk.Label(subtitle, text="Bienvenido. Use el menú izquierdo para navegar: Punto de Venta, Inventario, Caja, Devoluciones, Reportes y Microservicios.",
                 font=("Arial", 11), bootstyle="secondary", wraplength=900, justify=tk.LEFT).pack(anchor=tk.W, pady=(0,10))
        # Espacio para KPIs resumidos
        kpi_frame = ttk.Labelframe(self.content_frame, text="Resumen rápido", padding=10, bootstyle="primary")
        kpi_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(kpi_frame, text="Ventas hoy:", bootstyle="primary").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Label(kpi_frame, textvariable=self.ventas_hoy_var, bootstyle="primary").grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(kpi_frame, text="Estado de caja:", bootstyle="primary").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Label(kpi_frame, textvariable=self.estado_caja_var, bootstyle="primary").grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
    def mostrar_kanban(self):
        # Kanban eliminado por decisión del producto; mostrar mensaje alternativo
        self.limpiar_contenido()
        ttk.Label(self.content_frame, text="Funcionalidad de Kanban removida.", 
                 font=("Arial", 14), bootstyle="secondary").pack(pady=50)
        
    def mostrar_calendario(self):
        self.limpiar_contenido()
        ttk.Label(self.content_frame, text="Calendario - Próximamente", 
                 font=("Arial", 16)).pack(pady=50)
        
    def mostrar_ventas(self):
        self.limpiar_contenido()
        self.create_ventas_widgets()
        
    def mostrar_inventario(self):
        self.limpiar_contenido()
        self.create_inventario_widgets()
        
    def mostrar_caja(self):
        self.limpiar_contenido()
        self.create_caja_widgets()
        
    def mostrar_devoluciones(self):
        self.limpiar_contenido()
        self.create_devoluciones_widgets()
        
    def mostrar_reportes(self):
        self.limpiar_contenido()
        self.create_reportes_widgets()
        
    def mostrar_microservicios(self):
        self.limpiar_contenido()
        self.create_microservicios_widgets()
        
    def limpiar_contenido(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    # AQUÍ COMIENZAN TODOS LOS MÉTODOS ORIGINALES (se mantienen exactamente igual)
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Tabla de productos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_barras TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL,
                stock INTEGER NOT NULL,
                categoria TEXT NOT NULL,
                numero_serie TEXT UNIQUE
            )
        ''')
        
        # Tabla de ventas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                total REAL NOT NULL,
                estado_caja TEXT NOT NULL,
                metodo_pago TEXT NOT NULL,
                cliente_id INTEGER
            )
        ''')
        
        # Tabla de detalles de venta
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detalle_venta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER,
                producto_id INTEGER,
                cantidad INTEGER NOT NULL,
                precio REAL NOT NULL,
                numero_serie TEXT,
                FOREIGN KEY (venta_id) REFERENCES ventas (id),
                FOREIGN KEY (producto_id) REFERENCES productos (id)
            )
        ''')
        
        # Tabla de caja
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS caja (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_apertura TEXT NOT NULL,
                fecha_cierre TEXT,
                monto_inicial REAL NOT NULL,
                monto_final REAL,
                estado TEXT NOT NULL
            )
        ''')
        
        # Tabla de devoluciones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devoluciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL,
                motivo TEXT NOT NULL,
                estado_producto TEXT NOT NULL,
                fecha TEXT NOT NULL,
                autorizado_por TEXT,
                FOREIGN KEY (venta_id) REFERENCES ventas (id),
                FOREIGN KEY (producto_id) REFERENCES productos (id)
            )
        ''')
        
        # Tabla de usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                rol TEXT NOT NULL,
                nombre TEXT NOT NULL
            )
        ''')
        
        # Tabla de clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT,
                telefono TEXT,
                direccion TEXT
            )
        ''')
        
        # Tabla de empresa
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS empresa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                rif TEXT NOT NULL,
                direccion TEXT NOT NULL,
                telefono TEXT,
                email TEXT
            )
        ''')
        
        # Tabla de secuencia de facturación
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS secuencia_factura (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prefijo TEXT NOT NULL,
                siguiente_numero INTEGER NOT NULL DEFAULT 1,
                tipo TEXT NOT NULL
            )
        ''')
        
        # Insertar usuario admin por defecto
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute("INSERT INTO usuarios (username, password, rol, nombre) VALUES (?, ?, ?, ?)",
                          ('admin', password_hash, 'gerente', 'Administrador'))
        
        self.conn.commit()
    
    def load_initial_data(self):
        cursor = self.conn.cursor()
        
        # Verificar si ya hay productos
        cursor.execute("SELECT COUNT(*) FROM productos")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Insertar productos de ejemplo con códigos de barras y números de serie
            productos = [
                ("7501006554025", "Smart TV 55\" 4K", 899.99, 15, "Televisores", "SN-TV-001"),
                ("7501055300124", "Refrigeradora French Door", 1599.99, 8, "Refrigeradoras", "SN-RF-001"),
                ("7501006554032", "Lavadora Secadora", 749.99, 12, "Lavadoras", "SN-LV-001"),
                ("7501055300131", "Microondas Grill", 199.99, 20, "Cocina", "SN-MW-001"),
                ("7501006554049", "Cafetera Automática", 129.99, 25, "Pequeños Electrodomésticos", "SN-CF-001"),
                ("7501055300148", "Aspiradora Robot", 349.99, 10, "Limpieza", "SN-AS-001"),
                ("7501006554056", "Aire Acondicionado 12000 BTU", 699.99, 7, "Climatización", "SN-AC-001"),
                ("7501055300155", "Consola de Videojuegos", 499.99, 18, "Entretenimiento", "SN-CV-001"),
                ("7501006554063", "Horno Eléctrico", 299.99, 9, "Cocina", "SN-HE-001"),
                ("7501055300162", "Batidora Profesional", 89.99, 22, "Pequeños Electrodomésticos", "SN-BT-001")
            ]
            
            cursor.executemany("INSERT INTO productos (codigo_barras, nombre, precio, stock, categoria, numero_serie) VALUES (?, ?, ?, ?, ?, ?)", productos)
            
            # Insertar algunos clientes de ejemplo
            clientes = [
                ("Juan Pérez", "juan@email.com", "555-1234", "Calle 123, Ciudad"),
                ("María García", "maria@email.com", "555-5678", "Avenida 456, Ciudad"),
                ("Carlos López", "carlos@email.com", "555-9012", "Boulevard 789, Ciudad")
            ]
            
            cursor.executemany("INSERT INTO clientes (nombre, email, telefono, direccion) VALUES (?, ?, ?, ?)", clientes)
            
            # Insertar datos de empresa de ejemplo
            cursor.execute('''
                INSERT INTO empresa (nombre, rif, direccion, telefono, email) VALUES 
                ('ElectroStore S.A.', 'J-12345678-9', 'Av. Principal, Ciudad', '0212-3456789', 'contacto@electrostore.com')
            ''')
            
            # Insertar secuencia de factura por defecto
            cursor.execute('''
                INSERT INTO secuencia_factura (prefijo, siguiente_numero, tipo) VALUES 
                ('F-', 1, 'factura'), 
                ('NC-', 1, 'nota_credito')
            ''')
            
            self.conn.commit()
    
    def create_ventas_widgets(self):
        # Título
        title_label = ttk.Label(self.content_frame, text="Punto de Venta - ElectroStore", 
                               font=("Arial", 16, "bold"), bootstyle="inverse-primary")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")
        
        # Panel de búsqueda/escaneo (responsive)
        search_frame = ttk.Labelframe(self.content_frame, text="Escaneo de Productos", 
                                     padding="10", bootstyle="info")
        search_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        # permitir que la columna central (inputs) se expanda cuando la ventana cambia de tamaño
        try:
            search_frame.columnconfigure(0, weight=0)
            search_frame.columnconfigure(1, weight=1)
            search_frame.columnconfigure(2, weight=0)
        except Exception:
            pass
        
        ttk.Label(search_frame, text="Código de Barras:", bootstyle="info").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.codigo_barras_var = tk.StringVar()
        codigo_entry = ttk.Entry(search_frame, textvariable=self.codigo_barras_var,
                                 bootstyle="info")
        codigo_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        codigo_entry.bind('<Return>', self.buscar_por_codigo)
        
        ttk.Button(search_frame, text="Buscar Producto", command=self.buscar_por_codigo, 
                  bootstyle="info-outline").grid(row=0, column=2, padx=(10, 0))
        
        ttk.Label(search_frame, text="O buscar por nombre:", bootstyle="info").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.nombre_busqueda_var = tk.StringVar()
        nombre_search = ttk.Entry(search_frame, textvariable=self.nombre_busqueda_var,
                                   bootstyle="info")
        nombre_search.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        nombre_search.bind('<Return>', self.buscar_por_nombre)
        
        ttk.Button(search_frame, text="Buscar", command=self.buscar_por_nombre, 
                  bootstyle="info-outline").grid(row=1, column=2, padx=(10, 0))
        
        # Info del producto encontrado
        self.producto_info_var = tk.StringVar(value="Producto: ---\nPrecio: ---\nStock: ---")
        ttk.Label(search_frame, textvariable=self.producto_info_var, justify=tk.LEFT, 
                 bootstyle="info").grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=10)
        
        # Cantidad a agregar
        ttk.Label(search_frame, text="Cantidad:", bootstyle="info").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.cantidad_venta_var = tk.IntVar(value=1)
        ttk.Spinbox(search_frame, from_=1, to=100, textvariable=self.cantidad_venta_var, 
                   width=10, bootstyle="info").grid(row=3, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        ttk.Button(search_frame, text="Agregar al Carrito", command=self.agregar_al_carrito, 
                  bootstyle="success").grid(row=3, column=2, padx=(10, 0))
        
        # Método de pago
        ttk.Label(search_frame, text="Método de pago:", bootstyle="info").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.metodo_pago_var = tk.StringVar(value="Efectivo")
        metodos = ["Efectivo", "Tarjeta Débito", "Tarjeta Crédito", "Transferencia"]
        ttk.Combobox(search_frame, textvariable=self.metodo_pago_var, values=metodos, 
                    state="readonly", width=15, bootstyle="info").grid(row=4, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        # Carrito de compras
        cart_frame = ttk.Labelframe(self.content_frame, text="Carrito de Compra",
                                   padding="10", bootstyle="primary")
        cart_frame.grid(row=1, column=1, sticky=(tk.N, tk.S, tk.E, tk.W), pady=(0, 10))
        # make cart expand to fill available space
        cart_frame.columnconfigure(0, weight=1)
        cart_frame.rowconfigure(0, weight=1)
        
        # Treeview para carrito
        cart_columns = ("producto", "cantidad", "precio", "subtotal")
        self.cart_tree = ttk.Treeview(cart_frame, columns=cart_columns, show="headings", 
                                     height=10, bootstyle="info")
        
        self.cart_tree.heading("producto", text="Producto")
        self.cart_tree.heading("cantidad", text="Cantidad")
        self.cart_tree.heading("precio", text="Precio Unitario")
        self.cart_tree.heading("subtotal", text="Subtotal")
        
        self.cart_tree.column("producto", width=250)
        self.cart_tree.column("cantidad", width=100)
        self.cart_tree.column("precio", width=150)
        self.cart_tree.column("subtotal", width=150)
        
        cart_scrollbar = ttk.Scrollbar(cart_frame, orient=tk.VERTICAL, 
                                      command=self.cart_tree.yview, bootstyle="primary-round")
        self.cart_tree.configure(yscrollcommand=cart_scrollbar.set)
        
        self.cart_tree.grid(row=0, column=0, sticky=(tk.N, tk.E, tk.S, tk.W))
        cart_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Total y botón de venta
        total_frame = ttk.Frame(cart_frame)
        total_frame.grid(row=1, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))
        
        self.total_var = tk.StringVar(value="Total: $0.00")
        ttk.Label(total_frame, textvariable=self.total_var, font=("Arial", 12, "bold"), 
                 bootstyle="inverse-primary").grid(row=0, column=0, padx=(0, 20))
        
        ttk.Button(total_frame, text="Realizar Venta", command=self.realizar_venta, 
                  bootstyle="success").grid(row=0, column=1)
        
        # Producto actual para venta
        self.current_product = None
        
        # Configurar grid para que el panel de búsqueda y el carrito respondan
        try:
            # Columna 0 (búsqueda) y columna 1 (carrito) deben repartirse el espacio
            self.content_frame.columnconfigure(0, weight=1)
            self.content_frame.columnconfigure(1, weight=2)
            self.content_frame.rowconfigure(1, weight=1)
        except Exception:
            pass
        cart_frame.columnconfigure(0, weight=1)
        cart_frame.rowconfigure(0, weight=1)
    
    def create_inventario_widgets(self):
        # Título
        title_label = ttk.Label(self.content_frame, text="Gestión de Inventario", 
                               font=("Arial", 16, "bold"), bootstyle="inverse-primary")
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky="ew")
        
        # Treeview para productos
        columns = ("id", "codigo", "nombre", "precio", "stock", "categoria", "numero_serie")
        self.inv_tree = ttk.Treeview(self.content_frame, columns=columns, show="headings", 
                                    height=15, bootstyle="info")
        
        self.inv_tree.heading("id", text="ID")
        self.inv_tree.heading("codigo", text="Código Barras")
        self.inv_tree.heading("nombre", text="Nombre")
        self.inv_tree.heading("precio", text="Precio")
        self.inv_tree.heading("stock", text="Stock")
        self.inv_tree.heading("categoria", text="Categoría")
        self.inv_tree.heading("numero_serie", text="Número de Serie")
        
        self.inv_tree.column("id", width=50)
        self.inv_tree.column("codigo", width=120)
        self.inv_tree.column("nombre", width=200)
        self.inv_tree.column("precio", width=100)
        self.inv_tree.column("stock", width=80)
        self.inv_tree.column("categoria", width=150)
        self.inv_tree.column("numero_serie", width=150)
        
        scrollbar = ttk.Scrollbar(self.content_frame, orient=tk.VERTICAL, 
                                 command=self.inv_tree.yview, bootstyle="primary-round")
        self.inv_tree.configure(yscrollcommand=scrollbar.set)
        
        self.inv_tree.grid(row=1, column=0, columnspan=2, sticky=(tk.N, tk.E, tk.S, tk.W))
        scrollbar.grid(row=1, column=2, sticky=(tk.N, tk.S))
        
        # Botones de gestión
        btn_frame = ttk.Frame(self.content_frame)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Agregar Producto", command=self.agregar_producto, 
                  bootstyle="success").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Editar Producto", command=self.editar_producto, 
                  bootstyle="info").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Eliminar Producto", command=self.eliminar_producto, 
                  bootstyle="danger").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Actualizar", command=self.load_products, 
                  bootstyle="secondary").pack(side=tk.LEFT, padx=5)
        
        # Panel de alertas de inventario
        alertas_frame = ttk.Labelframe(self.content_frame, text="Alertas de Stock Bajo", 
                                      padding="10", bootstyle="warning")
        alertas_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.alertas_text = scrolledtext.ScrolledText(alertas_frame, height=5, width=100)
        self.alertas_text.pack(fill=tk.BOTH, expand=True)
        self.alertas_text.config(state=tk.DISABLED)
        
        # Configurar grid
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(1, weight=1)
    
    def create_caja_widgets(self):
        # Título
        title_label = ttk.Label(self.content_frame, text="Control de Caja", 
                               font=("Arial", 16, "bold"), bootstyle="inverse-primary")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")
        
        # Estado de caja
        estado_frame = ttk.Labelframe(self.content_frame, text="Estado de Caja", 
                                     padding="10", bootstyle="info")
        estado_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.estado_caja_var = tk.StringVar(value="Estado: CERRADA")
        ttk.Label(estado_frame, textvariable=self.estado_caja_var, font=("Arial", 12, "bold"), 
                 bootstyle="info").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.monto_inicial_var = tk.StringVar(value="Monto inicial: $0.00")
        ttk.Label(estado_frame, textvariable=self.monto_inicial_var, bootstyle="info").grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.ventas_hoy_var = tk.StringVar(value="Ventas hoy: $0.00")
        ttk.Label(estado_frame, textvariable=self.ventas_hoy_var, bootstyle="info").grid(row=2, column=0, sticky=tk.W, pady=2)
        
        # Controles de caja
        controles_frame = ttk.Labelframe(self.content_frame, text="Controles de Caja", 
                                        padding="10", bootstyle="primary")
        controles_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=(0, 10), pady=(10, 0))
        
        ttk.Label(controles_frame, text="Monto inicial:", bootstyle="primary").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.monto_apertura_var = tk.DoubleVar(value=0.0)
        ttk.Entry(controles_frame, textvariable=self.monto_apertura_var, width=15, 
                 bootstyle="primary").grid(row=0, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        ttk.Button(controles_frame, text="Abrir Caja", command=self.abrir_caja, 
                  bootstyle="success").grid(row=0, column=2, padx=(10, 0))
        ttk.Button(controles_frame, text="Cerrar Caja", command=self.cerrar_caja, 
                  bootstyle="danger").grid(row=0, column=3, padx=(10, 0))
        
        # Reporte de ventas del día
        ventas_frame = ttk.Labelframe(self.content_frame, text="Ventas de Hoy", 
                                     padding="10", bootstyle="secondary")
        ventas_frame.grid(row=1, column=1, rowspan=2, sticky=(tk.N, tk.E, tk.S, tk.W))
        ventas_frame.columnconfigure(0, weight=1)
        ventas_frame.rowconfigure(0, weight=1)
        
        # Treeview para ventas
        ventas_columns = ("id", "fecha", "total", "metodo_pago")
        self.ventas_tree = ttk.Treeview(ventas_frame, columns=ventas_columns, show="headings", 
                                       height=10, bootstyle="info")
        
        self.ventas_tree.heading("id", text="ID")
        self.ventas_tree.heading("fecha", text="Fecha y Hora")
        self.ventas_tree.heading("total", text="Total")
        self.ventas_tree.heading("metodo_pago", text="Método Pago")
        
        self.ventas_tree.column("id", width=50)
        self.ventas_tree.column("fecha", width=150)
        self.ventas_tree.column("total", width=100)
        self.ventas_tree.column("metodo_pago", width=100)
        
        ventas_scrollbar = ttk.Scrollbar(ventas_frame, orient=tk.VERTICAL, 
                                        command=self.ventas_tree.yview, bootstyle="primary-round")
        self.ventas_tree.configure(yscrollcommand=ventas_scrollbar.set)
        
        self.ventas_tree.grid(row=0, column=0, sticky=(tk.N, tk.E, tk.S, tk.W))
        ventas_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configurar grid
        self.content_frame.columnconfigure(1, weight=1)
        self.content_frame.rowconfigure(1, weight=1)
        ventas_frame.columnconfigure(0, weight=1)
        ventas_frame.rowconfigure(0, weight=1)
    
    def create_devoluciones_widgets(self):
        # Título
        title_label = ttk.Label(self.content_frame, text="Gestión de Devoluciones", 
                               font=("Arial", 16, "bold"), bootstyle="inverse-primary")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")
        
        # Panel de búsqueda de venta
        search_frame = ttk.Labelframe(self.content_frame, text="Buscar Venta para Devolución", 
                                     padding="10", bootstyle="info")
        search_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(search_frame, text="ID de Venta:", bootstyle="info").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.devolucion_venta_id_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.devolucion_venta_id_var, width=15, 
                 bootstyle="info").grid(row=0, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        ttk.Button(search_frame, text="Buscar Venta", command=self.buscar_venta_devolucion, 
                  bootstyle="info-outline").grid(row=0, column=2, padx=(10, 0))
        
        ttk.Label(search_frame, text="O buscar por número de serie:", bootstyle="info").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.devolucion_serie_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.devolucion_serie_var, width=15, 
                 bootstyle="info").grid(row=1, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        ttk.Button(search_frame, text="Buscar por Serie", command=self.buscar_serie_devolucion, 
                  bootstyle="info-outline").grid(row=1, column=2, padx=(10, 0))
        
        # Info de la venta
        self.devolucion_venta_info_var = tk.StringVar(value="Venta: ---")
        ttk.Label(search_frame, textvariable=self.devolucion_venta_info_var, bootstyle="info").grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # Productos de la venta
        products_frame = ttk.Labelframe(self.content_frame, text="Productos de la Venta", 
                                       padding="10", bootstyle="primary")
        products_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        products_frame.columnconfigure(0, weight=1)
        products_frame.rowconfigure(0, weight=1)
        
        columns = ("producto", "cantidad", "precio", "numero_serie")
        self.devolucion_tree = ttk.Treeview(products_frame, columns=columns, show="headings", 
                                           height=5, bootstyle="info")
        
        self.devolucion_tree.heading("producto", text="Producto")
        self.devolucion_tree.heading("cantidad", text="Cantidad")
        self.devolucion_tree.heading("precio", text="Precio Unitario")
        self.devolucion_tree.heading("numero_serie", text="Número de Serie")
        
        self.devolucion_tree.column("producto", width=200)
        self.devolucion_tree.column("cantidad", width=100)
        self.devolucion_tree.column("precio", width=100)
        self.devolucion_tree.column("numero_serie", width=150)
        
        scrollbar = ttk.Scrollbar(products_frame, orient=tk.VERTICAL, 
                                 command=self.devolucion_tree.yview, bootstyle="primary-round")
        self.devolucion_tree.configure(yscrollcommand=scrollbar.set)
        
        self.devolucion_tree.grid(row=0, column=0, sticky=(tk.N, tk.E, tk.S, tk.W))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Frame para devolución
        dev_frame = ttk.Labelframe(self.content_frame, text="Procesar Devolución", 
                                  padding="10", bootstyle="warning")
        dev_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(dev_frame, text="Producto:", bootstyle="warning").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.devolucion_producto_var = tk.StringVar()
        ttk.Entry(dev_frame, textvariable=self.devolucion_producto_var, state='readonly', 
                 width=30, bootstyle="warning").grid(row=0, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        ttk.Label(dev_frame, text="Cantidad a devolver:", bootstyle="warning").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.devolucion_cantidad_var = tk.IntVar(value=1)
        ttk.Spinbox(dev_frame, from_=1, to=100, textvariable=self.devolucion_cantidad_var, 
                   width=10, bootstyle="warning").grid(row=1, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        ttk.Label(dev_frame, text="Estado del producto:", bootstyle="warning").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.devolucion_estado_var = tk.StringVar()
        ttk.Combobox(dev_frame, textvariable=self.devolucion_estado_var, 
                    values=["vendible", "defectuoso"], state="readonly", width=15, 
                    bootstyle="warning").grid(row=2, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        ttk.Label(dev_frame, text="Motivo:", bootstyle="warning").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.devolucion_motivo_var = tk.StringVar()
        ttk.Entry(dev_frame, textvariable=self.devolucion_motivo_var, width=30, 
                 bootstyle="warning").grid(row=3, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        ttk.Button(dev_frame, text="Procesar Devolución", command=self.procesar_devolucion, 
                  bootstyle="warning").grid(row=4, column=0, columnspan=2, pady=10)
        
        # Configurar grid
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(2, weight=1)
        
        # Variables para almacenar la venta y productos seleccionados
        self.venta_devolucion = None
        self.productos_devolucion = []
        self.producto_devolucion_seleccionado = None
        
        # Configurar evento de selección
        self.devolucion_tree.bind('<<TreeviewSelect>>', self.seleccionar_producto_devolucion)
    
    def create_reportes_widgets(self):
        # Título
        title_label = ttk.Label(self.content_frame, text="Reportes y Dashboard", 
                               font=("Arial", 16, "bold"), bootstyle="inverse-primary")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")
        
        # Frame para filtros
        filters_frame = ttk.Labelframe(self.content_frame, text="Filtros", 
                                      padding="10", bootstyle="info")
        filters_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(filters_frame, text="Fecha inicio:", bootstyle="info").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.reporte_fecha_inicio_var = tk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        ttk.Entry(filters_frame, textvariable=self.reporte_fecha_inicio_var, width=12, 
                 bootstyle="info").grid(row=0, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        ttk.Label(filters_frame, text="Fecha fin:", bootstyle="info").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(10, 0))
        self.reporte_fecha_fin_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(filters_frame, textvariable=self.reporte_fecha_fin_var, width=12, 
                 bootstyle="info").grid(row=0, column=3, sticky=tk.W, pady=5, padx=(5, 0))
        
        ttk.Button(filters_frame, text="Generar Reporte", command=self.generar_reporte, 
                  bootstyle="info-outline").grid(row=0, column=4, padx=(10, 0))
        
        # KPIs
        kpi_frame = ttk.Labelframe(self.content_frame, text="Indicadores Clave", 
                                  padding="10", bootstyle="primary")
        kpi_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10), padx=(0, 10))
        
        self.ingresos_var = tk.StringVar(value="Ingresos: $0.00")
        ttk.Label(kpi_frame, textvariable=self.ingresos_var, font=("Arial", 12), 
                 bootstyle="primary").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.egresos_var = tk.StringVar(value="Egresos: $0.00")
        ttk.Label(kpi_frame, textvariable=self.egresos_var, font=("Arial", 12), 
                 bootstyle="primary").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.ventas_totales_var = tk.StringVar(value="Ventas totales: 0")
        ttk.Label(kpi_frame, textvariable=self.ventas_totales_var, font=("Arial", 12), 
                 bootstyle="primary").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.producto_mas_vendido_var = tk.StringVar(value="Producto más vendido: ---")
        ttk.Label(kpi_frame, textvariable=self.producto_mas_vendido_var, font=("Arial", 12), 
                 bootstyle="primary").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        # Reporte detallado
        report_frame = ttk.Labelframe(self.content_frame, text="Reporte Detallado", 
                                     padding="10", bootstyle="secondary")
        report_frame.grid(row=2, column=1, rowspan=2, sticky=(tk.N, tk.E, tk.S, tk.W))
        report_frame.columnconfigure(0, weight=1)
        report_frame.rowconfigure(0, weight=1)
        
        columns = ("fecha", "tipo", "descripcion", "monto")
        self.reporte_tree = ttk.Treeview(report_frame, columns=columns, show="headings", 
                                        height=15, bootstyle="info")
        
        self.reporte_tree.heading("fecha", text="Fecha")
        self.reporte_tree.heading("tipo", text="Tipo")
        self.reporte_tree.heading("descripcion", text="Descripción")
        self.reporte_tree.heading("monto", text="Monto")
        
        self.reporte_tree.column("fecha", width=120)
        self.reporte_tree.column("tipo", width=100)
        self.reporte_tree.column("descripcion", width=250)
        self.reporte_tree.column("monto", width=100)
        
        scrollbar = ttk.Scrollbar(report_frame, orient=tk.VERTICAL, 
                                 command=self.reporte_tree.yview, bootstyle="primary-round")
        self.reporte_tree.configure(yscrollcommand=scrollbar.set)
        
        self.reporte_tree.grid(row=0, column=0, sticky=(tk.N, tk.E, tk.S, tk.W))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configurar grid
        self.content_frame.columnconfigure(1, weight=1)
        self.content_frame.rowconfigure(2, weight=1)
        report_frame.columnconfigure(0, weight=1)
        report_frame.rowconfigure(0, weight=1)
    
    def create_microservicios_widgets(self):
        # Título
        title_label = ttk.Label(self.content_frame, text="Monitor de Microservicios", 
                               font=("Arial", 16, "bold"), bootstyle="inverse-primary")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")
        
        # Log de eventos
        log_frame = ttk.Labelframe(self.content_frame, text="Eventos del Sistema", 
                                  padding="10", bootstyle="primary")
        log_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.N, tk.E, tk.S, tk.W))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=100)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # Botones de control
        btn_frame = ttk.Frame(self.content_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Limpiar Log", command=self.limpiar_log, 
                  bootstyle="secondary").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Exportar Eventos", command=self.exportar_eventos, 
                  bootstyle="info").pack(side=tk.LEFT, padx=5)
        
        # Configurar grid
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(1, weight=1)

    # AQUÍ CONTINÚAN TODOS LOS MÉTODOS ORIGINALES RESTANTES
    # [Todos los métodos desde load_products() hasta el final se mantienen IDÉNTICOS]
    
    def load_products(self):
        # Si la vista de inventario aún no existe (la interfaz la crea al navegar), salir
        if not hasattr(self, 'inv_tree'):
            return

        # Limpiar treeview
        for item in self.inv_tree.get_children():
            self.inv_tree.delete(item)
        
        # Cargar productos desde la base de datos
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, codigo_barras, nombre, precio, stock, categoria, numero_serie FROM productos ORDER BY nombre")
        productos = cursor.fetchall()
        
        for producto in productos:
            self.inv_tree.insert("", tk.END, values=producto)
    
    def buscar_por_codigo(self, event=None):
        codigo = self.codigo_barras_var.get().strip()
        if not codigo:
            messagebox.showwarning("Advertencia", "Por favor ingrese un código de barras")
            return
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, nombre, precio, stock FROM productos WHERE codigo_barras = ?", (codigo,))
        producto = cursor.fetchone()
        
        if producto:
            self.current_product = {
                'id': producto[0],
                'nombre': producto[1],
                'precio': producto[2],
                'stock': producto[3]
            }
            self.producto_info_var.set(f"Producto: {producto[1]}\nPrecio: ${producto[2]:.2f}\nStock: {producto[3]}")
        else:
            messagebox.showerror("Error", "Producto no encontrado")
            self.current_product = None
            self.producto_info_var.set("Producto: ---\nPrecio: ---\nStock: ---")
    
    def buscar_por_nombre(self, event=None):
        nombre = self.nombre_busqueda_var.get().strip()
        if not nombre:
            messagebox.showwarning("Advertencia", "Por favor ingrese un nombre de producto")
            return
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, nombre, precio, stock, codigo_barras FROM productos WHERE nombre LIKE ?", (f'%{nombre}%',))
        productos = cursor.fetchall()
        
        if productos:
            if len(productos) == 1:
                producto = productos[0]
                self.current_product = {
                    'id': producto[0],
                    'nombre': producto[1],
                    'precio': producto[2],
                    'stock': producto[3]
                }
                self.codigo_barras_var.set(producto[4])
                self.producto_info_var.set(f"Producto: {producto[1]}\nPrecio: ${producto[2]:.2f}\nStock: {producto[3]}")
            else:
                # Mostrar diálogo para seleccionar producto
                self.mostrar_seleccion_producto(productos)
        else:
            messagebox.showerror("Error", "Producto no encontrado")
            self.current_product = None
            self.producto_info_var.set("Producto: ---\nPrecio: ---\nStock: ---")
    
    def mostrar_seleccion_producto(self, productos):
        seleccion_window = ttk.Toplevel(self.root)
        seleccion_window.title("Seleccionar Producto")
        seleccion_window.geometry("500x300")
        
        # Treeview para productos
        columns = ("id", "nombre", "precio", "stock")
        tree = ttk.Treeview(seleccion_window, columns=columns, show="headings", height=10, bootstyle="info")
        
        tree.heading("id", text="ID")
        tree.heading("nombre", text="Nombre")
        tree.heading("precio", text="Precio")
        tree.heading("stock", text="Stock")
        
        tree.column("id", width=50)
        tree.column("nombre", width=250)
        tree.column("precio", width=100)
        tree.column("stock", width=80)
        
        for producto in productos:
            tree.insert("", tk.END, values=producto[:4])
        
        def on_select():
            selected_item = tree.focus()
            if selected_item:
                values = tree.item(selected_item, 'values')
                self.current_product = {
                    'id': int(values[0]),
                    'nombre': values[1],
                    'precio': float(values[2]),
                    'stock': int(values[3])
                }
                # Buscar el código de barras del producto seleccionado
                for p in productos:
                    if p[0] == self.current_product['id']:
                        self.codigo_barras_var.set(p[4])
                        break
                self.producto_info_var.set(f"Producto: {values[1]}\nPrecio: ${values[2]}\nStock: {values[3]}")
                seleccion_window.destroy()
        
        scrollbar = ttk.Scrollbar(seleccion_window, orient=tk.VERTICAL, command=tree.yview, bootstyle="primary-round")
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        btn_frame = ttk.Frame(seleccion_window)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Seleccionar", command=on_select, bootstyle="success").pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancelar", command=seleccion_window.destroy, bootstyle="secondary").pack(side=tk.RIGHT, padx=10)
    
    def agregar_al_carrito(self):
        if not self.current_product:
            messagebox.showerror("Error", "Primero debe buscar un producto")
            return
        
        cantidad = self.cantidad_venta_var.get()
        
        if cantidad <= 0:
            messagebox.showerror("Error", "La cantidad debe ser mayor a cero")
            return
        
        if cantidad > self.current_product['stock']:
            messagebox.showerror("Error", f"No hay suficiente stock. Stock disponible: {self.current_product['stock']}")
            return
        
        # Verificar si el producto ya está en el carrito
        for item in self.carrito:
            if item['id'] == self.current_product['id']:
                # Actualizar cantidad si el producto ya está en el carrito
                nueva_cantidad = item['cantidad'] + cantidad
                if nueva_cantidad > self.current_product['stock']:
                    messagebox.showerror("Error", f"No hay suficiente stock. Stock disponible: {self.current_product['stock']}")
                    return
                item['cantidad'] = nueva_cantidad
                break
        else:
            # Agregar nuevo producto al carrito
            self.carrito.append({
                'id': self.current_product['id'],
                'nombre': self.current_product['nombre'],
                'precio': self.current_product['precio'],
                'cantidad': cantidad
            })
        
        # Actualizar carrito en la interfaz
        self.actualizar_carrito()
        
        # Limpiar búsqueda
        self.codigo_barras_var.set("")
        self.nombre_busqueda_var.set("")
        self.current_product = None
        self.producto_info_var.set("Producto: ---\nPrecio: ---\nStock: ---")
        self.cantidad_venta_var.set(1)
    
    def actualizar_carrito(self):
        # Limpiar treeview del carrito
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        
        # Calcular total
        total = 0
        
        # Agregar items al carrito
        for item in self.carrito:
            subtotal = item['precio'] * item['cantidad']
            total += subtotal
            self.cart_tree.insert("", tk.END, values=(
                item['nombre'],
                item['cantidad'],
                f"${item['precio']:.2f}",
                f"${subtotal:.2f}"
            ))
        
        # Actualizar total
        self.total_var.set(f"Total: ${total:.2f}")
    
    @manejar_errores
    def realizar_venta(self):
        if not self.carrito:
            messagebox.showerror("Error", "El carrito está vacío")
            return
        
        if not self.caja_abierta:
            messagebox.showerror("Error", "La caja está cerrada. Debe abrirla primero.")
            return
        
        # Confirmar venta
        confirmacion = messagebox.askyesno("Confirmar Venta", "¿Está seguro de realizar la venta?")
        if not confirmacion:
            return
        
        cursor = self.conn.cursor()
        
        try:
            # Calcular total de la venta
            total_venta = sum(item['precio'] * item['cantidad'] for item in self.carrito)
            
            # Registrar venta
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            metodo_pago = self.metodo_pago_var.get()
            cursor.execute("INSERT INTO ventas (fecha, total, estado_caja, metodo_pago) VALUES (?, ?, ?, ?)", 
                          (fecha, total_venta, "abierta", metodo_pago))
            venta_id = cursor.lastrowid
            
            # Registrar detalles de venta
            for item in self.carrito:
                # Obtener número de serie del producto
                cursor.execute("SELECT numero_serie FROM productos WHERE id = ?", (item['id'],))
                numero_serie = cursor.fetchone()[0]
                
                # Insertar detalle de venta
                cursor.execute(
                    "INSERT INTO detalle_venta (venta_id, producto_id, cantidad, precio, numero_serie) VALUES (?, ?, ?, ?, ?)",
                    (venta_id, item['id'], item['cantidad'], item['precio'], numero_serie)
                )
            
            # Publicar evento de venta para los microservicios
            evento_venta = {
                'tipo': 'VENTA',
                'venta_id': venta_id,
                'fecha': fecha,
                'monto': total_venta,
                'metodo_pago': metodo_pago,
                'productos': [{'id': item['id'], 'cantidad': item['cantidad']} for item in self.carrito]
            }
            self.kafka.publicar('inventario', evento_venta)
            self.kafka.publicar('contabilidad', evento_venta)
            
            # Actualizar ventas del día
            self.ventas_dia += total_venta
            self.ventas_hoy_var.set(f"Ventas hoy: ${self.ventas_dia:.2f}")
            
            # Confirmar transacción
            self.conn.commit()
            
            # Mostrar mensaje de éxito
            messagebox.showinfo("Venta Realizada", f"Venta realizada con éxito. Total: ${total_venta:.2f}")
            
            # Limpiar carrito
            self.carrito = []
            self.actualizar_carrito()
            
            # Actualizar productos
            self.load_products()
            
            # Actualizar ventas del día
            self.cargar_ventas_hoy()
            
            # Registrar en log
            self.log_evento(f"Venta realizada - ID: {venta_id}, Total: ${total_venta:.2f}")
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Ocurrió un error al procesar la venta: {str(e)}")
            self.log_evento(f"Error en venta: {str(e)}")
    
    def abrir_caja(self):
        if self.caja_abierta:
            messagebox.showinfo("Información", "La caja ya está abierta")
            return
        
        monto = self.monto_apertura_var.get()
        if monto < 0:
            messagebox.showerror("Error", "El monto inicial no puede ser negativo")
            return
        
        cursor = self.conn.cursor()
        
        try:
            # Registrar apertura de caja
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO caja (fecha_apertura, monto_inicial, estado) VALUES (?, ?, ?)",
                          (fecha, monto, "abierta"))
            
            self.conn.commit()
            
            # Actualizar estado
            self.caja_abierta = True
            self.monto_inicial = monto
            self.ventas_dia = 0.0
            
            self.actualizar_estado_caja()
            
            # Cargar ventas del día
            self.cargar_ventas_hoy()
            
            messagebox.showinfo("Caja Abierta", f"Caja abierta con monto inicial: ${monto:.2f}")
            
            # Registrar en log
            self.log_evento(f"Caja abierta - Monto inicial: ${monto:.2f}")
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al abrir caja: {str(e)}")
            self.log_evento(f"Error al abrir caja: {str(e)}")
    
    def cerrar_caja(self):
        if not self.caja_abierta:
            messagebox.showinfo("Información", "La caja ya está cerrada")
            return
        
        cursor = self.conn.cursor()
        
        try:
            # Calcular monto final
            monto_final = self.monto_inicial + self.ventas_dia
            
            # Registrar cierre de caja
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE caja SET fecha_cierre = ?, monto_final = ?, estado = 'cerrada' WHERE estado = 'abierta'",
                          (fecha, monto_final))
            
            self.conn.commit()
            
            # Mostrar resumen
            resumen = f"Resumen de caja:\n\n" \
                     f"Monto inicial: ${self.monto_inicial:.2f}\n" \
                     f"Ventas del día: ${self.ventas_dia:.2f}\n" \
                     f"Monto final: ${monto_final:.2f}\n\n" \
                     f"¿Desea cerrar la caja?"
            
            if messagebox.askyesno("Cerrar Caja", resumen):
                # Actualizar estado
                self.caja_abierta = False
                self.actualizar_estado_caja()
                
                messagebox.showinfo("Caja Cerrada", f"Caja cerrada. Monto final: ${monto_final:.2f}")
                
                # Registrar en log
                self.log_evento(f"Caja cerrada - Monto final: ${monto_final:.2f}")
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al cerrar caja: {str(e)}")
            self.log_evento(f"Error al cerrar caja: {str(e)}")
    
    def actualizar_estado_caja(self):
        if self.caja_abierta:
            self.estado_caja_var.set("Estado: ABIERTA")
            self.monto_inicial_var.set(f"Monto inicial: ${self.monto_inicial:.2f}")
            self.ventas_hoy_var.set(f"Ventas hoy: ${self.ventas_dia:.2f}")
        else:
            self.estado_caja_var.set("Estado: CERRADA")
            self.monto_inicial_var.set("Monto inicial: $0.00")
            self.ventas_hoy_var.set("Ventas hoy: $0.00")
    
    def cargar_ventas_hoy(self):
        # Limpiar treeview de ventas
        for item in self.ventas_tree.get_children():
            self.ventas_tree.delete(item)
        
        if not self.caja_abierta:
            return
        
        # Cargar ventas de hoy
        cursor = self.conn.cursor()
        hoy = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT id, fecha, total, metodo_pago FROM ventas WHERE fecha LIKE ? AND estado_caja = 'abierta' ORDER BY fecha", (hoy + '%',))
        ventas = cursor.fetchall()
        
        for venta in ventas:
            self.ventas_tree.insert("", tk.END, values=venta)
    
    @manejar_errores
    def agregar_producto(self):
        # Crear ventana de diálogo para agregar producto
        dialog = ttk.Toplevel(self.root)
        dialog.title("Agregar Producto")
        dialog.geometry("400x400")
        dialog.resizable(False, False)
        
        # Generar código de barras aleatorio
        codigo_barras = ''.join(random.choices(string.digits, k=13))
        numero_serie = 'SN-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # Campos del formulario
        ttk.Label(dialog, text="Código de Barras:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        codigo_var = tk.StringVar(value=codigo_barras)
        ttk.Entry(dialog, textvariable=codigo_var, state='readonly', bootstyle="info").grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Label(dialog, text="Número de Serie:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=10)
        serie_var = tk.StringVar(value=numero_serie)
        ttk.Entry(dialog, textvariable=serie_var, bootstyle="info").grid(row=1, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Label(dialog, text="Nombre:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=10)
        nombre_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=nombre_var, bootstyle="info").grid(row=2, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Label(dialog, text="Precio:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=10)
        precio_var = tk.DoubleVar()
        ttk.Entry(dialog, textvariable=precio_var, bootstyle="info").grid(row=3, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Label(dialog, text="Stock:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=10)
        stock_var = tk.IntVar()
        ttk.Entry(dialog, textvariable=stock_var, bootstyle="info").grid(row=4, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Label(dialog, text="Categoría:").grid(row=5, column=0, sticky=tk.W, padx=10, pady=10)
        categoria_var = tk.StringVar()
        categorias = ["Televisores", "Refrigeradoras", "Lavadoras", "Cocina", "Pequeños Electrodomésticos", "Limpieza", "Climatización", "Entretenimiento"]
        ttk.Combobox(dialog, textvariable=categoria_var, values=categorias, bootstyle="info").grid(row=5, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        # Botones
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        def guardar_producto():
            try:
                # Validación automática con pydantic
                producto = ProductoModel(
                    codigo_barras=codigo_var.get(),
                    nombre=nombre_var.get(),
                    precio=precio_var.get(),
                    stock=stock_var.get(),
                    categoria=categoria_var.get(),
                    numero_serie=serie_var.get()
                )
            except ValidationError as ve:
                messagebox.showerror("Error de validación", str(ve))
                return
            if not all([nombre_var.get(), precio_var.get(), stock_var.get(), categoria_var.get(), serie_var.get()]):
                messagebox.showerror("Error", "Todos los campos son obligatorios")
                return
            cursor = self.conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO productos (codigo_barras, nombre, precio, stock, categoria, numero_serie) VALUES (?, ?, ?, ?, ?, ?)",
                    (codigo_var.get(), nombre_var.get(), precio_var.get(), stock_var.get(), categoria_var.get(), serie_var.get())
                )
                self.conn.commit()
                messagebox.showinfo("Éxito", "Producto agregado correctamente")
                dialog.destroy()
                self.load_products()
                self.log_evento(f"Producto agregado: {nombre_var.get()}")
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "El código de barras o número de serie ya existe")
            except Exception as e:
                messagebox.showerror("Error", f"Error al agregar producto: {str(e)}")
        
        ttk.Button(btn_frame, text="Guardar", command=guardar_producto, bootstyle="success").pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy, bootstyle="secondary").pack(side=tk.LEFT, padx=10)
        
        # Configurar grid
        dialog.columnconfigure(1, weight=1)
    
    def editar_producto(self):
        selected_item = self.inv_tree.focus()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Por favor seleccione un producto para editar")
            return
        
        values = self.inv_tree.item(selected_item, 'values')
        product_id = values[0]
        
        # Crear ventana de diálogo para editar producto
        dialog = ttk.Toplevel(self.root)
        dialog.title("Editar Producto")
        dialog.geometry("400x400")
        dialog.resizable(False, False)
        
        # Obtener datos actuales del producto
        cursor = self.conn.cursor()
        cursor.execute("SELECT codigo_barras, nombre, precio, stock, categoria, numero_serie FROM productos WHERE id = ?", (product_id,))
        producto = cursor.fetchone()
        
        # Campos del formulario
        ttk.Label(dialog, text="Código de Barras:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        codigo_var = tk.StringVar(value=producto[0])
        ttk.Entry(dialog, textvariable=codigo_var, state='readonly', bootstyle="info").grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Label(dialog, text="Número de Serie:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=10)
        serie_var = tk.StringVar(value=producto[5])
        ttk.Entry(dialog, textvariable=serie_var, bootstyle="info").grid(row=1, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Label(dialog, text="Nombre:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=10)
        nombre_var = tk.StringVar(value=producto[1])
        ttk.Entry(dialog, textvariable=nombre_var, bootstyle="info").grid(row=2, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Label(dialog, text="Precio:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=10)
        precio_var = tk.DoubleVar(value=producto[2])
        ttk.Entry(dialog, textvariable=precio_var, bootstyle="info").grid(row=3, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Label(dialog, text="Stock:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=10)
        stock_var = tk.IntVar(value=producto[3])
        ttk.Entry(dialog, textvariable=stock_var, bootstyle="info").grid(row=4, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Label(dialog, text="Categoría:").grid(row=5, column=0, sticky=tk.W, padx=10, pady=10)
        categoria_var = tk.StringVar(value=producto[4])
        categorias = ["Televisores", "Refrigeradoras", "Lavadoras", "Cocina", "Pequeños Electrodomésticos", "Limpieza", "Climatización", "Entretenimiento"]
        ttk.Combobox(dialog, textvariable=categoria_var, values=categorias, bootstyle="info").grid(row=5, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        # Botones
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        def guardar_cambios():
            if not all([nombre_var.get(), precio_var.get(), stock_var.get(), categoria_var.get(), serie_var.get()]):
                messagebox.showerror("Error", "Todos los campos son obligatorios")
                return
            
            cursor = self.conn.cursor()
            try:
                cursor.execute(
                    "UPDATE productos SET nombre = ?, precio = ?, stock = ?, categoria = ?, numero_serie = ? WHERE id = ?",
                    (nombre_var.get(), precio_var.get(), stock_var.get(), categoria_var.get(), serie_var.get(), product_id)
                )
                self.conn.commit()
                messagebox.showinfo("Éxito", "Producto actualizado correctamente")
                dialog.destroy()
                self.load_products()
                
                # Registrar en log
                self.log_evento(f"Producto actualizado: {nombre_var.get()}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al actualizar producto: {str(e)}")
        
        ttk.Button(btn_frame, text="Guardar", command=guardar_cambios, bootstyle="success").pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy, bootstyle="secondary").pack(side=tk.LEFT, padx=10)
        
        # Configurar grid
        dialog.columnconfigure(1, weight=1)
    
    def eliminar_producto(self):
        selected_item = self.inv_tree.focus()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Por favor seleccione un producto para eliminar")
            return
        
        values = self.inv_tree.item(selected_item, 'values')
        product_id, nombre = values[0], values[2]
        
        confirmacion = messagebox.askyesno("Confirmar Eliminación", f"¿Está seguro de eliminar el producto '{nombre}'?")
        if not confirmacion:
            return
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM productos WHERE id = ?", (product_id,))
            self.conn.commit()
            messagebox.showinfo("Éxito", "Producto eliminado correctamente")
            self.load_products()
            
            # Registrar en log
            self.log_evento(f"Producto eliminado: {nombre}")
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al eliminar producto: {str(e)}")
            self.log_evento(f"Error al eliminar producto: {str(e)}")
    
    def buscar_venta_devolucion(self):
        venta_id = self.devolucion_venta_id_var.get().strip()
        if not venta_id:
            messagebox.showwarning("Advertencia", "Por favor ingrese un ID de venta")
            return
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, fecha, total FROM ventas WHERE id = ?", (venta_id,))
        venta = cursor.fetchone()
        
        if venta:
            self.venta_devolucion = {
                'id': venta[0],
                'fecha': venta[1],
                'total': venta[2]
            }
            self.devolucion_venta_info_var.set(f"Venta ID: {venta[0]} - Fecha: {venta[1]} - Total: ${venta[2]:.2f}")
            self.cargar_productos_venta_devolucion(venta_id)
        else:
            messagebox.showerror("Error", "Venta no encontrada")
            self.venta_devolucion = None
            self.devolucion_venta_info_var.set("Venta: ---")
    
    def buscar_serie_devolucion(self):
        numero_serie = self.devolucion_serie_var.get().strip()
        if not numero_serie:
            messagebox.showwarning("Advertencia", "Por favor ingrese un número de serie")
            return
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT v.id, v.fecha, v.total
            FROM ventas v
            JOIN detalle_venta dv ON v.id = dv.venta_id
            WHERE dv.numero_serie = ?
        ''', (numero_serie,))
        venta = cursor.fetchone()
        
        if venta:
            self.venta_devolucion = {
                'id': venta[0],
                'fecha': venta[1],
                'total': venta[2]
            }
            self.devolucion_venta_id_var.set(venta[0])
            self.devolucion_venta_info_var.set(f"Venta ID: {venta[0]} - Fecha: {venta[1]} - Total: ${venta[2]:.2f}")
            self.cargar_productos_venta_devolucion(venta[0])
        else:
            messagebox.showerror("Error", "No se encontró venta con ese número de serie")
            self.venta_devolucion = None
            self.devolucion_venta_info_var.set("Venta: ---")
    
    def cargar_productos_venta_devolucion(self, venta_id):
        # Limpiar treeview
        for item in self.devolucion_tree.get_children():
            self.devolucion_tree.delete(item)
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT p.nombre, dv.cantidad, dv.precio, dv.numero_serie, p.id
            FROM detalle_venta dv
            JOIN productos p ON dv.producto_id = p.id
            WHERE dv.venta_id = ?
        ''', (venta_id,))
        productos = cursor.fetchall()
        
        self.productos_devolucion = []
        for prod in productos:
            self.devolucion_tree.insert("", tk.END, values=prod[:4])
            self.productos_devolucion.append({
                'id': prod[4],
                'nombre': prod[0],
                'cantidad': prod[1],
                'precio': prod[2],
                'numero_serie': prod[3]
            })
    
    def seleccionar_producto_devolucion(self, event):
        selected_item = self.devolucion_tree.focus()
        if selected_item:
            values = self.devolucion_tree.item(selected_item, 'values')
            for prod in self.productos_devolucion:
                if prod['nombre'] == values[0] and prod['numero_serie'] == values[3]:
                    self.producto_devolucion_seleccionado = prod
                    break
            
            if self.producto_devolucion_seleccionado:
                self.devolucion_producto_var.set(self.producto_devolucion_seleccionado['nombre'])
                self.devolucion_cantidad_var.set(1)
                self.devolucion_estado_var.set("vendible")
                self.devolucion_motivo_var.set("")
    
    @manejar_errores
    def procesar_devolucion(self):
        if not self.venta_devolucion or not self.producto_devolucion_seleccionado:
            messagebox.showerror("Error", "Debe seleccionar una venta y un producto")
            return
        
        cantidad = self.devolucion_cantidad_var.get()
        estado = self.devolucion_estado_var.get()
        motivo = self.devolucion_motivo_var.get()
        
        if cantidad <= 0:
            messagebox.showerror("Error", "La cantidad debe ser mayor a cero")
            return
        
        if cantidad > self.producto_devolucion_seleccionado['cantidad']:
            messagebox.showerror("Error", "No puede devolver más de lo comprado")
            return
        
        if not estado:
            messagebox.showerror("Error", "Debe indicar el estado del producto")
            return
        
        if not motivo.strip():
            messagebox.showerror("Error", "Debe ingresar un motivo")
            return
        
        # Verificar si requiere autorización (producto de alto valor: >= $500)
        requiere_autorizacion = self.producto_devolucion_seleccionado['precio'] >= 500
        
        if requiere_autorizacion:
            # Pedir autenticación de gerente
            if not self.autenticar_gerente():
                messagebox.showerror("Error", "Autorización denegada")
                return
        
        # Procesar devolución
        cursor = self.conn.cursor()
        try:
            # Registrar la devolución
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            autorizado_por = "admin" if requiere_autorizacion else None
            cursor.execute('''
                INSERT INTO devoluciones (venta_id, producto_id, cantidad, motivo, estado_producto, fecha, autorizado_por)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (self.venta_devolucion['id'], self.producto_devolucion_seleccionado['id'], 
                  cantidad, motivo, estado, fecha, autorizado_por))
            
            # Publicar evento de devolución para los microservicios
            evento_devolucion = {
                'tipo': 'DEVOLUCION',
                'venta_id': self.venta_devolucion['id'],
                'producto_id': self.producto_devolucion_seleccionado['id'],
                'cantidad': cantidad,
                'monto': self.producto_devolucion_seleccionado['precio'] * cantidad,
                'estado_producto': estado,
                'requiere_autorizacion': requiere_autorizacion
            }
            self.kafka.publicar('inventario', evento_devolucion)
            self.kafka.publicar('contabilidad', evento_devolucion)
            
            self.conn.commit()
            messagebox.showinfo("Éxito", "Devolución procesada correctamente")
            
            # Limpiar formulario
            self.limpiar_formulario_devolucion()
            
            # Registrar en log
            self.log_evento(f"Devolución procesada - Venta ID: {self.venta_devolucion['id']}, Producto: {self.producto_devolucion_seleccionado['nombre']}")
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error al procesar devolución: {str(e)}")
            self.log_evento(f"Error en devolución: {str(e)}")
    
    def autenticar_gerente(self):
        # Crear una ventana de login
        login_window = ttk.Toplevel(self.root)
        login_window.title("Autenticación de Gerente")
        login_window.geometry("300x150")
        login_window.resizable(False, False)
        
        ttk.Label(login_window, text="Usuario:", bootstyle="info").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        usuario_var = tk.StringVar()
        ttk.Entry(login_window, textvariable=usuario_var, bootstyle="info").grid(row=0, column=1, padx=10, pady=10, sticky=(tk.W, tk.E))
        
        ttk.Label(login_window, text="Contraseña:", bootstyle="info").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        password_var = tk.StringVar()
        ttk.Entry(login_window, textvariable=password_var, show="*", bootstyle="info").grid(row=1, column=1, padx=10, pady=10, sticky=(tk.W, tk.E))
        
        resultado = [False]  # Usamos una lista para simular pass-by-reference
        
        def verificar():
            cursor = self.conn.cursor()
            password_hash = hashlib.sha256(password_var.get().encode()).hexdigest()
            cursor.execute("SELECT * FROM usuarios WHERE username = ? AND password = ? AND rol = 'gerente'",
                           (usuario_var.get(), password_hash))
            if cursor.fetchone():
                resultado[0] = True
                login_window.destroy()
            else:
                messagebox.showerror("Error", "Credenciales incorrectas")
                resultado[0] = False
        
        ttk.Button(login_window, text="Ingresar", command=verificar, bootstyle="success").grid(row=2, column=0, columnspan=2, pady=10)
        
        login_window.columnconfigure(1, weight=1)
        login_window.wait_window()
        
        return resultado[0]
    
    def limpiar_formulario_devolucion(self):
        self.devolucion_venta_id_var.set("")
        self.devolucion_serie_var.set("")
        self.devolucion_venta_info_var.set("Venta: ---")
        for item in self.devolucion_tree.get_children():
            self.devolucion_tree.delete(item)
        self.devolucion_producto_var.set("")
        self.devolucion_cantidad_var.set(1)
        self.devolucion_estado_var.set("")
        self.devolucion_motivo_var.set("")
        self.venta_devolucion = None
        self.productos_devolucion = []
        self.producto_devolucion_seleccionado = None
    
    def generar_reporte(self):
        fecha_inicio = self.reporte_fecha_inicio_var.get()
        fecha_fin = self.reporte_fecha_fin_var.get()
        
        try:
            # Validar fechas
            datetime.strptime(fecha_inicio, "%Y-%m-%d")
            datetime.strptime(fecha_fin, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha incorrecto. Use YYYY-MM-DD")
            return
        
        # Limpiar treeview de reporte
        for item in self.reporte_tree.get_children():
            self.reporte_tree.delete(item)
        
        cursor = self.conn.cursor()
        
        # Obtener ventas en el período
        cursor.execute('''
            SELECT fecha, total, metodo_pago 
            FROM ventas 
            WHERE date(fecha) BETWEEN ? AND ?
            ORDER BY fecha
        ''', (fecha_inicio, fecha_fin))
        ventas = cursor.fetchall()
        
        # Obtener devoluciones en el período
        cursor.execute('''
            SELECT d.fecha, p.nombre, d.cantidad, d.motivo, (p.precio * d.cantidad) as monto
            FROM devoluciones d
            JOIN productos p ON d.producto_id = p.id
            WHERE date(d.fecha) BETWEEN ? AND ?
            ORDER BY d.fecha
        ''', (fecha_inicio, fecha_fin))
        devoluciones = cursor.fetchall()
        
        # Calcular KPIs
        total_ventas = sum(venta[1] for venta in ventas)
        total_devoluciones = sum(devolucion[4] for devolucion in devoluciones)
        cantidad_ventas = len(ventas)
        
        # Obtener producto más vendido
        cursor.execute('''
            SELECT p.nombre, SUM(dv.cantidad) as total_vendido
            FROM detalle_venta dv
            JOIN productos p ON dv.producto_id = p.id
            JOIN ventas v ON dv.venta_id = v.id
            WHERE date(v.fecha) BETWEEN ? AND ?
            GROUP BY p.id
            ORDER BY total_vendido DESC
            LIMIT 1
        ''', (fecha_inicio, fecha_fin))
        producto_mas_vendido = cursor.fetchone()
        
        # Actualizar KPIs en la interfaz
        self.ingresos_var.set(f"Ingresos: ${total_ventas:.2f}")
        self.egresos_var.set(f"Egresos: ${total_devoluciones:.2f}")
        self.ventas_totales_var.set(f"Ventas totales: {cantidad_ventas}")
        
        if producto_mas_vendido:
            self.producto_mas_vendido_var.set(f"Producto más vendido: {producto_mas_vendido[0]} ({producto_mas_vendido[1]} unidades)")
        else:
            self.producto_mas_vendido_var.set("Producto más vendido: ---")
        
        # Agregar ventas al reporte
        for venta in ventas:
            self.reporte_tree.insert("", tk.END, values=(
                venta[0], "VENTA", f"Venta - {venta[2]}", f"${venta[1]:.2f}"
            ))
        
        # Agregar devoluciones al reporte
        for devolucion in devoluciones:
            self.reporte_tree.insert("", tk.END, values=(
                devolucion[0], "DEVOLUCIÓN", f"{devolucion[1]} - {devolucion[3]}", f"-${devolucion[4]:.2f}"
            ))
        
        # Registrar en log
        self.log_evento(f"Reporte generado desde {fecha_inicio} hasta {fecha_fin}")
    
    def log_evento(self, mensaje):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {mensaje}\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)
    
    def limpiar_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def exportar_eventos(self):
        # Exportar eventos a un archivo JSON
        filename = f"eventos_sistema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.kafka.eventos, f, indent=2)
        
        messagebox.showinfo("Éxito", f"Eventos exportados a {filename}")
        self.log_evento(f"Eventos exportados a {filename}")
    
    def monitorear_alertas(self):
        # Monitorear alertas de stock bajo en segundo plano
        def check_alertas():
            while True:
                time.sleep(10)  # Revisar cada 10 segundos
                
                if self.inventario_service.alertas_stock_bajo:
                    self.alertas_text.config(state=tk.NORMAL)
                    self.alertas_text.delete(1.0, tk.END)
                    
                    for producto in self.inventario_service.alertas_stock_bajo:
                        self.alertas_text.insert(tk.END, f"ALERTA: Stock bajo de {producto[0]} - {producto[1]} unidades\n")
                    
                    self.alertas_text.config(state=tk.DISABLED)
        
        # Ejecutar en un hilo separado
        thread = threading.Thread(target=check_alertas, daemon=True)
        thread.start()

class ProductoSchema(BaseModel):
    codigo_barras: str = Field(..., min_length=13, max_length=13)
    nombre: str = Field(..., min_length=1)
    precio: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    categoria: str = Field(..., min_length=1)
    numero_serie: str = Field(..., min_length=1)

if __name__ == "__main__":
    root = ttk.Window(themename="darkly")
    app = SistemaElectrodomesticos(root)
    root.mainloop()