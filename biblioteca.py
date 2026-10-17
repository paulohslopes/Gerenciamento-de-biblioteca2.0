import sqlite3
from datetime import date


class Biblioteca:
    def __init__(self, db_name='biblioteca.db'):
        self.conn = sqlite3.connect(db_name)
        self.conn.execute('PRAGMA foreign_keys = ON')
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS livros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                autor TEXT NOT NULL,
                categoria TEXT NOT NULL,
                ano INTEGER,
                quantidade INTEGER NOT NULL CHECK (quantidade >= 0)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS emprestimos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                livro_id INTEGER NOT NULL,
                data_emprestimo TEXT NOT NULL DEFAULT CURRENT_DATE,
                data_devolucao TEXT,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (livro_id) REFERENCES livros(id)
            )
        """)

        # Atualiza bancos antigos que ainda não possuem
        # a coluna data_devolucao.
        self.cursor.execute("PRAGMA table_info(emprestimos)")
        colunas = [coluna[1] for coluna in self.cursor.fetchall()]

        if 'data_devolucao' not in colunas:
            self.cursor.execute("""
                ALTER TABLE emprestimos
                ADD COLUMN data_devolucao TEXT
            """)

        self.conn.commit()

    # 1. Adicionar livro
    def adicionar_livro(self, titulo, autor, categoria, ano, quantidade):
        titulo = titulo.strip()
        autor = autor.strip()
        categoria = categoria.strip()

        if not titulo or not autor or not categoria:
            raise ValueError(
                'Título, autor e categoria são obrigatórios.'
            )

        ano = int(ano)
        quantidade = int(quantidade)

        if ano < 1 or ano > date.today().year:
            raise ValueError('Ano de publicação inválido.')

        if quantidade < 0:
            raise ValueError('A quantidade não pode ser negativa.')

        self.cursor.execute("""
            INSERT INTO livros
            (titulo, autor, categoria, ano, quantidade)
            VALUES (?, ?, ?, ?, ?)
        """, (titulo, autor, categoria, ano, quantidade))

        self.conn.commit()
        return self.cursor.lastrowid

    # 2. Atualizar quantidade
    def atualizar_quantidade(self, livro_id, nova_quantidade):
        livro_id = int(livro_id)
        nova_quantidade = int(nova_quantidade)

        if nova_quantidade < 0:
            raise ValueError('A quantidade não pode ser negativa.')

        self.cursor.execute("""
            UPDATE livros
            SET quantidade = ?
            WHERE id = ?
        """, (nova_quantidade, livro_id))

        self.conn.commit()
        return self.cursor.rowcount > 0

    # 3. Excluir livro com proteção
    def excluir_livro(self, livro_id):
        livro_id = int(livro_id)

        try:
            self.cursor.execute(
                'DELETE FROM livros WHERE id = ?',
                (livro_id,)
            )

            if self.cursor.rowcount == 0:
                return False

            self.conn.commit()
            return True

        except sqlite3.IntegrityError:
            self.conn.rollback()
            raise ValueError(
                'Não é possível excluir este livro, pois existem '
                'empréstimos registrados vinculados a ele.'
            )

    # 4. Listar livros
    def listar_livros(self):
        self.cursor.execute("""
            SELECT id, titulo, autor, categoria, ano, quantidade
            FROM livros
            ORDER BY titulo
        """)
        return self.cursor.fetchall()

    # 5. Pesquisar livro
    def pesquisar_livro(self, termo):
        termo = f'%{termo.strip()}%'

        self.cursor.execute("""
            SELECT id, titulo, autor, categoria, ano, quantidade
            FROM livros
            WHERE titulo LIKE ?
               OR autor LIKE ?
               OR categoria LIKE ?
            ORDER BY titulo
        """, (termo, termo, termo))

        return self.cursor.fetchall()

    # 6. Cadastrar usuário
    def cadastrar_usuario(self, nome, email):
        nome = nome.strip()
        email = email.strip()

        if not nome or not email:
            raise ValueError('Nome e e-mail são obrigatórios.')

        self.cursor.execute("""
            INSERT INTO usuarios (nome, email)
            VALUES (?, ?)
        """, (nome, email))

        self.conn.commit()
        return self.cursor.lastrowid

    # 7. Registrar empréstimo
    def registrar_emprestimo(self, usuario_id, livro_id):
        usuario_id = int(usuario_id)
        livro_id = int(livro_id)

        try:
            with self.conn:
                self.cursor.execute(
                    'SELECT id FROM usuarios WHERE id = ?',
                    (usuario_id,)
                )

                if self.cursor.fetchone() is None:
                    raise ValueError('Usuário não encontrado.')

                # Verifica a disponibilidade e reduz o estoque
                # somente se houver exemplares disponíveis.
                self.cursor.execute("""
                    UPDATE livros
                    SET quantidade = quantidade - 1
                    WHERE id = ? AND quantidade > 0
                """, (livro_id,))

                if self.cursor.rowcount == 0:
                    self.cursor.execute(
                        'SELECT id FROM livros WHERE id = ?',
                        (livro_id,)
                    )

                    if self.cursor.fetchone() is None:
                        raise ValueError('Livro não encontrado.')

                    raise ValueError(
                        'Livro indisponível no estoque.'
                    )

                self.cursor.execute("""
                    INSERT INTO emprestimos
                    (usuario_id, livro_id)
                    VALUES (?, ?)
                """, (usuario_id, livro_id))

                emprestimo_id = self.cursor.lastrowid

            return emprestimo_id

        except Exception:
            self.conn.rollback()
            raise

    # 8. Listar empréstimos ativos
    def listar_emprestimos_ativos(self):
        self.cursor.execute("""
            SELECT
                e.id,
                u.nome,
                l.titulo,
                e.data_emprestimo
            FROM emprestimos e
            JOIN usuarios u ON u.id = e.usuario_id
            JOIN livros l ON l.id = e.livro_id
            WHERE e.data_devolucao IS NULL
            ORDER BY e.data_emprestimo
        """)

        return self.cursor.fetchall()

    # 9. Registrar devolução
    def registrar_devolucao(self, emprestimo_id):
        emprestimo_id = int(emprestimo_id)

        try:
            with self.conn:
                self.cursor.execute("""
                    SELECT livro_id
                    FROM emprestimos
                    WHERE id = ?
                      AND data_devolucao IS NULL
                """, (emprestimo_id,))

                emprestimo = self.cursor.fetchone()

                if emprestimo is None:
                    raise ValueError(
                        'Empréstimo não encontrado ou já devolvido.'
                    )

                livro_id = emprestimo[0]

                self.cursor.execute("""
                    UPDATE emprestimos
                    SET data_devolucao = ?
                    WHERE id = ?
                      AND data_devolucao IS NULL
                """, (date.today().isoformat(), emprestimo_id))

                if self.cursor.rowcount == 0:
                    raise ValueError(
                        'Este empréstimo já foi devolvido.'
                    )

                self.cursor.execute("""
                    UPDATE livros
                    SET quantidade = quantidade + 1
                    WHERE id = ?
                """, (livro_id,))

            return True

        except Exception:
            self.conn.rollback()
            raise

    # Fechar conexão com o banco
    def fechar(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None
            self.cursor = None


# Ler um número inteiro digitado pelo usuário
def ler_inteiro(mensagem):
    valor = input(mensagem).strip()

    try:
        return int(valor)
    except ValueError:
        raise ValueError('Digite um número inteiro válido.') from None


# Exibir livros
def mostrar_livros(livros):
    if not livros:
        print('Nenhum livro encontrado.')
        return

    print('\nID | Título | Autor | Categoria | Ano | Quantidade')
    print('-' * 75)

    for livro in livros:
        print(
            f'{livro[0]} | {livro[1]} | {livro[2]} | '
            f'{livro[3]} | {livro[4]} | {livro[5]}'
        )


# Exibir empréstimos ativos
def mostrar_emprestimos(emprestimos):
    if not emprestimos:
        print('\nNão existem empréstimos ativos.')
        return

    print('\nID | Usuário | Livro | Data do empréstimo')
    print('-' * 65)

    for emprestimo in emprestimos:
        print(
            f'{emprestimo[0]} | {emprestimo[1]} | '
            f'{emprestimo[2]} | {emprestimo[3]}'
        )


# Menu principal
def main():
    db = Biblioteca()

    try:
        while True:
            print('\n===== SISTEMA DE BIBLIOTECA =====')
            print('1 - Adicionar livro')
            print('2 - Atualizar quantidade')
            print('3 - Excluir livro')
            print('4 - Listar livros')
            print('5 - Pesquisar livro')
            print('6 - Cadastrar usuário')
            print('7 - Registrar empréstimo')
            print('8 - Registrar devolução')
            print('9 - Consultar empréstimos ativos')
            print('10 - Encerrar sistema')

            opcao = input('Escolha uma opção: ').strip()

            if opcao == '10':
                print('Sistema encerrado.')
                break

            try:
                if opcao == '1':
                    titulo = input('Título: ')
                    autor = input('Autor: ')
                    categoria = input('Categoria: ')
                    ano = ler_inteiro('Ano de publicação: ')
                    quantidade = ler_inteiro('Quantidade disponível: ')

                    livro_id = db.adicionar_livro(
                        titulo, autor, categoria, ano, quantidade
                    )

                    print('Livro cadastrado com sucesso!')
                    print('ID:', livro_id)

                elif opcao == '2':
                    livro_id = ler_inteiro('ID do livro: ')
                    quantidade = ler_inteiro('Nova quantidade: ')

                    if db.atualizar_quantidade(livro_id, quantidade):
                        print('Quantidade atualizada com sucesso.')
                    else:
                        print('Livro não encontrado.')

                elif opcao == '3':
                    livro_id = ler_inteiro('ID do livro para excluir: ')
                    confirmar = input(
                        'Confirma a exclusão? Digite "sim": '
                    ).strip().lower()

                    if confirmar == 'sim':
                        if db.excluir_livro(livro_id):
                            print('Livro excluído com sucesso.')
                        else:
                            print('Livro não encontrado.')
                    else:
                        print('Exclusão cancelada.')

                elif opcao == '4':
                    mostrar_livros(db.listar_livros())

                elif opcao == '5':
                    termo = input('Título, autor ou categoria: ')
                    mostrar_livros(db.pesquisar_livro(termo))

                elif opcao == '6':
                    nome = input('Nome do usuário: ')
                    email = input('E-mail do usuário: ')

                    usuario_id = db.cadastrar_usuario(nome, email)

                    print('Usuário cadastrado com sucesso!')
                    print('ID:', usuario_id)

                elif opcao == '7':
                    usuario_id = ler_inteiro('ID do usuário: ')
                    livro_id = ler_inteiro('ID do livro: ')

                    emprestimo_id = db.registrar_emprestimo(
                        usuario_id, livro_id
                    )

                    print('Empréstimo registrado com sucesso!')
                    print('ID do empréstimo:', emprestimo_id)

                elif opcao == '9':
                    mostrar_emprestimos(
                        db.listar_emprestimos_ativos()
                    )

                elif opcao == '8':
                    mostrar_emprestimos(
                        db.listar_emprestimos_ativos()
                    )

                    emprestimo_id = ler_inteiro(
                        '\nID do empréstimo a devolver: '
                    )

                    db.registrar_devolucao(emprestimo_id)

                    print('Devolução registrada com sucesso!')
                    print('A quantidade disponível foi atualizada.')

                else:
                    print('Opção inválida. Tente novamente.')

            except ValueError as exc:
                print(f'Erro: {exc}')

            except sqlite3.IntegrityError as exc:
                print(f'Erro de integridade do banco: {exc}')

            except sqlite3.Error as exc:
                print(f'Erro no banco de dados: {exc}')

    finally:
        db.fechar()
        print('Conexão com o banco de dados encerrada.')


if __name__ == '__main__':
    main()
