from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


# 1. CATEGORIA
class Categoria(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

    def __str__(self):
        return self.nome


# 2. PRODUTO
class Produto(models.Model):
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    quantidade = models.PositiveIntegerField(default=0)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='produtos',
    )
    descricao = models.TextField(blank=True, null=True)
    imagem = models.CharField(
        'Imagem',
        max_length=200,
        blank=True,
        default='',
        help_text='Caminho dentro de static/, ex.: produtos/coca-cola-lata-350ml.jpg',
    )
    mais_vendido = models.BooleanField(
        default=False,
        verbose_name='Mais Vendido / Destaque',
    )

    class Meta:
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['nome', 'categoria'],
                name='produto_nome_unico_por_categoria',
            ),
            models.CheckConstraint(
                condition=models.Q(quantidade__gte=0),
                name='produto_quantidade_nao_negativa',
            ),
        ]

    def __str__(self):
        return self.nome


# 3. PESSOA (Tabela Base com ligação ao User)
class Pessoa(models.Model):
    usuario = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pessoa',
    )
    nome = models.CharField(max_length=100)
    endereco = models.CharField(max_length=150, blank=True, null=True)
    cpf = models.CharField(max_length=14, unique=True)
    celular = models.CharField(max_length=20)
    email = models.EmailField(unique=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Pessoa'
        verbose_name_plural = 'Pessoas'

    def __str__(self):
        return self.nome


# 4. SUBCLASSES DE PESSOA
class Aluno(Pessoa):
    rm = models.CharField(max_length=20, unique=True)
    curso = models.CharField(max_length=50)
    turma = models.CharField(max_length=20)


class Professor(Pessoa):
    area = models.CharField(max_length=50)
    detalhes_regime = models.CharField(max_length=50, help_text='Ex: Deta / Int')


class Funcionario(Pessoa):
    cargo = models.CharField(max_length=50)


class Visitante(Pessoa):
    motivo = models.CharField(max_length=100)
    funcao = models.CharField(max_length=50)


# 5. CARTÃO
class Cartao(models.Model):
    TIPOS = [
        ('CREDITO', 'Crédito'),
        ('DEBITO', 'Débito'),
    ]

    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.CASCADE,
        related_name='cartoes',
    )
    nome_titular = models.CharField(max_length=100)
    numero_mascarado = models.CharField(max_length=19)  # Ex: **** **** **** 1234
    bandeira = models.CharField(max_length=20, default='Outra')
    validade = models.CharField(max_length=5)  # Ex: 12/28
    tipo = models.CharField(max_length=10, choices=TIPOS, default='CREDITO')

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.numero_mascarado}'


# 6. VENDA
class Venda(models.Model):
    FORMA_PAGAMENTO_CHOICES = [
        ('DINHEIRO', 'Dinheiro'),
        ('PIX', 'Pix'),
        ('CARTAO', 'Cartão no Balcão (Maquininha)'),
        ('CARTAO_SALVO', 'Cartão Cadastrado'),
        ('FIADO', 'Conta Mensal (A Receber)'),
    ]

    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.PROTECT,
        related_name='vendas',
    )
    cartao = models.ForeignKey(
        Cartao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendas',
    )
    data_venda = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PAGAMENTO_CHOICES)

    class Meta:
        ordering = ['-data_venda']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name='venda_total_nao_negativo',
            ),
        ]

    def __str__(self):
        return f'Venda #{self.id} - {self.pessoa.nome}'


# 7. ITENS DA VENDA (Produtos que estão na compra)
class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name='itens_venda',
    )
    quantidade = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    preco_unitario = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['venda', 'produto'],
                name='item_venda_produto_unico',
            ),
            models.CheckConstraint(
                condition=models.Q(quantidade__gte=1),
                name='item_venda_quantidade_positiva',
            ),
        ]

    def __str__(self):
        return f'{self.quantidade}x {self.produto.nome} (Venda #{self.venda.id})'


# 8. CONTA A RECEBER (Fiado/Mensal)
class ContaReceber(models.Model):
    venda = models.OneToOneField(
        Venda,
        on_delete=models.CASCADE,
        related_name='conta_receber',
    )
    data_vencimento = models.DateField()
    pago = models.BooleanField(default=False, verbose_name='Foi Pago?')

    class Meta:
        ordering = ['pago', 'data_vencimento']

    def __str__(self):
        status = 'PAGO' if self.pago else 'PENDENTE'
        return f'Conta #{self.id} - {self.venda.pessoa.nome} [{status}]'


# 9. DESPESA (Gastos operacionais da cantina)
class Despesa(models.Model):
    CATEGORIAS = [
        ('INSUMOS', 'Insumos'),
        ('EQUIPAMENTOS', 'Equipamentos'),
        ('MANUTENCAO', 'Manutenção'),
        ('TRANSPORTE', 'Transporte'),
        ('OUTROS', 'Outros'),
    ]

    descricao = models.CharField(max_length=150)
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIAS,
        default='INSUMOS',
    )
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    data = models.DateField(default=timezone.localdate)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-id']
        verbose_name = 'Despesa'
        verbose_name_plural = 'Despesas'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor__gte=0),
                name='despesa_valor_nao_negativo',
            ),
        ]

    def __str__(self):
        return f'{self.descricao} - R$ {self.valor}'
