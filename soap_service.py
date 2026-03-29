from spyne import Application, rpc, ServiceBase, Unicode, Integer, Iterable
from spyne.model.complex import ComplexModel
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from werkzeug.serving import run_simple

# 1. Definição dos Modelos de Dados (Isso gerará o XSD no WSDL)
class Matricula(ComplexModel):
    _type_info = {
        'id_matricula': Unicode,
        'id_aluno': Unicode,
        'id_curso': Unicode,
        'status': Unicode,
    }

# 2. Base de dados simulada (em memória)
banco_de_matriculas = {}

# 3. Definição do Serviço com as 3 operações exigidas
class GestaoMatriculaService(ServiceBase):

    @rpc(Unicode, Unicode, _returns=Matricula) # Operação 1: Criar/Registrar
    def registrar_matricula(ctx, id_aluno, id_curso):
        nova_matricula = Matricula(
            id_matricula=f"MAT-{len(banco_de_matriculas)+1:04d}",
            id_aluno=id_aluno,
            id_curso=id_curso,
            status="ATIVA"
        )
        banco_de_matriculas[nova_matricula.id_matricula] = nova_matricula
        return nova_matricula

    @rpc(Unicode, _returns=Matricula) # Operação 2: Consultar
    def consultar_matricula(ctx, id_matricula):
        matricula = banco_de_matriculas.get(id_matricula)
        if matricula:
            return matricula
        return Matricula(id_matricula="0", id_aluno="0", id_curso="0", status="NAO ENCONTRADA")

    @rpc(Unicode, _returns=Iterable(Matricula)) # Operação 3: Listar
    def listar_matriculas_ativas(ctx, id_aluno):
        matriculas_do_aluno = [
            m for m in banco_de_matriculas.values() 
            if m.id_aluno == id_aluno and m.status == "ATIVA"
        ]
        if not matriculas_do_aluno:
            return [Matricula(id_matricula="0", id_aluno=id_aluno, id_curso="0", status="SEM MATRICULAS")]
        return matriculas_do_aluno

# 4. Configuração da Aplicação SOAP
application = Application(
    [GestaoMatriculaService],
    tns='urn:gestao.matriculas.uern',
    name='GestaoMatriculaService',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

wsgi_app = WsgiApplication(application)

# 5. Execução do Serviço
if __name__ == '__main__':
    print("Serviço SOAP rodando em: http://localhost:8000/?wsdl")
    run_simple('0.0.0.0', 8000, wsgi_app)