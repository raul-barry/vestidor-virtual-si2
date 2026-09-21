from app.services.fashion_context_builder import FashionContextBuilder
from app.services.recommendation_service import RecommendationService

class FashionAssistantService:
    """Rule-based adapter; a future LLM provider can replace only this layer."""
    def __init__(self,db): self.db=db; self.context_builder=FashionContextBuilder(db); self.engine=RecommendationService(db)
    def ask(self,user_id:int,message:str):
        context=self.context_builder.build(user_id); text=message.casefold(); color=next((x for x in context['colores'] if x.casefold() in text),'')
        if not color: color=next((x for x in ['negro','azul','verde','gris','blanco'] if x in text),'')
        style=next((x for x in context['estilos'] if x.casefold() in text),'')
        rows=self.engine.recommend(user_id,context['talla_superior'],color,'')
        for row in rows: row['motivo']=f"Coincide con tu talla {row['talla']}" + (f", tu preferencia por {color}" if color else "") + (f" y tu estilo {style}" if style else ".")
        return {"mode":"reglas con contexto del perfil","contexto":context,"respuesta":"Estas sugerencias usan productos y stock reales.","recomendaciones":rows}
