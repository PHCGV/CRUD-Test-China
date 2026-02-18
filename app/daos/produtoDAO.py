import oracledb
from app.models.produto import Produto

class ProdutoDAO:
    def __init__(self, conexao):
        self.conexao = conexao
        self.cursor = conexao.cursor()
        
    ## Create
    def Create(self, produto):
        try:
            id_novo = self.cursor.var(oracledb.NUMBER)
            sql = "INSERT INTO TB_PRODUTOS (NOME_PRODUTO, LINK_PRODUTO, LINK_IMAGEM, VALOR, PESO_GRAMAS, DATA_ATUALIZACAO, ID_MODALIDADE) VALUES (:1, :2, :3, :4, :5, :6, :7) RETURNING ID_PRODUTO INTO :8"
            
            dados = [
                produto.nome,
                produto.link_produto,
                produto.link_imagem,
                produto.valor,
                produto.peso,
                produto.data_atualizacao,
                produto.id_modalidade,
                id_novo
            ]
            self.cursor.execute(sql, dados)
            self.conexao.commit()
            return id_novo.getvalue()[0]
        except Exception as e:
            self.conexao.rollback()
            print(f"Erro ao adicionar produto: {e}")
            raise e
        
    ## Reads
    def ReadAll(self):
        sql = "SELECT ID_PRODUTO, NOME_PRODUTO, LINK_PRODUTO, LINK_IMAGEM, VALOR, PESO_GRAMAS, DATA_ATUALIZACAO, ID_MODALIDADE FROM TB_PRODUTOS"
        self.cursor.execute(sql)
        lista_produtos = []
        for linha in self.cursor:
            produto = Produto(
                id_produto = linha[0],
                nome = linha[1],
                link_produto = linha[2],
                link_imagem = linha[3],
                valor = linha[4],
                peso = linha[5],
                data_atualizacao = linha[6],
                id_modalidade = linha[7]
            )
            lista_produtos.append(produto)
        return lista_produtos
    
    def Read(self, id_produto):
        sql = "SELECT ID_PRODUTO, NOME_PRODUTO, LINK_PRODUTO, LINK_IMAGEM, VALOR, PESO_GRAMAS, DATA_ATUALIZACAO, ID_MODALIDADE FROM TB_PRODUTOS WHERE ID_PRODUTO = :1"
        self.cursor.execute(sql, [id_produto])
        linha = self.cursor.fetchone()
        if linha:
            produto = Produto(
                id_produto = linha[0],
                nome = linha[1],
                link_produto = linha[2],
                link_imagem = linha[3],
                valor = linha[4],
                peso = linha[5],
                data_atualizacao = linha[6],
                id_modalidade = linha[7]
            )
            return produto
        else:
            return None
    
    ## Updates
    def UpdateDate(self, id_produto):
        sql = "UPDATE TB_PRODUTOS SET DATA_ATUALIZACAO = SYSDATE WHERE ID_PRODUTO = :1"
        self.cursor.execute(sql, [id_produto])
        self.conexao.commit()
        
    def UpdateValue(self, id_produto, valor):
        sql = "UPDATE TB_PRODUTOS SET VALOR = :1 WHERE ID_PRODUTO = :2"
        self.cursor.execute(sql, [valor, id_produto])
        self.conexao.commit()
        self.UpdateDate(id_produto)

    def UpdateWeight(self, id_produto, peso):
        sql = "UPDATE TB_PRODUTOS SET PESO_GRAMAS = :1 WHERE ID_PRODUTO = :2"
        self.cursor.execute(sql,[peso, id_produto])
        self.conexao.commit()
        self.UpdateDate(id_produto)
    
    def UpdateLinkProduto(self, id_produto, link_novo):
        sql = "UPDATE TB_PRODUTOS SET LINK_PRODUTO = :1 WHERE ID_PRODUTO = :2"
        self.cursor.execute(sql,[link_novo, id_produto])
        self.conexao.commit()
        self.UpdateDate(id_produto)
    
    def UpdateLinkImagem(self, id_produto, link):
        sql = "UPDATE TB_PRODUTOS SET LINK_IMAGEM = :1 WHERE ID_PRODUTO = :2"  
        self.cursor.execute(sql,[link, id_produto])
        self.conexao.commit()
        self.UpdateDate(id_produto)
    
    def UpdateNome(self, id_produto, nome):
        sql = "UPDATE TB_PRODUTOS SET NOME_PRODUTO = :1 WHERE ID_PRODUTO = :2"
        self.cursor.execute(sql,[nome, id_produto])
        self.conexao.commit()
        self.UpdateDate(id_produto)
        
    ## Deletes
    
    def Delete(self, id_produto):
        sql = "DELETE FROM TB_PRODUTOS WHERE ID_PRODUTO = :1"
        self.cursor.execute(sql, [id_produto])
        self.conexao.commit()

        