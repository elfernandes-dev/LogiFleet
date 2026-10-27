"""
Ponto de Entrada da Aplicação de Logística e Frotas (Flask Runner).
Inicializa o servidor HTTP com suporte a argumentos de linha de comando ou variáveis de ambiente.
"""

import os
import sys
import argparse
from app import create_app

app = create_app()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Inicia o servidor de Gestão de Frotas e Logística.')
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 5000)), help='Porta HTTP do servidor')
    parser.add_argument('--host', type=str, default=os.environ.get('HOST', '0.0.0.0'), help='Interface de rede (host)')
    parser.add_argument('--debug', action='store_true', default=True, help='Modo de depuração ativo')

    args = parser.parse_args()

    print("=" * 65)
    print(" 🚀 SISTEMA DE GESTÃO DE LOGÍSTICA E AGENDAMENTO DE FROTAS")
    print(f" 🌐 Servidor ativo em: http://{args.host}:{args.port}")
    print(f" 📅 Painel de Agenda: http://{args.host}:{args.port}/calendar")
    print(f" 👤 Motoristas:       http://{args.host}:{args.port}/drivers")
    print(f" 🚛 Veículos:         http://{args.host}:{args.port}/vehicles")
    print("=" * 65)

    app.run(host=args.host, port=args.port, debug=args.debug)
