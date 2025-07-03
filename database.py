from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Date, func
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
import pandas as pd
import os

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Transacao(Base):
    __tablename__ = 'transacoes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    tipo = Column(String)
    valor = Column(Float)
    categoria = Column(String)
    data = Column(Date)

class Usuario(Base):
    __tablename__ = 'usuarios'

    user_id = Column(Integer, primary_key=True)

Base.metadata.create_all(engine)

# 📥 CRUD
def adicionar_transacao(user_id, tipo, valor, categoria):
    session = Session()
    nova = Transacao(
        user_id=user_id,
        tipo=tipo,
        valor=valor,
        categoria=categoria,
        data=datetime.now().date()
    )
    session.add(nova)
    session.commit()
    session.close()

def obter_resumo(user_id):
    session = Session()
    sete_dias = datetime.now().date() - timedelta(days=7)
    resultados = session.query(
        Transacao.tipo,
        Transacao.categoria,
        func.sum(Transacao.valor)
    ).filter(
        Transacao.user_id == user_id,
        Transacao.data >= sete_dias
    ).group_by(Transacao.tipo, Transacao.categoria).all()
    session.close()
    return resultados

def obter_saldo(user_id):
    session = Session()
    resultados = session.query(
        Transacao.tipo,
        func.sum(Transacao.valor)
    ).filter(
        Transacao.user_id == user_id
    ).group_by(Transacao.tipo).all()
    session.close()

    receitas = sum(v for t, v in resultados if t == "receita")
    gastos = sum(v for t, v in resultados if t == "gasto")
    return receitas - gastos

def exportar_transacoes(user_id):
    session = Session()
    query = session.query(Transacao).filter_by(user_id=user_id).order_by(Transacao.data.desc())
    rows = query.all()
    session.close()

    if not rows:
        return None

    df = pd.DataFrame([{
        "data": r.data.strftime("%Y-%m-%d"),
        "tipo": r.tipo,
        "valor": r.valor,
        "categoria": r.categoria
    } for r in rows])

    path = f"data/transacoes_{user_id}.csv"
    df.to_csv(path, index=False, sep=";")
    return path

def obter_totais_mes_atual(user_id):
    session = Session()
    mes_atual = datetime.now().strftime("%Y-%m")
    resultados = session.query(
        Transacao.tipo,
        func.sum(Transacao.valor)
    ).filter(
        Transacao.user_id == user_id,
        func.strftime('%Y-%m', Transacao.data) == mes_atual
    ).group_by(Transacao.tipo).all()
    session.close()

    receita = next((v for t, v in resultados if t == "receita"), 0)
    gasto = next((v for t, v in resultados if t == "gasto"), 0)
    return receita, gasto

def registrar_usuario(user_id):
    session = Session()
    if not session.query(Usuario).filter_by(user_id=user_id).first():
        session.add(Usuario(user_id=user_id))
        session.commit()
    session.close()

def listar_usuarios():
    session = Session()
    ids = session.query(Usuario.user_id).all()
    session.close()
    return [u[0] for u in ids]
