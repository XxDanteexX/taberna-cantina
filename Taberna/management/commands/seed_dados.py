from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from Taberna.models import Categoria, Produto


CATEGORIAS = [
    {
        'nome': 'Refrigerantes',
        'descricao': 'Refrigerantes em lata e garrafa, servidos gelados.',
        'produtos': [
            ('Coca-Cola Lata 350ml', '6.00', 48, 'Refrigerante Coca-Cola em lata de 350ml.', True),
            ('Coca-Cola Zero Lata 350ml', '6.00', 36, 'Refrigerante Coca-Cola Zero em lata de 350ml.', False),
            ('Guaraná Antarctica Lata 350ml', '5.50', 40, 'Refrigerante Guaraná Antarctica em lata de 350ml.', False),
            ('Fanta Laranja Lata 350ml', '5.50', 30, 'Refrigerante Fanta sabor laranja em lata de 350ml.', False),
            ('Sprite Lata 350ml', '5.50', 30, 'Refrigerante Sprite em lata de 350ml.', False),
            ('Pepsi Lata 350ml', '5.50', 24, 'Refrigerante Pepsi em lata de 350ml.', False),
            ('Coca-Cola 600ml', '8.00', 20, 'Refrigerante Coca-Cola em garrafa de 600ml.', False),
            ('Guaraná Antarctica 600ml', '7.50', 18, 'Refrigerante Guaraná Antarctica em garrafa de 600ml.', False),
        ],
    },
    {
        'nome': 'Doces',
        'descricao': 'Chocolates, biscoitos, balas e sobremesas para adoçar o dia.',
        'produtos': [
            ('Chocolate ao Leite 90g', '7.50', 25, 'Barra de chocolate ao leite de 90g.', True),
            ('Biscoito Recheado de Chocolate', '3.50', 40, 'Pacote de biscoito recheado sabor chocolate.', False),
            ('Brigadeiro', '3.50', 30, 'Brigadeiro artesanal de chocolate.', False),
            ('Paçoca Rolha', '2.00', 50, 'Paçoca de amendoim tradicional.', False),
            ('Bala de Goma', '2.50', 60, 'Pacote de balas de goma coloridas.', False),
            ('Pirulito', '1.50', 80, 'Pirulito sabor morango.', False),
            ('Chiclete de Menta', '2.50', 45, 'Chiclete sabor menta.', False),
            ('Bolo de Pote', '8.00', 12, 'Bolo de pote caseiro, sabor chocolate.', False),
        ],
    },
    {
        'nome': 'Salgados',
        'descricao': 'Salgados assados e fritos, ideais para o intervalo.',
        'produtos': [
            ('Coxinha de Frango', '7.00', 35, 'Coxinha frita recheada com frango.', True),
            ('Pastel de Carne', '7.50', 30, 'Pastel frito recheado com carne moída.', False),
            ('Pastel de Queijo', '7.00', 30, 'Pastel frito recheado com queijo.', False),
            ('Empada de Frango', '6.50', 20, 'Empada assada recheada com frango.', False),
            ('Esfiha de Carne', '6.50', 25, 'Esfiha assada recheada com carne.', False),
            ('Kibe Frito', '6.00', 20, 'Kibe frito recheado com carne.', False),
            ('Enroladinho de Salsicha', '5.50', 25, 'Enroladinho de massa assada com salsicha.', False),
            ('Pão de Queijo', '3.50', 40, 'Pão de queijo assado, unidade.', False),
        ],
    },
    {
        'nome': 'Snacks',
        'descricao': 'Salgadinhos, batatas e petiscos para beliscar.',
        'produtos': [
            ('Salgadinho de Milho', '5.00', 35, 'Pacote de salgadinho sabor milho.', False),
            ('Batata Frita Pacote', '6.00', 30, 'Pacote de batata frita crocante.', False),
            ('Doritos', '8.50', 24, 'Pacote de tortilha sabor queijo.', False),
            ('Cheetos', '6.50', 28, 'Pacote de salgadinho sabor queijo.', False),
            ('Amendoim Torrado', '3.50', 40, 'Pacote de amendoim torrado e salgado.', False),
            ('Pipoca de Micro-ondas', '4.50', 30, 'Pacote de pipoca para micro-ondas.', False),
            ('Torcida', '6.00', 25, 'Pacote de salgadinho sabor presunto.', False),
        ],
    },
    {
        'nome': 'Sucos',
        'descricao': 'Sucos naturais, néctares e água de coco.',
        'produtos': [
            ('Suco de Laranja 300ml', '6.00', 30, 'Suco natural de laranja, copo de 300ml.', True),
            ('Suco de Maracujá 300ml', '6.00', 25, 'Suco natural de maracujá, copo de 300ml.', False),
            ('Suco de Uva 300ml', '6.00', 25, 'Suco de uva, copo de 300ml.', False),
            ('Suco de Abacaxi 300ml', '6.00', 20, 'Suco natural de abacaxi, copo de 300ml.', False),
            ('Suco de Morango 300ml', '6.50', 20, 'Suco de morango, copo de 300ml.', False),
            ('Água de Coco 300ml', '7.00', 18, 'Água de coco natural, copo de 300ml.', False),
            ('Néctar de Pêssego Lata 290ml', '5.50', 24, 'Néctar de pêssego em lata de 290ml.', False),
            ('Suco de Caixinha Uva 200ml', '4.00', 36, 'Suco de uva em caixinha de 200ml.', False),
        ],
    },
]


class Command(BaseCommand):
    help = 'Cria as categorias e os produtos iniciais da cantina (idempotente).'

    @transaction.atomic
    def handle(self, *args, **options):
        categorias_criadas = 0
        produtos_criados = 0
        produtos_existentes = 0

        for dados_categoria in CATEGORIAS:
            categoria, categoria_criada = Categoria.objects.get_or_create(
                nome=dados_categoria['nome'],
                defaults={'descricao': dados_categoria['descricao']},
            )
            if categoria_criada:
                categorias_criadas += 1
            elif not categoria.descricao:
                categoria.descricao = dados_categoria['descricao']
                categoria.save(update_fields=['descricao'])

            for nome, preco, quantidade, descricao, mais_vendido in dados_categoria['produtos']:
                _, produto_criado = Produto.objects.get_or_create(
                    nome=nome,
                    categoria=categoria,
                    defaults={
                        'preco': Decimal(preco),
                        'quantidade': quantidade,
                        'descricao': descricao,
                        'mais_vendido': mais_vendido,
                    },
                )
                if produto_criado:
                    produtos_criados += 1
                else:
                    produtos_existentes += 1

        self.stdout.write(self.style.SUCCESS(
            f'Categorias criadas: {categorias_criadas}. '
            f'Produtos criados: {produtos_criados}. '
            f'Produtos já existentes: {produtos_existentes}.'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Total no banco: {Categoria.objects.count()} categorias e '
            f'{Produto.objects.count()} produtos.'
        ))
