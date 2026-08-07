# Último vendedor acessado — Design

## Objetivo

Destacar na tela de vendedores aquele cuja loja foi aberta mais recentemente pelo usuário no navegador atual, sem alterações na API ou no banco de dados.

## Experiência

Cada card de vendedor continua exibindo nome, loja e ações. Depois que o usuário selecionar **Abrir**, o nome do respectivo vendedor recebe uma etiqueta discreta **Último acessado**. Ao abrir outro vendedor, a etiqueta é transferida imediatamente. A marcação permanece após recarregar a página ou encerrar e reabrir o navegador.

## Dados e isolamento

O frontend mantém o `id_vendedor` em `localStorage`. A chave inclui o identificador do usuário autenticado, evitando que o último acesso de uma conta seja mostrado para outra conta no mesmo navegador.

O valor armazenado não altera nem é enviado à API. O estado React é inicializado a partir dessa chave depois que a conta atual é conhecida e é atualizado na ação de abrir a loja.

## Fluxo

1. O usuário clica em **Abrir** em um card de vendedor válido.
2. O frontend registra o ID do vendedor para o usuário autenticado em estado e `localStorage`.
3. O frontend abre o link da loja como já ocorre hoje.
4. Na renderização, apenas o card cujo ID coincide com o estado recebe a etiqueta.
5. Ao excluir o vendedor marcado, o frontend remove a chave local e limpa o estado.

## Resiliência

Se `localStorage` não estiver disponível, a abertura da loja continua funcionando e a etiqueta poderá valer somente para a página atual. IDs ausentes ou que não existam mais na lista não recebem etiqueta.

## Verificação

- Abrir um vendedor mostra a etiqueta no card correto.
- Abrir outro vendedor move a etiqueta.
- Recarregar a página conserva a etiqueta para o mesmo usuário.
- Outra conta no mesmo navegador não herda a marcação.
- Excluir o vendedor marcado remove a marcação.
