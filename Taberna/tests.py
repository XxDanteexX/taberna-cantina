from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.core import signing
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .dev_login import (
    DEV_LOGIN_SALT,
    DEV_USERNAME,
    obter_ou_criar_usuario_dev,
)

from .models import (
    Aluno,
    Cartao,
    Categoria,
    ContaReceber,
    Despesa,
    ItemVenda,
    Pessoa,
    Professor,
    Produto,
    Venda,
)
from .views import obter_perfil_usuario


def criar_pessoa(usuario=None, sufixo='1', email=None):
    return Pessoa.objects.create(
        usuario=usuario,
        nome=f'Pessoa {sufixo}',
        cpf=f'000.000.000-{sufixo.zfill(2)[-2:]}',
        celular='11999999999',
        email=email or f'pessoa{sufixo}@example.com',
    )


class CarrinhoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='cliente',
            password='SenhaForte!123',
            email='cliente@example.com',
        )
        self.pessoa = criar_pessoa(self.user, '1', 'cliente@example.com')
        self.categoria = Categoria.objects.create(nome='Bebidas')
        self.produto = Produto.objects.create(
            nome='Suco',
            preco=Decimal('5.50'),
            quantidade=5,
            categoria=self.categoria,
        )
        self.client.force_login(self.user)

    def _definir_carrinho(self, quantidade):
        session = self.client.session
        session['carrinho'] = {str(self.produto.id): quantidade}
        session.save()

    def test_pagina_do_carrinho_renderiza_item(self):
        self._definir_carrinho(2)
        response = self.client.get(reverse('ver_carrinho'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.produto.nome)
        self.assertContains(
            response,
            reverse('remover_do_carrinho', args=[self.produto.id]),
        )

    def test_pagina_do_carrinho_oferece_cartao_salvo(self):
        Cartao.objects.create(
            pessoa=self.pessoa,
            nome_titular='CLIENTE',
            numero_mascarado='**** **** **** 4242',
            bandeira='Visa',
            validade='12/30',
            tipo='CREDITO',
        )
        self._definir_carrinho(1)
        response = self.client.get(reverse('ver_carrinho'))
        self.assertContains(response, 'CARTAO_SALVO')

    def test_remover_item_do_carrinho(self):
        self._definir_carrinho(2)
        response = self.client.post(
            reverse('remover_do_carrinho', args=[self.produto.id])
        )
        self.assertRedirects(response, reverse('ver_carrinho'))
        self.assertNotIn('carrinho', self.client.session)

    def test_nao_adiciona_acima_do_estoque(self):
        self._definir_carrinho(5)
        self.client.post(
            reverse('adicionar_ao_carrinho', args=[self.produto.id])
        )
        self.assertEqual(self.client.session['carrinho'][str(self.produto.id)], 5)

    def test_nao_adiciona_produto_inexistente(self):
        response = self.client.post(
            reverse('adicionar_ao_carrinho', args=[999999])
        )
        self.assertRedirects(response, reverse('cardapio'))
        self.assertNotIn('carrinho', self.client.session)


class CheckoutTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='aluno1',
            password='SenhaForte!123',
            email='aluno1@example.com',
        )
        self.aluno = Aluno.objects.create(
            usuario=self.user,
            nome='Aluno Um',
            cpf='111.111.111-11',
            celular='11999999999',
            email='aluno1@example.com',
            rm='RM001',
            curso='Informática',
            turma='1A',
        )
        self.categoria = Categoria.objects.create(nome='Salgados')
        self.produto = Produto.objects.create(
            nome='Coxinha',
            preco=Decimal('5.50'),
            quantidade=5,
            categoria=self.categoria,
        )
        self.client.force_login(self.user)

    def _definir_carrinho(self, quantidade=2):
        session = self.client.session
        session['carrinho'] = {str(self.produto.id): quantidade}
        session.save()

    def test_checkout_cria_venda_e_decrementa_estoque(self):
        self._definir_carrinho(2)
        response = self.client.post(
            reverse('finalizar_compra'),
            {'forma_pagamento': 'DINHEIRO'},
        )
        self.assertRedirects(response, reverse('cardapio'))

        venda = Venda.objects.get()
        self.assertEqual(venda.total, Decimal('11.00'))
        self.assertEqual(venda.forma_pagamento, 'DINHEIRO')
        self.assertEqual(ItemVenda.objects.count(), 1)
        self.assertEqual(ItemVenda.objects.get().quantidade, 2)

        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade, 3)
        self.assertNotIn('carrinho', self.client.session)

    def test_checkout_cartao_balcao_nao_exige_cartao_cadastrado(self):
        self._definir_carrinho(1)
        response = self.client.post(
            reverse('finalizar_compra'),
            {'forma_pagamento': 'CARTAO'},
        )
        self.assertRedirects(response, reverse('cardapio'))

        venda = Venda.objects.get()
        self.assertEqual(venda.forma_pagamento, 'CARTAO')
        self.assertIsNone(venda.cartao)
        self.assertEqual(Cartao.objects.count(), 0)

    def test_checkout_cartao_salvo_sem_cartao_e_bloqueado(self):
        self._definir_carrinho(1)
        response = self.client.post(
            reverse('finalizar_compra'),
            {'forma_pagamento': 'CARTAO_SALVO'},
        )
        self.assertRedirects(response, reverse('cadastrar_cartao'))
        self.assertEqual(Venda.objects.count(), 0)

    def test_checkout_sem_pessoa_nao_cria_venda(self):
        usuario_sem_pessoa = User.objects.create_user(
            username='sem_pessoa',
            password='SenhaForte!123',
            email='sem_pessoa@example.com',
        )
        self.client.force_login(usuario_sem_pessoa)
        self._definir_carrinho(1)

        response = self.client.post(
            reverse('finalizar_compra'),
            {'forma_pagamento': 'DINHEIRO'},
        )
        self.assertRedirects(response, reverse('cardapio'))
        self.assertEqual(Venda.objects.count(), 0)

    def test_checkout_com_forma_invalida_nao_cria_venda(self):
        self._definir_carrinho(1)
        response = self.client.post(
            reverse('finalizar_compra'),
            {'forma_pagamento': 'BOLETO'},
        )
        self.assertRedirects(response, reverse('ver_carrinho'))
        self.assertEqual(Venda.objects.count(), 0)

    def test_checkout_fiado_bloqueado_para_aluno(self):
        self._definir_carrinho(1)
        response = self.client.post(
            reverse('finalizar_compra'),
            {'forma_pagamento': 'FIADO'},
        )
        self.assertRedirects(response, reverse('ver_carrinho'))
        self.assertEqual(Venda.objects.count(), 0)
        self.assertEqual(ContaReceber.objects.count(), 0)

    def test_checkout_fiado_permitido_para_professor(self):
        usuario = User.objects.create_user(
            username='prof1',
            password='SenhaForte!123',
            email='prof1@example.com',
        )
        Professor.objects.create(
            usuario=usuario,
            nome='Professor Um',
            cpf='222.222.222-22',
            celular='11999999999',
            email='prof1@example.com',
            area='Matemática',
            detalhes_regime='Integral',
        )
        self.client.force_login(usuario)
        self._definir_carrinho(1)

        response = self.client.post(
            reverse('finalizar_compra'),
            {'forma_pagamento': 'FIADO'},
        )
        self.assertRedirects(response, reverse('cardapio'))

        venda = Venda.objects.get()
        conta = ContaReceber.objects.get()
        self.assertEqual(conta.venda, venda)
        self.assertFalse(conta.pago)
        self.assertEqual(
            conta.data_vencimento,
            timezone.localdate() + timedelta(days=30),
        )

    def test_checkout_com_estoque_insuficiente_nao_cria_venda(self):
        self.produto.quantidade = 1
        self.produto.save(update_fields=['quantidade'])
        self._definir_carrinho(2)

        response = self.client.post(
            reverse('finalizar_compra'),
            {'forma_pagamento': 'DINHEIRO'},
        )
        self.assertRedirects(response, reverse('ver_carrinho'))
        self.assertEqual(Venda.objects.count(), 0)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade, 1)

    def test_checkout_remove_produto_excluido_do_carrinho(self):
        produto_id = self.produto.id
        self._definir_carrinho(1)
        self.produto.delete()

        response = self.client.post(
            reverse('finalizar_compra'),
            {'forma_pagamento': 'DINHEIRO'},
        )
        self.assertRedirects(response, reverse('cardapio'))
        self.assertEqual(Venda.objects.count(), 0)
        self.assertNotIn(str(produto_id), self.client.session.get('carrinho', {}))

    def test_cartao_salvo_de_outra_pessoa_e_rejeitado(self):
        outro_user = User.objects.create_user(
            username='outro',
            password='SenhaForte!123',
            email='outro@example.com',
        )
        outra_pessoa = criar_pessoa(outro_user, '2', 'outro@example.com')
        cartao_alheio = Cartao.objects.create(
            pessoa=outra_pessoa,
            nome_titular='OUTRO TITULAR',
            numero_mascarado='**** **** **** 4444',
            bandeira='Visa',
            validade='12/30',
            tipo='CREDITO',
        )
        self._definir_carrinho(1)

        response = self.client.post(
            reverse('finalizar_compra'),
            {'forma_pagamento': 'CARTAO_SALVO', 'cartao_id': cartao_alheio.id},
        )
        self.assertRedirects(response, reverse('cadastrar_cartao'))
        self.assertEqual(Venda.objects.count(), 0)

    def test_cartao_salvo_valido_registra_cartao_na_venda(self):
        cartao = Cartao.objects.create(
            pessoa=self.aluno,
            nome_titular='ALUNO UM',
            numero_mascarado='**** **** **** 4242',
            bandeira='Visa',
            validade='12/30',
            tipo='CREDITO',
        )
        self._definir_carrinho(1)

        response = self.client.post(
            reverse('finalizar_compra'),
            {'forma_pagamento': 'CARTAO_SALVO', 'cartao_id': cartao.id},
        )
        self.assertRedirects(response, reverse('cardapio'))
        venda = Venda.objects.get()
        self.assertEqual(venda.cartao_id, cartao.id)
        self.assertEqual(venda.forma_pagamento, 'CARTAO_SALVO')


class CartaoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='cartao_user',
            password='SenhaForte!123',
            email='cartao@example.com',
        )
        self.pessoa = criar_pessoa(self.user, '3', 'cartao@example.com')
        self.client.force_login(self.user)

    def _validade_futura(self):
        return (timezone.localdate() + timedelta(days=365 * 2)).strftime('%m/%y')

    def test_cadastra_cartao_valido_mascarando_numero(self):
        response = self.client.post(
            reverse('cadastrar_cartao'),
            {
                'nome_titular': 'TITULAR TESTE',
                'numero': '4242 4242 4242 4242',
                'validade': self._validade_futura(),
                'tipo': 'CREDITO',
            },
        )
        self.assertRedirects(response, reverse('cadastrar_cartao'))

        cartao = Cartao.objects.get()
        self.assertEqual(cartao.numero_mascarado, '**** **** **** 4242')
        self.assertEqual(cartao.bandeira, 'Visa')
        self.assertFalse(hasattr(cartao, 'numero'))

    @override_settings(DEBUG=False)
    def test_rejeita_numero_com_luhn_invalido(self):
        response = self.client.post(
            reverse('cadastrar_cartao'),
            {
                'nome_titular': 'TITULAR TESTE',
                'numero': '1234 5678 9012 3456',
                'validade': self._validade_futura(),
                'tipo': 'CREDITO',
            },
        )
        self.assertRedirects(response, reverse('cadastrar_cartao'))
        self.assertEqual(Cartao.objects.count(), 0)

    @override_settings(DEBUG=True)
    def test_aceita_numero_sem_luhn_em_debug(self):
        response = self.client.post(
            reverse('cadastrar_cartao'),
            {
                'nome_titular': 'TITULAR TESTE',
                'numero': '1234 5678 9012 3456',
                'validade': self._validade_futura(),
                'tipo': 'CREDITO',
            },
        )
        self.assertRedirects(response, reverse('cadastrar_cartao'))
        self.assertEqual(Cartao.objects.count(), 1)
        cartao = Cartao.objects.get()
        self.assertEqual(cartao.numero_mascarado, '**** **** **** 3456')

    def test_rejeita_validade_vencida(self):
        response = self.client.post(
            reverse('cadastrar_cartao'),
            {
                'nome_titular': 'TITULAR TESTE',
                'numero': '4242 4242 4242 4242',
                'validade': '01/20',
                'tipo': 'CREDITO',
            },
        )
        self.assertRedirects(response, reverse('cadastrar_cartao'))
        self.assertEqual(Cartao.objects.count(), 0)

    def test_nao_mostra_cartao_de_outra_pessoa(self):
        outro_user = User.objects.create_user(
            username='cartao_outro',
            password='SenhaForte!123',
            email='cartao_outro@example.com',
        )
        outra_pessoa = criar_pessoa(outro_user, '4', 'cartao_outro@example.com')
        Cartao.objects.create(
            pessoa=outra_pessoa,
            nome_titular='OUTRA PESSOA',
            numero_mascarado='**** **** **** 9999',
            bandeira='Mastercard',
            validade='12/30',
            tipo='CREDITO',
        )

        response = self.client.get(reverse('cadastrar_cartao'))
        self.assertNotContains(response, '**** **** **** 9999')

    def test_sem_pessoa_nao_acessa_cadastro_de_cartao(self):
        usuario = User.objects.create_user(
            username='cartao_sem_pessoa',
            password='SenhaForte!123',
            email='sem_pessoa_cartao@example.com',
        )
        self.client.force_login(usuario)
        response = self.client.get(reverse('cadastrar_cartao'))
        self.assertRedirects(response, reverse('cardapio'))


class PerfilELoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='prof_login',
            password='SenhaForte!123',
            email='prof_login@example.com',
        )
        self.professor = Professor.objects.create(
            usuario=self.user,
            nome='Professor Login',
            cpf='333.333.333-33',
            celular='11999999999',
            email='prof_login@example.com',
            area='História',
            detalhes_regime='Integral',
        )

    def test_perfil_professor_usa_vinculo_pessoa(self):
        self.assertEqual(obter_perfil_usuario(self.user), 'Professor')

    def test_perfil_sem_pessoa_nao_e_aluno_por_padrao(self):
        usuario = User.objects.create_user(
            username='sem_perfil',
            password='SenhaForte!123',
            email='sem_perfil@example.com',
        )
        self.assertEqual(obter_perfil_usuario(usuario), 'Usuário')

    def test_login_professor_com_cpf_sem_pontuacao(self):
        response = self.client.post(
            reverse('login'),
            {
                'identificador': '33333333333',
                'password': 'SenhaForte!123',
                'tipo_perfil': 'professor',
            },
        )
        self.assertRedirects(response, reverse('cardapio'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_nao_permite_perfil_diferente_do_vinculo(self):
        response = self.client.post(
            reverse('login'),
            {
                'identificador': '33333333333',
                'password': 'SenhaForte!123',
                'tipo_perfil': 'aluno',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_de_staff_por_username(self):
        User.objects.create_user(
            username='admin_taberna',
            password='SenhaForte!123',
            email='admin@example.com',
            is_staff=True,
        )
        response = self.client.post(
            reverse('login'),
            {
                'identificador': 'admin_taberna',
                'password': 'SenhaForte!123',
                'tipo_perfil': 'aluno',
            },
        )
        self.assertRedirects(response, reverse('cardapio'))

    def test_login_bloqueia_apos_cinco_falhas(self):
        url = reverse('login')
        dados = {
            'identificador': '33333333333',
            'password': 'senha-errada',
            'tipo_perfil': 'professor',
        }
        for _ in range(5):
            self.client.post(url, dados)

        dados['password'] = 'SenhaForte!123'
        response = self.client.post(url, dados)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

        cache.clear()
        response = self.client.post(url, dados)
        self.assertRedirects(response, reverse('cardapio'))

    def test_logout_exige_post(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)

        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)


class DevLoginTests(TestCase):
    def _criar_link(self):
        usuario = obter_ou_criar_usuario_dev()
        token = signing.dumps(usuario.pk, salt=DEV_LOGIN_SALT)
        return usuario, reverse('dev_login', args=[token])

    def test_helper_cria_superusuario_com_perfil_professor(self):
        usuario = obter_ou_criar_usuario_dev()
        self.assertEqual(usuario.username, DEV_USERNAME)
        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.is_superuser)
        self.assertEqual(obter_perfil_usuario(usuario), 'Professor')
        self.assertTrue(usuario.pessoa.cpf.startswith('000.000.000-'))

    @override_settings(DEBUG=True)
    def test_link_loga_como_desenvolvedor(self):
        usuario, url = self._criar_link()
        response = self.client.get(url)
        self.assertRedirects(response, reverse('cardapio'))
        self.assertEqual(int(self.client.session['_auth_user_id']), usuario.pk)

    @override_settings(DEBUG=False)
    def test_rota_responde_404_em_producao(self):
        _, url = self._criar_link()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @override_settings(DEBUG=True)
    def test_token_invalido_redireciona_para_login(self):
        response = self.client.get(reverse('dev_login', args=['invalido']))
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    @override_settings(DEBUG=True, DEV_LOGIN_MAX_AGE=-1)
    def test_token_expirado_redireciona_para_login(self):
        _, url = self._criar_link()
        response = self.client.get(url)
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    @override_settings(DEBUG=True)
    def test_comando_imprime_link(self):
        saida = StringIO()
        call_command('dev_login', stdout=saida)
        self.assertIn('/dev-login/', saida.getvalue())

    @override_settings(DEBUG=False)
    def test_comando_recusa_debug_false(self):
        with self.assertRaises(CommandError):
            call_command('dev_login', stdout=StringIO(), stderr=StringIO())


class PainelDonoTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username='dono',
            password='SenhaForte!123',
            email='dono@example.com',
            is_staff=True,
        )
        self.cliente = User.objects.create_user(
            username='cliente_painel',
            password='SenhaForte!123',
            email='cliente_painel@example.com',
        )
        self.pessoa = criar_pessoa(self.cliente, '88', 'cliente_painel@example.com')
        self.categoria = Categoria.objects.create(nome='Salgados do painel')
        self.produto = Produto.objects.create(
            nome='Coxinha do painel',
            preco=Decimal('5.00'),
            quantidade=10,
            categoria=self.categoria,
        )

    def test_anonimo_redireciona_para_login(self):
        response = self.client.get(reverse('painel_dono'))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('painel_dono')}",
        )

    def test_usuario_comum_recebe_403(self):
        self.client.force_login(self.cliente)
        response = self.client.get(reverse('painel_dono'))
        self.assertEqual(response.status_code, 403)

    def test_staff_acessa_painel(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('painel_dono'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Painel do dono')
        self.assertContains(response, 'Estoque')

    def test_link_do_painel_nao_aparece_para_usuario_comum(self):
        self.client.force_login(self.cliente)
        response = self.client.get(reverse('cardapio'))
        self.assertNotContains(response, reverse('painel_dono'))

    def test_link_do_painel_aparece_para_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('cardapio'))
        self.assertContains(response, reverse('painel_dono'))

    def test_painel_agrega_venda_e_despesa_do_mes(self):
        venda = Venda.objects.create(
            pessoa=self.pessoa,
            total=Decimal('10.00'),
            forma_pagamento='PIX',
        )
        ItemVenda.objects.create(
            venda=venda,
            produto=self.produto,
            quantidade=2,
            preco_unitario=Decimal('5.00'),
        )
        Despesa.objects.create(
            descricao='Insumos do painel',
            categoria='INSUMOS',
            valor=Decimal('3.00'),
            data=timezone.localdate(),
        )

        self.client.force_login(self.staff)
        response = self.client.get(reverse('painel_dono'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['receita_ano'], Decimal('10.00'))
        self.assertEqual(response.context['vendas_ano'], 1)
        self.assertEqual(response.context['itens_ano'], 2)
        self.assertEqual(response.context['despesas_ano'], Decimal('3.00'))
        self.assertEqual(response.context['resultado_ano'], Decimal('7.00'))

        indice_mes = timezone.localdate().month - 1
        self.assertEqual(response.context['chart_data']['receita'][indice_mes], 10.0)
        self.assertEqual(response.context['chart_data']['despesas'][indice_mes], 3.0)
        self.assertEqual(response.context['chart_data']['itens'][indice_mes], 2)
        self.assertEqual(response.context['chart_data']['vendas'][indice_mes], 1)

    def test_staff_adiciona_despesa(self):
        self.client.force_login(self.staff)
        hoje = timezone.localdate()
        response = self.client.post(reverse('painel_dono'), {
            'acao': 'adicionar_despesa',
            'ano': str(hoje.year),
            'descricao': 'Compra de copos',
            'valor': '12,50',
            'data': hoje.isoformat(),
            'categoria': 'INSUMOS',
        })

        self.assertRedirects(
            response,
            f"{reverse('painel_dono')}?ano={hoje.year}",
        )
        despesa = Despesa.objects.get(descricao='Compra de copos')
        self.assertEqual(despesa.valor, Decimal('12.50'))
        self.assertEqual(despesa.data, hoje)

    def test_usuario_comum_nao_adiciona_despesa(self):
        self.client.force_login(self.cliente)
        hoje = timezone.localdate()
        response = self.client.post(reverse('painel_dono'), {
            'acao': 'adicionar_despesa',
            'ano': str(hoje.year),
            'descricao': 'Tentativa indevida',
            'valor': '10,00',
            'data': hoje.isoformat(),
            'categoria': 'OUTROS',
        })

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Despesa.objects.filter(descricao='Tentativa indevida').exists())

    def test_login_nao_expoe_aba_do_dono(self):
        response = self.client.get(reverse('login'))
        self.assertNotContains(response, reverse('painel_dono'))
        self.assertNotContains(response, 'Painel do dono')
