"""Synthetic, stable fixtures for the second-partial multi-tenant demo."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BranchSpec:
    name: str
    address: str
    active: bool = True


@dataclass(frozen=True)
class ProductSpec:
    name: str
    category: str
    price: Decimal
    description: str


@dataclass(frozen=True)
class TenantSpec:
    name: str
    slug: str
    plan_code: str
    specialty: str
    branches: tuple[BranchSpec, ...]
    customer_count: int
    paid_sales: int
    reservation_count: int
    exchange_scenarios: int
    products: tuple[ProductSpec, ...]

    @property
    def active_branches(self) -> tuple[BranchSpec, ...]:
        return tuple(branch for branch in self.branches if branch.active)


CUSTOMERS = (
    ("Andrea Fernanda", "Rojas"), ("Carlos Alberto", "Méndez"),
    ("Valeria", "Suárez"), ("Diego Fernando", "Fernández"),
    ("Mariana", "Gutiérrez"), ("Gabriela Isabel", "Flores"),
    ("Rodrigo Andrés", "Salvatierra"), ("Daniela", "Cabrera"),
    ("Camila Alejandra", "Vargas"), ("José Miguel", "Justiniano"),
    ("Lucía Fernanda", "Rivero"), ("Pablo Esteban", "Montaño"),
    ("Natalia", "Suárez"), ("Fernando Javier", "Añez"),
    ("Carolina", "Gutiérrez"), ("Mauricio", "Paz"),
    ("Paola Andrea", "Molina"), ("Sergio", "Arce"),
    ("Alejandra", "Vaca"), ("Gabriel", "Roca"),
    ("Romina Belén", "Limpias"), ("Marco Antonio", "Rivero"),
    ("Sofía", "Méndez"), ("Raúl Alejandro", "Céspedes"),
    ("Fernanda", "García"), ("Javier", "Cuéllar"),
    ("Mónica Patricia", "Justiniano"), ("Andrés", "Dorado"),
    ("Daniel", "Parada"), ("Claudia", "Núñez"),
    ("Iván Marcelo", "Vargas"), ("Verónica", "Mendoza"),
    ("Paulo César", "Salvatierra"), ("Melissa", "Ortiz"),
    ("Álvaro", "Suárez"), ("Jimena", "Cabrera"),
    ("Esteban", "Rojas"), ("Micaela", "Flores"),
    ("René", "Montaño"), ("Belén", "Añez"),
)

STAFF = (
    ("María José", "Vaca", "ENCARGADO_SUCURSAL"),
    ("Luis Fernando", "Rojas", "ENCARGADO_SUCURSAL"),
    ("Carla Fernanda", "Gutiérrez", "ENCARGADO_SUCURSAL"),
    ("Elena Patricia", "Rivero", "ENCARGADO_SUCURSAL"),
    ("Paola Andrea", "Méndez", "CAJERO"),
    ("Miguel Ángel", "Suárez", "CAJERO"),
    ("Carla Fernanda", "Flores", "CAJERO"),
    ("Jorge Luis", "Cabrera", "CAJERO"),
    ("Elena Patricia", "Vaca", "EMPLEADO"),
)


def _p(name: str, category: str, price: str, description: str) -> ProductSpec:
    return ProductSpec(name, category, Decimal(price), description)


TENANTS = (
    TenantSpec(
        name="Magnolia Boutique", slug="magnolia-boutique", plan_code="GLAMOUR",
        specialty="Moda femenina y prendas elegantes",
        branches=(
            BranchSpec("Centro", "Calle Libertad 148, zona Centro"),
            BranchSpec("Equipetrol", "Avenida San Martín 220, Equipetrol"),
            BranchSpec("Ventura Mall", "Cuarto anillo, local 214, Ventura Mall"),
            BranchSpec("Las Palmas", "Avenida Piraí 3250, Las Palmas"),
        ), customer_count=36, paid_sales=164, reservation_count=12, exchange_scenarios=8,
        products=(
            _p("Vestido midi Aurora", "Vestidos", "389.90", "Vestido fluido con cintura marcada y caída ligera."),
            _p("Vestido satén Noche Clara", "Vestidos", "465.00", "Satén de brillo suave con escote drapeado."),
            _p("Vestido camisero Oliva", "Vestidos", "328.50", "Corte camisero con botones y cinturón del mismo tejido."),
            _p("Vestido Siena de lino", "Vestidos", "412.90", "Lino fresco, manga corta y falda en línea A."),
            _p("Blusa Alba con lazo", "Blusas", "218.00", "Blusa de tacto sedoso con lazo removible al cuello."),
            _p("Blusa Marfil plisada", "Blusas", "196.50", "Frente plisado y puños delicados para uso de día."),
            _p("Blusa Cielo bordada", "Blusas", "247.90", "Bordado floral discreto en algodón liviano."),
            _p("Blusa Violeta cruzada", "Blusas", "229.00", "Silueta cruzada con ajuste lateral y manga tres cuartos."),
            _p("Pantalón sastre Emilia", "Pantalones", "315.00", "Tiro alto y pierna recta con pinzas frontales."),
            _p("Pantalón palazzo Arena", "Pantalones", "298.90", "Pierna amplia y pretina plana para una silueta elegante."),
            _p("Pantalón Roma cropped", "Pantalones", "276.00", "Largo al tobillo y tejido con caída estructurada."),
            _p("Jean recto Celeste", "Pantalones", "344.90", "Denim de lavado medio y tiro cómodo."),
            _p("Falda midi Magnolia", "Faldas", "264.50", "Falda midi con movimiento y cierre lateral oculto."),
            _p("Falda plisada Perla", "Faldas", "289.00", "Pliegues permanentes y pretina elástica discreta."),
            _p("Falda lápiz Carmín", "Faldas", "253.90", "Corte lápiz con pequeña abertura posterior."),
            _p("Conjunto Alba de dos piezas", "Conjuntos", "538.00", "Top estructurado y falda coordinada para ocasiones especiales."),
            _p("Conjunto lino Terracota", "Conjuntos", "496.50", "Camisa corta y pantalón fluido en lino mezclado."),
            _p("Conjunto ejecutivo Serena", "Conjuntos", "612.00", "Chaleco entallado y pantalón sastre a juego."),
            _p("Chaqueta corta Amatista", "Chaquetas", "429.90", "Chaqueta ligera con botones joya y cuello redondo."),
            _p("Blazer estructurado Magnolia", "Chaquetas", "589.00", "Blazer forrado con solapa clásica y hombro suave."),
            _p("Cardigan Nube", "Chaquetas", "318.00", "Tejido fino de punto con botones nacarados."),
            _p("Kimono estampado Jardín", "Chaquetas", "355.50", "Kimono liviano con estampado botánico de temporada."),
        ),
    ),
    TenantSpec(
        name="Punto Nativo", slug="punto-nativo", plan_code="MODA",
        specialty="Moda casual y prendas de uso diario",
        branches=(
            BranchSpec("Centro", "Calle René Moreno 72, zona Centro"),
            BranchSpec("Mutualista", "Avenida Mutualista 180, zona Mutualista"),
            BranchSpec("Norte", "Avenida Banzer, sexto anillo, zona Norte"),
        ), customer_count=32, paid_sales=152, reservation_count=10, exchange_scenarios=6,
        products=(
            _p("Camisa de lino Brisa", "Camisas", "219.90", "Camisa casual de lino mezclado con cuello abierto."),
            _p("Camisa a cuadros La Estación", "Camisas", "198.00", "Franela liviana en cuadros pequeños para entretiempo."),
            _p("Camisa Oxford Castaño", "Camisas", "236.50", "Oxford de algodón con bolsillo frontal y puño ajustable."),
            _p("Camisa manga corta Guapurú", "Camisas", "184.90", "Estampado tropical discreto sobre base de algodón."),
            _p("Polo Piraí clásico", "Polos", "149.00", "Piqué suave con cuello acanalado y tapeta de dos botones."),
            _p("Polo Laguna verde", "Polos", "162.50", "Polo de algodón peinado en tono verde oliva."),
            _p("Polo Ribera azul", "Polos", "158.00", "Tejido transpirable con terminaciones reforzadas."),
            _p("Jean recto Cotoca", "Jeans", "298.90", "Denim resistente de lavado oscuro y corte recto."),
            _p("Jean claro Montero", "Jeans", "284.00", "Mezclilla de lavado claro con acabado usado sutil."),
            _p("Jean slim Guabirá", "Jeans", "315.50", "Corte slim con elasticidad para movimiento diario."),
            _p("Chino beige El Prado", "Pantalones", "245.00", "Sarga de algodón con bolsillos laterales discretos."),
            _p("Chino azul Cañoto", "Pantalones", "259.90", "Pantalón chino de tiro medio y pernera afinada."),
            _p("Jogger liviano El Trompillo", "Pantalones", "208.00", "Pretina con cordón y puños suaves para fin de semana."),
            _p("Blusa básica Tajibo", "Blusas", "139.90", "Algodón suave de corte recto para combinar a diario."),
            _p("Blusa rayada Manzana Uno", "Blusas", "168.50", "Rayas finas y cuello redondo en punto liviano."),
            _p("Blusa manga globo Guapay", "Blusas", "192.00", "Manga con volumen moderado y cuerpo de viscosa."),
            _p("Chaqueta denim Urubó", "Chaquetas", "349.90", "Denim de peso medio con bolsillos de parche."),
            _p("Sobrecamisa caqui Patujú", "Chaquetas", "276.00", "Sobrecamisa utilitaria con broches y bolsillos amplios."),
            _p("Básica cuello alto Azahares", "Prendas básicas", "119.50", "Punto elástico de tacto suave para usar en capas."),
            _p("Vestido camisero Mburucuyá", "Vestidos", "289.90", "Vestido casual con botones frontales y bolsillos laterales."),
        ),
    ),
    TenantSpec(
        name="Distrito Urbano", slug="distrito-urbano", plan_code="ESTILO",
        specialty="Moda urbana y juvenil",
        branches=(
            BranchSpec("Centro", "Calle 24 de Septiembre 310, zona Centro"),
            BranchSpec("Plan 3000", "Avenida Paurito, Plan 3000"),
            BranchSpec("La Ramada", "Calle Muchirí 45, zona La Ramada", active=False),
        ), customer_count=38, paid_sales=178, reservation_count=14, exchange_scenarios=8,
        products=(
            _p("Jean cargo Distrito", "Jeans", "338.00", "Denim relajado con bolsillos cargo y costuras reforzadas."),
            _p("Jean wide leg Andén", "Jeans", "359.90", "Pierna amplia y lavado gris con acabado urbano."),
            _p("Jean negro Pasaje", "Jeans", "326.50", "Denim negro de tiro alto y pernera recta."),
            _p("Sudadera oversized Nómada", "Sudaderas", "298.00", "Algodón perchado con hombro caído y capucha amplia."),
            _p("Sudadera gráfica Concreto", "Sudaderas", "329.90", "Estampa geométrica frontal de tinta al agua."),
            _p("Hoodie nocturno Distrito", "Sudaderas", "348.00", "Bolsillo canguro y cordones planos en contraste."),
            _p("Camiseta gráfica Ruta 7", "Camisetas", "149.90", "Jersey de algodón con ilustración original de ciudad."),
            _p("Camiseta tipográfica Pulso", "Camisetas", "139.00", "Tipografía minimalista estampada sobre algodón compacto."),
            _p("Camiseta boxy Marea", "Camisetas", "158.50", "Corte boxy y cuello reforzado para uso frecuente."),
            _p("Camiseta manga larga Frecuencia", "Camisetas", "179.90", "Jersey liviano con gráfico pequeño en la espalda."),
            _p("Chaqueta bomber Terminal", "Chaquetas", "419.00", "Exterior resistente al viento y puños acanalados."),
            _p("Chaqueta denim Subsuelo", "Chaquetas", "389.90", "Silueta amplia con bolsillos frontales y herrajes mate."),
            _p("Cortaviento Periférico", "Chaquetas", "365.00", "Capucha plegable y paneles ligeros para lluvia breve."),
            _p("Jogger grafito Vía Libre", "Pantalones", "246.50", "Tejido flexible con bolsillos profundos y tobillo ajustado."),
            _p("Pantalón cargo Nexo", "Pantalones", "279.00", "Sarga lavada con bolsillos laterales funcionales."),
            _p("Pantalón recto Línea Sur", "Pantalones", "258.90", "Pernera recta y cintura cómoda de inspiración skate."),
            _p("Bermuda denim Pasarela", "Jeans", "218.00", "Bermuda de mezclilla con dobladillo limpio."),
            _p("Camisa overshirt Galpón", "Camisas", "287.50", "Franela gruesa para llevar abierta sobre una básica."),
            _p("Gorra seis paneles Altura", "Accesorios", "108.00", "Gorra de algodón con hebilla metálica regulable."),
            _p("Chaleco utilitario Módulo", "Chaquetas", "299.90", "Chaleco liviano con cierres y bolsillos interiores."),
            _p("Polo urbano Borde", "Polos", "169.00", "Piqué mate con vivos tonales en cuello y mangas."),
            _p("Buzo liviano Circuito", "Sudaderas", "268.50", "Buzo de algodón con cuello alto y cierre corto."),
            _p("Jean carpenter Taller", "Jeans", "374.00", "Denim robusto con presilla lateral y bolsillo de herramienta."),
        ),
    ),
    TenantSpec(
        name="Atelier Sur", slug="atelier-sur", plan_code="GLAMOUR",
        specialty="Moda femenina, ejecutiva y casual",
        branches=(
            BranchSpec("Centro", "Calle Junín 205, zona Centro"),
            BranchSpec("Urbarí", "Avenida Beni 420, barrio Urbarí"),
            BranchSpec("San Martín", "Avenida San Martín 145, zona Equipetrol"),
            BranchSpec("Ventura Mall", "Tercer anillo externo, local 118, Ventura Mall"),
        ), customer_count=40, paid_sales=196, reservation_count=18, exchange_scenarios=10,
        products=(
            _p("Blazer sastre Valentina", "Blazers", "648.00", "Blazer forrado con solapa fina y corte de hombro natural."),
            _p("Blazer cruzado Inés", "Blazers", "695.50", "Doble botonadura y pinzas que definen la cintura."),
            _p("Blazer lino ejecutivo Sur", "Blazers", "589.00", "Lino mezclado con forro parcial y bolsillos con tapa."),
            _p("Vestido ejecutivo Amalia", "Vestidos", "472.90", "Vestido a la rodilla con escote limpio y manga corta."),
            _p("Vestido recto Candelaria", "Vestidos", "519.00", "Línea recta con costadillos y abertura posterior."),
            _p("Vestido envolvente Jacarandá", "Vestidos", "498.50", "Cintura cruzada ajustable en tejido con caída elegante."),
            _p("Blusa seda mate Julieta", "Blusas", "325.00", "Viscosa de tacto sedoso con cuello camisero suave."),
            _p("Blusa cuello lazo Magnolia Sur", "Blusas", "348.90", "Lazo desmontable y puño francés para oficina."),
            _p("Blusa popelina Alba", "Blusas", "269.00", "Popelina de algodón con canesú posterior y pinzas."),
            _p("Blusa crêpe Horizonte", "Blusas", "298.50", "Crêpe liviano con manga tres cuartos y puño abotonado."),
            _p("Pantalón sastre Renata", "Pantalones", "389.00", "Tiro alto con pinzas y pernera recta hasta el tobillo."),
            _p("Pantalón palazzo Mar", "Pantalones", "365.50", "Pierna fluida y pretina limpia para uso ejecutivo."),
            _p("Pantalón recto Carbón", "Pantalones", "348.00", "Tejido de sastrería con elasticidad y caída definida."),
            _p("Pantalón lino Castaña", "Pantalones", "329.90", "Lino mezclado de tiro medio y bolsillos discretos."),
            _p("Conjunto chaleco y sastre Eva", "Conjuntos", "738.00", "Chaleco entallado y pantalón coordinado de corte clásico."),
            _p("Conjunto casual Bruna", "Conjuntos", "598.50", "Blusa de manga corta y pantalón relajado a juego."),
            _p("Conjunto ejecutivo Maite", "Conjuntos", "769.00", "Top estructurado con falda recta de tiro medio."),
            _p("Falda lápiz Oriana", "Faldas", "318.00", "Falda forrada con abertura posterior y cierre invisible."),
            _p("Falda midi plisada Amapola", "Faldas", "356.90", "Pliegues finos y tejido ligero de movimiento suave."),
            _p("Cardigan fino Gabriela", "Chaquetas", "289.00", "Punto fino con escote en V y botones tono carey."),
            _p("Chaqueta corta Dalia", "Chaquetas", "459.50", "Chaqueta estructurada con cuello redondo y bolsillos discretos."),
            _p("Top satén Noelia", "Blusas", "239.00", "Top de satén mate con tirantes regulables y forro frontal."),
            _p("Camisa ejecutiva Abril", "Camisas", "279.90", "Camisa de algodón de trama fina y puño sencillo."),
            _p("Vestido camisero Emilia", "Vestidos", "439.00", "Cinturón desmontable y falda midi de caída natural."),
            _p("Chaleco sastre Sofía", "Blazers", "379.50", "Chaleco forrado con escote en V y cierre de botones."),
        ),
    ),
)


ROLE_NAMES = ("ADMINISTRADOR", "ENCARGADO_SUCURSAL", "CAJERO", "EMPLEADO", "CLIENTE")
SIZE_NAMES = ("XS", "S", "M", "L", "XL", "34", "36", "38", "40", "42")
COLOR_NAMES = (
    "Negro", "Blanco", "Azul Marino", "Terracota", "Verde Oliva",
    "Vino", "Arena", "Lavanda", "Denim", "Gris", "Crudo", "Carmín",
)
CATEGORY_DESCRIPTIONS = {
    "Vestidos": "Vestidos seleccionados para la colección de temporada.",
    "Blusas": "Blusas y tops de la línea de la boutique.",
    "Pantalones": "Pantalones de vestir y de uso cotidiano.",
    "Faldas": "Faldas con cortes y largos para distintas ocasiones.",
    "Conjuntos": "Prendas coordinadas de dos piezas.",
    "Chaquetas": "Chaquetas ligeras y prendas de abrigo.",
    "Blazers": "Sastrería femenina para ocasiones formales.",
    "Camisas": "Camisas casuales y de vestir.",
    "Polos": "Polos de algodón para uso diario.",
    "Jeans": "Prendas de denim en distintos lavados y cortes.",
    "Sudaderas": "Buzos y sudaderas de inspiración urbana.",
    "Camisetas": "Camisetas estampadas y básicas.",
    "Accesorios": "Accesorios seleccionados para completar el atuendo.",
    "Prendas básicas": "Prendas esenciales para combinar en capas.",
}
