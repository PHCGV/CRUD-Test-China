import math

class Produto:
    def __init__(self, nome, link_produto, link_imagem, valor, peso, data_atualizacao, id_modalidade, valor_convertido=None, valor_frete=None, id_produto=None):
        self.id_produto = id_produto
        self.nome = nome
        self.link_produto = link_produto
        self.link_imagem = link_imagem
        self.valor = valor #Valor em yuan
        self.id_modalidade = id_modalidade
        self.peso = peso 
        self.data_atualizacao = data_atualizacao
        self.valor_convertido = valor_convertido
        self.valor_frete = 0.0
        
    def calcular_valor(self, cotacao):
        if cotacao and cotacao > 0:
            self.valor_convertido = self.valor / cotacao #Valor em real
        else:
            self.valor_convertido = 0.0
        return self.valor_convertido

    def calcular_valor_frete(self, frete):
        peso_frete2 = self.peso - 100 #Reduzir das primeiras 100 gramas que são garantidas
        if peso_frete2 > 0:
            self.valor_frete = (frete.valor_100g_convertido + (frete.valor_100g_plus_convertido * (math.ceil(peso_frete2 / 100)))) #Adiciona o valor das primeiras 100 gramas e depois adiciona a quantidade restante
        else:
            self.valor_frete = frete.valor_100g_convertido
        return self.valor_frete
    