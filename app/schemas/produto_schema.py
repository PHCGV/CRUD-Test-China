from pydantic import AnyHttpUrl, BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

PRODUCT_IMAGE_PREFIX = "https://img.alicdn.com/bao/uploaded/"
PRODUCT_NAME_MAX_BYTES = 200

class ProdutoBase(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    link_imagem: Optional[str] = None
    link_produto: str
    valor: float = Field(gt=0, le=1_000_000)
    peso: int = Field(gt=0, le=200_000)
    id_modalidade: int = Field(gt=0)
    id_vendedor: Optional[int] = None

    @field_validator("nome")
    @classmethod
    def validate_nome_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > PRODUCT_NAME_MAX_BYTES:
            raise ValueError("nome deve ter no maximo 200 bytes em UTF-8")
        return value
    
class ProdutoCreate(ProdutoBase):
    link_imagem: Optional[AnyHttpUrl] = None
    link_produto: AnyHttpUrl
    id_vendedor: Optional[int] = Field(default=None, gt=0)

    @field_validator("link_imagem")
    @classmethod
    def validate_link_imagem_prefix(cls, value: Optional[AnyHttpUrl]) -> Optional[str]:
        if value is None:
            return None

        link = str(value).strip()
        if not link.startswith(PRODUCT_IMAGE_PREFIX):
            raise ValueError(f"link_imagem deve iniciar com {PRODUCT_IMAGE_PREFIX}")

        return link


class ProdutoUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=200)
    link_imagem: Optional[AnyHttpUrl] = None
    valor: Optional[float] = Field(default=None, gt=0, le=1_000_000)
    peso: Optional[int] = Field(default=None, gt=0, le=200_000)
    id_modalidade: Optional[int] = Field(default=None, gt=0)
    id_vendedor: Optional[int] = Field(default=None, gt=0)

    @field_validator("nome")
    @classmethod
    def validate_nome_bytes(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if len(value.encode("utf-8")) > PRODUCT_NAME_MAX_BYTES:
            raise ValueError("nome deve ter no maximo 200 bytes em UTF-8")
        return value

    @field_validator("link_imagem")
    @classmethod
    def validate_link_imagem_prefix(cls, value: Optional[AnyHttpUrl]) -> Optional[str]:
        if value is None:
            return None

        link = str(value).strip()
        if not link.startswith(PRODUCT_IMAGE_PREFIX):
            raise ValueError(f"link_imagem deve iniciar com {PRODUCT_IMAGE_PREFIX}")

        return link

class ProdutoResponse(ProdutoBase):
    id_produto: int
    data_atualizacao: Optional[datetime] = None
    
    valor_convertido: Optional[float] = None
    valor_frete: Optional[float] = None
    
    nome_modalidade: Optional[str] = None
    nome_vendedor: Optional[str] = None
    
    class Config:
        from_attributes = True