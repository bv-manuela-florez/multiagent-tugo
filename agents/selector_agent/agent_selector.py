from azure.identity import ClientSecretCredential
from azure.ai.agents import AgentsClient
import os
from dotenv import load_dotenv
from azure.ai.agents.models import ListSortOrder, MessageRole
from utils.keyvault import get_kv_variable  # Importa la función para obtener secretos

load_dotenv()  # Load variables from .env file

client_secret = get_kv_variable("AZURE-CLIENT-SECRET")
agents_client = AgentsClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=ClientSecretCredential(
                    tenant_id=os.environ["AZURE_TENANT_ID"],
                    client_id=os.environ["AZURE_CLIENT_ID"],
                    client_secret=client_secret,
                    ),
)

# Usa el agente existente por ID desde variable de entorno
AGENT_ID_SELECTOR = os.environ["AGENT_ID_SELECTOR"]

# Crea el thread solo una vez y lo reutiliza
_thread = None


def run_selector_agent(user_query):
    global _thread
    if not _thread:
        _thread = agents_client.threads.create()
        print(f"Created thread, ID: {_thread.id}")

    # Envía el mensaje del usuario al thread del agente
    message = agents_client.messages.create(
        thread_id=_thread.id,
        role="user",
        content=user_query,
    )
    print(f"Created message, ID: {message.id}")

    # Procesa la consulta con el agente existente
    run = agents_client.runs.create_and_process(thread_id=_thread.id, agent_id=AGENT_ID_SELECTOR)
    print(f"Run finished with status: {run.status}")

    if run.status == "failed":
        print(f"Run failed: {run.last_error}")
        return {
            "text": "Error: Run failed.",
            "thread_id": _thread.id,
            "agent_id": AGENT_ID_SELECTOR,
            "agent": "agent_selector"
        }

    # Recupera y retorna la última respuesta del agente
    messages = agents_client.messages.list(thread_id=_thread.id, order=ListSortOrder.ASCENDING)
    agent_response = None
    for msg in reversed(list(messages)):
        if msg.role == MessageRole.AGENT and getattr(msg, "text_messages", None):
            agent_response = msg.text_messages[-1].text.value
            break
    print(f"Agent response: {agent_response}")
    return {
        "text": agent_response,
        "thread_id": _thread.id,
        "agent_id": AGENT_ID_SELECTOR,
        "agent": "agent_selector"
    }
