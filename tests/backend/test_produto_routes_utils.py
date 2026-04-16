import os

os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")

from app.routes.produto_routes import truncate_utf8_bytes


def test_truncate_utf8_bytes_sem_truncamento():
    texto = "Produto Simples"
    assert truncate_utf8_bytes(texto, 200) == texto


def test_truncate_utf8_bytes_respeita_limite_multibyte():
    texto = "\u00e1" * 120  # 240 bytes em UTF-8
    resultado = truncate_utf8_bytes(texto, 200)

    assert len(resultado.encode("utf-8")) <= 200
    assert resultado == "\u00e1" * 100


def test_truncate_utf8_bytes_sem_quebrar_caractere():
    texto = "\u6c49"  # 3 bytes em UTF-8
    assert truncate_utf8_bytes(texto, 1) == ""


def test_truncate_utf8_bytes_lida_com_vazio():
    assert truncate_utf8_bytes("   ", 20) == ""
