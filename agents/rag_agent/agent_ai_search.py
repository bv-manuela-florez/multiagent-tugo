import os
import logging
from azure.ai.agents import AgentsClient
from azure.identity import ClientSecretCredential
from azure.ai.agents.models import ListSortOrder, MessageRole
from dotenv import load_dotenv
from utils.keyvault import get_kv_variable  # Importa la función para obtener secretos

load_dotenv(override=True)

logger = logging.getLogger(__name__)


class AISearchAgent:
    def __init__(self):
        client_secret = get_kv_variable("AZURE-CLIENT-SECRET")
        self.agents_client = AgentsClient(
            endpoint=os.environ["PROJECT_ENDPOINT"],
            credential=ClientSecretCredential(
                tenant_id=os.environ["AZURE_TENANT_ID"],
                client_id=os.environ["AZURE_CLIENT_ID"],
                client_secret=client_secret,
                ),
        )

        # Usa el agente existente por ID desde variable de entorno
        self.agent_id = os.environ["AGENT_ID_AI_SEARCH"]

        self.thread = None  # No uses variable de clase para el thread

    def send(self, user_query, thread_id=None):
        # Usa el thread_id proporcionado o crea uno nuevo si no hay
        if thread_id:
            self.thread = self.agents_client.threads.get(thread_id)
        else:
            self.thread = self.agents_client.threads.create()
            print(f"Created thread, ID: {self.thread.id}")

        logger.info("AISearchAgent.send called", extra={"custom_dimensions": {"query": user_query}})
        # Envía el mensaje del usuario al thread del agente
        message = self.agents_client.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=user_query,
        )
        print(f"Created message, ID: {message.id}")

        # Procesa la consulta con el agente existente
        run = self.agents_client.runs.create_and_process(thread_id=self.thread.id, agent_id=self.agent_id)
        print(f"Run finished with status: {run.status}")
        print("Run attributes and methods:", dir(run))
        token_usage = None
        if run.usage:
            token_usage = {
                "prompt_tokens": run.usage.get("prompt_tokens"),
                "completion_tokens": run.usage.get("completion_tokens"),
                "total_tokens": run.usage.get("total_tokens")
            }
            print(f"Token usage from run: {token_usage}")

        agent_tools = None
        if run.tools:
            agent_tools = [str(tool) for tool in run.tools]
            print(f"Agent tools from run: {agent_tools}")

        if run.status == "failed":
            logger.error("AISearchAgent run failed", extra={"custom_dimensions": {"error": run.last_error}})
            print(f"Run failed: {run.last_error}")
            return {
                "text": "Error: Run failed.",
                "thread_id": self.thread.id,
                "agent_id": self.agent_id,
                "agent": "agent_ai_search",
                "token_usage": token_usage,
                "agent_tools": agent_tools
            }

        # Recupera y retorna la última respuesta del agente
        messages = self.agents_client.messages.list(thread_id=self.thread.id, order=ListSortOrder.ASCENDING)
        for message in reversed(list(messages)):
            if message.role == MessageRole.AGENT and getattr(message, "text_messages", None):
                print(f"Agent response: {message.text_messages[-1].text.value}")
                return {
                    "text": message.text_messages[-1].text.value,
                    "thread_id": self.thread.id,
                    "agent_id": self.agent_id,
                    "agent": "agent_ai_search",
                    "token_usage": token_usage,
                    "agent_tools": agent_tools
                }
        return {
            "text": "No response from agent.",
            "thread_id": self.thread.id,
            "agent_id": self.agent_id,
            "agent": "agent_ai_search",
            "token_usage": token_usage,
            "agent_tools": agent_tools
        }

    def close(self):
        # Solo limpia la referencia al thread, no elimina el agente
        if self.thread:
            self.thread = None
