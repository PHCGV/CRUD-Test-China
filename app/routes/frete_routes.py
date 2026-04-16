from typing import Any
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.config.security import get_current_user, require_admin
from app.schemas.frete_schema import FreteCreate, FreteResponse, ModalidadeResponse
from app.models.frete import Frete
from app.models.usuario import Usuario
from app.daos.freteDAO import FreteDAO
from app.config.banco import conectar

router = APIRouter()
logger = logging.getLogger(__name__)
INTERNAL_ERROR_DETAIL = "Falha interna do servidor"


@router.post("/frete/", status_code=201)
async def create_frete(
    frete: FreteCreate,
    usuario_atual: Usuario = Depends(require_admin),
) -> dict[str, Any]:
    """Cria um novo método de frete.

    Args:
        frete: Payload de criação do frete.
        usuario_atual: Usuário autenticado.

    Raises:
        HTTPException: Em caso de falha de conexão ou persistência.

    Returns:
        dict[str, Any]: Mensagem de sucesso com ID gerado.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = FreteDAO(conexao)

        frete_obj = Frete(
            nome=frete.nome,
            servico=frete.servico,
            valor_100g=frete.valor_100g,
            valor_100g_plus=frete.valor_100g_plus,
        )

        try:
            id_frete = dao.CreateFrete(frete_obj, frete.modalidades_ids)
            return {"Mensagem": "Frete criado com sucesso", "id_frete": id_frete}
        except Exception:
            logger.exception("Erro ao criar frete")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()


@router.get("/frete/", response_model=List[FreteResponse])
async def read_all_frete(usuario_atual: Usuario = Depends(get_current_user)) -> list[FreteResponse]:
    """Lista fretes cadastrados.

    Args:
        usuario_atual: Usuário autenticado.

    Raises:
        HTTPException: Em caso de conexão inválida ou lista vazia.

    Returns:
        list[FreteResponse]: Lista de fretes disponíveis.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = FreteDAO(conexao)
        fretes_encontrados = dao.ReadAll()

        if not fretes_encontrados:
            raise HTTPException(status_code=404, detail="Frete nao encontrado")

        return fretes_encontrados
    finally:
        conexao.close()


@router.get("/modalidade/", response_model=list[ModalidadeResponse])
async def read_all_modalidades(usuario_atual: Usuario = Depends(get_current_user)) -> list[ModalidadeResponse]:
    """Lista modalidades de frete disponiveis para selecao de produtos."""
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = FreteDAO(conexao)

        try:
            modalidades = dao.ReadAllModalidades()
            return [
                ModalidadeResponse(id_modalidade=id_modalidade, nome_modalidade=nome_modalidade)
                for id_modalidade, nome_modalidade in modalidades
            ]
        except Exception:
            logger.exception("Erro ao listar modalidades")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()