from django.contrib import admin
from .models import Categoria, Produto, Aluno, Professor, Funcionario, Visitante, Venda, ItemVenda, ContaReceber

class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'quantidade', 'categoria', 'mais_vendido')
    list_editable = ('mais_vendido',) # Permite marcar/desmarcar direto na lista!

class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 1

class VendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'pessoa', 'data_venda', 'total', 'forma_pagamento')
    inlines = [ItemVendaInline]

class ContaReceberAdmin(admin.ModelAdmin):
    list_display = ('id', 'venda', 'data_vencimento', 'pago')
    list_editable = ('pago',)

admin.site.register(Categoria)
admin.site.register(Produto, ProdutoAdmin)
admin.site.register(Aluno)
admin.site.register(Professor)
admin.site.register(Funcionario)
admin.site.register(Visitante)
admin.site.register(Venda, VendaAdmin)
admin.site.register(ContaReceber, ContaReceberAdmin)