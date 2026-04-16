from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging

from app.config.banco import conectar
from app.config.security import get_current_user
from app.daos.produtoDAO import ProdutoDAO
from app.daos.vendedorDAO import VendedorDAO
from app.models.usuario import Usuario
from app.models.vendedor import Vendedor
from app.schemas.vendedor_schema import VendedorCreate, VendedorResponse, VendedorUpdate

router = APIRouter(prefix="/vendedor", tags=["Vendedor"])
logger = logging.getLogger(__name__)
INTERNAL_ERROR_DETAIL = "Falha interna do servidor"


@router.post("/", response_model=VendedorResponse, status_code=status.HTTP_201_CREATED)
def create_vendedor(
    vendedor: VendedorCreate,
    usuario_atual: Usuario = Depends(get_current_user),
) -> VendedorResponse:
    """Cria vendedor para o usuário autenticado.

    Args:
        vendedor: Dados do vendedor.
        usuario_atual: Usuário autenticado.

    Raises:
        HTTPException: Em caso de falha de conexão ou persistência.

    Returns:
        VendedorResponse: Vendedor criado.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = VendedorDAO(conexao)
        link_loja = str(vendedor.link_loja) if vendedor.link_loja is not None else None

        vendedor_obj = Vendedor(
            nome=vendedor.nome,
            loja=vendedor.loja,
            link_loja=link_loja,
            id_usuario_criador=usuario_atual.id_usuario,
        )

        try:
            id_gerado = dao.Create(vendedor_obj)
            criado = dao.Read(id_gerado, usuario_atual.id_usuario)
            if criado is None:
                raise HTTPException(status_code=500, detail="Falha ao recuperar vendedor criado")
            return criado
        except HTTPException:
            raise
        except Exception:
            logger.exception("Erro ao criar vendedor")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()


@router.get("/", response_model=List[VendedorResponse])
def read_all_vendedor(
    usuario_atual: Usuario = Depends(get_current_user),
) -> list[VendedorResponse]:
    """Lista vendedores do usuário autenticado.

    Args:
        usuario_atual: Usuário autenticado.

    Raises:
        HTTPException: Em caso de falha na conexão.

    Returns:
        list[VendedorResponse]: Lista de vendedores do usuário.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = VendedorDAO(conexao)
        return dao.ReadAll(usuario_atual.id_usuario)
    finally:
        conexao.close()


@router.get("/{id_vendedor}", response_model=VendedorResponse)
def read_vendedor(
    id_vendedor: int,
    usuario_atual: Usuario = Depends(get_current_user),
) -> VendedorResponse:
    """Obtém vendedor específico do usuário autenticado.

    Args:
        id_vendedor: ID do vendedor.
        usuario_atual: Usuário autenticado.

    Raises:
        HTTPException: Em caso de conexão inválida ou vendedor inexistente.

    Returns:
        VendedorResponse: Vendedor encontrado.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = VendedorDAO(conexao)
        vendedor = dao.Read(id_vendedor, usuario_atual.id_usuario)
        if not vendedor:
            raise HTTPException(status_code=404, detail="Vendedor nao encontrado")
        return vendedor
    finally:
        conexao.close()


@router.put("/{id_vendedor}", response_model=VendedorResponse)
def update_vendedor(
    id_vendedor: int,
    dados: VendedorUpdate,
    usuario_atual: Usuario = Depends(get_current_user),
) -> VendedorResponse:
    """Atualiza vendedor do usuário autenticado.

    Args:
        id_vendedor: ID do vendedor.
        dados: Dados parciais de atualização.
        usuario_atual: Usuário autenticado.

    Raises:
        HTTPException: Em caso de conexão inválida, não encontrado ou erro de banco.

    Returns:
        VendedorResponse: Vendedor atualizado.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = VendedorDAO(conexao)
        vendedor = dao.Read(id_vendedor, usuario_atual.id_usuario)
        if not vendedor:
            raise HTTPException(status_code=404, detail="Vendedor nao encontrado")

        nome = dados.nome if dados.nome is not None else vendedor.nome
        loja = dados.loja if dados.loja is not None else vendedor.loja
        # Regra de negocio: link da loja nao deve ser editado.
        link_loja = vendedor.link_loja

        try:
            dao.Update(id_vendedor, usuario_atual.id_usuario, nome, loja, link_loja)
            atualizado = dao.Read(id_vendedor, usuario_atual.id_usuario)
            if atualizado is None:
                raise HTTPException(status_code=500, detail="Falha ao recuperar vendedor atualizado")
            return atualizado
        except HTTPException:
            raise
        except Exception:
            logger.exception("Erro ao atualizar vendedor")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()


@router.delete("/{id_vendedor}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vendedor(
    id_vendedor: int,
    usuario_atual: Usuario = Depends(get_current_user),
) -> None:
    """Exclui vendedor do usuário autenticado.

    Args:
        id_vendedor: ID do vendedor.
        usuario_atual: Usuário autenticado.

    Raises:
        HTTPException: Em caso de conexão inválida, não encontrado ou integridade referencial.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = VendedorDAO(conexao)
        vendedor = dao.Read(id_vendedor, usuario_atual.id_usuario)
        if not vendedor:
            raise HTTPException(status_code=404, detail="Vendedor nao encontrado")

        try:
            dao_produto = ProdutoDAO(conexao)
            dao_produto.ClearVendorLink(id_vendedor, usuario_atual.id_usuario)
            dao.Delete(id_vendedor, usuario_atual.id_usuario)
        except Exception:
            logger.exception("Erro ao excluir vendedor")
            raise HTTPException(
                status_code=400,
                detail="Nao foi possivel excluir o vendedor. Verifique se existem produtos vinculados.",
            )
    finally:
        conexao.close()
