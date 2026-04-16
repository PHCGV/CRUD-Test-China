from pydantic import BaseModel, Field
from typing import Optional, List

class FreteBase(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    servico: str = Field(min_length=2, max_length=120)
    valor_100g: float
    valor_100g_plus: float
    
class FreteCreate(FreteBase):
    modalidades_ids: List[int]
    
class FreteResponse(FreteBase):
    id_frete: int
    
    modalidades: List[str] = []
    valor_100g_convertido: Optional[float] = None
    valor_100g_plus_convertido: Optional[float] = None
    
    class Config:
        from_attributes = True


class ModalidadeResponse(BaseModel):
    id_modalidade: int
    nome_modalidade: str
    