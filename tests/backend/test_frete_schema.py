import pytest
from pydantic import ValidationError

from app.schemas.frete_schema import FreteCreate


def test_frete_schema_valida_payload_completo():
    payload = FreteCreate(
        nome='Frete Express',
        servico='hoobuy',
        valor_100g=25.0,
        valor_100g_plus=8.5,
        modalidades_ids=[1, 2],
    )

    assert payload.servico == 'hoobuy'
    assert payload.modalidades_ids == [1, 2]


def test_frete_schema_exige_servico():
    with pytest.raises(ValidationError):
        FreteCreate(
            nome='Frete sem servico',
            valor_100g=20.0,
            valor_100g_plus=7.0,
            modalidades_ids=[1],
        )
