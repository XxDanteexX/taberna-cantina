"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView
from Taberna.views import (
    cardapio, 
    login_view, 
    logout_view, 
    ver_carrinho,
    adicionar_ao_carrinho, 
    remover_do_carrinho,
    limpar_carrinho, 
    finalizar_compra,
    cadastrar_cartao
)

admin.site.site_url = '/cardapio/'

urlpatterns = [
    path('', RedirectView.as_view(url='/login/')),
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('cardapio/', cardapio, name='cardapio'),
    path('carrinho/', ver_carrinho, name='ver_carrinho'),
    path('carrinho/adicionar/<int:produto_id>/', adicionar_ao_carrinho, name='adicionar_ao_carrinho'),
    path('carrinho/remover/<int:produto_id>/', remover_do_carrinho, name='remover_do_carrinho'),
    path('carrinho/limpar/', limpar_carrinho, name='limpar_carrinho'),
    path('carrinho/finalizar/', finalizar_compra, name='finalizar_compra'),
    path('cartoes/', cadastrar_cartao, name='cadastrar_cartao'),
]