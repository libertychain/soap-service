import sqlite3
import logging
import os
from datetime import datetime
from spyne import Application, rpc, ServiceBase, Unicode, Iterable, Fault
from spyne.model.complex import ComplexModel
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from werkzeug.serving import run_simple

# ===== LOGGING =====
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/soap_service.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('GestaoMatriculas')

# ===== BANCO DE DADOS =====
DB_PATH = 'matriculas.db'

def _conn():
    # timeout=10 → espera até 10s se outra conexão estiver gravando
    # antes de levantar "database is locked"
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    return c

def init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS matriculas (
            id_matricula  TEXT PRIMARY KEY,
            id_aluno      TEXT NOT NULL,
            id_curso      TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'ATIVA',
            data_registro TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Banco SQLite inicializado: %s", DB_PATH)

def _proximo_id():
    # Usa MAX do ID real (não COUNT) — sobrevive a DELETEs sem gerar duplicatas.
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT MAX(CAST(SUBSTR(id_matricula, 5) AS INTEGER)) FROM matriculas")
    row = cur.fetchone()
    conn.close()
    proximo = (row[0] or 0) + 1
    return f"MAT-{proximo:04d}"

# ===== WS-SECURITY — usuários permitidos =====
_USUARIOS = {
    'admin':  'admin123',
    'gestor': 'gestor456',
}

def _credenciais_validas(header):
    if header is None:
        return False
    token = getattr(header, 'UsernameToken', None)
    if token is None:
        return False
    return _USUARIOS.get(getattr(token, 'Username', None)) == getattr(token, 'Password', None)

# ===== MODELOS =====
class UsernameToken(ComplexModel):
    _type_info = {
        'Username': Unicode,
        'Password': Unicode,
    }

class WSSecurity(ComplexModel):
    _type_info = {
        'UsernameToken': UsernameToken,
    }

class Matricula(ComplexModel):
    _type_info = {
        'id_matricula':  Unicode,
        'id_aluno':      Unicode,
        'id_curso':      Unicode,
        'status':        Unicode,
        'data_registro': Unicode,
    }

class RespostaOperacao(ComplexModel):
    _type_info = {
        'sucesso':  Unicode,
        'mensagem': Unicode,
    }

# ===== SERVIÇO =====
class GestaoMatriculaService(ServiceBase):
    # WSSecurity declarado no nível do serviço — aparece no WSDL para todas as operações;
    # a validação é aplicada seletivamente nas operações protegidas.
    __in_header__ = WSSecurity

    # CREATE
    @rpc(Unicode, Unicode, _returns=Matricula)
    def registrar_matricula(ctx, id_aluno, id_curso):
        logger.info("OP=registrar_matricula aluno=%s curso=%s", id_aluno, id_curso)
        conn = None
        try:
            id_mat = _proximo_id()
            data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = _conn()
            conn.execute(
                "INSERT INTO matriculas VALUES (?, ?, ?, ?, ?)",
                (id_mat, id_aluno, id_curso, 'ATIVA', data)
            )
            conn.commit()
            logger.info("Matricula criada: %s", id_mat)
            return Matricula(
                id_matricula=id_mat, id_aluno=id_aluno,
                id_curso=id_curso, status='ATIVA', data_registro=data
            )
        except Exception as exc:
            logger.error("ERRO registrar_matricula: %s", exc)
            if conn is not None:
                try: conn.rollback()
                except Exception: pass
            raise Fault('Server', f'Erro interno: {exc}')
        finally:
            if conn is not None:
                try: conn.close()
                except Exception: pass

    # READ — individual
    @rpc(Unicode, _returns=Matricula)
    def consultar_matricula(ctx, id_matricula):
        logger.info("OP=consultar_matricula id=%s", id_matricula)
        conn = _conn()
        row = conn.execute(
            "SELECT * FROM matriculas WHERE id_matricula = ?", (id_matricula,)
        ).fetchone()
        conn.close()
        if row:
            return Matricula(
                id_matricula=row[0], id_aluno=row[1],
                id_curso=row[2], status=row[3], data_registro=row[4]
            )
        logger.warning("Matricula nao encontrada: %s", id_matricula)
        return Matricula(
            id_matricula='0', id_aluno='0',
            id_curso='0', status='NAO_ENCONTRADA', data_registro=''
        )

    # READ — lista
    @rpc(Unicode, _returns=Iterable(Matricula))
    def listar_matriculas_ativas(ctx, id_aluno):
        logger.info("OP=listar_matriculas_ativas aluno=%s", id_aluno)
        conn = _conn()
        rows = conn.execute(
            "SELECT * FROM matriculas WHERE id_aluno = ? AND status = 'ATIVA'",
            (id_aluno,)
        ).fetchall()
        conn.close()
        if not rows:
            logger.info("Nenhuma matricula ativa para aluno %s", id_aluno)
            return [Matricula(
                id_matricula='0', id_aluno=id_aluno,
                id_curso='0', status='SEM_MATRICULAS', data_registro=''
            )]
        return [
            Matricula(
                id_matricula=r[0], id_aluno=r[1],
                id_curso=r[2], status=r[3], data_registro=r[4]
            )
            for r in rows
        ]

    # UPDATE — cancelar (protegida por WS-Security)
    @rpc(Unicode, _returns=RespostaOperacao)
    def cancelar_matricula(ctx, id_matricula):
        logger.info("OP=cancelar_matricula id=%s auth=%s",
                    id_matricula, ctx.in_header is not None)
        if not _credenciais_validas(ctx.in_header):
            logger.warning("AUTH FALHOU — cancelar_matricula id=%s", id_matricula)
            raise Fault('Client.Unauthorized',
                        'Credenciais WS-Security invalidas ou ausentes')
        conn = _conn()
        existe = conn.execute(
            "SELECT 1 FROM matriculas WHERE id_matricula = ?", (id_matricula,)
        ).fetchone()
        if not existe:
            conn.close()
            logger.warning("Matricula nao encontrada para cancelar: %s", id_matricula)
            return RespostaOperacao(
                sucesso='false',
                mensagem=f'Matricula {id_matricula} nao encontrada'
            )
        conn.execute(
            "UPDATE matriculas SET status = 'CANCELADA' WHERE id_matricula = ?",
            (id_matricula,)
        )
        conn.commit()
        conn.close()
        logger.info("Matricula cancelada: %s", id_matricula)
        return RespostaOperacao(
            sucesso='true',
            mensagem=f'Matricula {id_matricula} cancelada com sucesso'
        )

    # DELETE (protegida por WS-Security)
    @rpc(Unicode, _returns=RespostaOperacao)
    def excluir_matricula(ctx, id_matricula):
        logger.info("OP=excluir_matricula id=%s auth=%s",
                    id_matricula, ctx.in_header is not None)
        if not _credenciais_validas(ctx.in_header):
            logger.warning("AUTH FALHOU — excluir_matricula id=%s", id_matricula)
            raise Fault('Client.Unauthorized',
                        'Credenciais WS-Security invalidas ou ausentes')
        conn = _conn()
        existe = conn.execute(
            "SELECT 1 FROM matriculas WHERE id_matricula = ?", (id_matricula,)
        ).fetchone()
        if not existe:
            conn.close()
            logger.warning("Matricula nao encontrada para excluir: %s", id_matricula)
            return RespostaOperacao(
                sucesso='false',
                mensagem=f'Matricula {id_matricula} nao encontrada'
            )
        conn.execute(
            "DELETE FROM matriculas WHERE id_matricula = ?", (id_matricula,)
        )
        conn.commit()
        conn.close()
        logger.info("Matricula excluida: %s", id_matricula)
        return RespostaOperacao(
            sucesso='true',
            mensagem=f'Matricula {id_matricula} excluida com sucesso'
        )


# ===== APLICAÇÃO =====
application = Application(
    [GestaoMatriculaService],
    tns='urn:gestao.matriculas.uern',
    name='GestaoMatriculaService',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

wsgi_app = WsgiApplication(application)

if __name__ == '__main__':
    init_db()
    print("=" * 60)
    print("  Serviço SOAP — Gestão de Matrículas  (Unidade 3)")
    print("=" * 60)
    print(f"  WSDL : http://localhost:8000/?wsdl")
    print(f"  Banco: {DB_PATH}")
    print(f"  Logs : logs/soap_service.log")
    print("=" * 60)
    run_simple('0.0.0.0', 8000, wsgi_app)
