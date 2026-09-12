from django.contrib import admin
from .models import Categoria, Produto, Aluno, Professor, Funcionario, Visitante

class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'quantidade', 'categoria', 'mais_vendido')
    list_editable = ('mais_vendido',) # Permite marcar/desmarcar direto na lista!

admin.site.register(Categoria)
admin.site.register(Produto, ProdutoAdmin)
admin.site.register(Aluno)
admin.site.register(Professor)
admin.site.register(Funcionario)
admin.site.register(Visitante)