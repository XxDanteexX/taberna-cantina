from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Categoria, Produto, Aluno, Professor, Funcionario, Visitante


def login_view(request):
    if request.user.is_authenticated:
        return redirect('cardapio')

    if request.method == 'POST':
        identificador = request.POST.get('identificador', '').strip()
        senha_input = request.POST.get('password')
        lembrar = request.POST.get('remember_me')
        tipo_perfil = request.POST.get('tipo_perfil')

        usuario_encontrado = None

        # 1. Busca por Perfil Específico
        if tipo_perfil == 'aluno':
            aluno = Aluno.objects.filter(rm=identificador).first() or Aluno.objects.filter(cpf=identificador).first()
            if aluno and aluno.usuario:
                usuario_encontrado = aluno.usuario.username

        elif tipo_perfil == 'professor':
            prof = Professor.objects.filter(cpf=identificador).first()
            if prof and prof.usuario:
                usuario_encontrado = prof.usuario.username

        elif tipo_perfil == 'funcionario':
            func = Funcionario.objects.filter(cpf=identificador).first()
            if func and func.usuario:
                usuario_encontrado = func.usuario.username

        # 2. Se não achou por perfil/RM/CPF, tenta direto por email ou username
        if not usuario_encontrado:
            user_by_email = User.objects.filter(email=identificador).first()
            usuario_encontrado = user_by_email.username if user_by_email else identificador

        # 3. Autenticação final da senha com o Django
        user = authenticate(request, username=usuario_encontrado, password=senha_input)

        if user is not None:
            auth_login(request, user)
            if lembrar:
                request.session.set_expiry(60 * 60 * 24 * 30)  # Mantém por 30 dias
            else:
                request.session.set_expiry(0)  # Expira ao fechar o navegador
            return redirect('cardapio')
        else:
            messages.error(request, 'Credenciais inválidas para o perfil selecionado.')

    return render(request, 'login.html')


def logout_view(request):
    auth_logout(request)
    return redirect('login')


@login_required(login_url='login')
def cardapio(request):
    categorias = Categoria.objects.all()
    produtos = Produto.objects.all()
    
    perfil = "Usuário"
    user_email = request.user.email
    user_nome = request.user.get_full_name() or request.user.username

    # Identificação do perfil para renderizar na tela
    if hasattr(request.user, 'aluno') or Aluno.objects.filter(email=user_email).exists() or Aluno.objects.filter(nome__iexact=user_nome).exists():
        perfil = "Aluno"
    elif hasattr(request.user, 'professor') or Professor.objects.filter(email=user_email).exists() or Professor.objects.filter(nome__iexact=user_nome).exists():
        perfil = "Professor"
    elif hasattr(request.user, 'funcionario') or Funcionario.objects.filter(email=user_email).exists() or Funcionario.objects.filter(nome__iexact=user_nome).exists():
        perfil = "Funcionário"
    elif hasattr(request.user, 'visitante') or Visitante.objects.filter(email=user_email).exists():
        perfil = "Visitante"
    elif request.user.is_staff:
        perfil = "Administrador"

    return render(request, 'cardapio.html', {
        'categorias': categorias,
        'produtos': produtos,
        'perfil': perfil,
    })