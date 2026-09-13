from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, timedelta
from .models import (
    Categoria, Produto, Aluno, Professor, Funcionario, 
    Visitante, Venda, ItemVenda, Pessoa, ContaReceber, Cartao
)


# Helper para verificar o perfil do usuário logado
def obter_perfil_usuario(user):
    user_email = user.email
    if hasattr(user, 'aluno') or Aluno.objects.filter(email=user_email).exists():
        return "Aluno"
    elif hasattr(user, 'professor') or Professor.objects.filter(email=user_email).exists():
        return "Professor"
    elif hasattr(user, 'funcionario') or Funcionario.objects.filter(email=user_email).exists():
        return "Funcionário"
    elif hasattr(user, 'visitante') or Visitante.objects.filter(email=user_email).exists():
        return "Visitante"
    return "Aluno"


def login_view(request):
    if request.user.is_authenticated:
        return redirect('cardapio')

    if request.method == 'POST':
        identificador = request.POST.get('identificador', '').strip()
        senha_input = request.POST.get('password')
        lembrar = request.POST.get('remember_me')
        tipo_perfil = request.POST.get('tipo_perfil')

        usuario_encontrado = None

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

        if not usuario_encontrado:
            user_by_email = User.objects.filter(email=identificador).first()
            usuario_encontrado = user_by_email.username if user_by_email else identificador

        user = authenticate(request, username=usuario_encontrado, password=senha_input)

        if user is not None:
            auth_login(request, user)
            if lembrar:
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)
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
    perfil = obter_perfil_usuario(request.user)

    # Processa os itens do carrinho armazenados na sessão
    carrinho_session = request.session.get('carrinho', {})
    itens_carrinho = []
    total_carrinho = 0

    for prod_id, qtd in carrinho_session.items():
        prod = Produto.objects.filter(id=prod_id).first()
        if prod:
            subtotal = prod.preco * qtd
            total_carrinho += subtotal
            itens_carrinho.append({
                'produto': prod,
                'quantidade': qtd,
                'subtotal': subtotal
            })

    # Regras e cartões do usuário logado
    pode_fiado = perfil in ["Professor", "Funcionário"]
    pessoa = Pessoa.objects.filter(usuario=request.user).first() or Pessoa.objects.first()
    cartoes = Cartao.objects.filter(pessoa=pessoa) if pessoa else []
    qtd_total_carrinho = sum(carrinho_session.values())

    return render(request, 'cardapio.html', {
        'categorias': categorias,
        'produtos': produtos,
        'perfil': perfil,
        'itens_carrinho': itens_carrinho,
        'total_carrinho': total_carrinho,
        'pode_fiado': pode_fiado,
        'cartoes': cartoes,
        'qtd_total_carrinho': qtd_total_carrinho,
    })


@login_required(login_url='login')
def ver_carrinho(request):
    """Tela dedicada exclusivamente para visualização do Carrinho e Checkout."""
    carrinho_session = request.session.get('carrinho', {})
    itens_carrinho = []
    total_carrinho = 0

    for prod_id, qtd in carrinho_session.items():
        prod = Produto.objects.filter(id=prod_id).first()
        if prod:
            subtotal = prod.preco * qtd
            total_carrinho += subtotal
            itens_carrinho.append({
                'produto': prod,
                'quantidade': qtd,
                'subtotal': subtotal
            })

    perfil = obter_perfil_usuario(request.user)
    pode_fiado = perfil in ["Professor", "Funcionário"]

    return render(request, 'carrinho.html', {
        'itens_carrinho': itens_carrinho,
        'total_carrinho': total_carrinho,
        'perfil': perfil,
        'pode_fiado': pode_fiado,
    })


@login_required(login_url='login')
def adicionar_ao_carrinho(request, produto_id):
    carrinho = request.session.get('carrinho', {})
    str_id = str(produto_id)
    carrinho[str_id] = carrinho.get(str_id, 0) + 1
    request.session['carrinho'] = carrinho
    request.session.modified = True  # Força o salvamento das alterações na sessão
    messages.success(request, "Item adicionado ao carrinho!")
    return redirect('cardapio')


@login_required(login_url='login')
def remover_do_carrinho(request, produto_id):
    """Remove totalmente um item específico do carrinho."""
    carrinho = request.session.get('carrinho', {})
    str_id = str(produto_id)
    if str_id in carrinho:
        del carrinho[str_id]
        request.session['carrinho'] = carrinho
        request.session.modified = True
        messages.info(request, "Item removido do carrinho.")
    return redirect('ver_carrinho')


@login_required(login_url='login')
def limpar_carrinho(request):
    if 'carrinho' in request.session:
        del request.session['carrinho']
        request.session.modified = True
    messages.info(request, "Carrinho limpo.")
    return redirect('cardapio')


@login_required(login_url='login')
def finalizar_compra(request):
    if request.method == 'POST':
        carrinho = request.session.get('carrinho', {})
        if not carrinho:
            messages.error(request, "Seu carrinho está vazio.")
            return redirect('cardapio')

        forma_pagamento = request.POST.get('forma_pagamento')
        pessoa = Pessoa.objects.filter(usuario=request.user).first() or Pessoa.objects.first()

        # Validação do cartão cadastrado caso a opção seja CARTAO_SALVO
        if forma_pagamento == 'CARTAO_SALVO':
            cartoes_usuario = Cartao.objects.filter(pessoa=pessoa)
            if not cartoes_usuario.exists():
                messages.warning(
                    request, 
                    "Você selecionou a opção Cartão Cadastrado, mas ainda não possui nenhum cartão cadastrado. Por favor, cadastre um cartão primeiro."
                )
                return redirect('cadastrar_cartao')

        total = 0
        itens_para_criar = []

        # Validação de Estoque
        for prod_id, qtd in carrinho.items():
            prod = get_object_or_404(Produto, id=prod_id)
            if prod.quantidade < qtd:
                messages.error(request, f"Estoque insuficiente para {prod.nome}.")
                return redirect('cardapio')
            total += prod.preco * qtd
            itens_para_criar.append((prod, qtd))

        # Registro da Venda
        venda = Venda.objects.create(
            pessoa=pessoa,
            total=total,
            forma_pagamento=forma_pagamento
        )

        for prod, qtd in itens_para_criar:
            ItemVenda.objects.create(
                venda=venda,
                produto=prod,
                quantidade=qtd,
                preco_unitario=prod.preco
            )
            prod.quantidade -= qtd
            prod.save()

        # Prazo Estendido / Conta a Receber (FIADO)
        if forma_pagamento == 'FIADO':
            ContaReceber.objects.create(
                venda=venda,
                data_vencimento=date.today() + timedelta(days=30),
                pago=False
            )

        del request.session['carrinho']
        request.session.modified = True
        messages.success(request, "Compra finalizada com sucesso!")

    return redirect('cardapio')


@login_required(login_url='login')
def cadastrar_cartao(request):
    pessoa = Pessoa.objects.filter(usuario=request.user).first() or Pessoa.objects.first()
    
    if request.method == 'POST':
        nome_titular = request.POST.get('nome_titular')
        numero = request.POST.get('numero', '').replace(' ', '')
        validade = request.POST.get('validade')
        tipo = request.POST.get('tipo')
        
        ultimos_digitos = numero[-4:] if len(numero) >= 4 else '0000'
        numero_mascarado = f"**** **** **** {ultimos_digitos}"

        Cartao.objects.create(
            pessoa=pessoa,
            nome_titular=nome_titular,
            numero_mascarado=numero_mascarado,
            validade=validade,
            tipo=tipo
        )
        messages.success(request, "Cartão cadastrado com sucesso!")
        return redirect('cadastrar_cartao')

    cartoes = Cartao.objects.filter(pessoa=pessoa) if pessoa else []
    return render(request, 'cadastrar_cartao.html', {'cartoes': cartoes})