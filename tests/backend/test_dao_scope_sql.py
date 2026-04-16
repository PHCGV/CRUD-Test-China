from app.daos.produtoDAO import ProdutoDAO
from app.daos.usuarioDAO import UsuarioDAO
from app.daos.vendedorDAO import VendedorDAO


class FakeVar:
    def __init__(self, value):
        self._value = [value]

    def getvalue(self):
        return self._value


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.executed_many = []
        self.rowcount = 1

    def var(self, _):
        return FakeVar(100)

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def executemany(self, sql, params_seq):
        self.executed_many.append((sql, list(params_seq)))


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commit_calls = 0
        self.rollback_calls = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commit_calls += 1

    def rollback(self):
        self.rollback_calls += 1


def test_produto_update_restringe_update_ao_dono_do_registro():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    dao = ProdutoDAO(conn)

    dao.Update(
        id_produto=55,
        id_usuario_criador=9,
        nome="Produto A",
        link_imagem="https://img.alicdn.com/bao/uploaded/a.jpg",
        valor=100.0,
        peso=350,
        id_modalidade=1,
        id_vendedor=4,
    )

    sql, params = cursor.executed[0]
    assert "WHERE ID_PRODUTO = :7 AND ID_USUARIO_CRIADOR = :8" in sql
    assert params[7] == 9


def test_produto_delete_restringe_delete_ao_dono_do_registro():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    dao = ProdutoDAO(conn)

    dao.Delete(55, 9)

    sql, params = cursor.executed[0]
    assert "WHERE ID_PRODUTO = :1 AND ID_USUARIO_CRIADOR = :2" in sql
    assert params == [55, 9]


def test_produto_clear_vendor_link_restringe_escopo_por_usuario():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    dao = ProdutoDAO(conn)

    dao.ClearVendorLink(77, 9)

    sql, params = cursor.executed[0]
    assert "WHERE ID_VENDEDOR = :1 AND ID_USUARIO_CRIADOR = :2" in sql
    assert params == [77, 9]


def test_vendedor_update_restringe_update_ao_dono_do_registro():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    dao = VendedorDAO(conn)

    dao.Update(11, 9, "Nome", "Loja", "https://example.com")

    sql, params = cursor.executed[0]
    assert "WHERE ID_VENDEDOR = :4 AND ID_USUARIO_CRIADOR = :5" in sql
    assert params == ["Nome", "Loja", "https://example.com", 11, 9]


def test_vendedor_delete_restringe_delete_ao_dono_do_registro():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    dao = VendedorDAO(conn)

    dao.Delete(11, 9)

    sql, params = cursor.executed[0]
    assert "WHERE ID_VENDEDOR = :1 AND ID_USUARIO_CRIADOR = :2" in sql
    assert params == [11, 9]


def test_usuario_update_password_controla_incremento_token_version():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    dao = UsuarioDAO(conn)

    dao.UpdatePassword(7, "hash-a", increment_token_version=False)
    sql_a, params_a = cursor.executed[0]
    assert "TOKEN_VERSION = TOKEN_VERSION + :2" in sql_a
    assert params_a == ["hash-a", 0, 7]

    dao.UpdatePassword(7, "hash-b", increment_token_version=True)
    sql_b, params_b = cursor.executed[1]
    assert "TOKEN_VERSION = TOKEN_VERSION + :2" in sql_b
    assert params_b == ["hash-b", 1, 7]


def test_usuario_delete_remove_tokens_reset_antes_de_apagar_usuario():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    dao = UsuarioDAO(conn)

    dao.Delete(22)

    assert len(cursor.executed) == 2
    sql_1, params_1 = cursor.executed[0]
    sql_2, params_2 = cursor.executed[1]
    assert "DELETE FROM TB_PASSWORD_RESET" in sql_1
    assert params_1 == [22]
    assert "DELETE FROM TB_USUARIOS" in sql_2
    assert params_2 == [22]
