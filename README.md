# Produtos e fretes importados - Python, FastAPI e Oracle

Aplicação pessoal de estudo para organizar produtos, vendedores e fretes, registrando valores em CNY e conversões para BRL com cotação configurável.

O projeto está em evolução. O **frontend React/Vite já está implementado** em `frontend/`; a descrição antiga de que seria construído no futuro estava desatualizada.

## Estrutura e tecnologias

- Backend Python/FastAPI: rotas, schemas de entrada, modelos e DAOs em `app/`.
- Persistência Oracle: schema em `China CRUD.sql` e suporte de desenvolvimento em `docker/oracle/`.
- Frontend React/Vite em `frontend/`.
- Extensão Chrome em `extension/`, com integração de sessão descrita no README do frontend.
- Docker Compose para o ambiente local; documentação operacional em [`deploy/README.md`](deploy/README.md).
- Testes de backend em `tests/backend/` e de componente em `frontend/tests/`.

## Executar localmente

Configure um arquivo `.env.docker` local conforme as variáveis exigidas pelo Compose, sem versionar credenciais. Depois:

```sh
docker compose --env-file .env.docker up -d --build
```

Endereços documentados para a stack local: frontend `http://localhost:5173`, backend `http://localhost:8050`, Oracle `localhost:1522/XEPDB1`.

Para executar a API fora do container, configure as dependências e o acesso ao Oracle e use `uvicorn main:app`. Consulte os [detalhes de ambiente e deploy](deploy/README.md).

## O que explorar no código

Separação entre validação de entrada, rotas e acesso ao banco; associação de produtos, fretes e vendedores; cálculos de importação e persistência. Os testes existentes incluem validações de schemas, cálculos, acesso SQL e segurança de entrada.

## Estado da verificação

Esta atualização do README foi conferida contra a estrutura do repositório. Não representa nova execução da aplicação, dos testes ou de um deploy. O sistema continua sendo um projeto de estudo em evolução.

## Imagens

![Interface do projeto](https://github.com/user-attachments/assets/8958b1d6-21c7-4f06-8637-87ec34d043c5)
![Tela de produtos e fretes](https://github.com/user-attachments/assets/2f857d19-7066-4ce7-ac87-9043c26b5fed)
![Exemplo da aplicação](https://github.com/user-attachments/assets/cd5e452d-9f6d-42de-9265-8f90a8d5a5bc)

[Portfólio](https://phcgv.vercel.app/) · [LinkedIn](https://www.linkedin.com/in/phcgv/)
