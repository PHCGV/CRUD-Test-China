import oracledb
import os
from dotenv import load_dotenv

load_dotenv()

def conectar():
    try:
        conexao = oracledb.connect(
            user=os.getenv("ORACLE_USER"),
            password=os.getenv("ORACLE_PASSWORD"),
            dsn=os.getenv("ORACLE_DSN")
        )
        print("Conexão estabelecida com sucesso!")
        return conexao
    except oracledb.DatabaseError as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None