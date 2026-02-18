from pydantic import BaseModel
from typing import Optional, List

class FreteBase(BaseModel):
    nome: str
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
    