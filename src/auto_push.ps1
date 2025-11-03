# Script para subir automáticamente el proyecto a GitHub
# Uso: Ejecuta este script en PowerShell desde la raíz del proyecto

# Agrega todos los cambios
git add .

# Crea un commit con mensaje automático (puedes cambiar el mensaje)
$fecha = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
git commit -m "Auto commit: $fecha"

# Sube los cambios al repositorio remoto
# Asegúrate de tener configurado el remote 'origin' y permisos

git push origin main
