from sqlalchemy import Column, Integer, String, Float
from src.database import Base # Importe a Base do seu arquivo database.py

class Endereco(Base):
    """
    Esta é a representação da sua tabela 'enderecos' no banco de dados.
    """
    __tablename__ = "enderecos"

    id = Column(Integer, primary_key=True, index=True)
    
    # Estamos usando String para o user_id para ser compatível com o UID do Firebase,
    # como estava no seu arquivo original.
    user_id = Column(String, unique=True, nullable=False, index=True) 
    
    rua = Column(String, nullable=False)
    numero = Column(String, nullable=False)
    bairro = Column(String, nullable=False)
    cidade = Column(String, nullable=False)
    estado = Column(String, nullable=False)
    cep = Column(String, nullable=False)
    complemento = Column(String, nullable=True)
    referencia = Column(String, nullable=True)
    
    # Colunas para armazenar as coordenadas geocodificadas
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # NOTA: Se você tem um modelo Usuario, você pode adicionar 
    # o relacionamento aqui, ex:
    # owner = relationship("Usuario", back_populates="endereco")
