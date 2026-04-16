from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
import logging

from app.config.security import get_current_user
from app.daos.vendedorDAO import VendedorDAO
from app.models.produto import Produto
from app.models.usuario import Usuario
from app.schemas.produto_schema import ProdutoCreate, ProdutoResponse, ProdutoUpdate
from app.daos.produtoDAO import ProdutoDAO
from app.daos.freteDAO import FreteDAO
from app.config.banco import conectar

router = APIRouter()
logger = logging.getLogger(__name__)
INTERNAL_ERROR_DETAIL = "Falha interna do servidor"


def truncate_utf8_bytes(value: str, max_bytes: int) -> str:
    """Trunca texto para um limite de bytes UTF-8 sem quebrar caracteres.

    Args:
        value: Texto de entrada a ser truncado.
        max_bytes: Quantidade máxima de bytes permitida na saída.

    Returns:
        str: Texto truncado dentro do limite de bytes informado.
    """
    text = str(value or "").strip()
    if not text:
        return text

    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text

    cut = encoded[:max_bytes]
    while cut:
        try:
            return cut.decode("utf-8").rstrip()
        except UnicodeDecodeError:
            cut = cut[:-1]
    return ""


@router.post("/produto/", status_code=201)
def create_produto(
    produto: ProdutoCreate,
    usuario_atual: Usuario = Depends(get_current_user),
) -> dict[str, int | str]:
    """Cria um produto para o usuário autenticado.

    Args:
        produto: Dados do produto.
        usuario_atual: Usuário autenticado.

    Raises:
        HTTPException: Em caso de conexão inválida, vendedor inválido ou erro de banco.

    Returns:
        dict[str, int | str]: Mensagem de sucesso e ID criado.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = ProdutoDAO(conexao)

        if produto.id_vendedor is not None:
            dao_vendedor = VendedorDAO(conexao)
            vendedor = dao_vendedor.Read(produto.id_vendedor, usuario_atual.id_usuario)
            if not vendedor:
                raise HTTPException(status_code=400, detail="Vendedor invalido para este usuario")

        link_produto = str(produto.link_produto)
        link_imagem = str(produto.link_imagem) if produto.link_imagem is not None else None

        produto_obj = Produto(
            nome=truncate_utf8_bytes(produto.nome, 200),
            link_produto=link_produto,
            link_imagem=link_imagem,
            valor=produto.valor,
            peso=produto.peso,
            id_modalidade=produto.id_modalidade,
            id_vendedor=produto.id_vendedor,
            id_usuario_criador=usuario_atual.id_usuario,
            data_atualizacao=None,
        )

        try:
            id_gerado = dao.Create(produto_obj)
            return {"Mensagem": "Produto adicionado com sucesso", "id_produto": id_gerado}
        except Exception:
            logger.exception("Erro ao criar produto")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()


@router.get("/produto/", response_model=List[ProdutoResponse])
def read_all_produto(
    cotacao: Optional[float] = Query(None, description="Valor do Yuan em Reais para conversao"),
    usuario_atual: Usuario = Depends(get_current_user),
) -> list[ProdutoResponse]:
    """Lista produtos do usuário autenticado com opção de conversão cambial.

    Args:
        cotacao: Cotação do yuan para conversão.
        usuario_atual: Usuário autenticado.

    Raises:
        HTTPException: Em caso de falha na conexão ou leitura.

    Returns:
        list[ProdutoResponse]: Lista de produtos do usuário.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = ProdutoDAO(conexao)

        try:
            lista_produtos = dao.ReadAll(usuario_atual.id_usuario)
            if cotacao is not None and cotacao > 0:
                for produto in lista_produtos:
                    produto.calcular_valor(cotacao)
            return lista_produtos

        except Exception:
            logger.exception("Erro ao listar produtos")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()


@router.get("/simularcusto/{id_produto}")
def simular_custo_produto(
    id_produto: int,
    cotacao: float = Query(..., description="Valor do Yuan para conversao"),
    usuario_atual: Usuario = Depends(get_current_user),
) -> dict[str, object]:
    """Simula custo total do produto com opções de frete.

    Args:
        id_produto: Identificador do produto.
        cotacao: Cotação para conversão de moeda.
        usuario_atual: Usuário autenticado.

    Raises:
        HTTPException: Em caso de validação ou falha de processamento.

    Returns:
        dict[str, object]: Dados do produto e opções de envio simuladas.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao_produto = ProdutoDAO(conexao)
        produto_encontrado = dao_produto.Read(id_produto, usuario_atual.id_usuario)

        if not produto_encontrado:
            raise HTTPException(status_code=404, detail="Produto nao encontrado")

        produto_encontrado.calcular_valor(cotacao)

        dao_frete = FreteDAO(conexao)
        fretes_disponiveis = dao_frete.ReadModalidade(produto_encontrado.id_modalidade)

        if not fretes_disponiveis:
            raise HTTPException(status_code=404, detail="Frete nao encontrado")

        disponiveis: list[dict[str, object]] = []
        for frete in fretes_disponiveis:
            frete.calcular_valor_convertido(cotacao)
            custo_envio = produto_encontrado.calcular_valor_frete(frete)
            servico = str(getattr(frete, "servico", "") or "").strip()
            metodo_envio = frete.nome if not servico else f"{frete.nome} - {servico}"
            disponiveis.append(
                {
                    "Metodo de envio": metodo_envio,
                    "Servico": servico or "Nao informado",
                    "Valor em Reais": round(custo_envio, 2),
                    "Detalhes": {
                        "Valor base": round(frete.valor_100g_convertido, 2),
                        "Valor adicional": round(frete.valor_100g_plus_convertido, 2),
                    },
                }
            )

        return {
            "produto": produto_encontrado.nome,
            "valor_produto": round(produto_encontrado.valor_convertido, 2),
            "peso_produto": produto_encontrado.peso,
            "opcoes_envio": disponiveis,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Erro ao simular custo do produto")
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()


@router.put("/produto/{id_produto}", response_model=ProdutoResponse)
def update_produto(
    id_produto: int,
    dados: ProdutoUpdate,
    usuario_atual: Usuario = Depends(get_current_user),
) -> ProdutoResponse:
    """Atualiza produto do usuário autenticado.

    Args:
        id_produto: ID do produto.
        dados: Dados parciais para atualização.
        usuario_atual: Usuário autenticado.

    Raises:
        HTTPException: Em caso de conexão inválida, não encontrado, validação ou erro de banco.

    Returns:
        ProdutoResponse: Produto atualizado.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = ProdutoDAO(conexao)
        produto = dao.Read(id_produto, usuario_atual.id_usuario)
        if not produto:
            raise HTTPException(status_code=404, detail="Produto nao encontrado")

        dados_update = dados.model_dump(exclude_unset=True)

        nome = truncate_utf8_bytes(dados_update.get("nome", produto.nome), 200)
        link_imagem = dados_update["link_imagem"] if "link_imagem" in dados_update else produto.link_imagem
        valor = dados_update.get("valor", produto.valor)
        peso = dados_update.get("peso", produto.peso)
        id_modalidade = dados_update.get("id_modalidade", produto.id_modalidade)
        id_vendedor = dados_update["id_vendedor"] if "id_vendedor" in dados_update else produto.id_vendedor

        if id_vendedor is not None:
            dao_vendedor = VendedorDAO(conexao)
            vendedor = dao_vendedor.Read(id_vendedor, usuario_atual.id_usuario)
            if not vendedor:
                raise HTTPException(status_code=400, detail="Vendedor invalido para este usuario")

        try:
            dao.Update(
                id_produto=id_produto,
                id_usuario_criador=usuario_atual.id_usuario,
                nome=nome,
                link_imagem=str(link_imagem) if link_imagem is not None else None,
                valor=valor,
                peso=peso,
                id_modalidade=id_modalidade,
                id_vendedor=id_vendedor,
            )
            atualizado = dao.Read(id_produto, usuario_atual.id_usuario)
            if atualizado is None:
                raise HTTPException(status_code=500, detail="Falha ao recuperar produto atualizado")
            return atualizado
        except HTTPException:
            raise
        except Exception:
            logger.exception("Erro ao atualizar produto")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()


@router.delete("/produto/{id_produto}", status_code=204)
def delete_produto(
    id_produto: int,
    usuario_atual: Usuario = Depends(get_current_user),
) -> None:
    """Exclui produto do usuário autenticado.

    Args:
        id_produto: ID do produto.
        usuario_atual: Usuário autenticado.

    Raises:
        HTTPException: Em caso de conexão inválida, não encontrado ou erro de banco.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = ProdutoDAO(conexao)
        produto = dao.Read(id_produto, usuario_atual.id_usuario)
        if not produto:
            raise HTTPException(status_code=404, detail="Produto nao encontrado")

        try:
            dao.Delete(id_produto, usuario_atual.id_usuario)
        except Exception:
            logger.exception("Erro ao excluir produto")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()
