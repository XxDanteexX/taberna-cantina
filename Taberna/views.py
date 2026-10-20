import hashlib
import re
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F, Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .dev_login import DEV_LOGIN_SALT, DEV_USERNAME

from .models import (
    Aluno,
    Cartao,
    Categoria,
    ContaReceber,
    Funcionario,
    ItemVenda,
    Professor,
    Produto,
    Venda,
    Visitante,
)

MAX_TENTATIVAS_LOGIN = 5
BLOQUEIO_LOGIN_SEGUNDOS = 5 * 60
TIPOS_PERFIL = {'aluno', 'professor', 'funcionario', 'visitante'}


class EstoqueInsuficiente(Exception):
    """Usada para desfazer a transação de checkout quando o estoque muda."""


# ---------------------------------------------------------------------------
# Helpers de perfil / pessoa
# ---------------------------------------------------------------------------

def obter_pessoa(user):
    """Retorna a Pessoa vinculada ao usuário, sem fallback para outra pessoa."""
    if not getattr(user, 'is_authenticated', False):
        return None
    try:
        return user.pessoa
    except ObjectDoesNotExist:
        return None


def obter_perfil_usuario(user):
    pessoa = obter_pessoa(user)
    if pessoa is None:
        return 'Usuário'

    for atributo, rotulo in (
        ('aluno', 'Aluno'),
        ('professor', 'Professor'),
        ('funcionario', 'Funcionário'),
        ('visitante', 'Visitante'),
    ):
        try:
            getattr(pessoa, atributo)
        except ObjectDoesNotExist:
            continue
        return rotulo

    return 'Pessoa'


def _somente_digitos(valor):
    return re.sub(r'\D', '', valor or '')


def _cpfs_busca(identificador):
    identificador = (identificador or '').strip()
    valores = {identificador}
    digitos = _somente_digitos(identificador)
    if len(digitos) == 11:
        valores.add(f'{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}')
    valores.discard('')
    return list(valores)


def _buscar_usuario_por_perfil(tipo_perfil, identificador):
    """Busca o usuário apenas no subtipo de pessoa escolhido na tela."""
    if tipo_perfil == 'aluno':
        aluno = Aluno.objects.filter(
            Q(rm__iexact=identificador) | Q(cpf__in=_cpfs_busca(identificador))
        ).first()
        return aluno.usuario if aluno and aluno.usuario else None

    if tipo_perfil == 'professor':
        professor = Professor.objects.filter(cpf__in=_cpfs_busca(identificador)).first()
        return professor.usuario if professor and professor.usuario else None

    if tipo_perfil == 'funcionario':
        funcionario = Funcionario.objects.filter(cpf__in=_cpfs_busca(identificador)).first()
        return funcionario.usuario if funcionario and funcionario.usuario else None

    if tipo_perfil == 'visitante':
        visitante = Visitante.objects.filter(email__iexact=identificador).first()
        return visitante.usuario if visitante and visitante.usuario else None

    return None


def _render_login(request, tipo_perfil):
    return render(request, 'login.html', {'tipo_perfil_selecionado': tipo_perfil})


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect('cardapio')

    tipo_selecionado = 'aluno'

    if request.method == 'POST':
        identificador = (request.POST.get('identificador') or '').strip()
        senha = request.POST.get('password') or ''
        lembrar = request.POST.get('remember_me')
        tipo_perfil = (request.POST.get('tipo_perfil') or '').strip()
        tipo_selecionado = tipo_perfil or 'aluno'

        if tipo_perfil not in TIPOS_PERFIL:
            messages.error(request, 'Selecione um perfil válido.')
            return _render_login(request, tipo_selecionado)

        if not identificador or not senha:
            messages.error(request, 'Informe o identificador e a senha.')
            return _render_login(request, tipo_selecionado)

        ip = request.META.get('REMOTE_ADDR') or 'desconhecido'
        hash_identificador = hashlib.sha256(
            identificador.lower().encode('utf-8')
        ).hexdigest()[:32]
        chave_tentativas = f'login:{ip}:{tipo_perfil}:{hash_identificador}'
        tentativas = cache.get(chave_tentativas, 0)

        if tentativas >= MAX_TENTATIVAS_LOGIN:
            messages.error(
                request,
                'Muitas tentativas de login. Aguarde alguns minutos e tente novamente.',
            )
            return _render_login(request, tipo_selecionado)

        usuario = _buscar_usuario_por_perfil(tipo_perfil, identificador)

        # A aba Visitante aceita qualquer usuário cadastrado com esse e-mail.
        if usuario is None and tipo_perfil == 'visitante':
            usuario = User.objects.filter(email__iexact=identificador).first()

        # Equipe administrativa pode entrar por usuário/e-mail, independente do vínculo.
        if usuario is None:
            usuario = User.objects.filter(
                Q(username__iexact=identificador) | Q(email__iexact=identificador),
                is_staff=True,
            ).first()

        user = None
        if usuario is not None:
            user = authenticate(
                request,
                username=usuario.username,
                password=senha,
            )

        if user is None:
            cache.set(
                chave_tentativas,
                tentativas + 1,
                BLOQUEIO_LOGIN_SEGUNDOS,
            )
            messages.error(
                request,
                'Credenciais inválidas para o perfil selecionado.',
            )
        else:
            cache.delete(chave_tentativas)
            auth_login(request, user)
            if lembrar:
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)
            return redirect('cardapio')

    return _render_login(request, tipo_selecionado)


@login_required(login_url='login')
@require_POST
def logout_view(request):
    auth_logout(request)
    return redirect('login')


@require_GET
def dev_login(request, token):
    """Login local por link assinado; desativado quando DEBUG=False."""
    if not settings.DEBUG:
        raise Http404

    try:
        usuario_id = signing.loads(
            token,
            salt=DEV_LOGIN_SALT,
            max_age=settings.DEV_LOGIN_MAX_AGE,
        )
        usuario = User.objects.get(
            pk=usuario_id,
            username=DEV_USERNAME,
            is_active=True,
        )
    except (signing.BadSignature, User.DoesNotExist, TypeError, ValueError):
        messages.error(
            request,
            'Link de desenvolvimento inválido ou expirado. '
            'Gere outro com "python manage.py dev_login".',
        )
        return redirect('login')

    auth_login(
        request,
        usuario,
        backend='django.contrib.auth.backends.ModelBackend',
    )
    messages.success(
        request,
        'Login de desenvolvimento ativado. Você está como superusuário de teste.',
    )
    return redirect('cardapio')


# ---------------------------------------------------------------------------
# Helpers do carrinho
# ---------------------------------------------------------------------------

def _ler_carrinho(request):
    carrinho = request.session.get('carrinho', {})
    return dict(carrinho) if isinstance(carrinho, dict) else {}


def obter_dados_carrinho(request):
    """Monta os itens válidos e remove da sessão entradas inválidas/obsoletas."""
    carrinho = _ler_carrinho(request)
    itens_brutos = []
    chaves_invalidas = set()

    for chave, valor in carrinho.items():
        try:
            produto_id = int(chave)
            quantidade = int(valor)
        except (TypeError, ValueError):
            chaves_invalidas.add(str(chave))
            continue
        if quantidade <= 0:
            chaves_invalidas.add(str(chave))
            continue
        itens_brutos.append((produto_id, quantidade))

    ids = [produto_id for produto_id, _ in itens_brutos]
    produtos = {
        produto.id: produto
        for produto in Produto.objects.filter(id__in=ids)
    }

    itens = []
    total = Decimal('0.00')
    ausentes = set()

    for produto_id, quantidade in itens_brutos:
        produto = produtos.get(produto_id)
        if produto is None:
            ausentes.add(produto_id)
            continue
        subtotal = produto.preco * quantidade
        total += subtotal
        itens.append({
            'produto': produto,
            'quantidade': quantidade,
            'subtotal': subtotal,
        })

    chaves_remover = chaves_invalidas | {str(produto_id) for produto_id in ausentes}
    if chaves_remover:
        for chave in chaves_remover:
            carrinho.pop(chave, None)
        request.session['carrinho'] = carrinho
        request.session.modified = True

    quantidade_total = sum(item['quantidade'] for item in itens)
    return itens, total, quantidade_total


# ---------------------------------------------------------------------------
# Cardápio / carrinho
# ---------------------------------------------------------------------------

@login_required(login_url='login')
def cardapio(request):
    categorias = Categoria.objects.all()
    produtos = Produto.objects.select_related('categoria').all()
    perfil = obter_perfil_usuario(request.user)
    pessoa = obter_pessoa(request.user)
    cartoes = Cartao.objects.filter(pessoa=pessoa) if pessoa else Cartao.objects.none()

    itens_carrinho, total_carrinho, qtd_total_carrinho = obter_dados_carrinho(request)

    return render(request, 'cardapio.html', {
        'categorias': categorias,
        'produtos': produtos,
        'perfil': perfil,
        'itens_carrinho': itens_carrinho,
        'total_carrinho': total_carrinho,
        'pode_fiado': perfil in ['Professor', 'Funcionário'],
        'cartoes': cartoes,
        'qtd_total_carrinho': qtd_total_carrinho,
    })


@login_required(login_url='login')
def ver_carrinho(request):
    """Tela dedicada exclusivamente para visualização do Carrinho e Checkout."""
    itens_carrinho, total_carrinho, qtd_total_carrinho = obter_dados_carrinho(request)
    perfil = obter_perfil_usuario(request.user)
    pessoa = obter_pessoa(request.user)
    cartoes = Cartao.objects.filter(pessoa=pessoa) if pessoa else Cartao.objects.none()

    return render(request, 'carrinho.html', {
        'itens_carrinho': itens_carrinho,
        'total_carrinho': total_carrinho,
        'qtd_total_carrinho': qtd_total_carrinho,
        'perfil': perfil,
        'pode_fiado': perfil in ['Professor', 'Funcionário'],
        'cartoes': cartoes,
    })


@login_required(login_url='login')
@require_POST
def adicionar_ao_carrinho(request, produto_id):
    produto = Produto.objects.filter(pk=produto_id).first()
    if produto is None:
        messages.error(request, 'Produto não encontrado.')
        return redirect('cardapio')

    carrinho = _ler_carrinho(request)
    chave = str(produto.id)

    try:
        quantidade_atual = int(carrinho.get(chave, 0))
    except (TypeError, ValueError):
        quantidade_atual = 0

    if produto.quantidade <= 0:
        messages.error(request, f'{produto.nome} está esgotado.')
        return redirect('cardapio')

    if quantidade_atual >= produto.quantidade:
        messages.warning(
            request,
            f'Quantidade máxima em estoque para {produto.nome} já está no carrinho.',
        )
        return redirect('cardapio')

    carrinho[chave] = quantidade_atual + 1
    request.session['carrinho'] = carrinho
    request.session.modified = True
    messages.success(request, 'Item adicionado ao carrinho!')
    return redirect('cardapio')


@login_required(login_url='login')
@require_POST
def remover_do_carrinho(request, produto_id):
    """Remove totalmente um item específico do carrinho."""
    carrinho = _ler_carrinho(request)
    if carrinho.pop(str(produto_id), None) is not None:
        if carrinho:
            request.session['carrinho'] = carrinho
        else:
            request.session.pop('carrinho', None)
        request.session.modified = True
        messages.info(request, 'Item removido do carrinho.')
    return redirect('ver_carrinho')


@login_required(login_url='login')
@require_POST
def limpar_carrinho(request):
    request.session.pop('carrinho', None)
    request.session.modified = True
    messages.info(request, 'Carrinho limpo.')
    if request.POST.get('origem') == 'carrinho':
        return redirect('ver_carrinho')
    return redirect('cardapio')


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

@login_required(login_url='login')
@require_POST
def finalizar_compra(request):
    itens, _, _ = obter_dados_carrinho(request)
    if not itens:
        messages.error(request, 'Seu carrinho está vazio.')
        return redirect('cardapio')

    forma_pagamento = (request.POST.get('forma_pagamento') or '').strip()
    if forma_pagamento not in dict(Venda.FORMA_PAGAMENTO_CHOICES):
        messages.error(request, 'Selecione uma forma de pagamento válida.')
        return redirect('ver_carrinho')

    pessoa = obter_pessoa(request.user)
    if pessoa is None:
        messages.error(
            request,
            'Seu usuário não está vinculado a uma pessoa. Procure a administração da cantina.',
        )
        return redirect('cardapio')

    perfil = obter_perfil_usuario(request.user)
    if forma_pagamento == 'FIADO' and perfil not in ('Professor', 'Funcionário'):
        messages.error(request, 'Seu perfil não tem permissão para comprar fiado.')
        return redirect('ver_carrinho')

    cartao = None
    if forma_pagamento == 'CARTAO_SALVO':
        try:
            cartao_id = int(request.POST.get('cartao_id', ''))
        except (TypeError, ValueError):
            cartao_id = None

        cartao = (
            Cartao.objects.filter(pk=cartao_id, pessoa=pessoa).first()
            if cartao_id
            else None
        )
        if cartao is None:
            messages.error(
                request,
                'Selecione um cartão cadastrado válido ou cadastre um novo cartão.',
            )
            return redirect('cadastrar_cartao')

    try:
        with transaction.atomic():
            ids = [item['produto'].id for item in itens]
            produtos_bloqueados = {
                produto.id: produto
                for produto in Produto.objects.select_for_update()
                .filter(id__in=ids)
                .order_by('id')
            }

            for item in itens:
                produto = produtos_bloqueados.get(item['produto'].id)
                if produto is None:
                    raise EstoqueInsuficiente(
                        f'O produto {item["produto"].nome} não está mais disponível.'
                    )
                if produto.quantidade < item['quantidade']:
                    raise EstoqueInsuficiente(
                        f'Estoque insuficiente para {produto.nome}. '
                        f'Disponível: {produto.quantidade}.'
                    )

            total = sum(
                (
                    produtos_bloqueados[item['produto'].id].preco * item['quantidade']
                    for item in itens
                ),
                Decimal('0.00'),
            )

            venda = Venda.objects.create(
                pessoa=pessoa,
                cartao=cartao,
                total=total,
                forma_pagamento=forma_pagamento,
            )

            for item in itens:
                produto = produtos_bloqueados[item['produto'].id]
                ItemVenda.objects.create(
                    venda=venda,
                    produto=produto,
                    quantidade=item['quantidade'],
                    preco_unitario=produto.preco,
                )
                atualizados = Produto.objects.filter(
                    pk=produto.pk,
                    quantidade__gte=item['quantidade'],
                ).update(quantidade=F('quantidade') - item['quantidade'])
                if not atualizados:
                    raise EstoqueInsuficiente(
                        f'Estoque insuficiente para {produto.nome}.'
                    )

            if forma_pagamento == 'FIADO':
                ContaReceber.objects.create(
                    venda=venda,
                    data_vencimento=timezone.localdate() + timedelta(days=30),
                    pago=False,
                )
    except EstoqueInsuficiente as exc:
        messages.error(request, str(exc))
        return redirect('ver_carrinho')

    request.session.pop('carrinho', None)
    request.session.modified = True
    messages.success(request, 'Compra finalizada com sucesso!')
    return redirect('cardapio')


# ---------------------------------------------------------------------------
# Cartões
# ---------------------------------------------------------------------------

def _luhn(numero):
    if not numero or not numero.isdigit():
        return False
    if len(set(numero)) == 1:
        return False
    soma = 0
    for indice, caractere in enumerate(reversed(numero)):
        digito = int(caractere)
        if indice % 2 == 1:
            digito *= 2
            if digito > 9:
                digito -= 9
        soma += digito
    return soma % 10 == 0


def _validade_valida(validade):
    match = re.fullmatch(r'(0[1-9]|1[0-2])/(\d{2})', validade or '')
    if not match:
        return False
    mes = int(match.group(1))
    ano = 2000 + int(match.group(2))
    hoje = timezone.localdate()
    return (ano, mes) >= (hoje.year, hoje.month)


def _detectar_bandeira(numero):
    if numero[:2] in {'34', '37'}:
        return 'American Express'
    if numero[:2] in {'51', '52', '53', '54', '55'}:
        return 'Mastercard'
    if len(numero) >= 4 and 2221 <= int(numero[:4]) <= 2720:
        return 'Mastercard'
    if numero[:4] in {'4011', '4312', '4389', '4514', '4573', '6362', '6363'}:
        return 'Elo'
    if numero.startswith('4'):
        return 'Visa'
    return 'Outra'


@login_required(login_url='login')
def cadastrar_cartao(request):
    pessoa = obter_pessoa(request.user)
    if pessoa is None:
        messages.error(
            request,
            'Seu usuário não está vinculado a uma pessoa. Procure a administração da cantina.',
        )
        return redirect('cardapio')

    if request.method == 'POST':
        nome_titular = (request.POST.get('nome_titular') or '').strip()
        numero = _somente_digitos(request.POST.get('numero'))
        validade = (request.POST.get('validade') or '').strip()
        tipo = (request.POST.get('tipo') or '').strip()

        erros = []

        if not nome_titular:
            erros.append('Informe o nome impresso no cartão.')
        elif len(nome_titular) > 100:
            erros.append('O nome do titular deve ter no máximo 100 caracteres.')

        if not 13 <= len(numero) <= 19:
            erros.append('O número do cartão deve ter entre 13 e 19 dígitos.')
        elif not _luhn(numero) and not settings.DEBUG:
            erros.append(
                'Número de cartão inválido (dígito verificador). '
                'Para testes, use 4242 4242 4242 4242 ou 5555 5555 5555 4444.'
            )

        if not _validade_valida(validade):
            erros.append('Validade inválida. Use o formato MM/AA e uma data futura.')

        if tipo not in dict(Cartao.TIPOS):
            erros.append('Selecione um tipo de cartão válido.')

        if erros:
            for erro in erros:
                messages.error(request, erro)
            return redirect('cadastrar_cartao')

        ultimos_digitos = numero[-4:]
        numero_mascarado = f'**** **** **** {ultimos_digitos}'

        if Cartao.objects.filter(
            pessoa=pessoa,
            numero_mascarado=numero_mascarado,
            validade=validade,
            tipo=tipo,
        ).exists():
            messages.warning(request, 'Este cartão já está cadastrado.')
            return redirect('cadastrar_cartao')

        Cartao.objects.create(
            pessoa=pessoa,
            nome_titular=nome_titular,
            numero_mascarado=numero_mascarado,
            bandeira=_detectar_bandeira(numero),
            validade=validade,
            tipo=tipo,
        )
        if not _luhn(numero) and settings.DEBUG:
            messages.warning(
                request,
                'Número de cartão sem dígito verificador válido aceito apenas '
                'porque DEBUG=True. Em produção ele seria rejeitado.',
            )
        messages.success(request, 'Cartão cadastrado com sucesso!')
        return redirect('cadastrar_cartao')

    _, _, qtd_total_carrinho = obter_dados_carrinho(request)
    cartoes = Cartao.objects.filter(pessoa=pessoa)
    return render(request, 'cadastrar_cartao.html', {
        'cartoes': cartoes,
        'perfil': obter_perfil_usuario(request.user),
        'qtd_total_carrinho': qtd_total_carrinho,
        'modo_debug': settings.DEBUG,
    })
