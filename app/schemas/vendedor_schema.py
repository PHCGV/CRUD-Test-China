from pydantic import AnyHttpUrl, BaseModel, Field


class VendedorBase(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    loja: str = Field(min_length=2, max_length=200)
    link_loja: str | None = None


class VendedorCreate(VendedorBase):
    link_loja: AnyHttpUrl | None = None


class VendedorUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    loja: str | None = Field(default=None, min_length=2, max_length=200)
    link_loja: AnyHttpUrl | None = None


class VendedorResponse(VendedorBase):
    id_vendedor: int

    class Config:
        from_attributes = True
