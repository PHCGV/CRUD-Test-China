import pytest
from pydantic import ValidationError

from app.schemas.produto_schema import PRODUCT_IMAGE_PREFIX, ProdutoCreate, ProdutoUpdate


def test_produto_create_valido_com_link_imagem_prefixado():
    payload = ProdutoCreate(
        nome="Produto Premium",
        link_produto="https://example.com/produto/123",
        link_imagem=f"{PRODUCT_IMAGE_PREFIX}imagem.jpg",
        valor=120.5,
        peso=350,
        id_modalidade=2,
        id_vendedor=10,
    )

    assert str(payload.link_produto).startswith("https://")
    assert payload.id_vendedor == 10


def test_produto_create_rejeita_nome_maior_que_200_bytes_utf8():
    nome_longo = "\u6c49" * 67  # 201 bytes

    with pytest.raises(ValidationError):
        ProdutoCreate(
            nome=nome_longo,
            link_produto="https://example.com/produto/123",
            link_imagem=f"{PRODUCT_IMAGE_PREFIX}imagem.jpg",
            valor=120.5,
            peso=350,
            id_modalidade=2,
        )


def test_produto_create_rejeita_link_imagem_fora_prefixo():
    with pytest.raises(ValidationError):
        ProdutoCreate(
            nome="Produto Premium",
            link_produto="https://example.com/produto/123",
            link_imagem="https://cdn.outra-origem.com/imagem.jpg",
            valor=120.5,
            peso=350,
            id_modalidade=2,
        )


def test_produto_update_aceita_link_imagem_none():
    payload = ProdutoUpdate(link_imagem=None, valor=10.0)
    assert payload.link_imagem is None


def test_produto_update_rejeita_link_imagem_fora_prefixo():
    with pytest.raises(ValidationError):
        ProdutoUpdate(link_imagem="https://example.com/imagem.jpg")
