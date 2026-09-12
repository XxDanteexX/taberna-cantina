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