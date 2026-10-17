import io
import sqlite3
import unittest
from contextlib import redirect_stdout
from datetime import date
from unittest.mock import patch

import biblioteca
from biblioteca import Biblioteca, ler_inteiro


class TestBiblioteca(unittest.TestCase):
    def setUp(self):
        self.db = Biblioteca(':memory:')

    def tearDown(self):
        self.db.fechar()

    def _livro(self, qtd=2, titulo='Dom Casmurro'):
        return self.db.adicionar_livro(titulo, 'Machado de Assis', 'Romance', 1899, qtd)

    def _usuario(self, email='ana@x.com'):
        return self.db.cadastrar_usuario('Ana', email)

    # livros
    def test_adicionar_e_listar(self):
        lid = self._livro()
        self.assertEqual(lid, 1)
        self.assertEqual(self.db.listar_livros()[0][1], 'Dom Casmurro')

    def test_adicionar_campos_vazios(self):
        with self.assertRaises(ValueError):
            self.db.adicionar_livro('  ', 'a', 'b', 2000, 1)

    def test_adicionar_ano_invalido(self):
        with self.assertRaises(ValueError):
            self.db.adicionar_livro('t', 'a', 'c', date.today().year + 1, 1)
        with self.assertRaises(ValueError):
            self.db.adicionar_livro('t', 'a', 'c', 0, 1)

    def test_adicionar_quantidade_negativa(self):
        with self.assertRaises(ValueError):
            self.db.adicionar_livro('t', 'a', 'c', 2000, -1)

    def test_adicionar_ano_nao_numerico(self):
        with self.assertRaises(ValueError):
            self.db.adicionar_livro('t', 'a', 'c', 'abc', 1)

    def test_atualizar_quantidade(self):
        lid = self._livro()
        self.assertTrue(self.db.atualizar_quantidade(lid, 10))
        self.assertEqual(self.db.listar_livros()[0][5], 10)
        self.assertFalse(self.db.atualizar_quantidade(999, 1))
        with self.assertRaises(ValueError):
            self.db.atualizar_quantidade(lid, -5)

    def test_pesquisar(self):
        self._livro()
        self.db.adicionar_livro('Python', 'Guido', 'Tecnologia', 2020, 1)
        self.assertEqual(len(self.db.pesquisar_livro('machado')), 1)
        self.assertEqual(len(self.db.pesquisar_livro('tecno')), 1)
        self.assertEqual(len(self.db.pesquisar_livro('zzz')), 0)
        self.assertEqual(len(self.db.pesquisar_livro('')), 2)

    def test_excluir_livro(self):
        lid = self._livro()
        self.assertTrue(self.db.excluir_livro(lid))
        self.assertFalse(self.db.excluir_livro(lid))

    def test_excluir_livro_com_emprestimo_bloqueado(self):
        lid = self._livro()
        uid = self._usuario()
        self.db.registrar_emprestimo(uid, lid)
        with self.assertRaises(ValueError):
            self.db.excluir_livro(lid)
        self.assertEqual(len(self.db.listar_livros()), 1)

    # usuários
    def test_usuario_email_duplicado(self):
        self._usuario()
        with self.assertRaises(sqlite3.IntegrityError):
            self._usuario()

    def test_usuario_campos_vazios(self):
        with self.assertRaises(ValueError):
            self.db.cadastrar_usuario('', 'a@b.com')

    # empréstimos
    def test_emprestimo_e_devolucao(self):
        lid = self._livro(qtd=1)
        uid = self._usuario()
        eid = self.db.registrar_emprestimo(uid, lid)
        self.assertEqual(self.db.listar_livros()[0][5], 0)
        ativos = self.db.listar_emprestimos_ativos()
        self.assertEqual(len(ativos), 1)
        self.assertEqual(ativos[0][1:3], ('Ana', 'Dom Casmurro'))

        self.assertTrue(self.db.registrar_devolucao(eid))
        self.assertEqual(self.db.listar_livros()[0][5], 1)
        self.assertEqual(self.db.listar_emprestimos_ativos(), [])

    def test_emprestimo_sem_estoque(self):
        lid = self._livro(qtd=0)
        uid = self._usuario()
        with self.assertRaises(ValueError) as ctx:
            self.db.registrar_emprestimo(uid, lid)
        self.assertIn('indisponível', str(ctx.exception))
        self.assertEqual(self.db.listar_emprestimos_ativos(), [])

    def test_emprestimo_usuario_ou_livro_inexistente(self):
        lid = self._livro()
        uid = self._usuario()
        with self.assertRaises(ValueError):
            self.db.registrar_emprestimo(999, lid)
        with self.assertRaises(ValueError) as ctx:
            self.db.registrar_emprestimo(uid, 999)
        self.assertIn('não encontrado', str(ctx.exception))
        # estoque não deve ter mudado
        self.assertEqual(self.db.listar_livros()[0][5], 2)

    def test_devolucao_dupla(self):
        lid = self._livro()
        uid = self._usuario()
        eid = self.db.registrar_emprestimo(uid, lid)
        self.db.registrar_devolucao(eid)
        with self.assertRaises(ValueError):
            self.db.registrar_devolucao(eid)
        # estoque não pode passar do original
        self.assertEqual(self.db.listar_livros()[0][5], 2)

    def test_devolucao_inexistente(self):
        with self.assertRaises(ValueError):
            self.db.registrar_devolucao(123)

    def test_migracao_banco_antigo(self):
        import os, tempfile
        path = os.path.join(tempfile.mkdtemp(), 'old.db')
        c = sqlite3.connect(path)
        c.execute('CREATE TABLE livros (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, autor TEXT NOT NULL, categoria TEXT NOT NULL, ano INTEGER, quantidade INTEGER NOT NULL CHECK (quantidade >= 0))')
        c.execute('CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL)')
        c.execute('CREATE TABLE emprestimos (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL, livro_id INTEGER NOT NULL, data_emprestimo TEXT NOT NULL DEFAULT CURRENT_DATE)')
        c.commit(); c.close()
        db = Biblioteca(path)
        cols = [r[1] for r in db.conn.execute('PRAGMA table_info(emprestimos)')]
        self.assertIn('data_devolucao', cols)
        db.fechar()

    def test_fechar_duas_vezes(self):
        self.db.fechar()
        self.db.fechar()


class TestEntradaNumerica(unittest.TestCase):
    def test_ler_inteiro_valido(self):
        with patch('builtins.input', return_value=' 42 '):
            self.assertEqual(ler_inteiro('N: '), 42)

    def test_ler_inteiro_invalido_tem_mensagem_amigavel(self):
        for entrada in ('abc', '', '3.5'):
            with patch('builtins.input', return_value=entrada):
                with self.assertRaises(ValueError) as ctx:
                    ler_inteiro('N: ')
                self.assertEqual(
                    str(ctx.exception), 'Digite um número inteiro válido.'
                )

    def test_menu_mostra_mensagem_amigavel_e_continua(self):
        # opção 2 com ID inválido, depois encerra o sistema
        entradas = iter(['2', 'abc', '10'])
        saida = io.StringIO()

        with patch.object(
            biblioteca, 'Biblioteca', lambda: Biblioteca(':memory:')
        ), patch('builtins.input', lambda _: next(entradas)), \
                redirect_stdout(saida):
            biblioteca.main()

        texto = saida.getvalue()
        self.assertIn('Erro: Digite um número inteiro válido.', texto)
        self.assertNotIn('invalid literal', texto)
        self.assertIn('Sistema encerrado.', texto)


if __name__ == '__main__':
    unittest.main(verbosity=2)
