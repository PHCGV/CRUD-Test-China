from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProdutoBase(BaseModel):
    nome: str
    link_imagem: Optional[str] = None
    link_produto: str
    valor: float
    peso: int
    id_modalidade: int
    
class ProdutoCreate(ProdutoBase):
    pass

class ProdutoResponse(ProdutoBase):
    id_produto: int
    data_atualizacao: Optional[datetime] = None
    
    valor_convertido: Optional[float] = None
    valor_frete: Optional[float] = None
    
    nome_modalidade: Optional[str] = None
    
    class Config:
        from_attributes = True