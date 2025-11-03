import pytest
from pydantic import ValidationError
from main import ProductoSchema

def test_producto_model_valido():
    producto = ProductoSchema(
        codigo_barras="1234567890123",
        nombre="Televisor",
        precio=100.0,
        stock=10,
        categoria="Electrónica",
        numero_serie="SN-12345678"
    )
    assert producto.nombre == "Televisor"

def test_producto_model_invalido():
    with pytest.raises(ValidationError):
        ProductoSchema(
            codigo_barras="123",
            nombre="",
            precio=-10,
            stock=-1,
            categoria="",
            numero_serie=""
        )
