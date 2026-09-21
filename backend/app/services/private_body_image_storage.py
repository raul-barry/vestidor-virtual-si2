from pathlib import Path
from uuid import uuid4

class PrivateBodyImageStorage:
    allowed_types={"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}
    max_bytes=5*1024*1024
    def __init__(self, root: Path | None=None): self.root=root or Path(__file__).resolve().parents[2]/"private_body_images"; self.root.mkdir(parents=True,exist_ok=True)
    def save(self,user_id:int,position:str,content:bytes,content_type:str)->str:
        if content_type not in self.allowed_types or len(content)>self.max_bytes: raise ValueError("Formato o tamaño de imagen no válido")
        name=f"{user_id}_{position}_{uuid4().hex}{self.allowed_types[content_type]}"; (self.root/name).write_bytes(content); return name
    def path(self,name:str)->Path: return self.root/Path(name).name
    def delete(self,name:str|None)->None:
        if name: self.path(name).unlink(missing_ok=True)
