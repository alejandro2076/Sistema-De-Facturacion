# ElectroStore ERP/POS

Sistema integral de gestión y facturación para comercios, desarrollado en Python. Permite administrar inventario, ventas, usuarios y emitir facturas digitales, con arquitectura modular y escalable.

---

## Descripción General
ElectroStore ERP/POS es una solución completa para la gestión de comercios, adaptable a cualquier tipo de producto. Incluye:
- Backend API REST con FastAPI
- Interfaz gráfica moderna con Tkinter/ttkbootstrap
- Base de datos PostgreSQL (soporte legacy para SQLite)
- Control de usuarios y roles
- Auditoría y logging avanzado
- Pruebas automatizadas
- Generación de facturas digitales (PDF)
- Preparado para integración con impresoras fiscales
- Despliegue con Docker y ejecutable standalone

---

## Estructura del Proyecto
```
├── src/
│   ├── main.py                # Lógica principal y GUI
│   ├── api.py                 # Endpoints FastAPI
│   ├── logging_config.py      # Configuración de logs
│   ├── alembic/               # Migraciones DB
│   ├── Dockerfile, docker-compose.yml
│   └── ...
├── requirements/
│   ├── requirements.txt
│   └── requirements-additional.txt
├── scripts/
│   ├── crear_usuarios_iniciales.py
│   ├── migrar_sqlite_a_postgres.py
│   ├── validate_system.py
│   └── verificar_usuarios.py
├── tests/
│   ├── test_api_critical.py
│   ├── test_backend.py
│   ├── test_gui_critical.py
│   └── test_integration.py
├── dist/                      # Ejecutable generado
├── logs/                      # Archivos de auditoría
├── README.md
```

---

## Instalación y Configuración

### 1. Instalar dependencias
```powershell
pip install -r requirements/requirements.txt
pip install -r requirements/requirements-additional.txt
```

### 2. Configurar base de datos
- Por defecto usa PostgreSQL. Edita la cadena de conexión en `src/main.py` si es necesario.
- Para migrar desde SQLite, ejecuta:
  ```powershell
  python scripts/migrar_sqlite_a_postgres.py
  ```

### 3. Crear usuarios iniciales
```powershell
python scripts/crear_usuarios_iniciales.py
```
Usuarios iniciales: superadmin, gerente, cajero, devteam, almacen (roles y contraseñas seguras).

### 4. Ejecutar el sistema
- **API:**
  ```powershell
  uvicorn src/api:app --reload
  ```
- **GUI:**
  ```powershell
  python src/main.py
  ```
- **Ejecutable:**
  ```powershell
  pyinstaller --onefile --windowed src/main.py
  # Ejecuta dist/main.exe
  ```
- **Docker:**
  ```powershell
  docker-compose up --build
  ```

### 5. Pruebas automatizadas y validación
```powershell
pytest tests/
python scripts/validate_system.py
```

---

## Funcionalidades Detalladas

### Inventario y Productos
- Registro, edición y eliminación de productos.
- Búsqueda avanzada con autocompletado por nombre, categoría y código de barras.
- Visualización de stock en tiempo real.
- Permisos granulares por rol (almacen, gerente, etc).
- Actualización automática de stock tras ventas y devoluciones.

### Punto de Venta
- Carrito de compras interactivo: agregar, modificar y eliminar productos antes de la venta.
- Validación de stock disponible.
- Selección de método de pago (efectivo, tarjeta, transferencia, pago móvil).
- Cálculo automático de impuestos:
  - IGTF (3%) para pagos en efectivo.
  - IVA (16%) para pagos electrónicos.
- Finalización de venta con registro en la base de datos y actualización de inventario.

### Facturación Digital
- Generación automática de factura en PDF al finalizar la venta.
- Factura incluye: datos de empresa, fecha, productos vendidos, cantidades, precios, impuestos y total.
- Archivos PDF listos para impresión o envío digital.
- Preparado para integración con impresoras fiscales (futuro).

### Gestión de Usuarios y Roles
- Creación y administración de usuarios con roles: superadmin, gerente, cajero, devteam, almacen.
- Permisos diferenciados para cada rol.
- Seguridad avanzada: contraseñas cifradas, autenticación JWT.

### Auditoría y Logging
- Registro de eventos críticos y errores en archivos de log.
- Auditoría de acciones de usuarios y cambios en inventario.
- Logs accesibles para revisión y cumplimiento.

### Pruebas y Validación
- Pruebas unitarias y de integración para API y GUI.
- Scripts de validación de sistema y usuarios.
- Cobertura de casos críticos: inventario, ventas, permisos, endpoints.

### Despliegue y Mantenimiento
- Docker y docker-compose para despliegue rápido y reproducible.
- PyInstaller para generación de ejecutable standalone.
- Scripts para migración de base de datos y limpieza de archivos legacy.
- Comandos PowerShell para depuración y mantenimiento.

---

## API REST y Endpoints
- Documentación automática con Swagger UI y Redoc:
  - [http://localhost:8000/docs](http://localhost:8000/docs)
  - [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Endpoints para gestión de productos, ventas, usuarios, reportes y auditoría.
- Ejemplo de uso (adaptable a cualquier producto):
```bash
curl -X POST "http://localhost:8000/productos" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "codigo_barras": "<código>",
    "nombre": "<nombre>",
    "precio": <precio>,
    "stock": <stock>,
    "categoria": "<categoría>",
    "numero_serie": "<serie>"
  }'
```

---

## Roles y Permisos
- **superadmin:** Acceso total, configuración y auditoría.
- **gerente:** Gestión avanzada, reportes y usuarios.
- **cajero:** Punto de venta y facturación.
- **devteam:** Desarrollo, mantenimiento y pruebas.
- **almacen:** Gestión de inventario y productos.

---

## Migración, Limpieza y Mantenimiento
- Migración de datos de SQLite a PostgreSQL con script dedicado.
- Limpieza automática de archivos legacy, logs vacíos y temporales.
- Validación de usuarios y datos con scripts.
- Comandos PowerShell para eliminar archivos innecesarios:
```powershell
Remove-Item .\electrostore.db -Force
Remove-Item .\src\electrostore.db -Force
Remove-Item .\src\logs -Recurse -Force
Remove-Item .\src\__pycache__ -Recurse -Force
Remove-Item .\src\alembic\versions\__pycache__ -Recurse -Force
Remove-Item .\tests\__pycache__ -Recurse -Force
Remove-Item .\app.log -Force
Remove-Item .\src\main.spec -Force
```

---

## Personalización y Extensibilidad
- El sistema es adaptable a cualquier tipo de producto registrado en la base de datos.
- Fácil integración de nuevas funcionalidades y módulos.
- Preparado para conectar con hardware fiscal y otros sistemas externos.

---

## Contacto y Soporte
Para dudas, soporte o mejoras, abre un issue en GitHub o contacta al equipo de desarrollo.

---
Este README está optimizado para documentación técnica y visualización en GitHub. Para detalles adicionales, consulta los scripts y archivos fuente incluidos en el proyecto.