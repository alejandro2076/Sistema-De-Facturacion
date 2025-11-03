# ElectroStore ERP/POS

Sistema ERP/POS robusto para ElectroStore, desarrollado en Python con FastAPI. Incluye backend seguro, validaciones automáticas, API REST, logging avanzado y pruebas de integración.

## Características principales
- API REST con FastAPI
- Autenticación JWT y gestión segura de contraseñas (bcrypt)
- Validaciones automáticas con Pydantic
- Logging avanzado y auditoría
- Pruebas unitarias y de integración
- Base de datos SQLite configurable por variable de entorno
- Documentación automática OpenAPI/Swagger

## Documentación de la API
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Redoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Instalación y uso

### Instalar dependencias
```bash
pip install -r requirements.txt
pip install -r requirements-additional.txt
```

### Ejecutar la API
```bash
uvicorn api:app --reload
```

### Ejecutar pruebas
```bash
pytest tests/
```

### Ejecutar con Docker
```bash
docker-compose up --build
```

## Estructura de carpetas
- `api.py`: API principal y endpoints
- `main.py`: Lógica de negocio y modelos
- `logging_config.py`: Configuración de logs y auditoría
- `test_backend.py`: Pruebas unitarias de modelos
- `test_integration.py`: Pruebas de integración
- `requirements.txt`: Dependencias

## Variables de entorno
- `ELECTROSTORE_DB`: Permite definir la base de datos a usar (por defecto `electrostore.db`).

## Ejemplos de uso

### Crear un producto (requiere token de admin/gerente)
```bash
curl -X POST "http://localhost:8000/productos" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "codigo_barras": "1234567890123",
    "nombre": "Televisor",
    "precio": 100.0,
    "stock": 10,
    "categoria": "Electrónica",
    "numero_serie": "SN-12345678"
  }'
```

### Registrar usuario
```bash
curl -X POST "http://localhost:8000/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "usuario1", "password": "clave123"}'
```

### Login y obtener token
```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "usuario1", "password": "clave123"}'
```

## Cómo ejecutar pruebas unitarias y de integración

### Pruebas unitarias (modelos)
```bash
pytest test_backend.py -v
```

### Pruebas de integración (API completa)
```bash
pytest test_integration.py -v
```

### Ejecutar todas las pruebas
```bash
pytest -v
```

## Levantar el entorno con Docker

1. Construye y ejecuta el servicio:
   ```bash
   docker-compose up --build
   ```
2. Accede a la API en [http://localhost:8000/docs](http://localhost:8000/docs) para probar y consultar la documentación interactiva.

## Configuración para PostgreSQL (producción)

Para usar PostgreSQL en vez de SQLite:
1. Edita `DATABASE_URL` en `.env` o en `docker-compose.yml`:
   ```
   DATABASE_URL=postgresql://electrostore:electrostorepass@db:5432/electrostore
   ```
2. Levanta el entorno con Docker Compose:
   ```bash
   docker-compose up --build
   ```
3. Ejecuta migraciones Alembic:
   ```bash
   alembic upgrade head
   ```

## ALERTAS Y MONITOREO
Para alertas avanzadas, se recomienda integrar Sentry:
```python
import sentry_sdk
sentry_sdk.init(dsn="<TU_DSN_SENTRY>")
```
El monitoreo Prometheus ya está disponible en `/metrics`.

---
Desarrollado para ElectroStore. Para soporte o mejoras, contacta al equipo de desarrollo.


## Nuevas implementaciones
_______________________________
```python
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import random
import string
```

## La Vista Comienza desde:

```python
class SistemaElectrodomesticos:
```
________________________________
# Vista de Interfaz - Sistema ElectroStore

## 🎨 Diseño General
**Tema**: Azul profesional con acentos verdes  
**Layout:** Sistema de pestañas con organización modular  
**Responsivo:** Adaptable a diferentes tamaños de pantalla

---

## 📋 Pestaña "Punto de Venta"

### 🔍 Panel de Escaneo y Búsqueda
```
[Escaneo de Productos]
├── Código de Barras: [_______________] [Buscar Producto] (Enter)
├── Buscar por Nombre: [_______________] [Buscar] (Enter)
├── 
└── ℹ️ Producto: ---
    Precio: ---  
    Stock: ---
```

### 🛒 Carrito de Compras
```
[Carrito de Compra]
├── ┌─────────────────────────────────────────────────────┐
│   │ Producto          │ Cantidad │ Precio Unit │ Subtotal │
│   ├─────────────────────────────────────────────────────┤
│   │ Smart TV 55" 4K   │    1     │   $899.99   │  $899.99 │
│   │ Cafetera Automáti │    2     │   $129.99   │  $259.98 │
│   └─────────────────────────────────────────────────────┘
│
└── Total: $1,159.97     [Realizar Venta]
```

---

## 📊 Pestaña "Gestión de Inventario"

### 📦 Tabla de Productos
```
┌─────────────────────────────────────────────────────────────────────────┐
│ ID │ Código Barras   │ Nombre              │ Precio  │ Stock │ Categoría│
├─────────────────────────────────────────────────────────────────────────┤
│ 1  │ 7501006554025   │ Smart TV 55" 4K     │ $899.99 │  15   │TV        │
│ 2  │ 7501055300124   │ Refrigeradora French│ $1599.99│  8    │Refriger. │
│ 3  │ 7501006554032   │ Lavadora Secadora   │ $749.99 │  12   │Lavadoras │
└─────────────────────────────────────────────────────────────────────────┘
```

### 🛠️ Controles de Inventario
```
[Agregar Producto] [Editar Producto] [Eliminar Producto] [Actualizar]
```

---

## 💰 Pestaña "Control de Caja"

### 📊 Estado de Caja
```
[Estado de Caja]
├── Estado: ABIERTA ✅
├── Monto inicial: $500.00
└── Ventas hoy: $1,159.97
```

### ⚙️ Controles de Caja
```
[Controles de Caja]
├── Monto inicial: [500.00] [Abrir Caja] [Cerrar Caja]
└── 
```

### 📈 Reporte de Ventas
```
[Ventas de Hoy]
┌─────────────────────────────────────┐
│ ID │ Fecha y Hora      │ Total      │
├─────────────────────────────────────┤
│ 15 │ 2024-01-15 10:30 │ $1,159.97  │
│ 14 │ 2024-01-15 09:45 │ $299.99    │
└─────────────────────────────────────┘
```

---

## 🎯 Flujos Visuales

### 1. Flujo de Venta
```
[Escaneo] → [Verificación] → [Info Producto] → [Selección Cantidad] 
→ [Agregar Carrito] → [Repetir] → [Revisar Carrito] → [Confirmar Venta]
```

### 2. Flujo de Gestión
```
[Seleccionar Producto] → [Editar/Eliminar] → [Confirmar] → [Actualizar Tabla]
```

### 3. Flujo de Caja
```
[Ingresar Monto] → [Abrir Caja] → [Realizar Ventas] → [Cerrar Caja] 
→ [Ver Resumen]
```

---

## 🎨 Paleta de Colores

**Primarios:**
- Fondo: #f0f8ff (Azul claro)
- Encabezados: #2c3e50 (Azul oscuro)
- Botones: #3498db (Azul)

**Secundarios:**
- Éxito: #27ae60 (Verde)
- Peligro: #e74c3c (Rojo)
- Advertencia: #f39c12 (Naranja)

**Texto:**
- Principal: #333333
- Secundario: #7f8c8d

---

## 📱 Responsividad

**Pantallas Grandes (>1200px):** Layout completo 3 columnas  
**Pantallas Medianas (900-1200px):** Reorganización de elementos  
**Pantallas Pequeñas (<900px):** Layout una columna, pestañas verticales

---

## 🔍 Experiencia de Usuario

**Feedback Visual:**
- ✅ Éxito: Notificaciones verdes
- ❌ Error: Mensajes rojos con detalles
- ⚠️ Advertencia: Alertas amarillas
- ❓ Confirmación: Diálogos modales

**Navegación:**
- Tab navigation entre campos
- Enter para buscar productos
- Focus indicators visibles

---

## 🖥️ Elementos de Interfaz

**Tipografía:**
- Títulos: Arial 16px bold
- Texto normal: Segoe UI
- Totales: Arial 12px bold

**Iconografía:**
- 📺 Televisores
- ❄️ Refrigeradoras
- 🔄 Lavadoras
- 🔥 Cocina
- ⚡ Pequeños Electrodomésticos
- 🧹 Limpieza
- ❄️🔥 Climatización
- 🎮 Entretenimiento

---

## 🎪 Estados Interactivos

**Botones:** Efecto hover y estados disabled  
**Campos:** Focus indicators y validación visual  
**Tablas:** Selección de filas y scroll suave  
**Notificaciones:** Transiciones de aparición/desaparición

Esta interfaz está optimizada para flujo de trabajo eficiente en tienda de electrodomésticos con navegación intuitiva y feedback visual claro.

## Repositorio

Repositorio oficial: [https://github.com/alejandro2076/Proyecto-ERP](https://github.com/alejandro2076/Proyecto-ERP)

## Paso a paso para subir cambios a GitHub

1. Abre PowerShell en la carpeta del proyecto.
2. Verifica el estado de los archivos:
   ```powershell
   git status
   ```
3. Agrega los archivos modificados:
   ```powershell
   git add .
   ```
4. Haz el commit con un mensaje descriptivo:
   ```powershell
   git commit -m "Descripción de los cambios"
   ```
5. Sube los cambios a la rama principal (`main`):
   ```powershell
   git push origin main
   ```

Si es la primera vez que subes el proyecto, asegúrate de haber configurado el remoto:
```powershell
git remote add origin https://github.com/alejandro2076/Proyecto-ERP.git
git push -u origin main
```

Puedes ver el repositorio y tus cambios en:
[https://github.com/alejandro2076/Proyecto-ERP](https://github.com/alejandro2076/Proyecto-ERP)