import pytest
import tkinter as tk
from src.main import SistemaElectrodomesticos

def test_app_starts():
    root = tk.Tk()
    app = SistemaElectrodomesticos(root)
    assert app.root.title() == "ElectroStore - Sistema de Gestión"
    # Simula navegación básica
    assert hasattr(app, 'main_container')
    assert hasattr(app, 'sidebar_frame')
    assert hasattr(app, 'main_content')
    # Simula mostrar ventas (si el método existe)
    if hasattr(app, 'mostrar_ventas'):
        app.mostrar_ventas()
    root.destroy()
