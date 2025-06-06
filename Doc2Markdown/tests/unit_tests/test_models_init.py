import pytest
from app.models import User, Document

def test_models_init_imports():
    """
    Prueba que los modelos User y Document pueden ser importados correctamente desde models/__init__.py
    """
    # Verificar que las clases existen y son importables
    assert User is not None
    assert Document is not None
    
    # Verificar que son clases (no módulos u otros objetos)
    assert isinstance(User, type)
    assert isinstance(Document, type)

def test_models_init_all():
    """
    Prueba que __all__ contiene los elementos correctos
    """
    from app.models import __all__ as models_all
    
    # Verificar que __all__ contiene exactamente 'User' y 'Document'
    assert set(models_all) == {'User', 'Document'}
    assert len(models_all) == 2

def test_models_can_be_instantiated():
    """
    Prueba que los modelos pueden ser instanciados con sus parámetros básicos
    """
    # Probar creación básica de User
    user = User(username="test", email="test@example.com", password_hash="hash")
    assert user.username == "test"
    assert user.email == "test@example.com"
    assert user.password_hash == "hash"
    
    # Probar creación básica de Document (sin 'owner_id', usando 'user_id')
    document = Document(title="Test Doc", user_id=1)  # Reemplazado 'owner_id' por 'user_id'
    assert document.title == "Test Doc"
    assert document.user_id == 1  # Verifica que 'user_id' esté asignado correctamente

@pytest.mark.parametrize("model_class", [User, Document])
def test_models_have_repr_method(model_class):
    """
    Prueba que los modelos tienen implementado el método __repr__
    """
    # Crear una instancia básica dependiendo de la clase
    if model_class is User:
        instance = model_class(username="test", email="test@example.com", password_hash="hash")
    else:
        instance = model_class(title="Test", user_id=1)  # Reemplazado 'owner_id' por 'user_id'
    
    # Verificar que __repr__ existe y devuelve un string
    repr_str = repr(instance)
    assert isinstance(repr_str, str)
    assert repr_str != ""
