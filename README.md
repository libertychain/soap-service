Gestor de Inscrições ou Matrículas - Web Service SOAP

Este projeto implementa um sistema orientado a serviços (SOA) utilizando Web Services SOAP. O serviço foi desenvolvido em Python com o framework Spyne e expõe operações para registrar, consultar e listar matrículas de alunos.

📋 Requisitos de Ambiente
Antes de iniciar, certifique-se de ter as seguintes ferramentas instaladas no seu computador:

Python: Versão 3.8 ou superior.
pip: Gerenciador de pacotes do Python (geralmente já vem instalado com o Python).
(Opcional) Postman, Insomnia ou SoapUI: Para facilitar os testes de consumo do serviço.
🛠️ Passos para Executar o Serviço
Siga os passos abaixo para colocar o Web Service no ar:

Extraia os arquivos: Descompacte o arquivo .zip recebido em uma pasta de sua preferência.
Abra o Terminal: Acesse a pasta onde os arquivos foram extraídos (ex: cd caminho/para/a/pasta).
Instale as dependências: Execute o comando abaixo para instalar as bibliotecas necessárias (Spyne, Werkzeug e LXML):
pip install -r requirements.txt
Inicie o servidor: Execute o arquivo principal do serviço com o comando:
python soap_service.py
Confirmação: Se tudo ocorreu bem, o terminal exibirá a seguinte mensagem:
Serviço SOAP rodando em: http://localhost:8000/?wsdl
O servidor ficará rodando nesta tela. Não feche o terminal enquanto estiver testando.
🌐 Acessando o Contrato (WSDL)
Com o servidor rodando, abra o seu navegador de internet (Chrome, Firefox, Edge) e acesse a seguinte URL:

👉 http://localhost:8000/?wsdl

Você verá o arquivo XML gerado automaticamente pelo framework, contendo a definição formal dos tipos (XSD), mensagens, portTypes, bindings e o serviço.

📡 Passos para Consumir o Serviço (Testes)
Para consumir e testar as operações do Web Service, você pode usar ferramentas como o Postman ou enviar requisições via cURL no terminal.

Usando o Postman (Recomendado)
1-Abra o Postman e crie uma nova requisição do tipo POST.
2-Na barra de URL, digite: http://localhost:8000/
3-Vá na aba Headers e adicione a seguinte chave e valor:
*Key: Content-Type
*Value: text/xml
4-Vá na aba Body, selecione a opção raw e certifique-se de que o dropdown ao lado esteja em XML.
5-Cole um dos envelopes XML abaixo e clique em Send.

Exemplo de Requisição: Registrar Matrícula
<soap11env:Envelope xmlns:soap11env="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="urn:gestao.matriculas.uern">   <soap11env:Body
<tns:registrar_matricula>
<tns:id_aluno>20231001</tns:id_aluno>
<tns:id_curso>CCO001</tns:id_curso>
</tns:registrar_matricula>
</soap11env:Body>
</soap11env:Envelope>
