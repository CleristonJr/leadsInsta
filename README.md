# 📋 LeadsInsta — Buscador de Leads no Instagram

Sistema que busca automaticamente **20 perfis profissionais** no Instagram com base em uma área, salvando em CSV sem duplicatas.

---

## 📁 Estrutura de Arquivos

```
LeadsInsta/
├── buscar_leads.py       ← Script principal
├── requirements.txt      ← Dependências Python
├── leads_dentista.csv    ← CSV gerado automaticamente
└── leads_nutricionista.csv
```

---

## ⚙️ Instalação

```bash
pip install -r requirements.txt
```

---

## 🔑 Configuração do `.env`

Abra o arquivo `.env` e preencha:

```
INSTAGRAM_USERNAME=seu_usuario
INSTAGRAM_PASSWORD=sua_senha
MAX_LEADS=20
DELAY_MIN=8
DELAY_MAX=20
```

> ⚠️ **Recomendado:** Use uma conta Instagram secundária, não a principal.

---

## ▶️ Como Usar

### Modo interativo (pergunta a área):
```bash
python buscar_leads.py
```

### Modo direto (passa a área como argumento):
```bash
python buscar_leads.py dentista
python buscar_leads.py "personal trainer"
python buscar_leads.py nutricionista
```

---

## 📊 Formato do CSV gerado

Arquivo: `leads_dentista.csv`

| username | link_perfil | data_encontrado |
|----------|-------------|-----------------|
| joaosilva | https://www.instagram.com/joaosilva/ | 2026-04-07 |

---

## 🏷️ Áreas com hashtags já configuradas

| Área | Hashtags usadas |
|------|----------------|
| dentista | #dentista, #odontologia, #clinicaodontologica... |
| nutricionista | #nutricionista, #nutricao, #alimentacaosaudavel... |
| personal | #personaltrainer, #personalfit... |
| advogado | #advogado, #direito, #advocacia... |
| psicologo | #psicologo, #psicologia, #saudemental... |
| medico | #medico, #medicina, #saude... |
| arquiteto | #arquiteto, #arquitetura... |
| contador | #contador, #contabilidade... |
| corretor | #corretordeimoveis, #imobiliaria... |
| coach | #coach, #coaching, #mentoria... |
| fotografo | #fotografo, #fotografia... |
| designer | #designer, #designgrafico... |
| veterinario | #veterinario, #veterinaria... |
| esteticista | #esteticista, #estetica... |
| fisioterapeuta | #fisioterapeuta, #fisioterapia... |
| engenheiro | #engenheiro, #engenharia... |

> Para áreas não listadas, o sistema usa a própria área como hashtag automaticamente.

---

## 🔄 Uso Diário (Agendamento)

Para rodar automaticamente todo dia, use o **Agendador de Tarefas do Windows**:

1. Abra o **Agendador de Tarefas** (Task Scheduler)
2. Clique em **Criar Tarefa Básica**
3. Defina o horário desejado
4. Em **Ação**, selecione: `python C:\caminho\LeadsInsta\buscar_leads.py dentista`

---

## ✅ Proteções Anti-Ban

- Delays aleatórios de 8–20 segundos entre requisições
- Sessão salva localmente (não faz login todo dia)
- Perfis privados são ignorados automaticamente
- Máximo de 20 leads por execução
