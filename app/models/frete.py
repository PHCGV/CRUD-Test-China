class Frete:
    def __init__(self, nome, valor_100g, valor_100g_plus, id_frete=None, valor_100g_convertido=None, valor_100g_plus_convertido=None, modalidades: list = None):
        self.id_frete = id_frete
        self.nome = nome
        self.valor_100g = valor_100g
        self.valor_100g_plus = valor_100g_plus
        
        self.valor_100g_convertido = None
        self.valor_100g_plus_convertido = None
        self.modalidades = modalidades or []

    def calcular_valor_convertido(self, cotacao):
        self.valor_100g_convertido = self.valor_100g / cotacao
        self.valor_100g_plus_convertido = self.valor_100g_plus / cotacao
        return self.valor_100g_convertido, self.valor_100g_plus_convertido
    