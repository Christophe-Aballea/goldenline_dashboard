from sqlalchemy import Column, Integer, String, Date, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from config import get_marketing_schema

Base = declarative_base()

marketing_schema = get_marketing_schema()


class CSP(Base):
    __tablename__ = 'csp'
    __table_args__ = {'schema': marketing_schema}
    
    id_csp = Column(Integer, primary_key=True)
    libelle = Column(String)
    csp = Column(String)

    clients = relationship('Client', back_populates='csp')


class Categorie(Base):
    __tablename__ = 'categories'
    __table_args__ = {'schema': marketing_schema}
    
    id_categorie = Column(Integer, primary_key=True)
    libelle = Column(String)

    achats = relationship('Achat', back_populates='categorie')


class Client(Base):
    __tablename__ = 'clients'
    __table_args__ = {'schema': marketing_schema}
    
    id_client = Column(String, primary_key=True)
    nb_enfants = Column(Integer)
    id_csp = Column(Integer, ForeignKey(f'{marketing_schema}.csp.id_csp'))

    csp = relationship('CSP', back_populates='clients')
    collectes = relationship('Collecte', back_populates='client')

class Collecte(Base):
    __tablename__ = 'collectes'
    __table_args__ = {'schema': marketing_schema}
    
    id_collecte = Column(Integer, primary_key=True)
    id_client = Column(String, ForeignKey(f'{marketing_schema}.clients.id_client'))
    date_passage = Column(Date)

    client = relationship('Client', back_populates='collectes')
    achats = relationship('Achat', back_populates='collecte')


class Achat(Base):
    __tablename__ = 'achats'
    __table_args__ = {'schema': marketing_schema}

    id_achat = Column(Integer, primary_key=True)
    id_collecte = Column(Integer, ForeignKey(f'{marketing_schema}.collectes.id_collecte'))
    id_categorie = Column(Integer, ForeignKey(f'{marketing_schema}.categories.id_categorie'))
    montant = Column(Numeric)

    collecte = relationship('Collecte', back_populates='achats')
    categorie = relationship('Categorie', back_populates='achats')


