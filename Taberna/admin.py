from django.contrib import admin

from .models import (
    Aluno,
    Cartao,
    Categoria,
    ContaReceber,
    Despesa,
    Funcionario,
    ItemVenda,
    Pessoa,
    Professor,
    Produto,
    Venda,
    Visitante,
)


class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'quantidade', 'categoria', 'mais_vendido')
    list_editable = ('mais_vendido',)
    list_filter = ('categoria', 'mais_vendido')
    search_fields = ('nome', 'descricao')


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 0
    can_delete = False
    readonly_fields = ('produto', 'quantidade', 'preco_unitario')


class VendaAdmin(admin.ModelAdmin):
    """Vendas são criadas apenas pelo checkout; aqui ficam somente para consulta."""

    list_display = ('id', 'pessoa', 'data_venda', 'total', 'forma_pagamento', 'cartao')
    list_filter = ('forma_pagamento', 'data_venda')
    search_fields = ('pessoa__nome', 'pessoa__cpf')
    date_hierarchy = 'data_venda'
    readonly_fields = (
        'pessoa',
        'cartao',
        'data_venda',
        'total',
        'forma_pagamento',
    )
    inlines = [ItemVendaInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ContaReceberAdmin(admin.ModelAdmin):
    list_display = ('id', 'venda', 'data_vencimento', 'pago')
    list_editable = ('pago',)
    list_filter = ('pago', 'data_vencimento')
    search_fields = ('venda__pessoa__nome', 'venda__pessoa__cpf')
    date_hierarchy = 'data_vencimento'


class DespesaAdmin(admin.ModelAdmin):
    list_display = ('data', 'descricao', 'categoria', 'valor')
    list_filter = ('categoria', 'data')
    search_fields = ('descricao',)
    date_hierarchy = 'data'
    ordering = ('-data', '-id')


class CartaoAdmin(admin.ModelAdmin):
    list_display = (
        'nome_titular',
        'numero_mascarado',
        'bandeira',
        'tipo',
        'validade',
        'pessoa',
    )
    list_filter = ('tipo', 'bandeira')
    search_fields = ('nome_titular', 'pessoa__nome', 'numero_mascarado')
    readonly_fields = (
        'pessoa',
        'nome_titular',
        'numero_mascarado',
        'bandeira',
        'validade',
        'tipo',
    )

    def has_add_permission(self, request):
        return False


class PessoaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf', 'email', 'celular', 'usuario')
    search_fields = ('nome', 'cpf', 'email')

    def has_add_permission(self, request):
        # Pessoas devem ser criadas como Aluno, Professor, Funcionário ou Visitante.
        return False


class AlunoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'rm', 'curso', 'turma', 'email')
    search_fields = ('nome', 'rm', 'cpf', 'email')


class ProfessorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'area', 'detalhes_regime', 'email')
    search_fields = ('nome', 'cpf', 'email')


class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cargo', 'email')
    search_fields = ('nome', 'cpf', 'email')


class VisitanteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'motivo', 'funcao', 'email')
    search_fields = ('nome', 'cpf', 'email')


admin.site.register(Categoria)
admin.site.register(Produto, ProdutoAdmin)
admin.site.register(Pessoa, PessoaAdmin)
admin.site.register(Aluno, AlunoAdmin)
admin.site.register(Professor, ProfessorAdmin)
admin.site.register(Funcionario, FuncionarioAdmin)
admin.site.register(Visitante, VisitanteAdmin)
admin.site.register(Cartao, CartaoAdmin)
admin.site.register(Venda, VendaAdmin)
admin.site.register(ContaReceber, ContaReceberAdmin)
admin.site.register(Despesa, DespesaAdmin)
