from sqlalchemy import select
from app.models.cliente import Cliente
from app.models.color import Color
from app.models.preferencia_cliente import PreferenciaCliente, PreferenciaClienteColor
from app.models.perfil_corporal import PerfilCorporal

class FashionContextBuilder:
    def __init__(self, db): self.db=db
    def build(self,user_id:int):
        customer=self.db.scalar(select(Cliente).where(Cliente.id_usuario==user_id)); pref=self.db.scalar(select(PreferenciaCliente).where(PreferenciaCliente.id_cliente==customer.id_cliente)) if customer else None
        colors=[] if not pref else self.db.scalars(select(Color.nombre).join(PreferenciaClienteColor).where(PreferenciaClienteColor.id_preferencia==pref.id_preferencia)).all()
        body=self.db.scalar(select(PerfilCorporal).where(PerfilCorporal.id_usuario==user_id))
        return {"talla_superior":pref.talla_superior if pref else "","talla_pantalon":pref.talla_pantalon if pref else "","talla_calzado":pref.talla_calzado if pref else "","colores":colors,"estilos":pref.estilos.split(',') if pref and pref.estilos else [],"perfil_corporal":bool(body)}
