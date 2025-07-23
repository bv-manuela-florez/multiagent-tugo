from dotenv import load_dotenv
import os
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FilePurpose, ListSortOrder
from azure.identity import ClientSecretCredential
from pathlib import Path
from utils.keyvault import get_kv_variable  # Importa la función para obtener secretos

# --- NUEVO: Azure Blob Storage ---
from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta

load_dotenv()


class InterpreterAgent:
    # Variables de clase para compartir thread entre instancias
    _thread = None
    _file = None
    _agents_client = None

    def __init__(self):
        client_secret = get_kv_variable("AZURE-CLIENT-SECRET")
        # Inicializa el cliente solo una vez
        if not InterpreterAgent._agents_client:
            InterpreterAgent._agents_client = AgentsClient(
                endpoint=os.environ["PROJECT_ENDPOINT"],
                credential=ClientSecretCredential(
                    tenant_id=os.environ["AZURE_TENANT_ID"],
                    client_id=os.environ["AZURE_CLIENT_ID"],
                    client_secret=client_secret,
                    ),
            )
        self.agents_client = InterpreterAgent._agents_client

        # Usa el agente existente por ID desde variable de entorno
        self.agent_id = os.environ["AGENT_ID_INTERPRETER"]

        # Sube el archivo solo una vez (si es necesario)
        if not InterpreterAgent._file:
            asset_file_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "notebook", "results_500.csv")
            )
            InterpreterAgent._file = self.agents_client.files.upload_and_poll(
                file_path=asset_file_path, purpose=FilePurpose.AGENTS
            )
            print(f"Uploaded file, file ID: {InterpreterAgent._file.id}")

        self.file = InterpreterAgent._file

        # --- Azure Blob Storage usando nombre de cuenta y clave ---
        account_name = os.environ.get("AZURE_BLOB_ACCOUNT_NAME") or get_kv_variable("AZURE-BLOB-ACCOUNT-NAME")
        account_key = os.environ.get("AZURE_BLOB_ACCOUNT_KEY") or get_kv_variable("AZURE-BLOB-ACCOUNT-KEY")
        self.account_key = account_key  # <-- Agregado
        self.container_name = os.environ.get("AZURE_BLOB_CONTAINER", "generated-images")
        blob_url = f"https://{account_name}.blob.core.windows.net"
        self.blob_service_client = BlobServiceClient(
            account_url=blob_url,
            credential=account_key
        )
        # Crea el contenedor si no existe
        try:
            self.blob_service_client.create_container(self.container_name)
        except Exception:
            pass  # Ya existe

        self.thread = None  # No uses variable de clase para el thread

    def send(self, user_query, thread_id=None):
        # Usa el thread_id proporcionado o crea uno nuevo si no hay
        if thread_id:
            self.thread = self.agents_client.threads.get(thread_id)
        else:
            self.thread = self.agents_client.threads.create()
            print(f"Created thread, thread ID: {self.thread.id}")

        # Envía el mensaje del usuario al thread del agente
        message = self.agents_client.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=user_query,
        )
        print(f"Created message, message ID: {message.id}")

        # Procesa la consulta con el agente existente
        run = self.agents_client.runs.create_and_process(thread_id=self.thread.id, agent_id=self.agent_id)
        print(f"Run finished with status: {run.status}")
        # Extraer token usage directamente de run.usage
        token_usage = None
        if run.usage:
            token_usage = {
                "prompt_tokens": run.usage.get("prompt_tokens"),
                "completion_tokens": run.usage.get("completion_tokens"),
                "total_tokens": run.usage.get("total_tokens")
            }
            print(f"Token usage from run: {token_usage}")

        # Extraer agent_tools si existen
        agent_tools = None
        if run.tools:
            # Si run.tools es una lista de objetos, extrae el nombre o tipo
            agent_tools = [str(tool) for tool in run.tools]
            print(f"Agent tools from run: {agent_tools}")

        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            return {
                "text": "Error: Run failed.",
                "images": [],
                "thread_id": self.thread.id,
                "agent_id": self.agent_id,
                "agent": "agent_interpreter",
                "token_usage": token_usage,
                "agent_tools": agent_tools
            }

        # Recupera y retorna la última respuesta del agente y guarda imágenes si existen
        messages = self.agents_client.messages.list(
            thread_id=self.thread.id,
            order=ListSortOrder.ASCENDING
        )
        images = []
        response_text = "No response from agent."

        for msg in reversed(list(messages)):
            # Guardar imágenes generadas por el agente en Azure Blob Storage
            for img in getattr(msg, "image_contents", []):
                file_id = img.image_file.file_id
                file_name = f"{file_id}_image_file.png"
                # Descarga en el directorio actual
                self.agents_client.files.save(file_id=file_id, file_name=file_name)
                src = Path(os.getcwd()) / file_name

                try:
                    blob_client = self.blob_service_client.get_blob_client(
                        container=self.container_name,
                        blob=file_name
                    )
                    with open(src, "rb") as data:
                        blob_client.upload_blob(
                            data,
                            overwrite=True,
                            content_settings=ContentSettings(content_type="image/png")
                        )
                    os.remove(src)
                    # --- NUEVO: Genera URL SAS válida por 24h ---
                    sas_token = generate_blob_sas(
                        account_name=blob_client.account_name,
                        container_name=self.container_name,
                        blob_name=file_name,
                        account_key=self.account_key,  # <-- Usar atributo de instancia
                        permission=BlobSasPermissions(read=True),
                        expiry=datetime.utcnow() + timedelta(hours=24)
                    )
                    blob_url = f"{blob_client.url}?{sas_token}"
                    images.append(blob_url)
                except Exception as e:
                    print(f"Error uploading file {file_name} to Azure Blob Storage: {e}")

            # Guardar archivos referenciados en anotaciones (opcional, igual que arriba si quieres)
            # ...existing code...

            # Obtener el texto de respuesta
            if getattr(msg, "text_messages", None):
                last_text = msg.text_messages[-1]
                response_text = last_text.text.value
                break
        print(f"Agent response: {response_text}, images: {images}, token usage: {token_usage}")
        return {
            "text": response_text,
            "images": images,
            "thread_id": self.thread.id,
            "agent_id": self.agent_id,
            "agent": "agent_interpreter",
            "token_usage": token_usage,
            "agent_tools": agent_tools
        }

    def close(self):
        # Elimina el archivo solo si existe y limpia las variables de clase
        if InterpreterAgent._file:
            self.agents_client.files.delete(InterpreterAgent._file.id)
            print("Deleted file")
            InterpreterAgent._file = None
        # No eliminar el agente, solo limpiar thread
        if InterpreterAgent._thread:
            InterpreterAgent._thread = None
