from fastapi import APIRouter, HTTPException
from typing import List

from app.schemas.frete_schema import FreteCreate, FreteResponse
from app.models.frete import Frete
from app.daos.freteDAO import FreteDAO
from app.config.banco import conectar

router = APIRouter()

## Post
@router.post("/frete/", status_code=201)
async def create_frete(frete: FreteCreate):
    
    conexao = conectar()
    dao = FreteDAO(conexao)

    frete_obj = Frete(
        nome = frete.nome,
        valor_100g = frete.valor_100g,
        valor_100g_plus = frete.valor_100g_plus
    )
    
    try:
        id_frete = dao.CreateFrete(frete_obj, frete.modalidades_ids)
        return {"Mensagem": "Frete criado com sucesso", "id_frete": id_frete}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

## Get
@router.get("/frete/", response_model=List[FreteResponse])
async def read_all_frete():
    conexao = conectar()
    dao = FreteDAO(conexao)
    freteEncontrado = dao.ReadAll()
    
    if not freteEncontrado:
        raise HTTPException(status_code=404, detail="Frete não encontrado")
    
    return freteEncontrado