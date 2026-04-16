from app.daos.freteDAO import FreteDAO
from app.models.frete import Frete


class FakeVar:
    def __init__(self, value):
        self._value = [value]

    def getvalue(self):
        return self._value


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []
        self.executed_many = []

    def var(self, _):
        return FakeVar(101)

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def executemany(self, sql, params_seq):
        self.executed_many.append((sql, list(params_seq)))

    def __iter__(self):
        return iter(self.rows)


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


def test_create_frete_persiste_servico_em_coluna_dedicada():
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    dao = FreteDAO(conn)

    frete = Frete(
        nome='Frete Azul',
        servico='acbuy',
        valor_100g=19.5,
        valor_100g_plus=6.2,
    )

    frete_id = dao.CreateFrete(frete, [1, 3])

    insert_sql, insert_params = cursor.executed[0]
    assert 'SERVICO_FRETE' in insert_sql
    assert "MODALIDADE" not in insert_sql
    assert "NOME_FRETE, SERVICO_FRETE, VALOR_100G, VALOR_100G_PLUS" in insert_sql
    assert insert_params[1] == 'acbuy'
    assert frete_id == 101
    assert conn.commit_calls == 1


def test_read_all_usa_servico_frete_no_select():
    cursor = FakeCursor(rows=[(1, 'Frete A', 'cssbuy', 10.0, 4.0, None, None)])
    conn = FakeConnection(cursor)
    dao = FreteDAO(conn)
    dao.GetModalidades = lambda _id_frete: ['Roupas']

    resultado = dao.ReadAll()

    select_sql, _ = cursor.executed[0]
    assert 'SERVICO_FRETE' in select_sql
    assert resultado[0].servico == 'cssbuy'
