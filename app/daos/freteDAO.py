import oracledb
from app.models.frete import Frete

class FreteDAO:
    def __init__(self, conexao):
        self.conexao = conexao
        self.cursor = conexao.cursor()
        
    ## Create
    def CreateFrete(self, frete: Frete, lista_modalidades: list):
        try:
            id_novo = self.cursor.var(oracledb.NUMBER)
            sql = "INSERT INTO TB_FRETE (NOME_FRETE, MODALIDADE, VALOR_100G, VALOR_100G_PLUS) VALUES (:1, 'Geral', :2, :3) RETURNING ID_FRETE INTO :4"
            
            self.cursor.execute(sql, [
                frete.nome,
                frete.valor_100g,
                frete.valor_100g_plus,
                id_novo
            ])
            id_gerado = id_novo.getvalue()[0]
            
            if lista_modalidades:
                sqlP = "INSERT INTO TB_FRETE_MODALIDADE (ID_FRETE, ID_MODALIDADE) VALUES (:1, :2)"

                dadosP = [(id_gerado, id_modalidade) for id_modalidade in lista_modalidades]
                self.cursor.executemany(sqlP, dadosP)
            
            self.conexao.commit()
            return id_gerado
    
        except Exception as e:
            self.conexao.rollback()
            print(f"Erro ao criar frete: {e}")
            raise e
        
    def ReadAll(self):
        sql = "SELECT ID_FRETE, NOME_FRETE, MODALIDADE, VALOR_100G, VALOR_100G_PLUS, VALOR_100G_CONVERTIDO, VALOR_100G_PLUS_CONVERTIDO FROM TB_FRETE"
        self.cursor.execute(sql)
        lista_frete = []
        for linha in self.cursor:
            frete = Frete(
                id_frete = linha[0],
                nome = linha[1],
                valor_100g = linha[3],
                valor_100g_plus = linha[4]
            )
            if linha[5]:
                frete.valor_100g_convertido = linha[5]
                frete.valor_100g_plus_convertido = linha[6]
            frete.modalidades = self.GetModalidades(frete.id_frete)
            lista_frete.append(frete)
        return lista_frete
    
    def ReadModalidade(self, id_modalidade_produto: int):
        sql = """
        SELECT F.ID_FRETE, F.NOME_FRETE, F.MODALIDADE, F.VALOR_100G, F.VALOR_100G_PLUS
        FROM TB_FRETE F
        JOIN TB_FRETE_MODALIDADE FM ON F.ID_FRETE = FM.ID_FRETE
        WHERE FM.ID_MODALIDADE = :1
        """
        self.cursor.execute(sql, [id_modalidade_produto])
        
        lista_resultado = []
        for linha in self.cursor:
            frete = Frete(
                id_frete = linha[0],
                nome = linha[1],
                valor_100g = linha[3],
                valor_100g_plus = linha[4]
            )
            lista_resultado.append(frete)
        return lista_resultado
    
    def GetModalidades(self, id_frete):
        sql = """
            SELECT M.NOME_MODALIDADE 
            FROM TB_MODALIDADE M
            JOIN TB_FRETE_MODALIDADE FM ON M.ID_MODALIDADE = FM.ID_MODALIDADE
            WHERE FM.ID_FRETE = :1
        """
        cursor_aux = self.conexao.cursor()
        cursor_aux.execute(sql, [id_frete])
        return [row[0] for row in cursor_aux]
    