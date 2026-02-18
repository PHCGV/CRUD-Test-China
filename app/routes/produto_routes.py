from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.models.produto import Produto
from app.schemas.produto_schema import ProdutoCreate,ProdutoResponse
from app.daos.produtoDAO import ProdutoDAO
from app.daos.freteDAO import FreteDAO
from app.config.banco import conectar

router = APIRouter()

@router.post("/produto/", status_code=201)
def create_produto(produto: ProdutoCreate):
    conexao = conectar()
    dao = ProdutoDAO(conexao)
    
    produto_obj = Produto(
        nome=produto.nome,
        link_produto=produto.link_produto,
        link_imagem=produto.link_imagem,
        valor=produto.valor,
        peso=produto.peso,
        id_modalidade=produto.id_modalidade,
        data_atualizacao=None
    )
    
    try:
        id_gerado = dao.Create(produto_obj)
        return {"Mensagem": "Produto adicionado com sucesso", "id_produto": id_gerado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/produto/", response_model=List[ProdutoResponse])
def read_all_produto(cotacao: Optional[float] = Query(None, description="Valor do Yuan em Reais para conversão")):
    conexao = conectar()
    dao = ProdutoDAO(conexao)
    
    try:
        lista_produtos = dao.ReadAll()
        if cotacao is not None and cotacao > 0:
            for Produto in lista_produtos:
                Produto.calcular_valor(cotacao)
        return lista_produtos
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Produto não encontrado")

@router.get("simularcusto/{id_produto}")
def simular_custo_produto(id_produto: int):
    id_produto: int
    cotacao: float = Query(..., description="Valor do Yuan para conversão")
    conexao = conectar()
    
    try:
        daoProduto = ProdutoDAO(conexao)
        produtoEncontrado = daoProduto.Read(id_produto)
        
        if not produtoEncontrado:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        produtoEncontrado.calcular_valor(cotacao)
        
        daoFrete = FreteDAO(conexao)
        fretesDisponiveis = daoFrete.ReadModalidade(produtoEncontrado.id_modalidade)
        
        if not fretesDisponiveis:
            raise HTTPException(status_code=404, detail="Frete não encontrado")
        
        disponiveis = []
        for frete in fretesDisponiveis:
            frete.calcular_valor_convertido(cotacao)
            custo_envio = produtoEncontrado.calcular_valor_frete(frete)
            disponiveis.append({ 
                                "Metodo de envio: ": frete.nome, 
                                "Valor em Reais: ": round(custo_envio,2),
                                "Detalhes: ": {
                                    "Valor base: ": round(frete.valor_100g_convertido,2),
                                    "Valor adicional: ": round(frete.valor_100g_plus_convertido,2)
                                }
                                })
        
        return { "produto": produtoEncontrado.nome, "valor_produto": round(produtoEncontrado.valor_convertido,2),
                "peso_produto": produtoEncontrado.peso, "opcoes_envio": disponiveis
                }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
   