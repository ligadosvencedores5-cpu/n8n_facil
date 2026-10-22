# ════════════════════════════════════════════════════════════════════════
# n8n FÁCIL — Seu servidor de automações no Railway, comandado por conversa
# MeusAgentesIA.com.br  ·  arquivo único
#
# O que este agente faz pela pessoa:
#   1. Instala o n8n na conta Railway DELA (projeto, disco permanente,
#      endereço https e configuração de webhooks) com 1 clique.
#   2. Conecta na API do n8n e cria automações prontas:
#      WhatsApp e atendimento · Planilhas e e-mail · Redes sociais e
#      conteúdo · Vendas e pagamentos (Hotmart, Kiwify, Monetizze, Eduzz...)
#   3. Cria automações sob medida a partir de uma descrição (IA).
#   4. Lista, liga, desliga, testa, apaga e mostra o histórico das automações.
#   5. Cuida do servidor: status, registros (logs), reiniciar, atualizar.
#
# COMO PUBLICAR
#   Coloque SÓ este arquivo num repositório do GitHub e publique no
#   Streamlit Cloud. Não precisa de requirements.txt (usa só o que já vem
#   com o Streamlit: requests e pandas). Cada pessoa entra com o próprio
#   nome e a própria chave Groq. Tokens e senhas ficam SÓ na sessão.
# ════════════════════════════════════════════════════════════════════════
import hashlib
import io
import json
import re
import secrets
import uuid
import zipfile
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="n8n Fácil — Automações", page_icon="⚡", layout="wide")

MODELO = "openai/gpt-oss-120b"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
SITE = "https://meusagentesia.com.br"
RAILWAY_API = "https://backboard.railway.com/graphql/v2"
IMAGEM_N8N = "n8nio/n8n"
PORTA_N8N = 5678
PASTA_DADOS = "/home/node/.n8n"

CATEGORIAS = {
    "whats":   ("💬", "WhatsApp e atendimento"),
    "planilha": ("📊", "Planilhas e e-mail"),
    "conteudo": ("📣", "Redes sociais e conteúdo"),
    "vendas":  ("💰", "Vendas e pagamentos"),
}
FUSOS = ["America/Sao_Paulo", "America/Manaus", "America/Cuiaba", "America/Belem", "America/Fortaleza", "America/Recife",
         "America/Bahia", "America/Porto_Velho", "America/Rio_Branco", "America/Noronha", "Europe/Lisbon", "UTC"]
DIAS_SEMANA = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]

REGRA_IA = (
    "Você é o assistente do n8n Fácil, um especialista em automações com n8n, Railway, WhatsApp, e-mail, "
    "redes sociais e plataformas de venda (Hotmart, Kiwify, Monetizze, Eduzz). Fale em português do Brasil, de "
    "forma simples, para quem nunca programou. Seja prático e direto, em passos curtos. Nunca invente dados da "
    "conta da pessoa: use só o que o aplicativo informar. Oriente a usar WhatsApp apenas com contatos que "
    "autorizaram receber mensagens (evita bloqueio do número e respeita a LGPD)."
)

# ══════════════════════════════════════════════════════════════════════════
# ESTILO
# ══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
#MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stDecoration"] { visibility:hidden; }
.stApp { background:#F8F7FB; }
.block-container { padding-top:1.1rem; }
h1, h2, h3, h4, p, li, label, span, div { color:#1F1A33; }
.cab { background:linear-gradient(135deg,#EA4B71,#C2185B 55%,#6D28D9); border-radius:18px; padding:20px 24px; margin-bottom:8px; }
.cab, .cab * { color:#FFFFFF !important; }
.cab h1 { margin:0; font-size:1.65em; } .cab p { margin:4px 0 0 0; opacity:.93; }
.card { background:#fff; border:1px solid #ECE6F1; border-radius:16px; padding:16px 18px; margin-bottom:12px; }
.passo { display:inline-block; background:#FDE2EA; color:#9F1239 !important; border-radius:20px; padding:2px 12px;
         font-size:.78em; font-weight:700; margin-bottom:6px; letter-spacing:.3px; }
.metrica { background:#fff; border:1px solid #ECE6F1; border-radius:16px; padding:14px; text-align:center; }
.metrica b { font-size:1.6em; display:block; color:#C2185B !important; }
.metrica small { color:#6E6585 !important; }
.chip { display:inline-block; padding:2px 10px; border-radius:20px; font-size:.78em; font-weight:700; }
.ok   { background:#DCFCE7; color:#166534 !important; }
.atr  { background:#FEE2E2; color:#991B1B !important; }
.neu  { background:#EDE9FE; color:#5B21B6 !important; }
.fim  { background:#FEF3C7; color:#92400E !important; }
.aviso { background:#FFFBEB; border:1px solid #FDE68A; border-radius:12px; padding:10px 14px; font-size:.9em; margin-bottom:10px; }
.aviso, .aviso * { color:#78350F !important; }
.link-box { background:#F1F5F9; border:1px dashed #94A3B8; border-radius:10px; padding:8px 12px; font-family:monospace;
            font-size:.88em; word-break:break-all; }
.check { font-size:1.02em; line-height:2.0; }
.stButton > button, [data-testid="stDownloadButton"] > button { border-radius:10px; font-weight:600; }
.stButton > button[kind="primary"] { background:#E11D63 !important; border-color:#E11D63 !important; }
.stButton > button[kind="primary"] * { color:#fff !important; }
.stButton > button[kind="primary"]:hover { background:#BE185D !important; }
.stTabs .react-aria-SelectionIndicator, [data-baseweb="tab-highlight"] { background:#E11D63 !important; }
.stTabs [aria-selected="true"] p { color:#E11D63 !important; }
[data-baseweb="tag"] { background:#E11D63 !important; } [data-baseweb="tag"] * { color:#fff !important; }
.rodape { text-align:center; color:#9C94B0 !important; font-size:.78em; margin-top:26px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# ESTADO — o que vai para a memória (.json) NUNCA inclui tokens nem senhas
# ══════════════════════════════════════════════════════════════════════════
PADRAO = {
    "u_nome": "", "u_chave": "",
    "rw_token": "",             # token do Railway (só nesta sessão)
    "rw_conta": {},             # {nome, email, workspaces:[{id,name}]}
    "rw": {},                   # ids públicos do servidor: workspace_id, project_id, project_nome, env_id, service_id, volume_id, domain, feito{}
    "n8n_url": "", "n8n_key": "",
    "canais": {"whats_prov": "evolution", "whats_base": "", "whats_inst": "", "whats_dono": "",
               "tg_chat": "", "smtp_host": "smtp.gmail.com", "smtp_port": 465, "smtp_user": "",
               "email_de": "", "email_para": ""},
    "segredos": {"whats_token": "", "whats_client": "", "tg_token": "", "smtp_senha": ""},   # só nesta sessão
    "cred_ids": {},             # credenciais criadas no n8n: chave -> {id, name, assin, url}
    "automacoes": [],           # {id, nome, categoria, modelo, criada, gatilho, url_gatilho, teste}
    "historico": [],            # {quando, acao, detalhe}
    "chat": [],
    "rascunho_ia": None,        # fluxo gerado pela IA aguardando confirmação
    "ver": 0,
}
for _k, _v in PADRAO.items():
    if _k not in st.session_state:
        st.session_state[_k] = json.loads(json.dumps(_v))
S = st.session_state
CHAVES_MEMORIA = ["rw", "n8n_url", "canais", "cred_ids", "automacoes", "historico", "chat"]


def agora() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def registrar(acao: str, detalhe: str = ""):
    S.historico.append({"quando": agora(), "acao": acao, "detalhe": detalhe})
    S.historico = S.historico[-300:]


class ErroAPI(Exception):
    pass


def rodar(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except ErroAPI as e:
        st.error(str(e))
        return None


def fez(fn, *a, **kw) -> bool:
    try:
        fn(*a, **kw)
        return True
    except ErroAPI as e:
        st.error(str(e))
        return False


def limpar_md(t: str) -> str:
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", str(t or ""))
    return re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", t).strip()


def slug(t: str, tam: int = 30) -> str:
    t = t.lower()
    for a, b in (("áàâã", "a"), ("éê", "e"), ("í", "i"), ("óôõ", "o"), ("ú", "u"), ("ç", "c")):
        for c in a:
            t = t.replace(c, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:tam] or "fluxo"


def br_data(iso: str) -> str:
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone().strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return str(iso or "")


# ══════════════════════════════════════════════════════════════════════════
# IA (Groq via HTTP)
# ══════════════════════════════════════════════════════════════════════════
def ia(mensagens, json_mode=False, temperatura=0.5) -> str:
    if isinstance(mensagens, str):
        mensagens = [{"role": "user", "content": mensagens}]
    corpo = {"model": MODELO, "messages": [{"role": "system", "content": REGRA_IA}] + mensagens, "temperature": temperatura}
    if json_mode:
        corpo["response_format"] = {"type": "json_object"}
    try:
        r = requests.post(GROQ_URL, json=corpo, timeout=180,
                          headers={"Authorization": f"Bearer {S.u_chave}", "Content-Type": "application/json"})
    except requests.RequestException as e:
        raise ErroAPI(f"Sem conexão com a IA agora. Tente de novo. ({e.__class__.__name__})")
    if r.status_code == 401:
        raise ErroAPI("🔑 Sua chave Groq não foi aceita. Clique em Sair e entre com uma chave válida.")
    if r.status_code == 429:
        raise ErroAPI("⏳ Limite de uso da sua chave Groq atingido. Espere um pouco e tente de novo.")
    if r.status_code == 400 and json_mode:
        mensagens[-1]["content"] += "\n\nResponda SOMENTE com JSON válido."
        return ia(mensagens, json_mode=False, temperatura=temperatura)
    if r.status_code != 200:
        raise ErroAPI(f"A IA não respondeu (código {r.status_code}). Tente de novo em instantes.")
    try:
        txt = r.json()["choices"][0]["message"]["content"] or ""
    except (ValueError, KeyError, IndexError):
        raise ErroAPI("A IA devolveu uma resposta inesperada. Tente de novo.")
    return re.sub(r"<think>.*?</think>", "", txt, flags=re.S).strip()


def ia_json(mensagens) -> dict:
    txt = ia(mensagens, json_mode=True, temperatura=0.3)
    achado = re.search(r"\{.*\}", txt, flags=re.S)
    for tentativa in (txt, achado.group(0) if achado else ""):
        if tentativa:
            try:
                return json.loads(tentativa)
            except ValueError:
                pass
    raise ErroAPI("A IA respondeu fora do formato esperado. Clique de novo.")


# ══════════════════════════════════════════════════════════════════════════
# RAILWAY (API GraphQL pública)
# ══════════════════════════════════════════════════════════════════════════
def rw(query: str, variaveis: dict = None, token: str = None) -> dict:
    tok = (token or S.rw_token or "").strip()
    if not tok:
        raise ErroAPI("Conecte sua conta Railway primeiro (aba 🚀 Instalar n8n, passo 1).")
    try:
        r = requests.post(RAILWAY_API, json={"query": query, "variables": variaveis or {}}, timeout=60,
                          headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    except requests.RequestException as e:
        raise ErroAPI(f"Não consegui falar com o Railway agora ({e.__class__.__name__}). Tente de novo em instantes.")
    if r.status_code in (401, 403):
        raise ErroAPI("🔑 O Railway recusou o token. Crie um novo em railway.com/account/tokens "
                      "(em Workspace escolha **No workspace**) e cole de novo.")
    try:
        dados = r.json()
    except ValueError:
        raise ErroAPI(f"Resposta inesperada do Railway (código {r.status_code}). Tente de novo.")
    if dados.get("errors"):
        msg = "; ".join(str(e.get("message", "")) for e in dados["errors"])
        if "not authorized" in msg.lower():
            raise ErroAPI("🔑 Este token não tem permissão para essa ação. Use um token da CONTA "
                          "(railway.com/account/tokens → Workspace: **No workspace**).")
        raise ErroAPI(f"O Railway respondeu: {msg}")
    return dados.get("data") or {}


def rw_conta(token: str) -> dict:
    d = rw("query { me { name email workspaces { id name } } }", token=token)
    me = d.get("me") or {}
    return {"nome": me.get("name") or "", "email": me.get("email") or "", "workspaces": me.get("workspaces") or []}


def rw_projetos(workspace_id: str = None) -> list:
    if workspace_id:
        d = rw("query($w: String!) { projects(workspaceId: $w) { edges { node { id name createdAt } } } }", {"w": workspace_id})
    else:
        d = rw("query { projects { edges { node { id name createdAt } } } }")
    return [e["node"] for e in (d.get("projects") or {}).get("edges", [])]


def rw_projeto(pid: str) -> dict:
    d = rw("""query($id: String!) { project(id: $id) { id name
              services { edges { node { id name } } } environments { edges { node { id name } } } } }""", {"id": pid})
    p = d.get("project") or {}
    return {"id": p.get("id"), "nome": p.get("name"),
            "servicos": [e["node"] for e in (p.get("services") or {}).get("edges", [])],
            "ambientes": [e["node"] for e in (p.get("environments") or {}).get("edges", [])]}


def rw_dominios() -> list:
    R = S.rw
    d = rw("""query($p: String!, $e: String!, $s: String!) { domains(projectId: $p, environmentId: $e, serviceId: $s) {
              serviceDomains { domain } customDomains { domain } } }""",
           {"p": R["project_id"], "e": R["env_id"], "s": R["service_id"]})
    dm = d.get("domains") or {}
    return [x["domain"] for x in (dm.get("customDomains") or []) + (dm.get("serviceDomains") or [])]


def rw_deploys(n: int = 5) -> list:
    R = S.rw
    d = rw("""query($i: DeploymentListInput!, $n: Int) { deployments(input: $i, first: $n) {
              edges { node { id status createdAt staticUrl } } } }""",
           {"i": {"projectId": R["project_id"], "serviceId": R["service_id"], "environmentId": R["env_id"]}, "n": n})
    return [e["node"] for e in (d.get("deployments") or {}).get("edges", [])]


def rw_logs(dep_id: str, build: bool = False, n: int = 200) -> list:
    campo = "buildLogs" if build else "deploymentLogs"
    d = rw("query($d: String!, $n: Int) { %s(deploymentId: $d, limit: $n) { timestamp message severity } }" % campo,
           {"d": dep_id, "n": n})
    return d.get(campo) or []


def rw_variaveis() -> dict:
    R = S.rw
    d = rw("query($p: String!, $e: String!, $s: String) { variables(projectId: $p, environmentId: $e, serviceId: $s) }",
           {"p": R["project_id"], "e": R["env_id"], "s": R["service_id"]})
    return d.get("variables") or {}


def rw_salvar_variaveis(vars_: dict, aplicar: bool = True):
    R = S.rw
    rw("mutation($i: VariableCollectionUpsertInput!) { variableCollectionUpsert(input: $i) }",
       {"i": {"projectId": R["project_id"], "environmentId": R["env_id"], "serviceId": R["service_id"],
              "variables": {k: str(v) for k, v in vars_.items()}, "skipDeploys": not aplicar}})


def rw_ligar(novo: bool = False):
    """novo=False: reimplanta a versão atual · novo=True: nova implantação (busca a imagem mais recente)."""
    R = S.rw
    v = {"s": R["service_id"], "e": R["env_id"]}
    if not novo:
        try:
            rw("mutation($s: String!, $e: String!) { serviceInstanceRedeploy(serviceId: $s, environmentId: $e) }", v)
            return
        except ErroAPI:
            pass
    rw("mutation($s: String!, $e: String!) { serviceInstanceDeployV2(serviceId: $s, environmentId: $e) }", v)


def rw_reiniciar():
    deps = rw_deploys(1)
    if not deps:
        raise ErroAPI("Ainda não existe nenhuma implantação para reiniciar.")
    rw("mutation($id: String!) { deploymentRestart(id: $id) }", {"id": deps[0]["id"]})


def rw_excluir_projeto():
    rw("mutation($id: String!) { projectDelete(id: $id) }", {"id": S.rw["project_id"]})


def variaveis_n8n(fuso: str) -> dict:
    return {
        "PORT": str(PORTA_N8N), "N8N_PORT": str(PORTA_N8N), "N8N_PROTOCOL": "https", "N8N_PROXY_HOPS": "1",
        "N8N_ENCRYPTION_KEY": secrets.token_hex(24), "GENERIC_TIMEZONE": fuso, "TZ": fuso,
        "N8N_RUNNERS_ENABLED": "true", "N8N_DIAGNOSTICS_ENABLED": "false",
        "EXECUTIONS_DATA_PRUNE": "true", "EXECUTIONS_DATA_MAX_AGE": "336",
        "N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS": "false", "RAILWAY_RUN_UID": "0",
    }


ETAPAS = [
    ("projeto", "Criar o projeto no Railway"),
    ("ambiente", "Encontrar o ambiente de produção"),
    ("servico", "Criar o serviço n8n (imagem oficial)"),
    ("config", "Configurar fuso horário, segurança e porta"),
    ("volume", "Criar o disco permanente (guarda seus dados)"),
    ("dominio", "Gerar o endereço público com https"),
    ("webhooks", "Configurar o endereço dos webhooks"),
    ("ligar", "Ligar o servidor"),
]


def instalar_etapa(chave: str, opc: dict):
    R = S.rw
    if chave == "projeto":
        inp = {"name": opc["projeto"], "description": "n8n instalado pelo n8n Fácil — MeusAgentesIA.com.br"}
        if opc.get("workspace_id"):
            inp["workspaceId"] = opc["workspace_id"]
        p = rw("mutation($i: ProjectCreateInput!) { projectCreate(input: $i) { id name } }", {"i": inp})["projectCreate"]
        R.update(project_id=p["id"], project_nome=p["name"], workspace_id=opc.get("workspace_id") or "")
    elif chave == "ambiente":
        envs = rw_projeto(R["project_id"])["ambientes"]
        if not envs:
            raise ErroAPI("O projeto foi criado, mas o Railway ainda não mostrou o ambiente. Clique em continuar em alguns segundos.")
        env = next((e for e in envs if e["name"].lower() == "production"), envs[0])
        R["env_id"] = env["id"]
    elif chave == "servico":
        s = rw("mutation($i: ServiceCreateInput!) { serviceCreate(input: $i) { id name } }",
               {"i": {"projectId": R["project_id"], "name": "n8n", "source": {"image": IMAGEM_N8N}}})["serviceCreate"]
        R["service_id"] = s["id"]
    elif chave == "config":
        rw_salvar_variaveis(variaveis_n8n(opc["fuso"]), aplicar=False)
        R["fuso"] = opc["fuso"]
    elif chave == "volume":
        v = rw("mutation($i: VolumeCreateInput!) { volumeCreate(input: $i) { id name } }",
               {"i": {"projectId": R["project_id"], "serviceId": R["service_id"], "environmentId": R["env_id"],
                      "mountPath": PASTA_DADOS}})["volumeCreate"]
        R["volume_id"] = v["id"]
    elif chave == "dominio":
        d = rw("mutation($i: ServiceDomainCreateInput!) { serviceDomainCreate(input: $i) { id domain } }",
               {"i": {"serviceId": R["service_id"], "environmentId": R["env_id"], "targetPort": PORTA_N8N}})["serviceDomainCreate"]
        R["domain"] = d["domain"]
    elif chave == "webhooks":
        dom = R["domain"]
        rw_salvar_variaveis({"N8N_HOST": dom, "WEBHOOK_URL": f"https://{dom}/", "N8N_EDITOR_BASE_URL": f"https://{dom}/"}, aplicar=False)
    elif chave == "ligar":
        rw_ligar(novo=True)
        R["instalado_em"] = agora()
        if not S.n8n_url:
            S.n8n_url = f"https://{R['domain']}"


def n8n_online(url: str) -> bool:
    try:
        return requests.get(url.rstrip("/") + "/healthz", timeout=8).status_code == 200
    except requests.RequestException:
        return False


STATUS_DEPLOY = {
    "SUCCESS": ("ok", "✅ Funcionando"), "BUILDING": ("neu", "🔧 Preparando"), "DEPLOYING": ("neu", "🚚 Ligando"),
    "INITIALIZING": ("neu", "⏳ Iniciando"), "QUEUED": ("neu", "⏳ Na fila"), "WAITING": ("neu", "⏳ Aguardando"),
    "FAILED": ("atr", "❌ Falhou"), "CRASHED": ("atr", "💥 Caiu"), "REMOVED": ("fim", "🗑️ Substituído"),
    "REMOVING": ("fim", "🗑️ Removendo"), "SLEEPING": ("fim", "😴 Dormindo"), "SKIPPED": ("fim", "⏭️ Pulado"),
}


# ══════════════════════════════════════════════════════════════════════════
# n8n (API pública REST)
# ══════════════════════════════════════════════════════════════════════════
def normalizar_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return ""
    if not re.match(r"^https?://", u):
        u = "https://" + u
    p = urlparse(u)
    return f"{p.scheme}://{p.netloc}"


def n8n(metodo: str, caminho: str, corpo=None, params=None, url: str = None, chave: str = None):
    base = normalizar_url(url or S.n8n_url)
    chave = (chave or S.n8n_key or "").strip()
    if not base or not chave:
        raise ErroAPI("Conecte seu n8n primeiro (aba 🔑 Conectar n8n).")
    try:
        r = requests.request(metodo, f"{base}/api/v1{caminho}", json=corpo, params=params, timeout=45,
                             headers={"X-N8N-API-KEY": chave, "Accept": "application/json"})
    except requests.RequestException as e:
        raise ErroAPI(f"Não consegui falar com o seu n8n ({e.__class__.__name__}). Ele está ligado? Veja a aba 🛠️ Servidor.")
    if r.status_code == 401:
        raise ErroAPI("🔑 O n8n recusou a chave da API. Crie uma nova em Settings → n8n API e cole na aba 🔑 Conectar n8n.")
    if r.status_code == 403:
        raise ErroAPI("🔒 Sua chave da API não tem permissão para isso. Crie a chave sem limitar as permissões (scopes).")
    if r.status_code in (502, 503, 504):
        raise ErroAPI("⏳ O n8n está ligando ou reiniciando. Espere 1 minuto e tente de novo.")
    if r.status_code >= 400:
        try:
            msg = r.json().get("message") or r.text[:300]
        except ValueError:
            msg = r.text[:300]
        if r.status_code == 404 and "/workflows" in caminho and caminho.count("/") <= 1:
            msg = "endereço errado ou API desligada. Confira o endereço do seu n8n."
        raise ErroAPI(f"O n8n respondeu (código {r.status_code}): {msg}")
    if not r.content:
        return {}
    try:
        return r.json()
    except ValueError:
        raise ErroAPI("O endereço respondeu, mas não parece ser um n8n. Confira o endereço.")


def n8n_listar() -> list:
    itens, cursor = [], None
    for _ in range(20):
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        d = n8n("GET", "/workflows", params=params)
        itens += d.get("data", [])
        cursor = d.get("nextCursor")
        if not cursor:
            break
    return itens


def n8n_execucoes(workflow_id: str = None, n: int = 20) -> list:
    params = {"limit": n}
    if workflow_id:
        params["workflowId"] = workflow_id
    return n8n("GET", "/executions", params=params).get("data", [])


def n8n_ativar(wid: str, ligar: bool = True):
    n8n("POST", f"/workflows/{wid}/{'activate' if ligar else 'deactivate'}")


def conectado_n8n() -> bool:
    return bool(S.n8n_url and S.n8n_key)


# ══════════════════════════════════════════════════════════════════════════
# CREDENCIAIS (criadas no n8n da pessoa — as senhas nunca vão para a memória)
# ══════════════════════════════════════════════════════════════════════════
def _assin(dados: dict) -> str:
    return hashlib.sha256(json.dumps(dados, sort_keys=True).encode()).hexdigest()[:12]


def garantir_credencial(chave: str, nome: str, tipo: str, dados: dict) -> dict:
    atual = S.cred_ids.get(chave)
    assin = _assin({"t": tipo, "d": dados})
    if atual and atual.get("assin") == assin and atual.get("url") == normalizar_url(S.n8n_url):
        return atual
    r = n8n("POST", "/credentials", {"name": nome, "type": tipo, "data": dados})
    S.cred_ids[chave] = {"id": str(r.get("id")), "name": r.get("name", nome), "assin": assin, "url": normalizar_url(S.n8n_url)}
    registrar("Credencial criada no n8n", nome)
    return S.cred_ids[chave]


def cred_ref(chave: str) -> dict:
    c = S.cred_ids.get(chave) or {}
    return {"id": c.get("id", "pendente"), "name": c.get("name", chave)}


def canal_pronto(canal: str) -> bool:
    c, s = S.canais, S.segredos
    if canal == "groq":
        return bool(S.u_chave)
    if canal == "whats":
        if c["whats_prov"] == "zapi":
            return bool(c["whats_inst"] and s["whats_token"])
        return bool(c["whats_base"] and c["whats_inst"] and s["whats_token"])
    if canal == "telegram":
        return bool(s["tg_token"] and c["tg_chat"])
    if canal == "email":
        return bool(c["smtp_host"] and c["smtp_user"] and s["smtp_senha"])
    return True


NOME_CANAL = {"groq": "🧠 IA (Groq)", "whats": "💬 WhatsApp", "telegram": "✈️ Telegram", "email": "📧 E-mail"}


def preparar_credenciais(canais: set):
    c, s = S.canais, S.segredos
    if "groq" in canais:
        garantir_credencial("groq", "Groq IA (n8n Fácil)", "httpHeaderAuth",
                            {"name": "Authorization", "value": f"Bearer {S.u_chave}"})
    if "whats" in canais:
        prov = c["whats_prov"]
        if prov == "evolution":
            garantir_credencial("whats", "WhatsApp Evolution (n8n Fácil)", "httpHeaderAuth", {"name": "apikey", "value": s["whats_token"]})
        elif prov == "meta":
            garantir_credencial("whats", "WhatsApp Cloud API (n8n Fácil)", "httpHeaderAuth",
                                {"name": "Authorization", "value": f"Bearer {s['whats_token']}"})
        elif prov == "zapi" and s["whats_client"]:
            garantir_credencial("whats", "Z-API Client-Token (n8n Fácil)", "httpHeaderAuth", {"name": "Client-Token", "value": s["whats_client"]})
    if "telegram" in canais:
        garantir_credencial("telegram", "Telegram (n8n Fácil)", "telegramApi", {"accessToken": s["tg_token"]})
    if "email" in canais:
        porta = int(c.get("smtp_port") or 465)
        garantir_credencial("email", "E-mail SMTP (n8n Fácil)", "smtp",
                            {"user": c["smtp_user"], "password": s["smtp_senha"], "host": c["smtp_host"],
                             "port": porta, "secure": porta == 465})


# ══════════════════════════════════════════════════════════════════════════
# PLANILHAS (tabelas de dados do próprio n8n — sem precisar de Google)
# ══════════════════════════════════════════════════════════════════════════
TABELAS = {
    "leads":   ("Leads e contatos", [("data", "string"), ("nome", "string"), ("telefone", "string"), ("email", "string"),
                                      ("interesse", "string"), ("origem", "string")]),
    "vendas":  ("Vendas", [("data", "string"), ("plataforma", "string"), ("produto", "string"), ("valor", "string"),
                           ("nome", "string"), ("email", "string"), ("telefone", "string"), ("status", "string")]),
    "atendimentos": ("Atendimentos WhatsApp", [("data", "string"), ("numero", "string"), ("nome", "string"),
                                               ("mensagem", "string"), ("resposta", "string")]),
}


def garantir_tabela(chave: str) -> str:
    nome, cols = TABELAS[chave]
    tabs = S.setdefault("tabelas", {})
    atual = tabs.get(chave)
    if atual and atual.get("url") == normalizar_url(S.n8n_url):
        return atual["id"]
    nome_n8n = f"{nome} (n8n Fácil)"
    try:
        existentes = n8n("GET", "/data-tables", params={"limit": 100}).get("data", [])
    except ErroAPI as e:
        if "404" in str(e):
            raise ErroAPI("Seu n8n é antigo e ainda não tem planilhas internas (Data tables). "
                          "Na aba 🛠️ Servidor clique em ⬆️ Atualizar n8n e tente de novo.")
        raise
    achada = next((t for t in existentes if t.get("name") == nome_n8n), None)
    if not achada:
        achada = n8n("POST", "/data-tables", {"name": nome_n8n, "columns": [{"name": c, "type": t} for c, t in cols]})
        registrar("Planilha criada no n8n", nome_n8n)
    tabs[chave] = {"id": str(achada["id"]), "nome": nome_n8n, "url": normalizar_url(S.n8n_url)}
    return tabs[chave]["id"]


def linhas_tabela(tid: str, limite: int = 1000) -> list:
    linhas, cursor = [], None
    while len(linhas) < limite:
        params = {"limit": 250}
        if cursor:
            params["cursor"] = cursor
        d = n8n("GET", f"/data-tables/{tid}/rows", params=params)
        linhas += d.get("data", [])
        cursor = d.get("nextCursor")
        if not cursor:
            break
    return linhas


# ══════════════════════════════════════════════════════════════════════════
# MONTADOR DE FLUXOS (gera o JSON que o n8n entende)
# ══════════════════════════════════════════════════════════════════════════
def js(s) -> str:
    """Texto -> literal de string JavaScript seguro dentro de uma expressão do n8n."""
    s = str(s).replace("{{", "{ {").replace("}}", "} }")
    return json.dumps(s, ensure_ascii=False)


def tpl_js(msg: str, mapa: dict) -> str:
    """'Oi {nome}!' -> expressão JS que troca {nome} pelo dado real."""
    partes, pos = [], 0
    for m in re.finditer(r"\{(\w+)\}", msg):
        if m.group(1) in mapa:
            if m.start() > pos:
                partes.append(js(msg[pos:m.start()]))
            partes.append(f"String({mapa[m.group(1)]} ?? '')")
            pos = m.end()
    if pos < len(msg):
        partes.append(js(msg[pos:]))
    return " + ".join(partes) or "''"


def D(no: str) -> str:
    return f"$('{no}').item.json"


RESPOSTA_IA = "$json.choices[0].message.content"


class Fluxo:
    def __init__(self, nome: str):
        self.nome, self.nodes, self.con = nome, [], {}

    def no(self, nome, tipo, versao, params, x, y=300, cred=None, webhook=None, continua=False, depois=None, saida=0):
        n = {"id": str(uuid.uuid4()), "name": nome, "type": tipo, "typeVersion": versao, "position": [x, y], "parameters": params}
        if cred:
            n["credentials"] = cred
        if webhook:
            n["webhookId"] = webhook
        if continua:
            n["onError"] = "continueRegularOutput"
        self.nodes.append(n)
        if depois:
            self.liga(depois, nome, saida)
        return nome

    def liga(self, de, para, saida=0):
        main = self.con.setdefault(de, {"main": []})["main"]
        while len(main) <= saida:
            main.append([])
        main[saida].append({"node": para, "type": "main", "index": 0})

    # ── gatilhos ──
    def webhook(self, nome, path, x=0, y=300):
        return self.no(nome, "n8n-nodes-base.webhook", 2, {"httpMethod": "POST", "path": path, "responseMode": "onReceived", "options": {}},
                       x, y, webhook=str(uuid.uuid4()))

    def formulario(self, nome, titulo, descricao, campos, path, x=0, y=300, final="Recebemos seus dados. Obrigado!"):
        vals = []
        for rot, tipo, obrig in campos:
            v = {"fieldLabel": rot, "fieldType": tipo, "requiredField": bool(obrig)}
            vals.append(v)
        return self.no(nome, "n8n-nodes-base.formTrigger", 2.2,
                       {"formTitle": titulo, "formDescription": descricao, "formFields": {"values": vals},
                        "responseMode": "onReceived", "options": {"path": path, "appendAttribution": False, "respondWithOptions": {
                            "values": {"respondWith": "text", "formSubmittedText": final}}}},
                       x, y, webhook=str(uuid.uuid4()))

    def agenda(self, nome, hora: str, dias: list, x=0, y=300):
        h, m = (hora or "09:00").split(":")[:2]
        idx = sorted(DIAS_SEMANA.index(d) for d in dias) if dias and len(dias) < 7 else None
        cron = f"{int(m)} {int(h)} * * {','.join(map(str, idx)) if idx else '*'}"
        return self.no(nome, "n8n-nodes-base.scheduleTrigger", 1.2, {"rule": {"interval": [{"field": "cronExpression", "expression": cron}]}}, x, y)

    def rss(self, nome, url, x=0, y=300):
        return self.no(nome, "n8n-nodes-base.rssFeedReadTrigger", 1, {"feedUrl": url, "pollTimes": {"item": [{"mode": "everyHour"}]}}, x, y)

    # ── ações ──
    def codigo(self, nome, codigo_js, x, y=300, depois=None):
        return self.no(nome, "n8n-nodes-base.code", 2, {"jsCode": codigo_js.strip()}, x, y, depois=depois)

    def http(self, nome, url, corpo_expr=None, cred=None, x=0, y=300, depois=None, metodo="POST", query=None, espacar=False, continua=True):
        p = {"method": metodo, "url": url, "options": {}}
        if cred:
            p.update(authentication="genericCredentialType", genericAuthType="httpHeaderAuth")
        if corpo_expr:
            p.update(sendBody=True, specifyBody="json", jsonBody="={{ JSON.stringify(" + corpo_expr + ") }}")
        if query:
            p.update(sendQuery=True, queryParameters={"parameters": [{"name": k, "value": v} for k, v in query.items()]})
        if espacar:
            p["options"] = {"batching": {"batch": {"batchSize": 1, "batchInterval": 4000}}}
        return self.no(nome, "n8n-nodes-base.httpRequest", 4.2, p, x, y, cred={"httpHeaderAuth": cred_ref(cred)} if cred else None,
                       continua=continua, depois=depois)

    def ia(self, nome, sistema, usuario_expr, x, y=300, depois=None, temperatura=0.7):
        corpo = ("{ model: '%s', temperature: %s, reasoning_effort: 'low', messages: [ { role: 'system', content: %s }, "
                 "{ role: 'user', content: String(%s) } ] }") % (MODELO, temperatura, js(sistema), usuario_expr)
        return self.http(nome, GROQ_URL, corpo, cred="groq", x=x, y=y, depois=depois, continua=False)

    def whats(self, nome, numero_expr, texto_expr, x, y=300, depois=None, espacar=False):
        c, s = S.canais, S.segredos
        prov = c["whats_prov"]
        if prov == "zapi":
            url = f"https://api.z-api.io/instances/{c['whats_inst']}/token/{s['whats_token'] or 'SEU_TOKEN'}/send-text"
            corpo = f"{{ phone: String({numero_expr}), message: String({texto_expr}) }}"
            cred = "whats" if s.get("whats_client") else None
        elif prov == "meta":
            url = f"https://graph.facebook.com/v21.0/{c['whats_inst']}/messages"
            corpo = (f"{{ messaging_product: 'whatsapp', to: String({numero_expr}), type: 'text', "
                     f"text: {{ body: String({texto_expr}) }} }}")
            cred = "whats"
        else:
            url = f"{c['whats_base'].rstrip('/')}/message/sendText/{c['whats_inst']}"
            corpo = f"{{ number: String({numero_expr}), text: String({texto_expr}) }}"
            cred = "whats"
        return self.http(nome, url, corpo, cred=cred, x=x, y=y, depois=depois, espacar=espacar)

    def telegram(self, nome, texto_expr, x, y=300, depois=None):
        return self.no(nome, "n8n-nodes-base.telegram", 1.2,
                       {"chatId": S.canais["tg_chat"], "text": "={{ String(" + texto_expr + ").slice(0, 4000) }}",
                        "additionalFields": {"appendAttribution": False}},
                       x, y, cred={"telegramApi": cred_ref("telegram")}, continua=True, depois=depois)

    def email(self, nome, para, assunto_expr, texto_expr, x, y=300, depois=None):
        c = S.canais
        return self.no(nome, "n8n-nodes-base.emailSend", 2.1,
                       {"fromEmail": c.get("email_de") or c.get("smtp_user"), "toEmail": para,
                        "subject": "={{ " + assunto_expr + " }}", "emailFormat": "text", "text": "={{ " + texto_expr + " }}",
                        "options": {"appendAttribution": False}},
                       x, y, cred={"smtp": cred_ref("email")}, continua=True, depois=depois)

    def avisar(self, destino, nome, texto_expr, x, y=300, depois=None, assunto="'Aviso do n8n Fácil'"):
        if destino == "whats":
            return self.whats(nome, js((numeros_validos(S.canais.get("whats_dono", "")) or [""])[0]), texto_expr, x, y, depois=depois)
        if destino == "telegram":
            return self.telegram(nome, texto_expr, x, y, depois=depois)
        if destino == "email":
            return self.email(nome, S.canais.get("email_para") or S.canais.get("smtp_user"), assunto, texto_expr, x, y, depois=depois)
        return depois

    def tabela(self, nome, tabela_id, x, y=300, depois=None):
        return self.no(nome, "n8n-nodes-base.dataTable", 1,
                       {"resource": "row", "operation": "insert", "dataTableId": {"__rl": True, "mode": "id", "value": tabela_id},
                        "columns": {"mappingMode": "autoMapInputData", "value": {}}, "options": {}},
                       x, y, continua=True, depois=depois)

    def esperar(self, nome, qtd, unidade, x, y=300, depois=None):
        return self.no(nome, "n8n-nodes-base.wait", 1.1, {"amount": qtd, "unit": unidade}, x, y, webhook=str(uuid.uuid4()), depois=depois)

    def json(self) -> dict:
        return {"name": self.nome, "nodes": self.nodes, "connections": self.con, "settings": {"executionOrder": "v1"}}


# ── códigos JavaScript usados dentro dos fluxos ───────────────────────────
JS_LER_WHATS = r"""
// Lê a mensagem recebida (Evolution API, Z-API ou WhatsApp Cloud API da Meta)
const b = $json.body ?? $json;
let numero = '', texto = '', nome = '', deMim = false, grupo = false;
if (b.data && b.data.key) {                      // Evolution API
  const d = b.data, jid = String(d.key.remoteJid || '');
  numero = jid.split('@')[0]; grupo = jid.includes('@g.us'); deMim = !!d.key.fromMe; nome = d.pushName || '';
  const m = d.message || {};
  texto = m.conversation || (m.extendedTextMessage && m.extendedTextMessage.text) || (m.imageMessage && m.imageMessage.caption) || '';
} else if (b.phone !== undefined) {              // Z-API
  numero = String(b.phone || ''); deMim = !!b.fromMe; grupo = !!b.isGroup; nome = b.senderName || b.chatName || '';
  texto = (b.text && b.text.message) || (b.image && b.image.caption) || '';
} else if (b.entry) {                            // WhatsApp Cloud API (Meta)
  const v = (((b.entry[0] || {}).changes || [])[0] || {}).value || {};
  const m = (v.messages || [])[0] || {};
  numero = m.from || ''; texto = (m.text && m.text.body) || '';
  nome = (((v.contacts || [])[0] || {}).profile || {}).name || '';
}
numero = String(numero).replace(/\D/g, '');
if (!numero || !texto || deMim || grupo) return [];   // ignora grupos, mensagens suas e mídias sem texto
return [{ json: { numero, texto, nome, primeiro_nome: (nome.split(' ')[0] || '') } }];
"""

JS_LEAD = r"""
// Organiza os dados do formulário
const j = $json;
const pega = (re) => { for (const [k, v] of Object.entries(j)) if (re.test(k)) return String(v ?? '').trim(); return ''; };
let tel = pega(/whats|telefone|celular|fone/i).replace(/\D/g, '');
if (tel.length === 10 || tel.length === 11) tel = '55' + tel;
const nome = pega(/nome/i);
const extras = Object.entries(j).filter(([k]) => !/nome|whats|telefone|celular|fone|e-?mail|submittedAt|formMode/i.test(k))
  .map(([k, v]) => k + ': ' + v).join(' | ');
return [{ json: { data: $now.toFormat('dd/MM/yyyy HH:mm'),
  nome, primeiro_nome: nome.split(' ')[0] || '', telefone: tel, email: pega(/e-?mail/i), interesse: extras, origem: 'Formulário' } }];
"""

JS_VENDA = r"""
// Entende o aviso de venda da Hotmart, Kiwify, Monetizze, Eduzz, Braip, Perfect Pay e outras
let corpo = $json.body ?? $json;
if (typeof corpo.json === 'string') { try { corpo = JSON.parse(corpo.json); } catch (e) {} }
const plano = {};
(function achatar(o, p) {
  if (o && typeof o === 'object') { for (const [k, v] of Object.entries(o)) achatar(v, p ? p + '.' + k : k); }
  else plano[String(p).toLowerCase().replace(/\[/g, '.').replace(/\]/g, '').replace(/\.+/g, '.')] = o;
})(corpo, '');
const pega = (regs, nao) => {
  for (const r of regs) for (const [k, v] of Object.entries(plano))
    if (r.test(k) && !(nao && nao.test(k)) && v !== null && v !== undefined && String(v).trim() !== '') return String(v).trim();
  return '';
};
const quem = /(buyer|comprador|customer|cliente|client|lead)/;
const nome = pega([new RegExp(quem.source + '.*(full_?name|nome|name)$'), /(^|\.)(full_?name|nome_?cliente|client_name|name|nome)$/], /(product|produto|offer|oferta|plan|affiliate|afiliado|producer|produtor)/);
const email = pega([new RegExp(quem.source + '.*e?-?mail'), /e-?mail/], /(producer|produtor|affiliate|afiliado)/);
let telefone = pega([new RegExp(quem.source + '.*(checkout_phone|phone|telefone|celular|mobile|whats|cel)'), /(checkout_phone|phone|telefone|celular|mobile|whats)/],
  /(producer|produtor|affiliate|afiliado|code|ddd$)/).replace(/\D/g, '');
const ddd = pega([/ddd/]).replace(/\D/g, '');
if (ddd && telefone.length <= 9) telefone = ddd + telefone;
if (telefone.length === 10 || telefone.length === 11) telefone = '55' + telefone;
const produto = pega([/(product|produto).*(name|nome)$/, /product_name|nome_produto|produto$/]);
let valor = pega([/purchase\.price\.value|full_price\.value|charge_amount|venda\.valor|sale_amount|valor_?total|(^|\.)(valor|price|amount)$/]);
if (plano['commissions.charge_amount'] !== undefined && valor === String(plano['commissions.charge_amount']).trim()) valor = (Number(valor) / 100).toFixed(2);
const link = pega([/(checkout|recovery|recuperacao|payment|boleto|pix).*(url|link)/, /(sale_url|checkout_link)/]);
const statusTxt = Object.entries(plano).filter(([k]) => /(event|status|tipo|type|situacao)/.test(k)).map(([, v]) => String(v)).join(' ').toLowerCase();
const chaves = Object.keys(plano).join(' ');
const plataforma = /hottok|hotmart|purchase\.transaction|data\.purchase\.status|data\.buyer\./.test(chaves) ? 'Hotmart' : /kiwify|webhook_event_type|order_status/.test(chaves) ? 'Kiwify'
  : /monetizze|chave_unica|comprador\./.test(chaves) ? 'Monetizze' : /eduzz|trans_cod|cus_name/.test(chaves) ? 'Eduzz'
  : /braip/.test(chaves) ? 'Braip' : /perfect/.test(chaves) ? 'Perfect Pay' : 'Outra';
const negado = /refund|reembols|cancel|chargeback|estorn|dispute|expired|expirad|recusad|refused/.test(statusTxt);
const aprovado = !negado && /approved|aprovad|paid|pago|finaliz|complete|conclu|order_approved|purchase_complete/.test(statusTxt);
const pendente = !negado && !aprovado && /abandon|cart|carrinho|billet|boleto|pix|waiting|aguardando|pending|pendente|printed|gerad|delayed/.test(statusTxt);
const dados = { data: $now.toFormat('dd/MM/yyyy HH:mm'), plataforma, produto, valor,
  nome, primeiro_nome: nome.split(' ')[0] || '', email, telefone, link, status: aprovado ? 'aprovada' : pendente ? 'pendente' : (negado ? 'cancelada' : statusTxt.slice(0, 60)) };
const MODO = '__MODO__';
if (MODO === 'aprovada' && !aprovado) return [];
if (MODO === 'pendente' && !pendente) return [];
return [{ json: dados }];
"""

JS_LINHA_VENDA = r"""
const v = $('Dados da venda').item.json;
return [{ json: { data: v.data, plataforma: v.plataforma, produto: v.produto, valor: v.valor, nome: v.nome, email: v.email, telefone: v.telefone, status: v.status } }];
"""

JS_LINHA_ATEND = r"""
const m = $('Ler mensagem').item.json;
return [{ json: { data: $now.toFormat('dd/MM/yyyy HH:mm'), numero: m.numero, nome: m.nome,
  mensagem: m.texto, resposta: String($('IA responde').item.json.choices[0].message.content || '') } }];
"""


def js_lista_numeros(numeros: list) -> str:
    return "return " + json.dumps([{"json": {"numero": n}} for n in numeros]) + ";"


def numeros_validos(txt: str) -> list:
    saida = []
    for linha in re.split(r"[\n,;]+", txt or ""):
        n = re.sub(r"\D", "", linha)
        if len(n) in (10, 11):
            n = "55" + n
        if len(n) >= 12:
            saida.append(n)
    return list(dict.fromkeys(saida))


# ══════════════════════════════════════════════════════════════════════════
# MODELOS PRONTOS (as automações que a pessoa cria com 1 clique)
# ══════════════════════════════════════════════════════════════════════════
def _destino_txt(d):
    return {"whats": "no seu WhatsApp", "telegram": "no seu Telegram", "email": "no seu e-mail", "nenhum": ""}.get(d, "")


def m_atendente(cfg):
    f = Fluxo(cfg["nome"])
    path = cfg["path"]
    sistema = (f"Você é a atendente virtual de {cfg['negocio']} no WhatsApp. Tom: {cfg['tom']}. Responda em português do Brasil, "
               "com mensagens curtas (até 4 frases), sem markdown, sem asteriscos e sem inventar nada. Use emojis com moderação. "
               f"Informações do negócio (use só isto): {cfg['info']}. Se a pessoa pedir algo que não está nas informações, "
               "ou pedir para falar com uma pessoa, diga com gentileza que um atendente humano vai responder em breve.")
    f.webhook("Mensagem recebida", path)
    f.codigo("Ler mensagem", JS_LER_WHATS, 260, depois="Mensagem recebida")
    f.ia("IA responde", sistema, f"'Cliente: ' + ({D('Ler mensagem')}.nome || 'sem nome') + '\\nMensagem: ' + {D('Ler mensagem')}.texto", 520, depois="Ler mensagem")
    f.whats("Responder no WhatsApp", f"{D('Ler mensagem')}.numero", RESPOSTA_IA, 780, depois="IA responde")
    canais = {"groq", "whats"}
    if cfg.get("salvar"):
        f.codigo("Organizar conversa", JS_LINHA_ATEND, 1040, depois="Responder no WhatsApp")
        f.tabela("Salvar na planilha", "{{TAB:atendimentos}}", 1300, depois="Organizar conversa")
    return f, canais, {"tipo": "webhook", "path": path,
                       "instrucao": "Cole este endereço no painel do seu WhatsApp (Evolution API: Webhook → evento MESSAGES_UPSERT; "
                                    "Z-API: Webhooks → Ao receber)."}


def m_lead_whats(cfg):
    f = Fluxo(cfg["nome"])
    campos = [("Nome", "text", True), ("WhatsApp (com DDD)", "text", True), ("E-mail", "email", False)]
    if cfg.get("pergunta"):
        campos.append((cfg["pergunta"], "textarea", False))
    f.formulario("Formulário", cfg["titulo"], cfg.get("descricao", ""), campos, cfg["path"], final=cfg.get("obrigado") or "Recebemos seus dados. Obrigado!")
    f.codigo("Organizar lead", JS_LEAD, 260, depois="Formulário")
    ult = f.whats("Boas-vindas no WhatsApp", f"{D('Organizar lead')}.telefone",
                  tpl_js(cfg["mensagem"], {"nome": f"{D('Organizar lead')}.primeiro_nome"}), 520, depois="Organizar lead")
    canais = {"whats"}
    x = 780
    if cfg.get("salvar"):
        f.codigo("Linha da planilha", "const l = $('Organizar lead').item.json; delete l.primeiro_nome; return [{ json: l }];", x, depois=ult)
        ult = f.tabela("Salvar na planilha", "{{TAB:leads}}", x + 260, depois="Linha da planilha")
        x += 520
    if cfg["avisar"] != "nenhum":
        texto = (f"'🎯 Novo lead!\\nNome: ' + {D('Organizar lead')}.nome + '\\nWhatsApp: ' + {D('Organizar lead')}.telefone + "
                 f"'\\nE-mail: ' + {D('Organizar lead')}.email + '\\n' + {D('Organizar lead')}.interesse")
        f.avisar(cfg["avisar"], "Avisar você", texto, x, depois=ult, assunto="'🎯 Novo lead: ' + " + f"{D('Organizar lead')}.nome")
        canais.add(cfg["avisar"])
    return f, canais, {"tipo": "form", "path": cfg["path"], "instrucao": "Divulgue este link (bio do Instagram, botão do site, anúncios)."}


def m_whats_agendado(cfg):
    f = Fluxo(cfg["nome"])
    nums = numeros_validos(cfg["numeros"])
    f.agenda("Horário marcado", cfg["hora"], cfg["dias"])
    f.codigo("Lista de contatos", js_lista_numeros(nums), 260, depois="Horário marcado")
    ant, canais = "Lista de contatos", {"whats"}
    texto = js(cfg["mensagem"])
    if cfg.get("variar"):
        f.ia("IA varia o texto", "Reescreva a mensagem a seguir com outras palavras, mantendo o sentido, o tom e o tamanho. "
                                "Responda só com a mensagem, sem aspas e sem markdown.", js(cfg["mensagem"]), 520, depois=ant)
        ant, texto, canais = "IA varia o texto", RESPOSTA_IA, canais | {"groq"}
    f.whats("Enviar no WhatsApp", f"{D('Lista de contatos')}.numero", texto, 780, depois=ant, espacar=True)
    return f, canais, {"tipo": "agenda", "instrucao": f"Envia para {len(nums)} contato(s) no horário marcado, com 4 segundos entre cada envio."}


def m_form_planilha(cfg):
    f = Fluxo(cfg["nome"])
    campos = [("Nome", "text", True), ("WhatsApp (com DDD)", "text", bool(cfg.get("tel_obrig"))), ("E-mail", "email", True)]
    for linha in (cfg.get("extras") or "").splitlines():
        if linha.strip():
            campos.append((linha.strip()[:60], "text", False))
    f.formulario("Formulário", cfg["titulo"], cfg.get("descricao", ""), campos, cfg["path"], final=cfg.get("obrigado") or "Recebemos seus dados. Obrigado!")
    f.codigo("Organizar dados", JS_LEAD, 260, depois="Formulário")
    f.codigo("Linha da planilha", "const l = $('Organizar dados').item.json; delete l.primeiro_nome; return [{ json: l }];", 520, depois="Organizar dados")
    ult = f.tabela("Salvar na planilha", "{{TAB:leads}}", 780, depois="Linha da planilha")
    canais, x = set(), 1040
    if cfg.get("responder") and cfg.get("resposta"):
        ult = f.email("E-mail para a pessoa", "={{ " + f"{D('Organizar dados')}.email" + " }}", js(cfg.get("assunto") or "Recebemos seu contato"),
                      tpl_js(cfg["resposta"], {"nome": f"{D('Organizar dados')}.primeiro_nome"}), x, depois=ult)
        canais.add("email")
        x += 260
    if cfg["avisar"] != "nenhum":
        texto = (f"'📝 Nova resposta no formulário!\\nNome: ' + {D('Organizar dados')}.nome + '\\nE-mail: ' + {D('Organizar dados')}.email + "
                 f"'\\nWhatsApp: ' + {D('Organizar dados')}.telefone + '\\n' + {D('Organizar dados')}.interesse")
        f.avisar(cfg["avisar"], "Avisar você", texto, x, depois=ult, assunto="'📝 Nova resposta: ' + " + f"{D('Organizar dados')}.nome")
        canais.add(cfg["avisar"])
    return f, canais, {"tipo": "form", "path": cfg["path"], "instrucao": "Cada resposta entra na planilha “Leads e contatos” (veja na aba 📊 Planilhas)."}


def m_resposta_ia_email(cfg):
    f = Fluxo(cfg["nome"])
    campos = [("Nome", "text", True), ("E-mail", "email", True), ("Sua mensagem", "textarea", True)]
    f.formulario("Formulário de contato", cfg["titulo"], cfg.get("descricao", ""), campos, cfg["path"],
                 final="Recebemos sua mensagem! Você vai receber a resposta no seu e-mail em instantes.")
    f.codigo("Organizar dados", JS_LEAD, 260, depois="Formulário de contato")
    sistema = (f"Você responde e-mails de contato em nome de {cfg['negocio']}. Tom: {cfg['tom']}. Escreva em português do Brasil, "
               "um e-mail curto e cordial, sem markdown, começando pelo nome da pessoa e terminando com uma assinatura com o nome do negócio. "
               f"Use só estas informações: {cfg['info']}. Se a resposta não estiver nas informações, diga que a equipe vai responder pessoalmente.")
    f.ia("IA escreve a resposta", sistema, f"'Nome: ' + {D('Organizar dados')}.nome + '\\nMensagem: ' + {D('Organizar dados')}.interesse", 520, depois="Organizar dados")
    ult = f.email("Responder por e-mail", "={{ " + f"{D('Organizar dados')}.email" + " }}", js(f"Re: seu contato com {cfg['negocio']}"), RESPOSTA_IA, 780,
                  depois="IA escreve a resposta")
    canais = {"groq", "email"}
    if cfg["avisar"] != "nenhum":
        texto = (f"'📩 Contato respondido pela IA\\nDe: ' + {D('Organizar dados')}.nome + ' (' + {D('Organizar dados')}.email + ')\\n\\nPergunta: ' + "
                 f"{D('Organizar dados')}.interesse + '\\n\\nResposta enviada:\\n' + {D('IA escreve a resposta')}.choices[0].message.content")
        f.avisar(cfg["avisar"], "Cópia para você", texto, 1040, depois=ult, assunto="'📩 Contato respondido: ' + " + f"{D('Organizar dados')}.nome")
        canais.add(cfg["avisar"])
    return f, canais, {"tipo": "form", "path": cfg["path"], "instrucao": "Coloque este link no botão “Fale conosco” do seu site ou Instagram."}


def m_relatorio(cfg):
    f = Fluxo(cfg["nome"])
    f.agenda("Horário do relatório", cfg["hora"], cfg["dias"])
    tab = cfg["tabela"]
    f.no("Ler a planilha", "n8n-nodes-base.dataTable", 1,
         {"resource": "row", "operation": "get", "dataTableId": {"__rl": True, "mode": "id", "value": "{{TAB:%s}}" % tab}, "returnAll": True,
          "options": {}}, 260, depois="Horário do relatório")
    resumo = r"""
const linhas = $input.all().map(i => i.json).filter(l => l && Object.keys(l).length);
const ultimas = linhas.slice(-60).map(l => Object.entries(l).filter(([k]) => !['id', 'createdAt', 'updatedAt'].includes(k)).map(([k, v]) => k + ': ' + v).join(' | '));
return [{ json: { total: linhas.length, amostra: ultimas.join('\n') } }];
"""
    f.no("Resumir dados", "n8n-nodes-base.code", 2, {"jsCode": resumo.strip(), "mode": "runOnceForAllItems"}, 520, depois="Ler a planilha")
    f.ia("IA escreve o relatório", "Você é um analista de negócios. Escreva um relatório curto em português do Brasil, sem markdown, com: "
                                  "1) números principais, 2) destaques, 3) três ações práticas para a próxima semana. Use só os dados recebidos.",
         f"'Planilha: {TABELAS[tab][0]}\\nTotal de linhas: ' + $json.total + '\\nRegistros mais recentes:\\n' + $json.amostra", 780, depois="Resumir dados")
    f.avisar(cfg["avisar"], "Enviar relatório", RESPOSTA_IA, 1040, depois="IA escreve o relatório", assunto=js(f"📊 Relatório — {TABELAS[tab][0]}"))
    return f, {"groq", cfg["avisar"]}, {"tipo": "agenda", "instrucao": "O relatório chega no horário marcado, com base nos dados da planilha."}


def m_post_diario(cfg):
    f = Fluxo(cfg["nome"])
    f.agenda("Horário do post", cfg["hora"], cfg["dias"])
    sistema = (f"Você é social media de {cfg['negocio']} (nicho: {cfg['nicho']}; público: {cfg['publico']}; tom: {cfg['tom']}). "
               f"Crie UM post pronto para {cfg['rede']} em português do Brasil, sem markdown, no formato:\n"
               "IDEIA DA IMAGEM: (descrição da arte ou do vídeo)\nLEGENDA: (texto pronto, com gancho na primeira linha e chamada para ação)\n"
               "HASHTAGS: (8 a 12 hashtags)\nNão repita ideias comuns; varie o formato (dica, bastidor, prova social, pergunta, oferta).")
    tema = js(cfg.get("temas") or "")
    f.ia("IA cria o post", sistema, f"'Data de hoje: ' + $now.toFormat('dd/MM/yyyy') + '. Temas sugeridos: ' + {tema} + '. Escolha um ângulo novo.'", 260,
         depois="Horário do post", temperatura=0.9)
    f.avisar(cfg["avisar"], "Enviar o post para você", "'📣 Post de hoje para " + cfg["rede"] + "\\n\\n' + " + RESPOSTA_IA, 520,
             depois="IA cria o post", assunto="'📣 Seu post de hoje está pronto'")
    return f, {"groq", cfg["avisar"]}, {"tipo": "agenda", "instrucao": f"Todo dia marcado você recebe o post pronto {_destino_txt(cfg['avisar'])}."}


def m_rss_post(cfg):
    f = Fluxo(cfg["nome"])
    f.rss("Novidade no blog/site", cfg["feed"])
    sistema = (f"Você transforma artigos em posts para {cfg['rede']} de {cfg['negocio']} (tom: {cfg['tom']}). Escreva em português do Brasil, sem markdown: "
               "LEGENDA pronta com gancho, 3 pontos principais e chamada para ler o artigo completo, e depois HASHTAGS (8 a 10).")
    f.ia("IA cria o post", sistema, "'Título: ' + $json.title + '\\nResumo: ' + ($json.contentSnippet || $json.content || '').slice(0, 3000) + '\\nLink: ' + $json.link",
         260, depois="Novidade no blog/site")
    f.avisar(cfg["avisar"], "Enviar o post para você",
             "'📰 Post a partir de: ' + " + D("Novidade no blog/site") + ".title + '\\n' + " + D("Novidade no blog/site") + ".link + '\\n\\n' + " + RESPOSTA_IA,
             520, depois="IA cria o post", assunto="'📰 Novo post a partir do blog'")
    return f, {"groq", cfg["avisar"]}, {"tipo": "rss", "instrucao": "A cada hora o n8n confere o endereço; cada novidade vira um post pronto."}


def m_facebook(cfg):
    f = Fluxo(cfg["nome"])
    f.agenda("Horário da publicação", cfg["hora"], cfg["dias"])
    sistema = (f"Você é social media de {cfg['negocio']} (nicho: {cfg['nicho']}; tom: {cfg['tom']}). Escreva UM post para a Página do Facebook em "
               "português do Brasil, pronto para publicar: sem markdown, sem 'LEGENDA:', com gancho, conteúdo útil, chamada para ação e 3 a 5 hashtags.")
    f.ia("IA cria o post", sistema, f"'Data: ' + $now.toFormat('dd/MM/yyyy') + '. Temas: ' + {js(cfg.get('temas') or '')}", 260, depois="Horário da publicação",
         temperatura=0.9)
    f.http("Publicar na Página", f"https://graph.facebook.com/v21.0/{cfg['pagina_id']}/feed", None, None, 520, depois="IA cria o post",
           query={"message": "={{ " + RESPOSTA_IA + " }}", "access_token": cfg["pagina_token"]}, continua=False)
    canais = {"groq"}
    if cfg["avisar"] != "nenhum":
        f.avisar(cfg["avisar"], "Avisar você", "'✅ Post publicado na sua Página do Facebook:\\n\\n' + " + f"{D('IA cria o post')}.choices[0].message.content",
                 780, depois="Publicar na Página", assunto="'✅ Post publicado no Facebook'")
        canais.add(cfg["avisar"])
    return f, canais, {"tipo": "agenda", "instrucao": "Publica sozinho na sua Página no horário marcado."}


def m_venda(cfg):
    f = Fluxo(cfg["nome"])
    f.webhook("Aviso de venda", cfg["path"])
    f.codigo("Dados da venda", JS_VENDA.replace("__MODO__", "aprovada"), 260, depois="Aviso de venda")
    ult, x, canais = "Dados da venda", 520, set()
    v = D("Dados da venda")
    mapa = {"nome": f"{v}.primeiro_nome", "produto": f"{v}.produto", "valor": f"{v}.valor"}
    if cfg.get("whats_cliente") and cfg.get("msg_whats"):
        ult = f.whats("Boas-vindas no WhatsApp", f"{v}.telefone", tpl_js(cfg["msg_whats"], mapa), x, depois=ult)
        canais.add("whats")
        x += 260
    if cfg.get("email_cliente") and cfg.get("msg_email"):
        ult = f.email("E-mail para o cliente", "={{ " + f"{v}.email" + " }}", tpl_js(cfg.get("assunto_email") or "Seu acesso a {produto}", mapa),
                      tpl_js(cfg["msg_email"], mapa), x, depois=ult)
        canais.add("email")
        x += 260
    if cfg.get("salvar"):
        f.codigo("Linha da planilha", JS_LINHA_VENDA, x, depois=ult)
        ult = f.tabela("Salvar na planilha", "{{TAB:vendas}}", x + 260, depois="Linha da planilha")
        x += 520
    if cfg["avisar"] != "nenhum":
        texto = (f"'💰 VENDA APROVADA! (' + {v}.plataforma + ')\\nProduto: ' + {v}.produto + '\\nValor: ' + {v}.valor + "
                 f"'\\nCliente: ' + {v}.nome + '\\nE-mail: ' + {v}.email + '\\nWhatsApp: ' + {v}.telefone")
        f.avisar(cfg["avisar"], "Avisar você", texto, x, depois=ult, assunto="'💰 Nova venda: ' + " + f"{v}.produto")
        canais.add(cfg["avisar"])
    return f, canais, {"tipo": "webhook", "path": cfg["path"],
                       "instrucao": "Cole este endereço como Webhook/Postback na sua plataforma (Hotmart: Ferramentas → Webhook; "
                                    "Kiwify: Apps → Webhooks; Monetizze: Ferramentas → Postback)."}


def m_recuperacao(cfg):
    f = Fluxo(cfg["nome"])
    f.webhook("Aviso da plataforma", cfg["path"])
    f.codigo("Dados da venda", JS_VENDA.replace("__MODO__", "pendente"), 260, depois="Aviso da plataforma")
    f.esperar("Esperar", int(cfg["espera"]), cfg["unidade"], 520, depois="Dados da venda")
    v = D("Dados da venda")
    mapa = {"nome": f"{v}.primeiro_nome", "produto": f"{v}.produto", "link": f"{v}.link", "valor": f"{v}.valor"}
    f.whats("Mensagem de recuperação", f"{v}.telefone", tpl_js(cfg["mensagem"], mapa), 780, depois="Esperar")
    canais = {"whats"}
    if cfg["avisar"] != "nenhum":
        f.avisar(cfg["avisar"], "Avisar você", f"'🛒 Recuperação enviada para ' + {v}.nome + ' (' + {v}.telefone + ') — ' + {v}.produto",
                 1040, depois="Mensagem de recuperação", assunto="'🛒 Recuperação de venda enviada'")
        canais.add(cfg["avisar"])
    return f, canais, {"tipo": "webhook", "path": cfg["path"],
                       "instrucao": "Cole este endereço na plataforma marcando os eventos de carrinho abandonado, boleto e Pix gerado."}


DEST = ["whats", "telegram", "email", "nenhum"]
NOME_DEST = {"whats": "💬 Meu WhatsApp", "telegram": "✈️ Meu Telegram", "email": "📧 Meu e-mail", "nenhum": "🚫 Não avisar"}
TONS = ["Simpático e acolhedor", "Profissional e objetivo", "Divertido e descontraído", "Premium e elegante"]

MODELOS = {
    "atendente": {"cat": "whats", "titulo": "🤖 Atendente IA 24h no WhatsApp", "fn": m_atendente,
                  "desc": "Responde sozinho cada mensagem que chega no seu WhatsApp, com as informações do seu negócio.",
                  "campos": [("negocio", "Nome do negócio", "texto", ""), ("info", "O que a IA precisa saber (produtos, preços, horário, endereço, regras)", "area", ""),
                             ("tom", "Tom de voz", "tom", TONS[0]), ("salvar", "Guardar cada conversa na planilha “Atendimentos”", "check", True)]},
    "lead_whats": {"cat": "whats", "titulo": "🎯 Formulário de lead + boas-vindas no WhatsApp", "fn": m_lead_whats,
                   "desc": "Cria um formulário online; quem preencher recebe na hora uma mensagem sua no WhatsApp e você é avisado.",
                   "campos": [("titulo", "Título do formulário", "texto", "Quero saber mais"), ("descricao", "Texto abaixo do título", "texto", "Preencha e receba as informações no seu WhatsApp."),
                              ("pergunta", "Pergunta extra (opcional)", "texto", "Qual é o seu interesse?"),
                              ("mensagem", "Mensagem de boas-vindas — use {nome}", "area", "Oi, {nome}! 👋 Recebi seu cadastro. Em que posso te ajudar?"),
                              ("obrigado", "Mensagem na tela depois de enviar", "texto", "Pronto! Confira seu WhatsApp. 😉"),
                              ("salvar", "Guardar cada lead na planilha “Leads e contatos”", "check", True), ("avisar", "Avisar você em", "destino", "telegram")]},
    "whats_agendado": {"cat": "whats", "titulo": "⏰ Mensagens agendadas no WhatsApp", "fn": m_whats_agendado,
                       "desc": "Envia uma mensagem para uma lista de contatos nos dias e horário que você escolher (lembretes, avisos, ofertas).",
                       "campos": [("numeros", "Números (um por linha, com DDD)", "area", ""), ("mensagem", "Mensagem", "area", ""),
                                  ("dias", "Dias", "dias", ["Segunda", "Quarta", "Sexta"]), ("hora", "Horário", "hora", "09:00"),
                                  ("variar", "Deixar a IA variar o texto a cada envio (parece menos robô)", "check", True)]},
    "form_planilha": {"cat": "planilha", "titulo": "📝 Formulário → planilha + e-mail", "fn": m_form_planilha,
                      "desc": "Formulário online que guarda cada resposta numa planilha, responde a pessoa por e-mail e te avisa.",
                      "campos": [("titulo", "Título do formulário", "texto", "Cadastro"), ("descricao", "Texto abaixo do título", "texto", ""),
                                 ("extras", "Perguntas extras (uma por linha)", "area", "Cidade\nComo nos conheceu?"),
                                 ("tel_obrig", "WhatsApp obrigatório", "check", False),
                                 ("responder", "Mandar e-mail automático para a pessoa", "check", True),
                                 ("assunto", "Assunto do e-mail", "texto", "Recebemos seu cadastro ✅"),
                                 ("resposta", "Texto do e-mail — use {nome}", "area", "Olá, {nome}!\n\nRecebemos seu cadastro. Em breve entraremos em contato.\n\nAbraços!"),
                                 ("obrigado", "Mensagem na tela depois de enviar", "texto", "Cadastro recebido! Confira seu e-mail."),
                                 ("avisar", "Avisar você em", "destino", "telegram")]},
    "resposta_ia": {"cat": "planilha", "titulo": "📩 Fale conosco respondido pela IA", "fn": m_resposta_ia_email,
                    "desc": "Formulário de contato: a IA escreve uma resposta personalizada e envia por e-mail em segundos.",
                    "campos": [("titulo", "Título do formulário", "texto", "Fale conosco"), ("descricao", "Texto abaixo do título", "texto", "Respondemos em minutos."),
                               ("negocio", "Nome do negócio", "texto", ""), ("info", "Informações para a IA responder", "area", ""),
                               ("tom", "Tom de voz", "tom", TONS[1]), ("avisar", "Mandar cópia para você em", "destino", "email")]},
    "relatorio": {"cat": "planilha", "titulo": "📊 Relatório automático da planilha", "fn": m_relatorio,
                  "desc": "Nos dias marcados, a IA lê sua planilha (leads, vendas ou atendimentos) e te manda um resumo com ações.",
                  "campos": [("tabela", "Qual planilha", "tabela", "vendas"), ("dias", "Dias", "dias", ["Segunda"]), ("hora", "Horário", "hora", "08:00"),
                             ("avisar", "Enviar para", "destino_obrig", "email")]},
    "post_diario": {"cat": "conteudo", "titulo": "✍️ Post pronto todo dia", "fn": m_post_diario,
                    "desc": "A IA cria a ideia da imagem, a legenda e as hashtags e te entrega no horário marcado.",
                    "campos": [("negocio", "Nome do negócio/perfil", "texto", ""), ("nicho", "Nicho", "texto", ""), ("publico", "Público", "texto", ""),
                               ("rede", "Rede social", "rede", "Instagram"), ("tom", "Tom de voz", "tom", TONS[2]),
                               ("temas", "Temas ou produtos para falar (opcional)", "area", ""), ("dias", "Dias", "dias", DIAS_SEMANA[1:6]),
                               ("hora", "Horário", "hora", "08:00"), ("avisar", "Receber em", "destino_obrig", "telegram")]},
    "rss_post": {"cat": "conteudo", "titulo": "📰 Blog/notícias → post para redes", "fn": m_rss_post,
                 "desc": "Cada novidade de um blog ou site (endereço RSS) vira um post pronto para suas redes.",
                 "campos": [("feed", "Endereço RSS (ex.: seublog.com/feed)", "texto", ""), ("negocio", "Nome do perfil", "texto", ""),
                            ("rede", "Rede social", "rede", "Instagram"), ("tom", "Tom de voz", "tom", TONS[1]),
                            ("avisar", "Receber em", "destino_obrig", "telegram")]},
    "facebook": {"cat": "conteudo", "titulo": "📘 Publicar sozinho na Página do Facebook", "fn": m_facebook,
                 "desc": "A IA escreve e publica direto na sua Página do Facebook nos dias e horário marcados.",
                 "campos": [("negocio", "Nome do negócio", "texto", ""), ("nicho", "Nicho", "texto", ""), ("tom", "Tom de voz", "tom", TONS[0]),
                            ("temas", "Temas (opcional)", "area", ""), ("pagina_id", "ID da Página do Facebook", "texto", ""),
                            ("pagina_token", "Token de acesso da Página", "senha", ""), ("dias", "Dias", "dias", ["Segunda", "Quarta", "Sexta"]),
                            ("hora", "Horário", "hora", "11:00"), ("avisar", "Avisar você em", "destino", "nenhum")]},
    "venda": {"cat": "vendas", "titulo": "💰 Venda aprovada → boas-vindas + aviso", "fn": m_venda,
              "desc": "Hotmart, Kiwify, Monetizze, Eduzz, Braip...: cada venda aprovada gera boas-vindas no WhatsApp e no e-mail do cliente, "
                      "entra na planilha de vendas e te avisa.",
              "campos": [("whats_cliente", "Mandar boas-vindas no WhatsApp do cliente", "check", True),
                         ("msg_whats", "Mensagem no WhatsApp — use {nome} e {produto}", "area",
                          "Oi, {nome}! 🎉 Sua compra de {produto} foi aprovada. Seu acesso chega no seu e-mail. Qualquer dúvida, é só chamar aqui!"),
                         ("email_cliente", "Mandar e-mail para o cliente", "check", False), ("assunto_email", "Assunto do e-mail", "texto", "Bem-vindo(a) ao {produto}! 🎉"),
                         ("msg_email", "Texto do e-mail — use {nome} e {produto}", "area", "Olá, {nome}!\n\nObrigado pela compra de {produto}.\n\nAbraços!"),
                         ("salvar", "Guardar cada venda na planilha “Vendas”", "check", True), ("avisar", "Avisar você em", "destino", "whats")]},
    "recuperacao": {"cat": "vendas", "titulo": "🛒 Recuperar carrinho, boleto e Pix", "fn": m_recuperacao,
                    "desc": "Quando alguém abandona o carrinho ou gera boleto/Pix e não paga, manda uma mensagem de recuperação depois do tempo que você escolher.",
                    "campos": [("espera", "Esperar quanto tempo", "numero", 30), ("unidade", "Unidade", "unidade", "minutes"),
                               ("mensagem", "Mensagem — use {nome}, {produto} e {link}", "area",
                                "Oi, {nome}! Vi que você começou a compra de {produto} e não finalizou. Ficou alguma dúvida? Seu link: {link}"),
                               ("avisar", "Avisar você em", "destino", "nenhum")]},
}

TESTES = {
    "atendente": lambda: {"event": "messages.upsert", "data": {"key": {"remoteJid": f"{re.sub(r'[^0-9]', '', S.canais.get('whats_dono', '')) or '5511999999999'}@s.whatsapp.net", "fromMe": False},
                                                               "pushName": "Teste do n8n Fácil", "message": {"conversation": "Olá! Qual o horário de atendimento?"}}},
    "venda": lambda: {"event": "PURCHASE_APPROVED", "data": {"product": {"name": "Produto Teste"}, "buyer": {"name": "Cliente Teste", "email": S.canais.get("email_para") or "teste@exemplo.com",
                      "checkout_phone": re.sub(r"[^0-9]", "", S.canais.get("whats_dono", "")) or "5511999999999"}, "purchase": {"status": "APPROVED", "price": {"value": 14.9}}}},
    "recuperacao": lambda: {"event": "PURCHASE_OUT_OF_SHOPPING_CART", "data": {"product": {"name": "Produto Teste"}, "buyer": {"name": "Cliente Teste",
                            "phone": re.sub(r"[^0-9]", "", S.canais.get("whats_dono", "")) or "5511999999999"}, "checkout_url": "https://exemplo.com/checkout"}},
}


def url_gatilho(info: dict) -> str:
    base = normalizar_url(S.n8n_url)
    if info.get("tipo") == "webhook":
        return f"{base}/webhook/{info['path']}"
    if info.get("tipo") == "form":
        return f"{base}/form/{info['path']}"
    return ""


def trocar_tabelas(wf: dict) -> dict:
    txt = json.dumps(wf, ensure_ascii=False)
    for chave in re.findall(r"\{\{TAB:(\w+)\}\}", txt):
        txt = txt.replace("{{TAB:%s}}" % chave, garantir_tabela(chave))
    return json.loads(txt)


def criar_no_n8n(wf: dict, canais: set, ativar: bool) -> dict:
    faltando = [NOME_CANAL[c] for c in canais if c in NOME_CANAL and not canal_pronto(c)]
    if faltando:
        raise ErroAPI("Configure antes na aba 🔌 Canais: " + ", ".join(faltando))
    preparar_credenciais(canais)
    wf = trocar_tabelas(wf)
    criado = n8n("POST", "/workflows", wf)
    if ativar:
        try:
            n8n_ativar(criado["id"], True)
            criado["active"] = True
        except ErroAPI as e:
            criado["_erro_ativar"] = str(e)
    return criado


# ══════════════════════════════════════════════════════════════════════════
# CRIAR COM IA / IMPORTAR (validação do JSON antes de mandar ao n8n)
# ══════════════════════════════════════════════════════════════════════════
TIPOS_IA = {
    "n8n-nodes-base.webhook": 2, "n8n-nodes-base.formTrigger": 2.2, "n8n-nodes-base.scheduleTrigger": 1.2,
    "n8n-nodes-base.rssFeedReadTrigger": 1, "n8n-nodes-base.code": 2, "n8n-nodes-base.httpRequest": 4.2,
    "n8n-nodes-base.wait": 1.1, "n8n-nodes-base.telegram": 1.2, "n8n-nodes-base.emailSend": 2.1, "n8n-nodes-base.dataTable": 1,
}
GATILHOS = {"n8n-nodes-base.webhook", "n8n-nodes-base.formTrigger", "n8n-nodes-base.scheduleTrigger", "n8n-nodes-base.rssFeedReadTrigger",
            "n8n-nodes-base.manualTrigger", "n8n-nodes-base.cron", "n8n-nodes-base.emailReadImap", "n8n-nodes-base.telegramTrigger"}
CAMPOS_NO = ["id", "name", "type", "typeVersion", "position", "parameters", "credentials", "webhookId", "onError", "disabled", "notes",
             "alwaysOutputData", "retryOnFail", "maxTries", "waitBetweenTries", "executeOnce"]


def exemplo_para_ia() -> str:
    cfg = {"nome": "Exemplo", "path": "exemplo-venda", "whats_cliente": True, "msg_whats": "Oi, {nome}! Obrigado pela compra de {produto}.",
           "email_cliente": False, "salvar": True, "avisar": "telegram"}
    f, _, _ = m_venda(cfg)
    wf = f.json()
    for n in wf["nodes"]:
        if n["type"] == "n8n-nodes-base.code":
            n["parameters"]["jsCode"] = "// código JavaScript aqui (return [{ json: {...} }])"
    return json.dumps({"name": wf["name"], "nodes": wf["nodes"], "connections": wf["connections"]}, ensure_ascii=False)


def contexto_canais_ia() -> str:
    c = S.canais
    linhas = [f"- IA: POST {GROQ_URL} com body JSON {{model:'{MODELO}', messages:[...]}}; a resposta fica em $json.choices[0].message.content. "
              "O app conecta a credencial sozinho (não coloque chave no fluxo)."]
    if canal_pronto("whats"):
        f = Fluxo("x")
        f.whats("W", "'5511999999999'", "'texto'", 0)
        linhas.append(f"- WhatsApp: use exatamente este nó httpRequest para enviar: {json.dumps(f.nodes[0]['parameters'], ensure_ascii=False)} "
                      "(troque só o número e o texto nas expressões).")
    if canal_pronto("telegram"):
        linhas.append(f"- Telegram: nó n8n-nodes-base.telegram com parameters {{chatId:'{c['tg_chat']}', text:'={{{{ ... }}}}', additionalFields:{{appendAttribution:false}}}}.")
    if canal_pronto("email"):
        linhas.append(f"- E-mail: nó n8n-nodes-base.emailSend com parameters {{fromEmail:'{c.get('email_de') or c['smtp_user']}', toEmail:'...', subject:'...', "
                      "emailFormat:'text', text:'...', options:{appendAttribution:false}}.")
    tabs = S.get("tabelas", {})
    if tabs:
        linhas.append("- Planilhas internas (nó n8n-nodes-base.dataTable, resource 'row', operation 'insert' ou 'get', dataTableId {__rl:true, mode:'id', value:'ID'}, "
                      "columns {mappingMode:'autoMapInputData', value:{}}): " + "; ".join(f"{TABELAS[k][0]} = {v['id']} (colunas: "
                                                                                          f"{', '.join(c for c, _ in TABELAS[k][1])})" for k, v in tabs.items() if k in TABELAS))
    return "\n".join(linhas)


def gerar_fluxo_ia(descricao: str) -> dict:
    prompt = f"""Crie um workflow do n8n para este pedido de uma pessoa leiga:
\"\"\"{descricao}\"\"\"

Use SOMENTE estes tipos de nó (type: typeVersion): {json.dumps(TIPOS_IA)}.
Regras:
- Exatamente 1 gatilho (webhook, formTrigger, scheduleTrigger ou rssFeedReadTrigger).
- scheduleTrigger: parameters {{"rule": {{"interval": [{{"field": "cronExpression", "expression": "0 9 * * 1-5"}}]}}}} (fuso do servidor: {S.rw.get('fuso', 'America/Sao_Paulo')}).
- formTrigger: parameters {{"formTitle": "...", "formFields": {{"values": [{{"fieldLabel": "Nome", "fieldType": "text", "requiredField": true}}]}}, "options": {{"path": "caminho-curto"}}}}.
- webhook: parameters {{"httpMethod": "POST", "path": "caminho-curto", "responseMode": "onReceived", "options": {{}}}}.
- Para lógica, filtros e organizar dados use nós code (JavaScript, parameters {{"jsCode": "..."}}); para parar o fluxo retorne [].
- Expressões começam com "=" e usam {{{{ }}}}. Para dados de um nó anterior use $('Nome do nó').item.json.campo.
- Nunca use $env. Datas: $now.toFormat('dd/MM/yyyy HH:mm').
- Nomes de nós em português, curtos, sem aspas simples.
- Position: x de 0 em diante, de 260 em 260; y = 300.
Canais da pessoa já configurados:
{contexto_canais_ia()}
Exemplo de workflow válido (formato a seguir): {exemplo_para_ia()}

Responda SOMENTE com JSON: {{"nome": "nome curto da automação", "explicacao": "como funciona em 3 a 5 frases simples, incluindo o que a pessoa precisa fazer depois", "nodes": [...], "connections": {{...}}}}"""
    d = ia_json([{"role": "user", "content": prompt}])
    return validar_fluxo({"name": d.get("nome") or d.get("name") or "Automação criada com IA", "nodes": d.get("nodes"),
                          "connections": d.get("connections")}, restrito=True) | {"_explicacao": d.get("explicacao", "")}


def validar_fluxo(d: dict, restrito: bool = False) -> dict:
    nodes = d.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ErroAPI("O fluxo não tem nenhum passo (nodes). Tente descrever de novo, com mais detalhes.")
    limpos, nomes = [], set()
    for i, n in enumerate(nodes):
        if not isinstance(n, dict) or not n.get("type") or not n.get("name"):
            raise ErroAPI("Um dos passos veio sem nome ou sem tipo. Tente de novo.")
        if n["name"] in nomes:
            raise ErroAPI(f"Há dois passos com o mesmo nome ({n['name']}). Tente de novo.")
        nomes.add(n["name"])
        if restrito and n["type"] not in TIPOS_IA:
            raise ErroAPI(f"A IA usou um tipo de passo que o app não aceita ({n['type']}). Clique de novo para gerar outra versão.")
        novo = {k: n[k] for k in CAMPOS_NO if k in n}
        novo.setdefault("id", str(uuid.uuid4()))
        novo.setdefault("typeVersion", TIPOS_IA.get(n["type"], 1))
        if not isinstance(novo.get("position"), list) or len(novo["position"]) != 2:
            novo["position"] = [i * 260, 300]
        if not isinstance(novo.get("parameters"), dict):
            novo["parameters"] = {}
        if n["type"] in ("n8n-nodes-base.webhook", "n8n-nodes-base.formTrigger", "n8n-nodes-base.wait"):
            novo.setdefault("webhookId", str(uuid.uuid4()))
        limpos.append(novo)
    if not any(n["type"] in GATILHOS or "trigger" in n["type"].lower() or n["type"].endswith("webhook") for n in limpos):
        raise ErroAPI("O fluxo não tem um gatilho (o que faz ele começar). Tente de novo.")
    con = d.get("connections") if isinstance(d.get("connections"), dict) else {}
    con_ok = {}
    for de, saidas in con.items():
        if de not in nomes or not isinstance(saidas, dict):
            continue
        main = []
        for lista in saidas.get("main") or []:
            main.append([c for c in (lista or []) if isinstance(c, dict) and c.get("node") in nomes])
        con_ok[de] = {"main": main}
    return {"name": str(d.get("name") or "Automação")[:120], "nodes": limpos, "connections": con_ok, "settings": {"executionOrder": "v1"}}


def caminhos_unicos(wf: dict) -> dict:
    """Evita conflito de endereço com outra automação (o n8n não aceita dois gatilhos no mesmo caminho)."""
    sufixo = secrets.token_hex(2)
    for n in wf["nodes"]:
        p = n.get("parameters", {})
        if n["type"] == "n8n-nodes-base.webhook" and p.get("path"):
            p["path"] = f"{slug(p['path'], 40)}-{sufixo}"
        if n["type"] == "n8n-nodes-base.formTrigger":
            op = p.setdefault("options", {})
            op["path"] = f"{slug(op.get('path') or p.pop('path', '') or wf['name'], 40)}-{sufixo}"
    return wf


def gatilho_do_fluxo(wf: dict) -> dict:
    for n in wf["nodes"]:
        p = n.get("parameters", {})
        if n["type"] == "n8n-nodes-base.webhook":
            return {"tipo": "webhook", "path": p.get("path") or n.get("webhookId")}
        if n["type"] == "n8n-nodes-base.formTrigger":
            return {"tipo": "form", "path": (p.get("options") or {}).get("path") or p.get("path") or n.get("webhookId")}
        if n["type"] == "n8n-nodes-base.scheduleTrigger":
            return {"tipo": "agenda"}
        if "rss" in n["type"].lower():
            return {"tipo": "rss"}
    return {"tipo": "outro"}


def ligar_credenciais(wf: dict) -> set:
    """Conecta as credenciais certas nos passos do fluxo gerado pela IA ou importado."""
    usados = set()
    base_whats = (S.canais.get("whats_base") or "").rstrip("/")
    for n in wf["nodes"]:
        p = n.get("parameters", {})
        url = str(p.get("url", ""))
        if n["type"] == "n8n-nodes-base.httpRequest" and "api.groq.com" in url:
            usados.add("groq")
            p.update(authentication="genericCredentialType", genericAuthType="httpHeaderAuth")
            p.pop("sendHeaders", None), p.pop("headerParameters", None)
            n["_cred"] = "groq"
        elif n["type"] == "n8n-nodes-base.httpRequest" and canal_pronto("whats") and (
                (base_whats and url.startswith(base_whats)) or "z-api.io" in url or "graph.facebook.com" in url and "/messages" in url):
            usados.add("whats")
            if S.canais["whats_prov"] != "zapi" or S.segredos.get("whats_client"):
                p.update(authentication="genericCredentialType", genericAuthType="httpHeaderAuth")
                n["_cred"] = "whats"
        elif n["type"] == "n8n-nodes-base.telegram":
            usados.add("telegram")
            n["_cred"] = "telegram"
        elif n["type"] == "n8n-nodes-base.emailSend":
            usados.add("email")
            n["_cred"] = "email"
    return usados


def aplicar_credenciais(wf: dict):
    for n in wf["nodes"]:
        c = n.pop("_cred", None)
        if c == "telegram":
            n["credentials"] = {"telegramApi": cred_ref("telegram")}
        elif c == "email":
            n["credentials"] = {"smtp": cred_ref("email")}
        elif c in ("groq", "whats"):
            n["credentials"] = {"httpHeaderAuth": cred_ref(c)}


def criar_fluxo_livre(wf: dict, ativar: bool, categoria: str, origem: str) -> dict:
    wf = caminhos_unicos(json.loads(json.dumps(wf)))
    canais = ligar_credenciais(wf)
    faltando = [NOME_CANAL[c] for c in canais if not canal_pronto(c)]
    if faltando:
        raise ErroAPI("Este fluxo usa canais que ainda não foram configurados na aba 🔌 Canais: " + ", ".join(faltando))
    preparar_credenciais(canais)
    aplicar_credenciais(wf)
    wf = trocar_tabelas(wf)
    corpo = {k: wf[k] for k in ("name", "nodes", "connections", "settings")}
    criado = n8n("POST", "/workflows", corpo)
    if ativar:
        try:
            n8n_ativar(criado["id"], True)
            criado["active"] = True
        except ErroAPI as e:
            criado["_erro_ativar"] = str(e)
    info = gatilho_do_fluxo(wf)
    S.automacoes.append({"id": criado["id"], "nome": wf["name"], "categoria": categoria, "modelo": origem, "criada": agora(),
                         "gatilho": info.get("tipo"), "url_gatilho": url_gatilho(info), "instrucao": ""})
    registrar("Automação criada", f"{wf['name']} ({origem})")
    return criado


def criar_de_modelo(chave: str, cfg: dict, ativar: bool) -> tuple:
    m = MODELOS[chave]
    cfg = dict(cfg)
    cfg["path"] = f"{slug(cfg['nome'], 30)}-{secrets.token_hex(2)}"
    _, canais, _ = m["fn"](cfg)
    faltando = [NOME_CANAL[c] for c in canais if c in NOME_CANAL and not canal_pronto(c)]
    if faltando:
        raise ErroAPI("Configure antes na aba 🔌 Canais: " + ", ".join(faltando))
    preparar_credenciais(canais)
    f, canais, info = m["fn"](cfg)          # remonta já com as credenciais criadas
    wf = trocar_tabelas(f.json())
    criado = n8n("POST", "/workflows", wf)
    if ativar:
        try:
            n8n_ativar(criado["id"], True)
            criado["active"] = True
        except ErroAPI as e:
            criado["_erro_ativar"] = str(e)
    S.automacoes.append({"id": criado["id"], "nome": cfg["nome"], "categoria": m["cat"], "modelo": chave, "criada": agora(),
                         "gatilho": info.get("tipo"), "url_gatilho": url_gatilho(info), "instrucao": info.get("instrucao", "")})
    registrar("Automação criada", f"{cfg['nome']} (modelo {m['titulo']})")
    return criado, info


def testar_automacao(auto: dict) -> str:
    gerador = TESTES.get(auto.get("modelo"))
    if not gerador or not auto.get("url_gatilho"):
        raise ErroAPI("Este tipo de automação não tem teste automático. Abra no n8n e clique em “Execute workflow”.")
    try:
        r = requests.post(auto["url_gatilho"], json=gerador(), timeout=30)
    except requests.RequestException as e:
        raise ErroAPI(f"Não consegui enviar o teste ({e.__class__.__name__}).")
    if r.status_code == 404:
        raise ErroAPI("O n8n não encontrou o endereço: a automação está DESLIGADA. Ligue e teste de novo.")
    if r.status_code >= 400:
        raise ErroAPI(f"O n8n respondeu com erro {r.status_code}: {r.text[:200]}")
    registrar("Teste enviado", auto["nome"])
    return "Teste enviado! Em alguns segundos veja o resultado em 📜 Execuções (e no seu WhatsApp/Telegram/e-mail)."


def apagar_automacao(wid: str):
    try:
        n8n_ativar(wid, False)          # desliga antes: libera o endereço do webhook
    except ErroAPI:
        pass
    n8n("DELETE", f"/workflows/{wid}")
    S.automacoes = [a for a in S.automacoes if a["id"] != wid]
    registrar("Automação apagada", wid)


# ══════════════════════════════════════════════════════════════════════════
# EXPORTAÇÃO (texto, Excel sem biblioteca extra, memória .json)
# ══════════════════════════════════════════════════════════════════════════
def _xml(t) -> str:
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(t))[:32000]
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _col(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def xlsx_bytes(abas: list) -> bytes:
    folhas = []
    for _, linhas in abas:
        xml, larg = [], {}
        for i, linha in enumerate(linhas, 1):
            cels = []
            for j, v in enumerate(linha, 1):
                ref = f"{_col(j)}{i}"
                if isinstance(v, bool) or v is None:
                    v = "" if v is None else ("Sim" if v else "Não")
                if isinstance(v, (int, float)):
                    est = 1 if i == 1 else (2 if isinstance(v, float) else 4)
                    cels.append(f'<c r="{ref}" s="{est}"><v>{v}</v></c>')
                    tam = len(str(v))
                else:
                    sv = str(v)
                    est = 1 if i == 1 else (3 if (len(sv) > 60 or "\n" in sv) else 4)
                    cels.append(f'<c r="{ref}" s="{est}" t="inlineStr"><is><t xml:space="preserve">{_xml(sv)}</t></is></c>')
                    tam = max((len(x) for x in sv.splitlines()), default=0)
                larg[j] = max(larg.get(j, 10), min(tam + 2, 70))
            xml.append(f'<row r="{i}">{"".join(cels)}</row>')
        cols = "".join(f'<col min="{j}" max="{j}" width="{w}" customWidth="1"/>' for j, w in sorted(larg.items()))
        cong = ('<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" '
                'state="frozen"/></sheetView></sheetViews>') if len(linhas) > 1 else ""
        folhas.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                      + cong + (f"<cols>{cols}</cols>" if cols else "") + f'<sheetData>{"".join(xml)}</sheetData></worksheet>')
    n = len(folhas)
    R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
          + "".join(f'<Override PartName="/xl/worksheets/sheet{k}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for k in range(1, n + 1))
          + "</Types>")
    rels = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{R}/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    usados, nomes = set(), []
    for nome, _ in abas:
        b = re.sub(r"[\[\]:*?/\\]", " ", nome).strip()[:28] or "Dados"
        f, c = b, 2
        while f.lower() in usados:
            f, c = f"{b[:25]} {c}", c + 1
        usados.add(f.lower())
        nomes.append(f)
    wb = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="{R}"><sheets>'
          + "".join(f'<sheet name="{_xml(nomes[k - 1])}" sheetId="{k}" r:id="rId{k}"/>' for k in range(1, n + 1)) + "</sheets></workbook>")
    wbr = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
           + "".join(f'<Relationship Id="rId{k}" Type="{R}/worksheet" Target="worksheets/sheet{k}.xml"/>' for k in range(1, n + 1))
           + f'<Relationship Id="rId{n + 1}" Type="{R}/styles" Target="styles.xml"/></Relationships>')
    est = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
           '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>'
           '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
           '<fill><patternFill patternType="solid"><fgColor rgb="FFE11D63"/><bgColor indexed="64"/></patternFill></fill></fills>'
           '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
           '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
           '<cellXfs count="5"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
           '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
           '<xf numFmtId="4" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment vertical="top"/></xf>'
           '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
           '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top"/></xf></cellXfs>'
           '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels); z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wbr); z.writestr("xl/styles.xml", est)
        for k, x in enumerate(folhas, 1):
            z.writestr(f"xl/worksheets/sheet{k}.xml", x)
    return buf.getvalue()



def nome_categoria(c: str) -> str:
    e, n = CATEGORIAS.get(c, ("🧩", "Sob medida"))
    return f"{e} {n}"


def relatorio_txt() -> str:
    R = S.rw
    L = ["=" * 64, "⚡ n8n FÁCIL — RELATÓRIO DO SEU SERVIDOR DE AUTOMAÇÕES", f"Nome: {S.u_nome}", f"Gerado em: {agora()}", "=" * 64, ""]
    L += ["■ SERVIDOR", "-" * 64,
          f"Projeto no Railway: {R.get('project_nome') or '—'}",
          f"Endereço do n8n: {S.n8n_url or ('https://' + R['domain'] if R.get('domain') else '—')}",
          f"Fuso horário: {R.get('fuso') or '—'}", f"Instalado em: {R.get('instalado_em') or '—'}", ""]
    c = S.canais
    L += ["■ CANAIS", "-" * 64]
    for k in ("groq", "whats", "telegram", "email"):
        L.append(f"{NOME_CANAL[k]}: {'configurado' if canal_pronto(k) else 'não configurado'}")
    L += [f"WhatsApp: {({'evolution': 'Evolution API', 'zapi': 'Z-API', 'meta': 'WhatsApp Cloud API (Meta)'}).get(c['whats_prov'])}"
          f" · número de avisos: {c.get('whats_dono') or '—'}", ""]
    L += [f"■ AUTOMAÇÕES CRIADAS PELO APP ({len(S.automacoes)})", "-" * 64]
    for i, a in enumerate(S.automacoes, 1):
        L += [f"{i}) {a['nome']} — {nome_categoria(a['categoria'])}", f"   Criada em {a['criada']} · gatilho: {a.get('gatilho') or '—'}"]
        if a.get("url_gatilho"):
            L.append(f"   Endereço: {a['url_gatilho']}")
        if a.get("instrucao"):
            L.append(f"   O que fazer: {a['instrucao']}")
        L.append("")
    if S.historico:
        L += [f"■ HISTÓRICO ({len(S.historico)})", "-" * 64] + [f"{h['quando']} · {h['acao']}" + (f" — {h['detalhe']}" if h["detalhe"] else "") for h in S.historico] + [""]
    L += ["Observação: tokens, chaves e senhas NÃO aparecem neste relatório."]
    return "\n".join(L)


def relatorio_xlsx() -> bytes:
    R = S.rw
    abas = [("Resumo", [["Item", "Valor"], ["Nome", S.u_nome], ["Gerado em", agora()], ["Projeto Railway", R.get("project_nome", "")],
                        ["Endereço do n8n", S.n8n_url], ["Fuso horário", R.get("fuso", "")], ["Instalado em", R.get("instalado_em", "")]]
             + [[NOME_CANAL[k], "configurado" if canal_pronto(k) else "não configurado"] for k in ("groq", "whats", "telegram", "email")])]
    if S.automacoes:
        abas.append(("Automações", [["Nome", "Categoria", "Modelo", "Criada em", "Gatilho", "Endereço", "O que fazer", "ID no n8n"]] + [
            [a["nome"], nome_categoria(a["categoria"]), MODELOS.get(a.get("modelo"), {}).get("titulo", a.get("modelo", "")), a["criada"],
             a.get("gatilho", ""), a.get("url_gatilho", ""), a.get("instrucao", ""), a["id"]] for a in S.automacoes]))
    if S.get("_lista"):
        abas.append(("No n8n agora", [["Nome", "Ligada", "Criada", "Atualizada", "ID"]] + [
            [w.get("name"), bool(w.get("active")), br_data(w.get("createdAt")), br_data(w.get("updatedAt")), w.get("id")] for w in S["_lista"]]))
    if S.historico:
        abas.append(("Histórico", [["Quando", "Ação", "Detalhe"]] + [[h["quando"], h["acao"], h["detalhe"]] for h in S.historico]))
    return xlsx_bytes(abas)


def memoria_json() -> bytes:
    dados = {k: S[k] for k in CHAVES_MEMORIA}
    dados["tabelas"] = S.get("tabelas", {})
    dados.update({"_app": "n8n_facil", "_versao": 1, "_nome": S.u_nome, "_salvo_em": datetime.now().isoformat(timespec="seconds"),
                  "_aviso": "Tokens, chaves e senhas não são salvos neste arquivo."})
    return json.dumps(dados, ensure_ascii=False, indent=2).encode("utf-8")


# ══════════════════════════════════════════════════════════════════════════
# GUIA PARA INICIANTES (rodapé e tela de entrada)
# ══════════════════════════════════════════════════════════════════════════
GUIA = [
    ("🧰 O que é isso e o que você precisa", """
**n8n** é um “robô de automações”: ele liga seus aplicativos (WhatsApp, e-mail, Hotmart, formulários, planilhas…) e faz tarefas sozinho, 24 horas.
**Railway** é o lugar na internet onde o seu n8n fica ligado (um servidor só seu).
Este agente faz a parte difícil por você: **instala, configura e cria as automações**.

Você vai precisar de:
- Uma **chave Groq** (grátis) para entrar no app.
- Uma **conta no Railway** (railway.com). O Railway cobra pelo uso do servidor: confira o plano atual em **railway.com/pricing**.
- 15 minutos na primeira vez.
"""),
    ("🔑 Passo 1 — Criar a chave Groq (grátis)", """
1. Acesse **console.groq.com/keys** e entre com sua conta Google.
2. Clique em **Create API Key**, dê um nome e confirme.
3. Copie o código que começa com **gsk_** e cole na tela de entrada.
"""),
    ("🚂 Passo 2 — Criar a conta e o token do Railway", """
1. Acesse **railway.com** e clique em **Sign in / Get started** (pode entrar com o GitHub ou e-mail).
2. Se o Railway pedir, escolha um plano / cadastre o cartão (sem isso ele não liga servidores).
3. Abra **railway.com/account/tokens**.
4. Em **Create new token**, dê um nome (ex.: *n8n Facil*) e em **Workspace** escolha **No workspace**. Clique em **Create**.
5. Copie o token e cole na aba **🚀 Instalar n8n → Passo 1**.
O token é como uma senha: não mande para ninguém. O app **não salva** o token em arquivo.
"""),
    ("🚀 Passo 3 — Instalar o n8n (1 clique)", """
Na aba **🚀 Instalar n8n**, escolha o nome do projeto e o fuso horário e clique em **Instalar n8n agora**. O agente:
1. cria o projeto no seu Railway;
2. cria o serviço com a **imagem oficial do n8n**;
3. cria o **disco permanente** (suas automações não se perdem);
4. gera o **endereço https** e configura os webhooks;
5. liga o servidor.
Leva de **2 a 5 minutos** para ligar. Clique em **Verificar se já ligou** até aparecer ✅.
"""),
    ("👤 Passo 4 — Criar seu usuário no n8n e a chave da API", """
1. Clique no endereço do seu n8n (aparece depois da instalação).
2. **Na primeira vez, o n8n pede para criar o dono**: coloque seu e-mail e uma senha forte. Faça isso logo (quem abrir primeiro vira dono).
3. Dentro do n8n, clique no seu nome (canto inferior esquerdo) → **Settings** → **n8n API** → **Create an API key**.
4. Dê um nome (ex.: *n8n Facil*), em validade escolha **No expiration** e clique em **Save**.
5. **Copie a chave na hora** (ela só aparece uma vez) e cole na aba **🔑 Conectar n8n**.
"""),
    ("🔌 Passo 5 — Conectar seus canais", """
Na aba **🔌 Canais** você conecta por onde as automações falam:
- **💬 WhatsApp**: o n8n envia e recebe mensagens por uma “ponte”. Aceitamos **Evolution API** (você ou seu técnico instala; é só ler o QR Code),
  **Z-API** (serviço pago brasileiro, mais simples) ou a **API oficial da Meta**. Cole o endereço, a instância e o token que o serviço te der.
- **✈️ Telegram** (o jeito mais fácil de receber avisos): no Telegram fale com **@BotFather**, mande */newbot*, copie o token,
  mande um “oi” para o seu robô e clique em **Descobrir meu chat** no app.
- **📧 E-mail**: no Gmail, ative a verificação em 2 etapas e crie uma **senha de app** em *myaccount.google.com/apppasswords*. Use essa senha (não a senha normal).
Use **Testar** em cada canal antes de criar automações.
"""),
    ("🧩 Passo 6 — Criar automações", """
Na aba **🧩 Criar automação** você tem 3 jeitos:
- **📦 Modelos prontos** (recomendado): escolha a categoria, preencha os campos e clique em **Criar no meu n8n**.
- **✨ Criar com IA**: descreva o que quer em português (“quando chegar venda na Kiwify, me avise no Telegram e mande e-mail de boas-vindas”).
- **📥 Importar**: cole um fluxo .json (por exemplo, de n8n.io/workflows).
Depois de criar, o app mostra o **endereço** que você precisa colar no outro serviço (Hotmart, Evolution API…) ou o **link do formulário** para divulgar.
"""),
    ("💰 Como ligar Hotmart, Kiwify e Monetizze", """
1. Crie a automação **💰 Venda aprovada** (ou **🛒 Recuperar carrinho**).
2. Copie o endereço que aparece (termina com /webhook/...).
3. **Hotmart**: Ferramentas → Webhook (API e notificações) → Cadastrar webhook → cole o endereço → marque *Compra aprovada* (ou *Abandono de carrinho*).
4. **Kiwify**: Apps → Webhooks → Criar → cole o endereço → marque *Compra aprovada* (ou *Carrinho abandonado*, *Boleto/Pix gerado*).
5. **Monetizze**: Ferramentas → Postback → cole o endereço.
6. Use **🧪 Testar** em **📋 Minhas automações** para simular uma venda.
"""),
    ("📋 Acompanhar, ligar, desligar e corrigir", """
Na aba **📋 Minhas automações**: veja todas, **ligue/desligue**, **teste**, veja as **execuções** (✅ deu certo / ❌ deu erro, com o motivo),
baixe o .json ou apague. Para editar algo detalhado, clique em **Abrir no n8n**.
Na aba **📊 Planilhas** você vê e baixa em Excel os leads, vendas e atendimentos que as automações guardaram.
"""),
    ("🛠️ Servidor: status, registros e atualização", """
Na aba **🛠️ Servidor**: veja se o n8n está ligado, leia os registros (logs) quando algo der errado, **reinicie**, **atualize o n8n**
para a versão mais nova e ajuste configurações. Lá também fica a opção de **apagar o servidor** (cuidado: apaga tudo).
"""),
    ("💾 Como não perder nada (IMPORTANTE)", """
Suas automações ficam **no seu n8n** (no disco permanente do Railway) — não somem quando você fecha este app.
Este app guarda só a sua **memória** (endereços, lista do que foi criado, histórico). Ao terminar, abra **💾 Minha memória** e
clique em **Salvar minha memória (.json)**. Na próxima vez, abra esse arquivo e **cole de novo** o token do Railway e a chave da API do n8n
(por segurança, eles nunca são salvos em arquivo).
"""),
    ("🆘 Problemas comuns", """
- **“O Railway recusou o token”**: crie outro token em railway.com/account/tokens com **No workspace**.
- **O endereço do n8n não abre**: espere 3 minutos e clique em **Verificar se já ligou**; veja os registros na aba 🛠️ Servidor.
- **“O n8n recusou a chave da API”**: crie uma nova chave em Settings → n8n API.
- **WhatsApp não envia**: confira se a instância está conectada (QR Code lido) e se o número tem DDI 55 + DDD.
- **E-mail não sai**: use a **senha de app** do Gmail, servidor smtp.gmail.com, porta 465.
- **Automação com erro**: em 📋 Minhas automações → 📜 Execuções, leia o motivo; corrija os dados e crie de novo, ou abra no n8n.
"""),
    ("🛡️ Boas práticas e segurança", """
- Envie WhatsApp **só para quem autorizou** (evita bloqueio do número e respeita a LGPD). Os envios em lista saem com intervalo de 4 segundos.
- Nunca compartilhe tokens, chaves e senhas. Se vazar, apague e crie outro.
- A IA ajuda, mas confira as respostas automáticas antes de deixar ligado para clientes.
"""),
]


def mostrar_guia():
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("## 📘 Como usar — guia para iniciantes")
        st.caption("Abra cada item na ordem. Na primeira vez, separe uns 15 minutos.")
        for t, c in GUIA:
            with st.expander(t):
                st.markdown(c)
        txt = "\n\n".join(f"{t.upper()}\n{'-' * 50}\n{limpar_md(c)}" for t, c in GUIA)
        st.download_button("📥 Baixar este guia (.txt)", data=txt.encode("utf-8"), file_name="guia_n8n_facil.txt", mime="text/plain", key="dl_guia")


# ══════════════════════════════════════════════════════════════════════════
# TELA DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════
if not S.u_chave:
    _, meio, _ = st.columns([1, 2, 1])
    with meio:
        st.markdown("""<div style="text-align:center;padding:18px 0 4px 0;">
          <div style="font-size:3.4em;">⚡</div><h1 style="margin:0;">n8n Fácil</h1>
          <p style="color:#6E6585 !important;">Seu servidor de automações no Railway — instalado, configurado e comandado por um agente.
          WhatsApp, e-mail, planilhas, redes sociais e vendas no automático.</p>
        </div>""", unsafe_allow_html=True)
        nome = st.text_input("👤 Seu nome", placeholder="Como quer ser chamado?", key="u_inp_nome")
        chave = st.text_input("🔑 Sua chave Groq API", type="password", placeholder="gsk_...", key="u_inp_chave")
        if st.button("✨ ENTRAR", type="primary", width="stretch"):
            if len(nome.strip()) < 2:
                st.warning("Digite um nome com pelo menos 2 letras.")
            elif not chave.strip().startswith("gsk_"):
                st.warning("A chave Groq começa com **gsk_**. Confira e cole novamente.")
            else:
                S.u_nome, S.u_chave = nome.strip(), chave.strip()
                st.rerun()
        st.markdown(f"""<div class="card" style="font-size:.9em;line-height:1.7;">
        🔑 <b>Não tem chave?</b> Crie grátis em <a href="https://console.groq.com/keys" target="_blank">console.groq.com/keys</a>.<br>
        🚂 Você também vai precisar de uma conta em <a href="https://railway.com" target="_blank">railway.com</a> (veja o guia abaixo).<br>
        🔒 Chaves, tokens e senhas ficam só nesta sessão do navegador.<br>
        🤖 Mais agentes em <a href="{SITE}" target="_blank">MeusAgentesIA.com.br</a>.</div>""", unsafe_allow_html=True)
    mostrar_guia()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════
# CABEÇALHO + MEMÓRIA
# ══════════════════════════════════════════════════════════════════════════
hora = datetime.now().hour
saud = "Bom dia" if hora < 12 else ("Boa tarde" if hora < 18 else "Boa noite")
c_cab, c_mem = st.columns([3, 2])
with c_cab:
    st.markdown(f"""<div class="cab"><h1>⚡ n8n Fácil</h1>
    <p>{saud}, {S.u_nome}! Seu servidor de automações no Railway, comandado por conversa.</p></div>""", unsafe_allow_html=True)
with c_mem:
    with st.expander("💾 Minha memória: salvar, abrir, recomeçar ou sair"):
        st.download_button("💾 Salvar minha memória (.json)", data=memoria_json(),
                           file_name=f"n8n_facil_{slug(S.u_nome, 20)}_{datetime.now().strftime('%Y-%m-%d')}.json",
                           mime="application/json", width="stretch")
        st.caption("🔒 Tokens, chaves e senhas nunca vão para o arquivo.")
        arq = st.file_uploader("📂 Abrir minha memória", type=["json"], key=f"up_mem_{S.ver}")
        if arq is not None and st.button("Carregar esta memória", width="stretch"):
            try:
                dados = json.loads(arq.getvalue().decode("utf-8"))
                if dados.get("_app") != "n8n_facil":
                    raise ValueError
                for k in CHAVES_MEMORIA + ["tabelas"]:
                    if k in dados:
                        S[k] = dados[k]
                for k, v in PADRAO["canais"].items():
                    S.canais.setdefault(k, v)
                S.ver += 1
                st.success("Memória carregada! Agora cole de novo o token do Railway e a chave da API do n8n.")
                st.rerun()
            except Exception:
                st.error("Esse arquivo não é uma memória do n8n Fácil.")
        st.divider()
        if not S.get("_conf_reset"):
            if st.button("🆕 Recomeçar do zero", width="stretch"):
                S["_conf_reset"] = True
                st.rerun()
        else:
            st.warning("Isso limpa ESTE APP (endereços, lista e histórico). **Nada é apagado no Railway nem no n8n.**")
            r1, r2 = st.columns(2)
            if r1.button("✅ Sim, recomeçar", width="stretch", key="b_reset_sim"):
                ver = S.ver
                for k, v in PADRAO.items():
                    if k not in ("u_nome", "u_chave"):
                        S[k] = json.loads(json.dumps(v))
                for k in [k for k in S.keys() if str(k).startswith("_")] + ["tabelas"]:
                    S.pop(k, None)
                S.ver = ver + 1
                st.rerun()
            if r2.button("✖ Cancelar", width="stretch", key="b_reset_nao"):
                S["_conf_reset"] = False
                st.rerun()
        st.divider()
        if st.button("🚪 Sair", width="stretch"):
            for k in list(S.keys()):
                del S[k]
            st.rerun()

abas = st.tabs(["🏠 Início", "🚀 Instalar n8n", "🔑 Conectar n8n", "🔌 Canais", "🧩 Criar automação", "📋 Minhas automações",
                "📊 Planilhas", "🛠️ Servidor", "💬 Assistente", "📑 Relatório"])
V = S.ver


def chip(classe: str, texto: str) -> str:
    return f'<span class="chip {classe}">{texto}</span>'


def caixa_link(url: str):
    st.markdown(f'<div class="link-box">{url}</div>', unsafe_allow_html=True)


def bloco_token_railway(chave_widget: str):
    """Campo para colar o token do Railway (usado no Instalar e no Servidor)."""
    tok = st.text_input("Token do Railway", type="password", key=f"{chave_widget}_{V}", placeholder="cole aqui o token criado em railway.com/account/tokens")
    if st.button("🔗 Conectar minha conta Railway", type="primary", key=f"b_{chave_widget}_{V}"):
        if len(tok.strip()) < 20:
            st.warning("Cole o token completo (ele é bem comprido).")
        else:
            with st.spinner("Conferindo com o Railway…"):
                conta = rodar(rw_conta, tok.strip())
            if conta is not None:
                S.rw_token, S.rw_conta = tok.strip(), conta
                registrar("Conta Railway conectada", conta.get("email") or conta.get("nome"))
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# 1. INÍCIO
# ══════════════════════════════════════════════════════════════════════════
with abas[0]:
    R = S.rw
    tem_servidor = bool(R.get("domain") or S.n8n_url)
    etapas_ok = [
        ("Conta Railway conectada", bool(S.rw_token), "🚀 Instalar n8n → Passo 1"),
        ("n8n instalado no seu Railway", bool(R.get("feito", {}).get("ligar")) or bool(S.n8n_url), "🚀 Instalar n8n → Passo 2"),
        ("n8n conectado ao app (chave da API)", bool(S.get("_api_ok")), "🔑 Conectar n8n"),
        ("Pelo menos 1 canal configurado", any(canal_pronto(c) for c in ("whats", "telegram", "email")), "🔌 Canais"),
        ("Primeira automação criada", bool(S.automacoes), "🧩 Criar automação"),
    ]
    feitas = sum(1 for _, ok, _ in etapas_ok if ok)
    cols = st.columns(4)
    for col, (rot, val, sub) in zip(cols, [
        ("Configuração", f"{feitas}/5", "etapas concluídas"),
        ("Automações", len(S.automacoes), "criadas pelo app"),
        ("Ligadas agora", sum(1 for w in S.get("_lista", []) if w.get("active")) if S.get("_lista") else "—", "atualize em 📋"),
        ("Canais prontos", sum(1 for c in ("whats", "telegram", "email") if canal_pronto(c)), "de 3"),
    ]):
        col.markdown(f'<div class="metrica"><b>{val}</b>{rot}<br><small>{sub}</small></div>', unsafe_allow_html=True)
    st.write("")
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("### ✅ Sua configuração")
        proxima = None
        for rot, ok, onde in etapas_ok:
            st.markdown(f'<div class="check">{"✅" if ok else "⬜"} {rot} {"" if ok else f"<small>— vá em <b>{onde}</b></small>"}</div>',
                        unsafe_allow_html=True)
            if not ok and proxima is None:
                proxima = onde
        if proxima:
            st.info(f"👉 **Próximo passo:** abra a aba **{proxima}**.")
        else:
            st.success("🎉 Tudo pronto! Crie mais automações ou converse com o 💬 Assistente.")
    with c2:
        st.markdown("### 🌐 Seu n8n")
        if tem_servidor:
            url = S.n8n_url or f"https://{R['domain']}"
            st.markdown(f"**Endereço:** [{url}]({url})")
            if st.button("🔎 Verificar se está ligado", key="b_ini_online", width="stretch"):
                with st.spinner("Conferindo…"):
                    S["_online"] = n8n_online(url)
                    S["_online_em"] = agora()
            if "_online" in S:
                st.markdown(chip("ok", "✅ Ligado e respondendo") if S["_online"] else chip("atr", "⏳ Ainda não respondeu"), unsafe_allow_html=True)
                st.caption(f"Verificado em {S['_online_em']}")
        else:
            st.markdown("""<div class="card">Você ainda não tem um n8n. Em <b>🚀 Instalar n8n</b> o agente instala tudo no seu Railway em poucos minutos.<br><br>
            Já tem um n8n (no Railway ou em outro lugar)? Vá direto em <b>🔑 Conectar n8n</b>.</div>""", unsafe_allow_html=True)
    st.markdown("### 🧩 O que você pode automatizar")
    cc = st.columns(4)
    for col, (cat, (emo, nome_c)) in zip(cc, CATEGORIAS.items()):
        itens = "".join(f"<li>{m['titulo']}</li>" for m in MODELOS.values() if m["cat"] == cat)
        col.markdown(f'<div class="card"><b>{emo} {nome_c}</b><ul style="padding-left:18px;margin:6px 0 0 0;font-size:.9em">{itens}</ul></div>',
                     unsafe_allow_html=True)
    st.caption("✨ E qualquer outra ideia: descreva em português em 🧩 Criar automação → Criar com IA.")


# ══════════════════════════════════════════════════════════════════════════
# 2. INSTALAR n8n NO RAILWAY
# ══════════════════════════════════════════════════════════════════════════
with abas[1]:
    st.markdown('<span class="passo">PASSO 1</span>', unsafe_allow_html=True)
    st.markdown("### 🚂 Conectar sua conta Railway")
    if S.rw_token:
        conta = S.rw_conta
        st.success(f"Conectado como **{conta.get('nome') or 'sua conta'}** {('(' + conta['email'] + ')') if conta.get('email') else ''}.")
        if st.button("Trocar de conta / token", key="b_troca_tok"):
            S.rw_token, S.rw_conta = "", {}
            st.rerun()
    else:
        st.markdown("""1. Crie sua conta em **[railway.com](https://railway.com)** (se o Railway pedir, escolha um plano/cadastre o cartão).
2. Abra **[railway.com/account/tokens](https://railway.com/account/tokens)** → *Create new token* → em **Workspace** escolha **No workspace** → *Create*.
3. Copie o token e cole abaixo.""")
        bloco_token_railway("tok_inst")

    if S.rw_token:
        st.markdown('<span class="passo">PASSO 2</span>', unsafe_allow_html=True)
        st.markdown("### 🚀 Instalar ou escolher o seu n8n")
        R = S.rw
        feito = R.setdefault("feito", {})
        if R.get("project_id") and feito.get("ligar"):
            url = f"https://{R['domain']}" if R.get("domain") else S.n8n_url
            st.success(f"✅ Seu n8n está instalado no projeto **{R.get('project_nome')}**.")
            st.markdown(f"**Endereço do seu n8n:** [{url}]({url})")
            st.markdown("""<div class="aviso">⏳ Depois da instalação, o n8n leva de <b>2 a 5 minutos</b> para ligar na primeira vez.
            <b>Assim que abrir, crie seu usuário dono</b> (quem abrir primeiro vira dono) e siga para <b>🔑 Conectar n8n</b>.</div>""", unsafe_allow_html=True)
            if st.button("🔎 Verificar se já ligou", type="primary", key="b_verif_inst"):
                with st.spinner("Conferindo o Railway e o n8n…"):
                    deps = rodar(rw_deploys, 1)
                    S["_online"], S["_online_em"] = n8n_online(url), agora()
                if deps:
                    cls, txt = STATUS_DEPLOY.get(deps[0]["status"], ("neu", deps[0]["status"]))
                    st.markdown(f"Railway: {chip(cls, txt)} &nbsp; n8n: " + (chip("ok", "✅ respondendo") if S["_online"] else chip("fim", "⏳ ligando…")),
                                unsafe_allow_html=True)
                    if S["_online"]:
                        st.balloons()
                        st.success(f"🎉 Pronto! Abra {url}, crie seu usuário dono e vá para a aba 🔑 Conectar n8n.")
                    elif cls == "atr":
                        st.error("A implantação falhou. Veja os registros na aba 🛠️ Servidor ou clique em Reimplantar lá.")
            with st.expander("🔁 Instalar outro n8n (novo projeto)"):
                st.caption("Isso só esquece este servidor NO APP. Nada é apagado no Railway.")
                if st.button("Começar nova instalação", key="b_nova_inst"):
                    S.rw, S.n8n_url, S.n8n_key = {}, "", ""
                    S.pop("_api_ok", None)
                    st.rerun()
        else:
            modo = st.radio("O que você quer fazer?", ["🆕 Instalar um n8n novo", "📂 Já tenho n8n no Railway (só gerenciar)"],
                            horizontal=True, key=f"r_modo_inst_{V}")
            if modo.startswith("🆕"):
                ws = S.rw_conta.get("workspaces") or []
                ws_id = ""
                if len(ws) > 1:
                    nomes_ws = {w["id"]: w["name"] for w in ws}
                    ws_id = st.selectbox("Workspace (espaço) do Railway", list(nomes_ws), format_func=lambda i: nomes_ws[i], key=f"s_ws_{V}")
                elif ws:
                    ws_id = ws[0]["id"]
                ci1, ci2 = st.columns(2)
                proj = ci1.text_input("Nome do projeto", value=R.get("project_nome") or f"n8n-{slug(S.u_nome, 16)}", key=f"t_proj_{V}",
                                      disabled=bool(R.get("project_id")))
                fuso = ci2.selectbox("Fuso horário (para agendamentos)", FUSOS, index=FUSOS.index(R.get("fuso", "America/Sao_Paulo")) if R.get("fuso") in FUSOS else 0,
                                     key=f"s_fuso_{V}")
                st.markdown("O agente vai fazer, nesta ordem:")
                for k, rot in ETAPAS:
                    st.markdown(f"{'✅' if feito.get(k) else '⬜'} {rot}")
                parcial = any(feito.values())
                if st.button("▶️ Continuar instalação" if parcial else "🚀 Instalar n8n agora", type="primary", key="b_instalar"):
                    if len(proj.strip()) < 3:
                        st.warning("Dê um nome ao projeto (pelo menos 3 letras).")
                    else:
                        opc = {"projeto": proj.strip(), "workspace_id": ws_id, "fuso": fuso}
                        with st.status("Instalando o n8n no seu Railway…", expanded=True) as stt:
                            erro = None
                            for k, rot in ETAPAS:
                                if feito.get(k):
                                    st.write(f"✅ {rot} (já feito)")
                                    continue
                                st.write(f"⏳ {rot}…")
                                try:
                                    instalar_etapa(k, opc)
                                    feito[k] = True
                                    st.write(f"✅ {rot}")
                                except ErroAPI as e:
                                    erro = e
                                    st.write(f"❌ {rot}")
                                    break
                            if erro:
                                stt.update(label="A instalação parou numa etapa", state="error")
                                registrar("Instalação interrompida", str(erro)[:200])
                            else:
                                stt.update(label="n8n instalado! Ligando o servidor…", state="complete")
                                registrar("n8n instalado no Railway", f"{R.get('project_nome')} · https://{R.get('domain')}")
                        if erro:
                            st.error(f"{erro}\n\nO que já foi feito ficou guardado: corrija e clique em **Continuar instalação**.")
                        else:
                            st.rerun()
            else:
                cx = st.columns([3, 1])
                if cx[1].button("🔄 Buscar projetos", key="b_busca_proj", width="stretch") or "_projetos" not in S:
                    lista = []
                    for w in (S.rw_conta.get("workspaces") or [None]):
                        r = rodar(rw_projetos, w["id"] if w else None)
                        lista += r or []
                    S["_projetos"] = {p["id"]: p for p in lista}
                projs = S.get("_projetos", {})
                if not projs:
                    st.info("Nenhum projeto encontrado nesta conta.")
                else:
                    pid = cx[0].selectbox("Projeto", list(projs), format_func=lambda i: projs[i]["name"], key=f"s_proj_exist_{V}")
                    det = rodar(rw_projeto, pid) if pid else None
                    if det and det["servicos"]:
                        servs = {s["id"]: s["name"] for s in det["servicos"]}
                        sid = st.selectbox("Serviço do n8n", list(servs), format_func=lambda i: servs[i],
                                           index=next((i for i, s in enumerate(servs) if "n8n" in servs[s].lower()), 0), key=f"s_serv_exist_{V}")
                        envs = {e["id"]: e["name"] for e in det["ambientes"]}
                        eid = st.selectbox("Ambiente", list(envs), format_func=lambda i: envs[i], key=f"s_env_exist_{V}")
                        if st.button("✅ Usar este n8n", type="primary", key="b_usar_exist"):
                            S.rw = {"project_id": pid, "project_nome": det["nome"], "service_id": sid, "env_id": eid,
                                    "feito": {k: True for k, _ in ETAPAS}, "instalado_em": "já existia"}
                            doms = rodar(rw_dominios) or []
                            if doms:
                                S.rw["domain"] = doms[0]
                                S.n8n_url = f"https://{doms[0]}"
                            try:
                                v = rw_variaveis()
                                S.rw["fuso"] = v.get("GENERIC_TIMEZONE", "")
                            except ErroAPI:
                                pass
                            registrar("n8n existente conectado", det["nome"])
                            st.rerun()
                    elif det:
                        st.info("Esse projeto não tem serviços.")


# ══════════════════════════════════════════════════════════════════════════
# 3. CONECTAR n8n (chave da API)
# ══════════════════════════════════════════════════════════════════════════
with abas[2]:
    st.markdown("### 🔑 Conectar o app ao seu n8n")
    url_sug = S.n8n_url or (f"https://{S.rw['domain']}" if S.rw.get("domain") else "")
    if url_sug:
        st.markdown(f"**1.** Abra seu n8n: [{url_sug}]({url_sug}) — na primeira vez, **crie o usuário dono** (e-mail e senha).")
    else:
        st.markdown("**1.** Abra seu n8n no navegador e entre com seu usuário.")
    st.markdown("""**2.** No n8n: clique no seu nome (canto de baixo, à esquerda) → **Settings** → **n8n API** → **Create an API key**.
Dê um nome (ex.: *n8n Facil*), escolha **No expiration** e clique em **Save**. **Copie a chave na hora** (ela só aparece uma vez).

**3.** Cole o endereço e a chave abaixo:""")
    k1, k2 = st.columns(2)
    url_in = k1.text_input("Endereço do seu n8n", value=url_sug, key=f"t_url_n8n_{V}", placeholder="https://seu-n8n.up.railway.app")
    key_in = k2.text_input("Chave da API do n8n", type="password", key=f"t_key_n8n_{V}", placeholder="cole a chave da API")
    if st.button("🔌 Conectar e testar", type="primary", key="b_con_n8n"):
        if not url_in.strip() or len(key_in.strip()) < 10:
            st.warning("Preencha o endereço e a chave.")
        else:
            with st.spinner("Testando a conexão…"):
                ok = rodar(n8n, "GET", "/workflows", None, {"limit": 1}, url_in, key_in)
            if ok is not None:
                if normalizar_url(url_in) != normalizar_url(S.n8n_url):
                    S.cred_ids, S["tabelas"] = {}, {}
                S.n8n_url, S.n8n_key, S["_api_ok"] = normalizar_url(url_in), key_in.strip(), True
                registrar("n8n conectado ao app", S.n8n_url)
                st.success("✅ Conectado! Agora configure seus canais na aba 🔌 Canais e crie automações.")
    if S.get("_api_ok"):
        st.markdown(chip("ok", f"✅ Conectado a {S.n8n_url}"), unsafe_allow_html=True)
    elif S.n8n_url and not S.n8n_key:
        st.info("Você já tem o endereço salvo. Por segurança, a chave da API não fica na memória: cole de novo para continuar.")
    with st.expander("❓ Não acho “n8n API” nas configurações"):
        st.markdown("""- Confira se você está logado como **dono** (owner).
- Em versões antigas, o menu fica em **Settings → API**. Se não aparecer, atualize o n8n em 🛠️ Servidor → ⬆️ Atualizar n8n.
- No n8n Cloud em período de teste a API não é liberada; no seu servidor do Railway ela funciona normalmente.""")


# ══════════════════════════════════════════════════════════════════════════
# 4. CANAIS (WhatsApp, Telegram, e-mail, IA)
# ══════════════════════════════════════════════════════════════════════════
def campo(rotulo, chave, segredo=False, ajuda=None, ph=""):
    alvo = S.segredos if segredo else S.canais
    val = st.text_input(rotulo, value=str(alvo.get(chave, "") or ""), type="password" if segredo else "default", key=f"c_{chave}_{V}",
                        help=ajuda, placeholder=ph)
    alvo[chave] = val.strip()


def testar_whats_direto() -> str:
    c, s = S.canais, S.segredos
    dono = (numeros_validos(c.get("whats_dono", "")) or [""])[0]
    if not dono:
        raise ErroAPI("Preencha o seu número (com DDD) para receber o teste.")
    texto = "✅ Teste do n8n Fácil: seu WhatsApp está conectado!"
    try:
        if c["whats_prov"] == "zapi":
            h = {"Client-Token": s["whats_client"]} if s.get("whats_client") else {}
            r = requests.post(f"https://api.z-api.io/instances/{c['whats_inst']}/token/{s['whats_token']}/send-text", json={"phone": dono, "message": texto},
                              headers=h, timeout=30)
        elif c["whats_prov"] == "meta":
            r = requests.post(f"https://graph.facebook.com/v21.0/{c['whats_inst']}/messages", timeout=30,
                              headers={"Authorization": f"Bearer {s['whats_token']}"},
                              json={"messaging_product": "whatsapp", "to": dono, "type": "text", "text": {"body": texto}})
        else:
            r = requests.post(f"{c['whats_base'].rstrip('/')}/message/sendText/{c['whats_inst']}", json={"number": dono, "text": texto},
                              headers={"apikey": s["whats_token"]}, timeout=30)
    except requests.RequestException as e:
        raise ErroAPI(f"Não consegui falar com o serviço de WhatsApp ({e.__class__.__name__}). Confira o endereço.")
    if r.status_code >= 400:
        raise ErroAPI(f"O serviço de WhatsApp recusou (código {r.status_code}): {r.text[:200]}")
    return f"Mensagem de teste enviada para {dono}. Confira seu WhatsApp!"


def telegram_descobrir_chat() -> str:
    tok = S.segredos.get("tg_token")
    if not tok:
        raise ErroAPI("Cole primeiro o token do robô.")
    try:
        r = requests.get(f"https://api.telegram.org/bot{tok}/getUpdates", timeout=20).json()
    except (requests.RequestException, ValueError):
        raise ErroAPI("Não consegui falar com o Telegram. Confira o token.")
    if not r.get("ok"):
        raise ErroAPI("O Telegram recusou o token. Copie de novo no @BotFather.")
    for up in reversed(r.get("result", [])):
        msg = up.get("message") or up.get("channel_post") or {}
        if msg.get("chat", {}).get("id"):
            return str(msg["chat"]["id"])
    raise ErroAPI("Ainda não achei nenhuma mensagem. Abra seu robô no Telegram, mande um “oi” e clique de novo.")


def telegram_teste() -> str:
    try:
        r = requests.post(f"https://api.telegram.org/bot{S.segredos['tg_token']}/sendMessage",
                          json={"chat_id": S.canais["tg_chat"], "text": "✅ Teste do n8n Fácil: seu Telegram está conectado!"}, timeout=20).json()
    except (requests.RequestException, ValueError):
        raise ErroAPI("Não consegui falar com o Telegram.")
    if not r.get("ok"):
        raise ErroAPI(f"O Telegram recusou: {r.get('description', '')}")
    return "Mensagem de teste enviada no seu Telegram!"


def email_teste() -> str:
    import smtplib
    import ssl
    from email.message import EmailMessage
    c, s = S.canais, S.segredos
    msg = EmailMessage()
    msg["Subject"], msg["From"] = "✅ Teste do n8n Fácil", c.get("email_de") or c["smtp_user"]
    msg["To"] = c.get("email_para") or c["smtp_user"]
    msg.set_content("Seu e-mail está conectado ao n8n Fácil. As automações já podem enviar e-mails.")
    porta = int(c.get("smtp_port") or 465)
    try:
        if porta == 465:
            with smtplib.SMTP_SSL(c["smtp_host"], porta, context=ssl.create_default_context(), timeout=25) as sv:
                sv.login(c["smtp_user"], s["smtp_senha"])
                sv.send_message(msg)
        else:
            with smtplib.SMTP(c["smtp_host"], porta, timeout=25) as sv:
                sv.starttls(context=ssl.create_default_context())
                sv.login(c["smtp_user"], s["smtp_senha"])
                sv.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        raise ErroAPI("Usuário ou senha recusados. No Gmail use uma SENHA DE APP (myaccount.google.com/apppasswords).")
    except Exception as e:
        raise ErroAPI(f"Não consegui enviar ({e.__class__.__name__}: {str(e)[:120]}). Confira servidor e porta.")
    return f"E-mail de teste enviado para {msg['To']}!"


with abas[3]:
    st.markdown("### 🔌 Seus canais")
    st.caption("Configure uma vez; todas as automações usam. Senhas e tokens ficam só nesta sessão e são guardados como credenciais seguras no SEU n8n.")
    st.markdown(f"**{NOME_CANAL['groq']}** — {chip('ok', '✅ pronta (sua chave de entrada)')}", unsafe_allow_html=True)

    with st.expander(f"💬 WhatsApp — {'✅ configurado' if canal_pronto('whats') else '⬜ não configurado'}", expanded=not canal_pronto("whats")):
        provs = {"evolution": "Evolution API", "zapi": "Z-API", "meta": "API oficial da Meta (WhatsApp Cloud)"}
        prov = st.radio("Qual serviço você usa?", list(provs), format_func=lambda k: provs[k], horizontal=True,
                        index=list(provs).index(S.canais.get("whats_prov", "evolution")), key=f"c_prov_{V}")
        S.canais["whats_prov"] = prov
        if prov == "evolution":
            campo("Endereço da Evolution API", "whats_base", ph="https://sua-evolution.com")
            campo("Nome da instância", "whats_inst", ph="minha-instancia")
            campo("API Key (apikey)", "whats_token", segredo=True)
        elif prov == "zapi":
            campo("ID da instância", "whats_inst")
            campo("Token da instância", "whats_token", segredo=True)
            campo("Client-Token (Segurança da conta — opcional)", "whats_client", segredo=True)
        else:
            campo("Phone number ID", "whats_inst", ajuda="No painel developers.facebook.com → WhatsApp → API Setup")
            campo("Token de acesso permanente", "whats_token", segredo=True)
            st.caption("⚠️ Na API oficial, mensagens para quem não falou com você nas últimas 24h exigem modelo aprovado pela Meta.")
        campo("Seu número para receber avisos e testes (com DDD)", "whats_dono", ph="11 99999-9999")
        if st.button("🧪 Testar WhatsApp", key="b_t_whats", disabled=not canal_pronto("whats")):
            with st.spinner("Enviando…"):
                r = rodar(testar_whats_direto)
            if r:
                st.success(r)

    with st.expander(f"✈️ Telegram — {'✅ configurado' if canal_pronto('telegram') else '⬜ não configurado'}"):
        st.markdown("No Telegram, fale com **@BotFather** → */newbot* → escolha um nome → copie o **token**. Depois **mande um “oi” para o seu robô**.")
        campo("Token do robô", "tg_token", segredo=True)
        t1, t2 = st.columns(2)
        if t1.button("🔎 Descobrir meu chat", key="b_tg_chat", width="stretch"):
            r = rodar(telegram_descobrir_chat)
            if r:
                S.canais["tg_chat"] = r
                S.ver += 1
                st.rerun()
        campo("Chat ID", "tg_chat")
        if t2.button("🧪 Testar Telegram", key="b_t_tg", width="stretch", disabled=not canal_pronto("telegram")):
            r = rodar(telegram_teste)
            if r:
                st.success(r)

    with st.expander(f"📧 E-mail — {'✅ configurado' if canal_pronto('email') else '⬜ não configurado'}"):
        st.markdown("Gmail: ative a verificação em 2 etapas e crie uma **senha de app** em *myaccount.google.com/apppasswords*.")
        e1, e2 = st.columns([3, 1])
        with e1:
            campo("Servidor SMTP", "smtp_host", ph="smtp.gmail.com")
        porta = e2.selectbox("Porta", [465, 587], index=0 if int(S.canais.get("smtp_port") or 465) == 465 else 1, key=f"c_porta_{V}")
        S.canais["smtp_port"] = porta
        campo("Seu e-mail (usuário)", "smtp_user")
        campo("Senha de app", "smtp_senha", segredo=True)
        campo("Remetente (opcional)", "email_de", ph="Minha Loja <contato@minhaloja.com>")
        campo("E-mail para receber avisos", "email_para")
        if st.button("🧪 Testar e-mail", key="b_t_mail", disabled=not canal_pronto("email")):
            with st.spinner("Enviando…"):
                r = rodar(email_teste)
            if r:
                st.success(r)
    st.markdown("""<div class="aviso">🔒 Ao criar uma automação, o app cadastra estes acessos como <b>credenciais</b> dentro do seu n8n
    (guardadas com criptografia lá). Se você trocar uma senha aqui, as próximas automações usam a nova.</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# 5. CRIAR AUTOMAÇÃO
# ══════════════════════════════════════════════════════════════════════════
UNIDADES = {"minutes": "minutos", "hours": "horas", "days": "dias"}
REDES = ["Instagram", "Facebook", "LinkedIn", "TikTok", "X (Twitter)", "WhatsApp Status"]
OBRIGATORIOS = {"negocio", "info", "numeros", "mensagem", "feed", "pagina_id", "pagina_token", "titulo", "nicho"}


def aviso_conexao() -> bool:
    if not conectado_n8n():
        st.warning("Conecte seu n8n primeiro na aba **🔑 Conectar n8n**.")
        return False
    return True


def mostrar_resultado_criacao(res: dict):
    st.success(f"✅ Automação **{res['nome']}** criada no seu n8n" + (" e **LIGADA**!" if res.get("ativa") else " (desligada)."))
    if res.get("erro_ativar"):
        st.warning(f"Ela foi criada, mas não ligou: {res['erro_ativar']}\n\nAbra no n8n para ver o passo com problema.")
    if res.get("url"):
        st.markdown("**Endereço do gatilho:**" if res.get("gatilho") == "webhook" else "**Link do formulário (divulgue):**")
        caixa_link(res["url"])
    if res.get("instrucao"):
        st.info(f"👉 {res['instrucao']}")
    st.markdown(f"[🔗 Abrir no n8n]({normalizar_url(S.n8n_url)}/workflow/{res['id']})")


with abas[4]:
    st.markdown("### 🧩 Criar automação")
    if aviso_conexao():
        modo = st.radio("Como você quer criar?", ["📦 Modelos prontos", "✨ Criar com IA", "📥 Importar fluxo (.json)"], horizontal=True, key=f"r_modo_criar_{V}")

        if modo.startswith("📦"):
            cats = list(CATEGORIAS)
            pre = S.get("_modelo_sel")
            cat_ini = cats.index(MODELOS[pre]["cat"]) if pre in MODELOS else 0
            cat = st.radio("Categoria", cats, format_func=nome_categoria, horizontal=True, index=cat_ini, key=f"r_cat_{V}")
            opcoes = [k for k, m in MODELOS.items() if m["cat"] == cat]
            chave = st.radio("Modelo", opcoes, format_func=lambda k: MODELOS[k]["titulo"], index=opcoes.index(pre) if pre in opcoes else 0,
                             key=f"r_mod_{cat}_{V}")
            m = MODELOS[chave]
            st.markdown(f'<div class="card">{m["desc"]}</div>', unsafe_allow_html=True)
            cfg = {"nome": st.text_input("Nome da automação", value=m["titulo"].split(" ", 1)[1], key=f"m_{chave}_nome_{V}")}
            col_a, col_b = st.columns(2)
            for i, (ch, rot, tipo, pad) in enumerate(m["campos"]):
                k = f"m_{chave}_{ch}_{V}"
                alvo = col_a if (tipo not in ("area",) and i % 2 == 0) else (col_b if tipo != "area" else st)
                if tipo == "area":
                    cfg[ch] = st.text_area(rot, value=pad, key=k, height=110)
                elif tipo == "check":
                    cfg[ch] = alvo.checkbox(rot, value=pad, key=k)
                elif tipo == "tom":
                    cfg[ch] = alvo.selectbox(rot, TONS, index=TONS.index(pad), key=k)
                elif tipo in ("destino", "destino_obrig"):
                    ops = DEST if tipo == "destino" else DEST[:3]
                    cfg[ch] = alvo.selectbox(rot, ops, index=ops.index(pad), format_func=lambda d: NOME_DEST[d] + ("" if d == "nenhum" or canal_pronto(d) else " (configurar)"),
                                             key=k)
                elif tipo == "dias":
                    cfg[ch] = alvo.multiselect(rot, DIAS_SEMANA, default=pad, key=k)
                elif tipo == "hora":
                    h = alvo.time_input(rot, value=datetime.strptime(pad, "%H:%M").time(), key=k, step=900)
                    cfg[ch] = h.strftime("%H:%M")
                elif tipo == "numero":
                    cfg[ch] = alvo.number_input(rot, min_value=1, max_value=1000, value=int(pad), key=k)
                elif tipo == "unidade":
                    cfg[ch] = alvo.selectbox(rot, list(UNIDADES), format_func=lambda u: UNIDADES[u], index=list(UNIDADES).index(pad), key=k)
                elif tipo == "tabela":
                    cfg[ch] = alvo.selectbox(rot, list(TABELAS), format_func=lambda t: TABELAS[t][0], index=list(TABELAS).index(pad), key=k)
                elif tipo == "rede":
                    cfg[ch] = alvo.selectbox(rot, REDES, index=REDES.index(pad), key=k)
                elif tipo == "senha":
                    cfg[ch] = alvo.text_input(rot, type="password", key=k)
                else:
                    cfg[ch] = alvo.text_input(rot, value=pad, key=k)
            if chave == "facebook":
                st.caption("ID e token da Página: developers.facebook.com → Graph API Explorer → escolha sua Página → permissões pages_manage_posts. "
                           "Prefira um token de longa duração.")
            if chave == "whats_agendado" and cfg.get("numeros"):
                st.caption(f"📱 {len(numeros_validos(cfg['numeros']))} número(s) válido(s). Envie só para quem autorizou receber.")
            try:
                _, precisa, _ = m["fn"](dict(cfg, path="previa"))
            except Exception:
                precisa = set()
            if precisa:
                st.markdown("**Usa:** " + " · ".join((("✅ " if canal_pronto(c) else "⚠️ ") + NOME_CANAL.get(c, c)) for c in sorted(precisa) if c in NOME_CANAL))
            ativar = st.checkbox("Ligar a automação assim que criar", value=True, key=f"m_{chave}_ativar_{V}")
            if st.button("🚀 Criar no meu n8n", type="primary", key=f"b_criar_{chave}_{V}"):
                vazios = [rot for ch, rot, tipo, _ in m["campos"] if ch in OBRIGATORIOS and tipo in ("texto", "area", "senha") and not str(cfg.get(ch, "")).strip()]
                if chave == "whats_agendado" and not numeros_validos(cfg.get("numeros", "")):
                    vazios.append("Números (nenhum número válido)")
                if chave in ("whats_agendado", "relatorio", "post_diario", "facebook") and not cfg.get("dias"):
                    vazios.append("Dias")
                if not cfg["nome"].strip():
                    vazios.append("Nome da automação")
                if vazios:
                    st.warning("Preencha: " + ", ".join(vazios))
                else:
                    with st.spinner("Criando no seu n8n…"):
                        r = rodar(criar_de_modelo, chave, cfg, ativar)
                    if r:
                        criado, info = r
                        S["_ultimo"] = {"id": criado["id"], "nome": cfg["nome"], "ativa": criado.get("active"), "erro_ativar": criado.get("_erro_ativar"),
                                        "url": url_gatilho(info), "gatilho": info.get("tipo"), "instrucao": info.get("instrucao")}
                        S.pop("_modelo_sel", None)
            if S.get("_ultimo"):
                mostrar_resultado_criacao(S["_ultimo"])

        elif modo.startswith("✨"):
            st.markdown("Descreva em português o que você quer que aconteça sozinho. Quanto mais detalhe, melhor.")
            st.caption("Ex.: “Toda segunda às 8h, leia a planilha de vendas e me mande no Telegram quantas vendas teve na semana” · "
                       "“Quando alguém preencher um formulário de orçamento, mande um e-mail com o orçamento e me avise no WhatsApp”.")
            desc = st.text_area("O que a automação deve fazer?", key=f"t_desc_ia_{V}", height=120)
            if st.button("✨ Montar com IA", type="primary", key="b_gerar_ia"):
                if len(desc.strip()) < 15:
                    st.warning("Descreva com um pouco mais de detalhe.")
                else:
                    with st.spinner("A IA está montando o fluxo…"):
                        S.rascunho_ia = rodar(gerar_fluxo_ia, desc.strip())
            rasc = S.rascunho_ia
            if rasc:
                st.markdown(f"#### 🧩 {rasc['name']}")
                if rasc.get("_explicacao"):
                    st.info(rasc["_explicacao"])
                passos = " → ".join(n["name"] for n in rasc["nodes"])
                st.markdown(f"**Passos:** {passos}")
                with st.expander("Ver o JSON do fluxo"):
                    st.json({k: rasc[k] for k in ("name", "nodes", "connections")}, expanded=False)
                ativ_ia = st.checkbox("Ligar assim que criar", value=False, key=f"c_ativ_ia_{V}",
                                      help="Recomendado: crie desligada, abra no n8n, confira e ligue.")
                cat_ia = st.selectbox("Categoria", list(CATEGORIAS) + ["outra"], format_func=lambda c: nome_categoria(c) if c in CATEGORIAS else "🧩 Outra",
                                      key=f"s_cat_ia_{V}")
                b1, b2 = st.columns(2)
                if b1.button("🚀 Criar no meu n8n", type="primary", key="b_criar_ia", width="stretch"):
                    wf = {k: rasc[k] for k in ("name", "nodes", "connections", "settings")}
                    with st.spinner("Criando…"):
                        criado = rodar(criar_fluxo_livre, wf, ativ_ia, cat_ia, "ia")
                    if criado:
                        a = S.automacoes[-1]
                        S["_ultimo_ia"] = {"id": criado["id"], "nome": rasc["name"], "ativa": criado.get("active"), "erro_ativar": criado.get("_erro_ativar"),
                                           "url": a.get("url_gatilho"), "gatilho": a.get("gatilho"), "instrucao": rasc.get("_explicacao")}
                        S.rascunho_ia = None
                        st.rerun()
                if b2.button("🗑️ Descartar", key="b_desc_ia", width="stretch"):
                    S.rascunho_ia = None
                    st.rerun()
            if S.get("_ultimo_ia") and not S.rascunho_ia:
                mostrar_resultado_criacao(S["_ultimo_ia"])

        else:
            st.markdown("Cole o conteúdo de um fluxo do n8n (.json) — por exemplo, um modelo de **n8n.io/workflows** — ou envie o arquivo.")
            arq_wf = st.file_uploader("Arquivo .json do fluxo", type=["json"], key=f"up_wf_{V}")
            txt = st.text_area("…ou cole o JSON aqui", key=f"t_json_wf_{V}", height=140)
            ativ_imp = st.checkbox("Ligar assim que criar", value=False, key=f"c_ativ_imp_{V}")
            if st.button("📥 Importar para o meu n8n", type="primary", key="b_importar"):
                bruto = arq_wf.getvalue().decode("utf-8", "ignore") if arq_wf else txt
                try:
                    d = json.loads(bruto)
                    if isinstance(d, dict) and "workflow" in d and isinstance(d["workflow"], dict):
                        d = d["workflow"]
                    wf = validar_fluxo(d, restrito=False)
                except (ValueError, TypeError):
                    st.error("Isso não é um JSON válido de fluxo do n8n.")
                    wf = None
                except ErroAPI as e:
                    st.error(str(e))
                    wf = None
                if wf:
                    with st.spinner("Importando…"):
                        criado = rodar(criar_fluxo_livre, wf, ativ_imp, "outra", "importado")
                    if criado:
                        st.success(f"✅ Fluxo **{wf['name']}** importado!")
                        st.markdown(f"[🔗 Abrir no n8n]({normalizar_url(S.n8n_url)}/workflow/{criado['id']}) — confira as credenciais dos passos marcados em vermelho.")


# ══════════════════════════════════════════════════════════════════════════
# 6. MINHAS AUTOMAÇÕES
# ══════════════════════════════════════════════════════════════════════════
ST_EXEC = {"success": ("ok", "✅ Deu certo"), "error": ("atr", "❌ Erro"), "crashed": ("atr", "💥 Falhou"), "waiting": ("neu", "⏳ Esperando"),
           "running": ("neu", "▶️ Rodando"), "canceled": ("fim", "✖ Cancelada"), "new": ("neu", "🆕 Na fila")}


def detalhe_execucao(eid: str) -> str:
    d = n8n("GET", f"/executions/{eid}", params={"includeData": "true"})
    rd = ((d.get("data") or {}).get("resultData") or {})
    linhas = []
    for no, runs in (rd.get("runData") or {}).items():
        er = (runs or [{}])[0].get("error")
        linhas.append(f"{'❌' if er else '✅'} **{no}**" + (f" — {er.get('message', '')} {er.get('description') or ''}" if er else ""))
    erro = rd.get("error") or {}
    if erro.get("message"):
        linhas.insert(0, f"**Motivo:** {erro.get('message')}")
    return "\n\n".join(linhas) or "Sem detalhes."


with abas[5]:
    st.markdown("### 📋 Minhas automações")
    if aviso_conexao():
        a1, a2 = st.columns([1, 3])
        if a1.button("🔄 Atualizar lista", type="primary", key="b_lista", width="stretch") or "_lista" not in S:
            with st.spinner("Buscando no seu n8n…"):
                lista = rodar(n8n_listar)
                exe = rodar(n8n_execucoes, None, 100)
            if lista is not None:
                S["_lista"] = sorted(lista, key=lambda w: w.get("updatedAt") or "", reverse=True)
                S["_exec_todas"] = exe or []
        lista = S.get("_lista", [])
        exe = S.get("_exec_todas", [])
        ok_n = sum(1 for e in exe if e.get("status") == "success")
        er_n = sum(1 for e in exe if e.get("status") in ("error", "crashed"))
        a2.markdown(f"**{len(lista)}** automações · **{sum(1 for w in lista if w.get('active'))}** ligadas · últimas execuções: "
                    f"{chip('ok', f'{ok_n} ✅')} {chip('atr', f'{er_n} ❌')}", unsafe_allow_html=True)
        meus = {a["id"]: a for a in S.automacoes}
        filtro = st.text_input("🔎 Procurar", key=f"t_filtro_{V}", placeholder="nome da automação")
        if not lista:
            st.info("Nenhuma automação ainda. Crie a primeira em 🧩 Criar automação.")
        for w in lista:
            if filtro and filtro.lower() not in str(w.get("name", "")).lower():
                continue
            wid, meu = w["id"], meus.get(w["id"], {})
            ultimas = [e for e in exe if str(e.get("workflowId")) == str(wid)]
            with st.container(border=True):
                t1, t2 = st.columns([3, 2])
                t1.markdown(f"**{w.get('name')}** &nbsp; " + (chip("ok", "🟢 Ligada") if w.get("active") else chip("fim", "⚪ Desligada"))
                            + (f" &nbsp; {chip('neu', nome_categoria(meu['categoria']))}" if meu else ""), unsafe_allow_html=True)
                ult = ultimas[0] if ultimas else None
                t1.caption(f"Atualizada em {br_data(w.get('updatedAt'))}" + (f" · última execução: {br_data(ult.get('startedAt'))} "
                                                                              f"({ST_EXEC.get(ult.get('status'), ('', ult.get('status')))[1]})" if ult else ""))
                if meu.get("url_gatilho"):
                    t1.markdown(f'<div class="link-box">{meu["url_gatilho"]}</div>', unsafe_allow_html=True)
                b = t2.columns(3)
                if b[0].button("⏸️ Desligar" if w.get("active") else "▶️ Ligar", key=f"b_tog_{wid}", width="stretch"):
                    if fez(n8n_ativar, wid, not w.get("active")):
                        w["active"] = not w.get("active")
                        registrar("Automação " + ("ligada" if w["active"] else "desligada"), w.get("name"))
                        st.rerun()
                b[1].link_button("🔗 Abrir", f"{normalizar_url(S.n8n_url)}/workflow/{wid}", width="stretch")
                if b[2].button("🗑️", key=f"b_del_{wid}", width="stretch", help="Apagar"):
                    S["_conf_del"] = wid
                c = t2.columns(3)
                if TESTES.get(meu.get("modelo")) and c[0].button("🧪 Testar", key=f"b_test_{wid}", width="stretch"):
                    r = rodar(testar_automacao, meu)
                    if r:
                        st.success(r)
                ver_exec = c[1].toggle("📜 Execuções", key=f"tg_exec_{wid}")
                if c[2].button("⬇️ JSON", key=f"b_json_{wid}", width="stretch"):
                    d = rodar(n8n, "GET", f"/workflows/{wid}")
                    if d:
                        S[f"_json_{wid}"] = json.dumps({k: d.get(k) for k in ("name", "nodes", "connections", "settings")}, ensure_ascii=False, indent=2)
                if S.get(f"_json_{wid}"):
                    st.download_button("💾 Baixar .json", data=S[f"_json_{wid}"].encode("utf-8"), file_name=f"{slug(w.get('name', 'fluxo'))}.json",
                                       mime="application/json", key=f"dl_json_{wid}")
                if S.get("_conf_del") == wid:
                    st.warning(f"Apagar **{w.get('name')}** do seu n8n? Isso não pode ser desfeito.")
                    d1, d2 = st.columns(2)
                    if d1.button("✅ Sim, apagar", key=f"b_del_sim_{wid}", width="stretch"):
                        if fez(apagar_automacao, wid):
                            S["_lista"] = [x for x in S["_lista"] if x["id"] != wid]
                            S.pop("_conf_del", None)
                            st.rerun()
                    if d2.button("✖ Cancelar", key=f"b_del_nao_{wid}", width="stretch"):
                        S.pop("_conf_del", None)
                        st.rerun()
                if ver_exec:
                    execs = rodar(n8n_execucoes, wid, 10) or []
                    if not execs:
                        st.caption("Ainda não rodou nenhuma vez.")
                    for e in execs:
                        cls, txt = ST_EXEC.get(e.get("status"), ("neu", e.get("status")))
                        st.markdown(f"{chip(cls, txt)} &nbsp; {br_data(e.get('startedAt'))} &nbsp; <small>#{e.get('id')}</small>", unsafe_allow_html=True)
                        if e.get("status") in ("error", "crashed"):
                            with st.expander(f"Ver o motivo do erro #{e.get('id')}"):
                                det = rodar(detalhe_execucao, e["id"])
                                if det:
                                    st.markdown(det)


# ══════════════════════════════════════════════════════════════════════════
# 7. PLANILHAS
# ══════════════════════════════════════════════════════════════════════════
with abas[6]:
    st.markdown("### 📊 Planilhas")
    st.caption("Leads, vendas e atendimentos que as automações guardam ficam em planilhas dentro do seu n8n (Data tables). Veja e baixe aqui.")
    if aviso_conexao():
        p1, p2 = st.columns([1, 1])
        if p1.button("🔄 Atualizar planilhas", key="b_tabs", width="stretch") or "_tabs_n8n" not in S:
            S["_tabs_n8n"] = (rodar(n8n, "GET", "/data-tables", None, {"limit": 100}) or {}).get("data", [])
        if p2.button("➕ Criar as planilhas padrão", key="b_tabs_padrao", width="stretch"):
            with st.spinner("Criando…"):
                for k in TABELAS:
                    if rodar(garantir_tabela, k) is None:
                        break
                S["_tabs_n8n"] = (rodar(n8n, "GET", "/data-tables", None, {"limit": 100}) or {}).get("data", [])
        tabs = S.get("_tabs_n8n", [])
        if not tabs:
            st.info("Nenhuma planilha ainda. Elas são criadas sozinhas quando você cria uma automação que guarda dados.")
        else:
            nomes_t = {t["id"]: t["name"] for t in tabs}
            tid = st.selectbox("Planilha", list(nomes_t), format_func=lambda i: nomes_t[i], key=f"s_tab_{V}")
            linhas = rodar(linhas_tabela, tid) or []
            if not linhas:
                st.info("Esta planilha ainda está vazia.")
            else:
                df = pd.DataFrame(linhas)
                ocultas = [c for c in ("id", "createdAt", "updatedAt") if c in df.columns]
                df_vis = df.drop(columns=ocultas).iloc[::-1].reset_index(drop=True)
                st.markdown(f"**{len(df_vis)}** linha(s)")
                busca = st.text_input("🔎 Filtrar", key=f"t_busca_tab_{V}")
                if busca:
                    df_vis = df_vis[df_vis.apply(lambda r: busca.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
                st.dataframe(df_vis, width="stretch", hide_index=True)
                nome_arq = slug(nomes_t[tid])
                x1, x2 = st.columns(2)
                x1.download_button("📊 Baixar em Excel", data=xlsx_bytes([(nomes_t[tid][:28], [list(df_vis.columns)] + df_vis.astype(str).values.tolist())]),
                                   file_name=f"{nome_arq}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
                x2.download_button("📄 Baixar em CSV", data=df_vis.to_csv(index=False, sep=";").encode("utf-8-sig"), file_name=f"{nome_arq}.csv",
                                   mime="text/csv", width="stretch")


# ══════════════════════════════════════════════════════════════════════════
# 8. SERVIDOR (Railway)
# ══════════════════════════════════════════════════════════════════════════
SEGREDOS_VAR = ("KEY", "SECRET", "PASSWORD", "TOKEN")

with abas[7]:
    st.markdown("### 🛠️ Servidor")
    R = S.rw
    url_srv = S.n8n_url or (f"https://{R['domain']}" if R.get("domain") else "")
    if url_srv:
        s1, s2 = st.columns([3, 1])
        s1.markdown(f"**Endereço:** [{url_srv}]({url_srv})")
        if s2.button("🔎 Está ligado?", key="b_srv_on", width="stretch"):
            S["_online"], S["_online_em"] = n8n_online(url_srv), agora()
        if "_online" in S:
            s1.markdown(chip("ok", "✅ n8n respondendo") if S["_online"] else chip("atr", "❌ n8n não respondeu"), unsafe_allow_html=True)
    if not R.get("service_id"):
        st.info("O controle do servidor funciona para n8n instalados ou escolhidos na aba 🚀 Instalar n8n.")
    elif not S.rw_token:
        st.info("Por segurança o token do Railway não fica salvo. Cole de novo para controlar o servidor:")
        bloco_token_railway("tok_srv")
    else:
        st.markdown(f"**Projeto:** {R.get('project_nome')} · **Fuso:** {R.get('fuso') or '—'}")
        if st.button("🔄 Ver implantações", key="b_deps") or "_deps" not in S:
            S["_deps"] = rodar(rw_deploys, 8) or []
        deps = S.get("_deps", [])
        if deps:
            cls, txt = STATUS_DEPLOY.get(deps[0]["status"], ("neu", deps[0]["status"]))
            st.markdown(f"**Situação atual:** {chip(cls, txt)} &nbsp; desde {br_data(deps[0].get('createdAt'))}", unsafe_allow_html=True)
            with st.expander("📜 Histórico de implantações"):
                st.dataframe(pd.DataFrame([{"Quando": br_data(d.get("createdAt")), "Situação": STATUS_DEPLOY.get(d["status"], ("", d["status"]))[1],
                                            "ID": d["id"]} for d in deps]), width="stretch", hide_index=True)
        o1, o2, o3 = st.columns(3)
        if o1.button("🔁 Reiniciar", key="b_restart", width="stretch", help="Desliga e liga de novo (resolve travamentos)"):
            if fez(rw_reiniciar):
                registrar("Servidor reiniciado")
                st.success("Reiniciando… volta em 1 a 2 minutos.")
        if o2.button("🚀 Reimplantar", key="b_redeploy", width="stretch", help="Aplica mudanças de configuração"):
            if fez(rw_ligar, False):
                registrar("Servidor reimplantado")
                st.success("Reimplantação iniciada. Leva de 2 a 4 minutos.")
                S.pop("_deps", None)
        if o3.button("⬆️ Atualizar n8n", key="b_update", width="stretch", help="Busca a versão mais nova do n8n"):
            if fez(rw_ligar, True):
                registrar("n8n atualizado para a versão mais nova")
                st.success("Atualizando… seus dados ficam guardados no disco permanente. Leva de 2 a 5 minutos.")
                S.pop("_deps", None)

        with st.expander("📄 Registros (logs) — para descobrir problemas"):
            if deps:
                tipo_log = st.radio("Quais registros?", ["Funcionamento", "Preparação (build)"], horizontal=True, key=f"r_log_{V}")
                dsel = st.selectbox("Implantação", [d["id"] for d in deps], format_func=lambda i: next(
                    f"{br_data(d.get('createdAt'))} — {STATUS_DEPLOY.get(d['status'], ('', d['status']))[1]}" for d in deps if d["id"] == i), key=f"s_dep_log_{V}")
                if st.button("Carregar registros", key="b_logs"):
                    logs = rodar(rw_logs, dsel, tipo_log.startswith("Prep"), 300) or []
                    texto = "\n".join(f"{br_data(l.get('timestamp'))[-5:]}  {l.get('message', '')}" for l in logs) or "Sem registros."
                    st.code(texto[-15000:], language=None)
                    S["_ultimos_logs"] = texto[-6000:]
                if S.get("_ultimos_logs") and st.button("🤖 Pedir para a IA explicar estes registros", key="b_ia_logs"):
                    with st.spinner("Lendo os registros…"):
                        exp = rodar(ia, f"Explique para uma pessoa leiga, em até 8 linhas, se há algum problema nestes registros do n8n rodando no "
                                         f"Railway e o que fazer. Registros:\n{S['_ultimos_logs']}")
                    if exp:
                        st.info(exp)

        with st.expander("⚙️ Configurações (variáveis)"):
            vars_ = rodar(rw_variaveis) or {}
            vis = {k: ("•••••• (oculto)" if any(s in k.upper() for s in SEGREDOS_VAR) else v) for k, v in sorted(vars_.items()) if not k.startswith("RAILWAY_")}
            if vis:
                st.dataframe(pd.DataFrame([{"Variável": k, "Valor": v} for k, v in vis.items()]), width="stretch", hide_index=True)
            st.caption("Mude só se souber o que está fazendo. Ex.: GENERIC_TIMEZONE muda o fuso dos agendamentos. "
                       "Nunca mude N8N_ENCRYPTION_KEY (suas credenciais deixariam de abrir).")
            v1, v2 = st.columns(2)
            nome_v = v1.text_input("Variável", key=f"t_var_n_{V}", placeholder="GENERIC_TIMEZONE")
            val_v = v2.text_input("Valor", key=f"t_var_v_{V}", placeholder="America/Sao_Paulo")
            if st.button("💾 Salvar e aplicar", key="b_var_salvar"):
                if not re.match(r"^[A-Z_][A-Z0-9_]*$", nome_v.strip()):
                    st.warning("Use só letras MAIÚSCULAS, números e _ no nome da variável.")
                elif nome_v.strip() == "N8N_ENCRYPTION_KEY":
                    st.error("Por segurança o app não muda essa variável.")
                else:
                    if fez(rw_salvar_variaveis, {nome_v.strip(): val_v}, True):
                        if nome_v.strip() in ("GENERIC_TIMEZONE", "TZ"):
                            S.rw["fuso"] = val_v
                        registrar("Variável alterada", nome_v.strip())
                        st.success("Salvo! O servidor vai reimplantar com a nova configuração.")

        with st.expander("🗑️ Zona de perigo — apagar o servidor"):
            st.error("Apaga o projeto inteiro no Railway: o n8n, o disco com TODAS as automações, credenciais e planilhas. Não tem volta.")
            conf = st.text_input(f"Para confirmar, digite o nome do projeto: {R.get('project_nome')}", key=f"t_conf_del_{V}")
            if st.button("Apagar tudo no Railway", key="b_del_proj", disabled=conf.strip() != (R.get("project_nome") or "").strip() or not conf.strip()):
                if fez(rw_excluir_projeto):
                    registrar("Servidor apagado no Railway", R.get("project_nome"))
                    S.rw, S.n8n_url, S.n8n_key = {}, "", ""
                    for k in ("_api_ok", "_lista", "_deps", "_online", "tabelas"):
                        S.pop(k, None)
                    S.cred_ids = {}
                    S.ver += 1
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# 9. ASSISTENTE (conversa que executa ações)
# ══════════════════════════════════════════════════════════════════════════
ACOES = {
    "listar": "📋 Atualizar e mostrar minhas automações",
    "ligar": "▶️ Ligar a automação",
    "desligar": "⏸️ Desligar a automação",
    "status": "🔎 Ver se o servidor está ligado",
    "reiniciar": "🔁 Reiniciar o servidor",
    "criar_ia": "✨ Montar a automação com IA",
    "modelo": "📦 Abrir o modelo pronto",
}


def contexto_assistente() -> str:
    lista = [{"id": w["id"], "nome": w.get("name"), "ligada": bool(w.get("active"))} for w in S.get("_lista", [])][:60]
    return json.dumps({
        "railway_conectado": bool(S.rw_token), "n8n_instalado": bool(S.rw.get("feito", {}).get("ligar") or S.n8n_url),
        "endereco_n8n": S.n8n_url, "api_n8n_conectada": bool(S.get("_api_ok")),
        "canais_prontos": [NOME_CANAL[c] for c in ("whats", "telegram", "email") if canal_pronto(c)],
        "automacoes_no_n8n": lista or "lista ainda não carregada",
        "modelos_prontos": {k: m["titulo"] for k, m in MODELOS.items()},
    }, ensure_ascii=False)


def executar_acao(a: dict) -> str:
    tipo = a.get("tipo")
    if tipo == "listar":
        S["_lista"] = n8n_listar()
        return "Lista atualizada:\n" + "\n".join(f"- {'🟢' if w.get('active') else '⚪'} {w.get('name')}" for w in S["_lista"]) if S["_lista"] else "Você ainda não tem automações."
    if tipo in ("ligar", "desligar"):
        n8n_ativar(str(a.get("id")), tipo == "ligar")
        S.pop("_lista", None)
        registrar(f"Automação {'ligada' if tipo == 'ligar' else 'desligada'} pelo assistente", str(a.get("id")))
        return f"Pronto! Automação {'ligada' if tipo == 'ligar' else 'desligada'}."
    if tipo == "status":
        url = S.n8n_url or (f"https://{S.rw['domain']}" if S.rw.get("domain") else "")
        if not url:
            return "Você ainda não tem um n8n instalado. Vá em 🚀 Instalar n8n."
        on = n8n_online(url)
        extra = ""
        if S.rw_token and S.rw.get("service_id"):
            deps = rw_deploys(1)
            if deps:
                extra = f" Railway: {STATUS_DEPLOY.get(deps[0]['status'], ('', deps[0]['status']))[1]}."
        return ("✅ Seu n8n está ligado e respondendo." if on else "❌ Seu n8n não respondeu agora.") + extra
    if tipo == "reiniciar":
        rw_reiniciar()
        registrar("Servidor reiniciado pelo assistente")
        return "🔁 Reiniciando. Em 1 a 2 minutos ele volta."
    if tipo == "criar_ia":
        S.rascunho_ia = gerar_fluxo_ia(str(a.get("descricao") or ""))
        return f"✨ Montei o fluxo **{S.rascunho_ia['name']}**. Abra a aba 🧩 Criar automação → ✨ Criar com IA para conferir e criar."
    if tipo == "modelo" and a.get("modelo") in MODELOS:
        S["_modelo_sel"] = a["modelo"]
        S.ver += 1
        return f"Abra a aba 🧩 Criar automação: deixei o modelo **{MODELOS[a['modelo']]['titulo']}** selecionado."
    return "Não entendi essa ação."


with abas[8]:
    st.markdown("### 💬 Assistente")
    st.caption("Pergunte qualquer coisa sobre n8n, Railway e automações — ou peça: “liste minhas automações”, “desligue a de vendas”, "
               "“meu servidor está ligado?”, “crie uma automação que…”.")
    for i, msg in enumerate(S.chat):
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "⚡"):
            st.markdown(msg["content"])
    pend = S.get("_acao_pend")
    if pend:
        rot = ACOES.get(pend.get("tipo"), pend.get("tipo"))
        alvo = next((w.get("name") for w in S.get("_lista", []) if str(w["id"]) == str(pend.get("id"))), "")
        p1, p2 = st.columns([2, 1])
        if p1.button(f"{rot}{(': ' + alvo) if alvo else ''}", type="primary", key="b_exec_acao", width="stretch"):
            with st.spinner("Fazendo…"):
                r = rodar(executar_acao, pend)
            S.pop("_acao_pend", None)
            if r:
                S.chat.append({"role": "assistant", "content": r})
            st.rerun()
        if p2.button("✖ Não fazer", key="b_nao_acao", width="stretch"):
            S.pop("_acao_pend", None)
            st.rerun()
    pergunta = st.chat_input("Escreva para o assistente…")
    if pergunta:
        S.chat.append({"role": "user", "content": pergunta})
        instr = ("Responda SEMPRE em JSON: {\"resposta\": \"texto em markdown para a pessoa\", \"acao\": null ou {\"tipo\": um de "
                 f"{list(ACOES)}, \"id\": \"id da automação (para ligar/desligar)\", \"descricao\": \"pedido completo (para criar_ia)\", "
                 "\"modelo\": \"chave do modelo (para modelo)\"}}. Proponha uma ação só quando a pessoa pedir algo que o app pode fazer; "
                 "o app vai mostrar um botão para ela confirmar. Se a pessoa quiser criar algo que um modelo pronto resolve, prefira tipo 'modelo'. "
                 f"Estado atual do app: {contexto_assistente()}")
        hist = [{"role": "user", "content": instr}, {"role": "assistant", "content": "{\"resposta\": \"Entendido.\", \"acao\": null}"}] + S.chat[-12:]
        with st.spinner("Pensando…"):
            d = rodar(ia_json, hist)
        if d:
            resp = str(d.get("resposta") or "").strip() or "Certo!"
            S.chat.append({"role": "assistant", "content": resp})
            ac = d.get("acao")
            if isinstance(ac, dict) and ac.get("tipo") in ACOES:
                S["_acao_pend"] = ac
        else:
            S.chat.pop()
        st.rerun()
    if S.chat and st.button("🧹 Limpar conversa", key="b_limpa_chat"):
        S.chat = []
        S.pop("_acao_pend", None)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# 10. RELATÓRIO
# ══════════════════════════════════════════════════════════════════════════
with abas[9]:
    st.markdown("### 📑 Relatório e exportação")
    st.caption("Tudo o que foi feito: servidor, canais, automações e histórico. Tokens e senhas nunca aparecem.")
    marca = datetime.now().strftime("%Y%m%d_%H%M")
    e1, e2, e3 = st.columns(3)
    e1.download_button("📄 Relatório (.txt)", data=relatorio_txt().encode("utf-8"), file_name=f"n8n_facil_relatorio_{marca}.txt",
                       mime="text/plain", width="stretch")
    e2.download_button("📊 Relatório (Excel)", data=relatorio_xlsx(), file_name=f"n8n_facil_relatorio_{marca}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    e3.download_button("💾 Minha memória (.json)", data=memoria_json(), file_name=f"n8n_facil_memoria_{marca}.json",
                       mime="application/json", width="stretch")
    with st.expander("👀 Ver o relatório"):
        st.text(relatorio_txt())
    if S.historico:
        st.markdown("#### 🕓 Histórico")
        st.dataframe(pd.DataFrame(list(reversed(S.historico))).rename(columns={"quando": "Quando", "acao": "Ação", "detalhe": "Detalhe"}),
                     width="stretch", hide_index=True)

mostrar_guia()
st.markdown(f'<div class="rodape">n8n é marca da n8n GmbH; Railway é marca da Railway Corp. Este app usa as APIs oficiais na SUA conta.<br>'
            f'© 2026 <a href="{SITE}" target="_blank" style="color:#9C94B0;">MeusAgentesIA.com.br</a></div>', unsafe_allow_html=True)
