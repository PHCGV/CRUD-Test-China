from app.models.frete import Frete


def test_frete_calcula_valor_convertido():
    frete = Frete(
        nome='Frete Premium',
        servico='cssbuy',
        valor_100g=30.0,
        valor_100g_plus=12.0,
    )

    base, adicional = frete.calcular_valor_convertido(2.0)

    assert base == 15.0
    assert adicional == 6.0


def test_frete_servico_padrao_quando_vazio():
    frete = Frete(
        nome='Frete Economico',
        servico=' ',
        valor_100g=10.0,
        valor_100g_plus=5.0,
    )

    assert frete.servico == 'Nao informado'
