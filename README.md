# 🚛 LogiFleet — Sistema de Gestão de Logística e Agendamento de Frotas

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.x-black?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![FullCalendar](https://img.shields.io/badge/FullCalendar-6.x-0275d8)](https://fullcalendar.io/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

O **LogiFleet** é um MVP (Minimum Viable Product) de alta fidelidade para **Gestão Logística, Alocação de Condutores e Agendamento de Frotas Corporativas**. Desenvolvido com base em princípios **SOLID**, **Clean Code** e boas práticas de engenharia de software, o sistema resolve o desafio crítico de evitar conflitos de horários e duplicidade na alocação de motoristas e veículos.

---

## 📋 Sumário
1. [Visão Geral & Recursos Principais](#-visão-geral--recursos-principais)
2. [Stack Tecnológica](#-stack-tecnológica)
3. [Modelagem de Dados (Database Schema)](#-modelagem-de-dados-database-schema)
4. [Estrutura de Pastas](#-estrutura-de-pastas)
5. [Instalação e Execução Local](#-instalação-e-execução-local)
6. [Guia de Uso dos Módulos](#-guia-de-uso-dos-módulos)
7. [Regras de Negócio & Prevenção de Conflitos](#-regras-de-negócio--prevenção-de-conflitos)
8. [Melhorias Futuras para Produção](#-melhorias-futuras-para-produção)

---

## 🌟 Visão Geral & Recursos Principais

- 📅 **Painel de Agendamento Interativo (FullCalendar 6.x):**
  - Visualizações dinâmica por Mês (`dayGridMonth`), Semana (`timeGridWeek`) e Lista (`listWeek`).
  - Criação rápida de ordens clicando em qualquer dia do calendário.
  - Edição, reclassificação de status e exclusão com 1 clique sobre o evento.
  - Indicadores visuais codificados por cores conforme o status operacional.
  - Filtros instantâneos por Motorista, Veículo e Status da Ordem de Serviço.
- ⚡ **Detector Proativo de Conflitos (Conflict Prevention Engine):**
  - Bloqueio estrito (HTTP 409 Conflict) caso o mesmo motorista ou veículo já possua uma ordem de serviço na data solicitada.
  - Alerta visual no formulário detalhando o cliente e o serviço conflitante.
- 👤 **Gestão de Motoristas (CRUD):**
  - Validação algorítmica de CPF (cálculo de dígitos verificadores e rejeição de repetições).
  - Máscara dinâmica de preenchimento (`000.000.000-00`).
  - Proteção de integridade referencial: bloqueia exclusão de motoristas com ordens ativas.
- 🚛 **Gestão de Veículos da Frota (CRUD):**
  - Validação de placas tanto no padrão **Mercosul** (`ABC1D23`) quanto **Tradicional Brasileiro** (`ABC-1234`).
  - Controle de disponibilidade operacional com flag `is_active` (veículos em manutenção/inativos não podem ser escalados).
  - Bloqueio de exclusão em caso de serviços pendentes.
- 🎨 **Interface Responsiva & Acessível:**
  - Construído com Bootstrap 5 e Bootstrap Icons.
  - Modais de confirmação para todas as ações destrutivas (sem alert/confirm nativos).
  - Sistema de Notificações Toast para feedback em tempo real.

---

## 🛠 Stack Tecnológica

| Camada | Tecnologia | Descrição |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+ | Linguagem central de processamento |
| **Framework Web** | Flask 3.1+ | Microframework modular com Blueprints |
| **ORM** | SQLAlchemy 2.0+ / Flask-SQLAlchemy | Mapeamento Objeto-Relacional e integridade de schema |
| **Banco de Dados** | SQLite 3 | Base local relacional armazenada em `logistics.db` |
| **Frontend** | HTML5 / CSS3 / Jinja2 | Templates server-side com filtros customizados |
| **CSS Framework** | Bootstrap 5.3.3 | Estilização responsiva e componentes |
| **Ícones** | Bootstrap Icons 1.11 | Conjunto visual de ícones vetoriais |
| **Componente de Agenda** | FullCalendar 6.1.15 | Calendário interativo com suporte a eventos assíncronos |
| **Comunicação HTTP** | JavaScript Vanilla (Fetch API) | Operações assíncronas RESTful sem reload |

---

## 🗄 Modelagem de Dados (Database Schema)

```text
  +-------------------------+          +-------------------------+
  |         drivers         |          |        vehicles         |
  +-------------------------+          +-------------------------+
  | id: INTEGER (PK)        |          | id: INTEGER (PK)        |
  | name: VARCHAR(100)      |          | model: VARCHAR(50)      |
  | tax_id: VARCHAR(14) (UQ)|          | color: VARCHAR(30)      |
  | created_at: DATETIME    |          | license_plate: (UQ)     |
  +-------------------------+          | is_active: BOOLEAN      |
              | 1                      | created_at: DATETIME    |
              |                        +-------------------------+
              |                                     | 1
              |                                     |
              +------------------+  +---------------+
                                 |  |
                                 v  v N
                    +-----------------------------+
                    |      service_schedules      |
                    +-----------------------------+
                    | id: INTEGER (PK)            |
                    | schedule_date: DATE (INDEX) |
                    | driver_id: INTEGER (FK)     |
                    | vehicle_id: INTEGER (FK)    |
                    | client_name: VARCHAR(120)   |
                    | delivery_address: TEXT      |
                    | order_number: VARCHAR(50)   |
                    | notes: TEXT                 |
                    | status: VARCHAR(20)         |
                    | created_at: DATETIME        |
                    +-----------------------------+
```

### Regras de Status da Ordem de Serviço
- `SCHEDULED` (Agendado): Cor Azul (`#0d6efd`)
- `IN_PROGRESS` (Em Rota / Andamento): Cor Amarela (`#ffc107`)
- `COMPLETED` (Concluído com Sucesso): Cor Verde (`#198754`)
- `CANCELLED` (Cancelado): Cor Cinza (`#6c757d`)

---

## 📁 Estrutura de Pastas

```text
logistics-app/
├── app/
│   ├── __init__.py          # Fábrica da aplicação (create_app), config SQLite e filtros Jinja
│   ├── models.py            # Modelos ORM: Driver, Vehicle e ServiceSchedule
│   ├── routes.py            # Controladores de Views (Jinja) e Endpoints de API REST
│   ├── services.py          # Regras de negócio, validação de CPF/Placa e Conflict Engine
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # Estilização refinada, badges de frota e customização FullCalendar
│   │   └── js/
│   │       ├── calendar.js  # Integração com FullCalendar 6.x, filtros e modais de agendamento
│   │       └── main.js      # Utilitários globais, sistema de Toasts, máscaras e CRUDs
│   └── templates/
│       ├── base.html        # Layout mestre com Navbar, Toasts e Modal de Confirmação
│       ├── calendar.html    # Painel interativo com métricas, filtros e FullCalendar
│       ├── drivers.html     # Listagem, busca e modal de cadastro de motoristas
│       └── vehicles.html    # Listagem, busca e modal de cadastro de veículos
├── run.py                   # Ponto de entrada CLI (python run.py)
├── requirements.txt         # Dependências do projeto Python
├── .gitignore               # Ignora ambientes virtuais, caches e banco SQLite
└── README.md                # Documentação técnica completa
```

---

## 🚀 Instalação e Execução Local

### Pré-requisitos
- **Python 3.10 ou superior** instalado na máquina.
- Git instalado (opcional, para clonagem).

### Passo a Passo

1. **Clonar ou acessar a pasta do projeto:**
   ```bash
   cd logistics-app
   ```

2. **Criar e ativar o ambiente virtual (venv):**
   - **Linux / macOS:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - **Windows:**
     ```powershell
     python -m venv venv
     venv\Scripts\activate
     ```

3. **Instalar as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Inicializar a aplicação:**
   ```bash
   python run.py
   ```

5. **Acessar no navegador:**
   - Acesse: **`http://localhost:5000`** (ou `http://127.0.0.1:5000`)
   - O banco de dados `logistics.db` será criado e inicializado automaticamente com dados de teste na primeira execução.

---

## 📖 Guia de Uso dos Módulos

### 1. Painel de Agendamento (`/calendar`)
- **Criar Novo Agendamento:**
  - Clique diretamente em qualquer dia do calendário.
  - O modal será aberto com a data selecionada pré-preenchida.
  - Selecione o Motorista, Veículo, informe o Cliente, Endereço de Entrega, Número do Pedido e Instruções.
  - Clique em **"Confirmar Agendamento"**.
- **Editar ou Alterar Status:**
  - Clique no card de um agendamento existente no calendário.
  - O modal exibirá os dados atuais. Modifique os campos ou altere o status (ex: para *Em Andamento* ou *Concluído*).
  - Para cancelar/excluir, clique no botão **"Excluir Ordem"** (com confirmação).
- **Filtros Operacionais:**
  - Utilize os seletores no topo da tela para filtrar eventos por motorista específico, veículo ou status.

### 2. Gestão de Motoristas (`/drivers`)
- **Cadastrar:** Clique em **"Novo Motorista"**, insira o Nome Completo e o CPF (com máscara automática `000.000.000-00`). O sistema checa a validade dos dígitos verificadores.
- **Editar:** Clique no botão azul de lápis na linha correspondente.
- **Excluir:** Clique no botão vermelho de lixeira. O sistema valida se há ordens de serviço ativas antes de prosseguir.

### 3. Gestão de Veículos (`/vehicles`)
- **Cadastrar:** Clique em **"Novo Veículo"**, informe Modelo, Cor Predominante e Placa (padrão Mercosul `ABC1D23` ou Tradicional `ABC-1234`).
- **Disponibilidade:** Alterne a chave *Veículo Ativo na Operação*. Veículos desativados não aparecerão nas opções do calendário.
- **Excluir:** Clique no botão de lixeira para remover o veículo com validação de dependências.

---

## 🛡 Regras de Negócio & Prevenção de Conflitos

```text
[Tentativa de Agendamento]
           │
           ▼
[Verifica Data e Veículo Ativo]
           │
           ▼
[Existe agendamento para este MOTORISTA nesta DATA? (status != CANCELLED)]
   ├── SIM ──► HTTP 409 Conflict: "O motorista já possui serviço nesta data"
   └── NÃO ──► Prossegue
                 │
                 ▼
[Existe agendamento para este VEÍCULO nesta DATA? (status != CANCELLED)]
   ├── SIM ──► HTTP 409 Conflict: "O veículo já está alocado nesta data"
   └── NÃO ──► Salva com sucesso (HTTP 201 Created)
```

---

## Melhorias Futuras para Produção

Para escalar o sistema para ambientes empresariais de grande porte:
1. **Migração do Banco de Dados:** Substituir o SQLite por **PostgreSQL 15+** com pooling de conexões (PgBouncer) e suporte a réplicas de leitura.
2. **Autenticação & Controle de Acesso (RBAC):** Adicionar autenticação com **JWT**, sessões seguras e níveis de permissão (ex: *Administrador*, *Expedição*, *Motorista*).
3. **Notificações em Tempo Real:** Integrar **WebSockets** (Flask-SocketIO) para atualização instantânea dos eventos do calendário quando outro operador criar ou alterar um agendamento.
4. **Roteirização Inteligente & Geolocalização:** Integração com APIs de mapas (Google Maps Platform / OpenStreetMap) para cálculo de distâncias, tempo estimado de chegada (ETA) e otimização de rotas.
5. **Auditoria e Logs de Ações:** Registro de histórico de alterações de status e movimentação de frotas com timestamp e usuário responsável.
