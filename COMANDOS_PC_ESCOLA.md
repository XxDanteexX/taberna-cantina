# Taberna Cantina — Comandos para o PC da escola

**Repositório:** https://github.com/XxDanteexX/taberna-cantina  
**Usuário GitHub:** XxDanteexX

> Esta é a versão colorida do guia. Abra este arquivo no VS Code.
> Para ver formatado, use **Ctrl + Shift + V**.
> O arquivo `.txt` continua disponível, mas arquivos `.txt` não têm cores por padrão.

---

## Como usar

1. No VS Code: **Terminal > New Terminal > Command Prompt**.
2. O prompt deve ser parecido com `C:\Users\...>`.
   Se aparecer `PS C:\...>`, você está no PowerShell. Troque para **Command Prompt**.
3. Copie apenas o conteúdo dos blocos de comando.
4. As linhas `REM` são comentários. Pode copiar junto; o `cmd` ignora.
5. Tenha **Git** e **Python 3.12 ou superior** instalados.

### Resumo

1. Clonar o repositório.
2. Criar a venv, instalar dependências, criar o banco, popular o cardápio, criar o login de desenvolvimento e o superusuário `root`.
3. Rodar o servidor e abrir o link.

---

## Passo 1 — Clonar o repositório

Se pedir login do GitHub, conclua antes de seguir.

```bat
REM Vai para a pasta Downloads
cd /d "%USERPROFILE%\Downloads"

REM Clona o repositório para a pasta taberna-cantina
git clone https://github.com/XxDanteexX/taberna-cantina.git
```

> Se a pasta `taberna-cantina` já existir, apague ou renomeie antes.

---

## Passo 2 — Criar a venv, instalar e preparar o banco

Copie e cole este bloco inteiro de uma vez.  
Ele **não pergunta nome nem senha**.

```bat
REM Entra na pasta do projeto
cd /d "%USERPROFILE%\Downloads\taberna-cantina"

REM Se o manage.py estiver em uma subpasta, entra nela
if not exist manage.py cd taberna-cantina-main

REM Confere se o manage.py está na pasta atual
dir manage.py
if not exist manage.py echo ERRO: manage.py nao encontrado. Ajuste a pasta antes de continuar.

REM Cria a venv (ambiente isolado do projeto)
python -m venv .venv

REM Garante o pip dentro da venv
.venv\Scripts\python.exe -m ensurepip --upgrade

REM Atualiza o pip
.venv\Scripts\python.exe -m pip install --upgrade pip

REM Instala o Django e as demais dependências
.venv\Scripts\python.exe -m pip install -r requirements.txt

REM Cria as tabelas do banco db.sqlite3
.venv\Scripts\python.exe manage.py migrate

REM Cria as 5 categorias e os 39 produtos
.venv\Scripts\python.exe manage.py seed_dados

REM Cria o usuário dev_taberna e imprime o link de login
.venv\Scripts\python.exe manage.py dev_login
```

> **Importante:** copie o link que aparecer. Ele expira em 1 hora.  
> O `dev_login` não pergunta nome nem senha.

---

## Passo 2.1 — Criar o superusuário root

Rode:

```bat
REM Cria o superusuário que você vai usar no site e no /admin/
.venv\Scripts\python.exe manage.py createsuperuser
```

Quando o comando pedir, digite exatamente:

```text
Username: root
Email address: (pressione Enter para deixar vazio)
Password: root1234
Password (again): root1234
```

No final deve aparecer: **Superuser created successfully.**

> **Importante:** `root1234` é uma senha fraca, apenas para o projeto local
> da escola. Não use essa senha em um site publicado na internet.

Se o `root` já existir e você quiser trocar a senha:

```bat
.venv\Scripts\python.exe manage.py changepassword root
```

Digite `root1234` duas vezes.

---

## Passo 3 — Rodar o servidor

Este comando deixa o terminal ocupado. Rode só depois de copiar o link.

```bat
REM Inicia o servidor local
.venv\Scripts\python.exe manage.py runserver
```

Abra no navegador:

```text
http://127.0.0.1:8000/
```

Depois abra o link do `dev_login` que você copiou.

- Para parar o servidor: **Ctrl + C**.
- Admin do Django: `http://127.0.0.1:8000/admin/`
  - **Usuário:** `root`
  - **Senha:** `root1234`
- No login normal do site, use `root` / `root1234` em qualquer aba. O sistema reconhece a equipe administrativa e libera o Painel do dono.

---

## Se o Python não for reconhecido

Troque apenas esta linha do Passo 2:

```bat
python -m venv .venv
```

por:

```bat
py -m venv .venv
```

O restante do Passo 2 continua igual.

> Se o Python abrir a Microsoft Store, instale o Python do site python.org
> e marque a opção **Add python.exe to PATH**.

---

## Se o link expirar

Pare o servidor com **Ctrl + C** e rode:

```bat
REM Gera um novo link de login
.venv\Scripts\python.exe manage.py dev_login
```

Copie o novo link e rode de novo:

```bat
.venv\Scripts\python.exe manage.py runserver
```

---

## Se a porta 8000 estiver ocupada

```bat
REM Usa a porta 8001
.venv\Scripts\python.exe manage.py runserver 8001
```

Abra `http://127.0.0.1:8001/` e troque a porta do link para `8001`.

---

## Se o manage.py não for encontrado

```bat
REM Procura o manage.py dentro da pasta clonada
dir /s /b "%USERPROFILE%\Downloads\taberna-cantina\manage.py"
```

Entre na pasta mostrada e rode o Passo 2 de novo.

Normalmente a pasta correta é:

```text
C:\Users\SEU_USUARIO\Downloads\taberna-cantina
```

---

## Se o Git disser "Repository not found"

- Confirme que você está logado na conta **XxDanteexX**.
- Confirme se a URL está exatamente:
  `https://github.com/XxDanteexX/taberna-cantina.git`
- O repositório é privado; use o navegador ou um token do GitHub.

---

## Conferir se está tudo certo (opcional)

```bat
REM Roda os testes automatizados
.venv\Scripts\python.exe manage.py test
```

O esperado é terminar com **OK** e **48 testes passando**.

---

## Dicas

- Use o superusuário `root` (senha `root1234`) para entrar no `/admin/` e no Painel do dono.
- O `dev_login` também cria o usuário `dev_taberna`, mas o `root` é o seu usuário principal.
- Se o seed disser `0 criados` e `39 já existentes`, está correto.
- As fotos dos produtos ficam em `Taberna/static/produtos/` e aparecem como miniaturas ao lado do nome; para trocar, edite o campo `Imagem` do produto no `/admin/` ou substitua o arquivo.
- Para testar cartão, use `4242 4242 4242 4242`.
- Em `DEBUG=True`, qualquer número de 13 a 19 dígitos também é aceito.
- A pasta `.venv` e o arquivo `db.sqlite3` não vão para o GitHub.
- Eles ficam dentro da pasta do projeto e são recriados no PC da escola.
- Se o terminal for PowerShell, use `.\.venv\Scripts\python.exe` ou troque para **Command Prompt**.

---

## Para enviar alterações para o GitHub

Depois de editar o projeto, rode na pasta do projeto:

```bat
REM Adiciona todas as alterações
git add .

REM Cria o commit com uma descrição
git commit -m "Descrição da alteração"

REM Envia para o GitHub
git push
```

> Se o Git pedir login, conclua antes.  
> A pasta local já está conectada ao repositório.  
> Se não houver alterações, o Git pode responder `nothing to commit`.  
> O `db.sqlite3` e a pasta `.venv` continuam fora do Git.

---

## No final da aula

1. Pare o servidor com **Ctrl + C**.
2. Feche o VS Code.
3. Exclua a pasta `taberna-cantina` de Downloads, se quiser.

> Se quiser guardar os dados de teste, copie o arquivo `db.sqlite3`
> para outro lugar antes de excluir a pasta.
