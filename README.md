# Taberna — Gerenciamento de Cantina

Sistema Django para cardápio, carrinho, checkout, estoque, fiado e cadastro de
cartões mascarados.

## Requisitos

- Python 3.12 ou superior
- Dependências em `requirements.txt` (Django 6.1.1)

## Desenvolvimento

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Com `DJANGO_DEBUG` ausente, o projeto usa `DEBUG=True` e uma chave de
desenvolvimento local. Nenhuma variável é obrigatória para rodar localmente.

Acesse `/admin/` para cadastrar categorias, produtos e pessoas. Para que um
usuário consiga comprar, ele precisa estar vinculado a uma `Pessoa`
(`Aluno`, `Professor`, `Funcionário` ou `Visitante`).

### Painel do dono

O painel administrativo da cantina fica em `/painel-dono/` e reúne:

- receita, quantidade de vendas, itens vendidos, gastos e ticket médio;
- gráfico mensal de receita, gastos e itens vendidos, com filtro por ano;
- vendas recentes;
- cadastro e histórico de gastos;
- estoque completo, com destaque para produtos esgotados ou com estoque baixo.

O painel é restrito a usuários com `is_staff` ou `is_superuser` e não aparece
nas abas de login. Para liberar o acesso, crie um superusuário com
`python manage.py createsuperuser` (ou use o login de desenvolvimento). Um
usuário comum que tente abrir a URL recebe uma resposta 403.

### Dados iniciais

Para criar as categorias e os produtos de exemplo:

```bash
python manage.py seed_dados
```

O comando é idempotente: pode ser executado novamente sem duplicar categorias
ou produtos. Ele não sobrescreve preços/estoques de produtos já existentes.

Cada produto recebe uma imagem ilustrativa em `Taberna/static/produtos/`, e o
caminho fica no campo `Produto.imagem`. As imagens atuais são JPEG 640x480 e
aparecem como miniaturas compactas ao lado do nome do produto, para orientar a
escolha sem ocupar o card inteiro. Para trocar uma foto, edite o campo no admin
ou substitua o arquivo correspondente. As imagens são ilustrativas e podem ser
substituídas por fotos próprias antes de publicar o projeto.

### Login de desenvolvimento

Para entrar sem preencher cadastro de pessoa:

```bash
python manage.py dev_login
```

O comando cria (ou reutiliza) o usuário `dev_taberna`, superusuário com perfil
Professor, e imprime um link de login assinado. Basta abrir o link no navegador.
O link expira em 1 hora por padrão (`DJANGO_DEV_LOGIN_MAX_AGE`).

Esse login funciona **somente com `DJANGO_DEBUG=True`**. Com `DEBUG=False`, a
rota responde 404 e o comando recusa a execução. Nunca habilite em produção.

## Produção

Defina, no mínimo:

- `DJANGO_DEBUG=False`
- `DJANGO_SECRET_KEY` (obrigatória; o processo não inicia sem ela)
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS` quando aplicável

Com `DEBUG=False`, o projeto habilita redirecionamento HTTPS, cookies seguros e
HSTS por padrão. Rode `python manage.py check --deploy`, `migrate` e
`collectstatic`. Veja `.env.example`.

## Testes

```bash
python manage.py test
```

## Decisões de segurança e integridade

- O checkout é transacional e revalida o estoque com bloqueio de linha.
- Fiado é autorizado no servidor apenas para Professor e Funcionário.
- Cartões salvam somente os quatro últimos dígitos, com validação de Luhn e
  validade. Em `DEBUG=True`, números sem Luhn válido também são aceitos, com
  aviso, para facilitar testes; em produção a validação é obrigatória.
- Vendas são somente leitura no admin para evitar divergência entre total e
  estoque; eventuais correções exigem um fluxo administrativo planejado.
- Excluir pessoas com vendas é bloqueado (`PROTECT`), preservando o histórico.
- O login tem limite de tentativas por IP/identificador (cache local).
