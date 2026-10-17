# Sistema de Biblioteca

![Testes](https://github.com/paulohslopes/sistema-biblioteca/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-green)

Sistema de gerenciamento de biblioteca para terminal, feito em **Python** com banco de dados **SQLite**. Permite controlar o acervo de livros, cadastrar usuários e registrar empréstimos e devoluções, com validação de dados e controle de estoque.

## Funcionalidades

- Cadastrar, listar, pesquisar e excluir livros
- Atualizar a quantidade de exemplares de um livro
- Pesquisar por título, autor ou categoria
- Cadastrar usuários (o e-mail é único)
- Registrar empréstimos com baixa automática no estoque
- Registrar devoluções com reposição automática no estoque
- Consultar empréstimos ativos

## Regras e proteções

- Campos obrigatórios não aceitam texto vazio.
- O ano de publicação precisa ser válido (não pode ser maior que o ano atual).
- A quantidade não pode ser negativa (validada no código e no banco).
- Um livro sem estoque não pode ser emprestado.
- Um livro com empréstimos registrados não pode ser excluído (chave estrangeira).
- Empréstimos e devoluções são transações: se algo falha, nada é alterado.
- Um empréstimo não pode ser devolvido duas vezes.
- Entradas que não são números geram uma mensagem clara, sem derrubar o programa.
- Bancos criados em versões antigas são atualizados automaticamente (coluna `data_devolucao`).

## Tecnologias

- Python 3.8 ou superior
- SQLite (módulo `sqlite3` da biblioteca padrão)
- `unittest` para os testes

Não há dependências externas para instalar.

## Como executar

```bash
git clone https://github.com/paulohslopes/sistema-biblioteca.git
cd sistema-biblioteca
python biblioteca.py
```

No Linux e no macOS, use `python3` se `python` não estiver disponível. O arquivo `biblioteca.db` é criado automaticamente na primeira execução.

## Menu

```text
===== SISTEMA DE BIBLIOTECA =====
1 - Adicionar livro
2 - Atualizar quantidade
3 - Excluir livro
4 - Listar livros
5 - Pesquisar livro
6 - Cadastrar usuário
7 - Registrar empréstimo
8 - Registrar devolução
9 - Consultar empréstimos ativos
10 - Encerrar sistema
```

## Exemplo de uso

```text
Escolha uma opção: 7
ID do usuário: 1
ID do livro: 1
Empréstimo registrado com sucesso!
ID do empréstimo: 1

Escolha uma opção: 9

ID | Usuário | Livro | Data do empréstimo
-----------------------------------------------------------------
1 | Ana | Dom Casmurro | 2026-10-17
```

## Estrutura do banco de dados

| Tabela | Campos principais |
|---|---|
| `livros` | `id`, `titulo`, `autor`, `categoria`, `ano`, `quantidade` |
| `usuarios` | `id`, `nome`, `email` (único) |
| `emprestimos` | `id`, `usuario_id`, `livro_id`, `data_emprestimo`, `data_devolucao` |

Um empréstimo está ativo enquanto `data_devolucao` é nulo.

## Testes

```bash
python -m unittest -v
```

Os testes usam um banco em memória e cobrem cadastro, busca, estoque, empréstimos, devoluções, erros de validação, migração de banco antigo e o tratamento de entradas inválidas no menu.

## Estrutura do projeto

```text
sistema-biblioteca/
├── biblioteca.py        # classe Biblioteca e menu de terminal
├── test_biblioteca.py   # testes automatizados
├── README.md
├── LICENSE
├── .gitignore
└── .github/workflows/tests.yml   # testes automáticos no GitHub
```

## Possíveis melhorias

- Relatório de empréstimos por categoria, com gráfico
- Prazo de devolução e cálculo de atraso
- Limite de empréstimos por usuário
- Interface web ou gráfica

## Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE).

## Autor

[Paulo Henrique](https://github.com/paulohslopes)
