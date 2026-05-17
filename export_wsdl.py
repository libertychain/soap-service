"""
Exporta o WSDL gerado dinamicamente pelo Spyne para o arquivo servico.wsdl.
Execute APÓS o serviço estar rodando: python soap_service.py
"""
import urllib.request
import xml.dom.minidom
import sys

WSDL_URL = 'http://localhost:8000/?wsdl'
OUTPUT   = 'servico.wsdl'

def main():
    print(f"Buscando WSDL em {WSDL_URL} ...")
    try:
        with urllib.request.urlopen(WSDL_URL, timeout=5) as resp:
            raw = resp.read()
    except Exception as exc:
        print(f"ERRO: {exc}")
        print("Certifique-se de que o serviço está rodando (python soap_service.py)")
        sys.exit(1)

    dom = xml.dom.minidom.parseString(raw)
    pretty = dom.toprettyxml(indent='  ', encoding='UTF-8').decode('utf-8')

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(pretty)

    print(f"WSDL salvo em '{OUTPUT}' ({len(raw)} bytes)")

if __name__ == '__main__':
    main()
