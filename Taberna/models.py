from django.db import models
from django.contrib.auth.models import User  # Importante!

# 1. CATEGORIA
class Categoria(models.Model):
    nome = models.CharField(max_length=50)

    def __str__(self):
        return self.nome

# 2. PRODUTO
class Produto(models.Model):
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=6, decimal_places=2)
    quantidade = models.IntegerField()
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    descricao = models.TextField(blank=True, null=True)
    mais_vendido = models.BooleanField(default=False, verbose_name="Mais Vendido / Destaque")

    def __str__(self):
        return self.nome

# 3. PESSOA (Tabela Base com ligação ao User)
class Pessoa(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nome = models.CharField(max_length=100)
    endereco = models.CharField(max_length=150, blank=True, null=True)
    cpf = models.CharField(max_length=14, unique=True)
    celular = models.CharField(max_length=20)
    email = models.EmailField()

    def __str__(self):
        return self.nome

# 4. SUBCLASSES DE PESSOA
class Aluno(Pessoa):
    rm = models.CharField(max_length=20, unique=True)
    curso = models.CharField(max_length=50)
    turma = models.CharField(max_length=20)

class Professor(Pessoa):
    area = models.CharField(max_length=50)
    detalhes_regime = models.CharField(max_length=50, help_text="Ex: Deta / Int")

class Funcionario(Pessoa):
    cargo = models.CharField(max_length=50)

class Visitante(Pessoa):
    motivo = models.CharField(max_length=100)
    funcao = models.CharField(max_length=50)
# 5. VENDA
class Venda(models.Model):
    FORMA_PAGAMENTO_CHOICES = [
        ('DINHEIRO', 'Dinheiro'),
        ('PIX', 'Pix'),
        ('CARTAO', 'Cartão de Crédito/Débito'),
        ('FIADO', 'Conta Mensal (A Receber)'),
    ]

    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name='vendas')
    data_venda = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PAGAMENTO_CHOICES)

    def __str__(self):
        return f"Venda #{self.id} - {self.pessoa.nome}"

# 6. ITENS DA VENDA (Produtos que estão na compra)
class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome} (Venda #{self.venda.id})"

# 7. CONTRA A RECEBER (Fiado/Mensal)
class ContaReceber(models.Model):
    venda = models.OneToOneField(Venda, on_delete=models.CASCADE, related_name='conta_receber')
    data_vencimento = models.DateField()
    pago = models.BooleanField(default=False, verbose_name="Foi Pago?")

    def __str__(self):
        status = "PAGO" if self.pago else "PENDENTE"
        return f"Conta #{self.id} - {self.venda.pessoa.nome} [{status}]"
class Cartao(models.Model):
    TIPOS = [
        ('CREDITO', 'Crédito'),
        ('DEBITO', 'Débito'),
    ]
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name='cartaos')
    nome_titular = models.CharField(max_length=100)
    numero_mascarado = models.CharField(max_length=19)  # Ex: **** **** **** 1234
    bandeira = models.CharField(max_length=20, default='Mastercard')
    validade = models.CharField(max_length=5)  # Ex: 12/28
    tipo = models.CharField(max_length=10, choices=TIPOS, default='CREDITO')

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.numero_mascarado}"