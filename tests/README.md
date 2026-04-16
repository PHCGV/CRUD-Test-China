# Testes

## Estrutura

- `tests/backend`: testes de backend com `pytest`
- `frontend/tests`: testes de frontend com `Vitest + React Testing Library`
- `scripts/scan-tests.ps1`: executa backend e frontend em sequencia e imprime um resumo PASS/FAIL por etapa

### Cobertura backend atual (foco em risco)

- Frete: modelo, schema e SQL do DAO
- Produto: validacoes de schema e utilitario de truncamento UTF-8
- Usuario/Seguranca: token JWT, rate limit de login, regras de autorizacao e schemas de auth
- Escopo SQL por usuario: ProdutoDAO, VendedorDAO e UsuarioDAO

## Como rodar:

### 1) Backend (pytest)

```powershell
pytest -q
```

### 2) Frontend (Vitest)

```powershell
Set-Location frontend
npm run test
```

### 3) Scan unificado

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\scan-tests.ps1
```
