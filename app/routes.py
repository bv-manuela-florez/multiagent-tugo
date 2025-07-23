from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from agents.rag_agent.agent_ai_search import AISearchAgent
from agents.interpreter_agent.agent_interpreter import InterpreterAgent
from agents.selector_agent.agent_selector import run_selector_agent
from utils.model_cosmos import ConversationChat, ConversationChatInput, ConversationChatResponse, User, TokenUsage
from datetime import datetime
import pytz
from fastapi import HTTPException
import json
from azure.storage.blob import BlobServiceClient
import os
from utils.keyvault import get_kv_variable
from utils.telemetry import tracer

router = APIRouter()
templates = Jinja2Templates(directory="templates")
user_agents = {}
kv = get_kv_variable()


def get_user_agents(user_id):
    if user_id not in user_agents:
        user_agents[user_id] = {
            "ai_search": AISearchAgent(),
            "interpreter": InterpreterAgent()
        }
    return user_agents[user_id]


def get_users_from_blob():
    account_url = f"https://{os.environ['AZURE_BLOB_ACCOUNT_NAME']}.blob.core.windows.net"
    container_name = os.environ.get("AZURE_BLOB_USERS_CONTAINER", "users")
    blob_name = "users.json"
    blob_service_client = BlobServiceClient(
        account_url=account_url,
        credential=kv.get_secret('AZURE-BLOB-ACCOUNT-KEY').value
    )
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    users_data = blob_client.download_blob().readall()
    return json.loads(users_data)


@router.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/login")


@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    users = get_users_from_blob()
    if not any(u["username"] == username and u["password"] == password for u in users):
        with tracer.span(name="login_failed"):
            print("Span enviado a App Insights: login_failed")
            pass
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Usuario o contraseña incorrectos"
            }
        )
    request.session['user'] = username
    with tracer.span(name="user_login"):
        print("Span enviado a App Insights: user_login")
        pass
    return RedirectResponse(url="/chat", status_code=303)


@router.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    if not request.session.get('user'):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("chat.html", {"request": request, "username": request.session['user']})


@router.post("/chat")
async def chat_api(request: Request):
    if not request.session.get('user'):
        with tracer.span(name="chat_unauthenticated"):
            print("Span enviado a App Insights: chat_unauthenticated")
            pass
        return JSONResponse({"respuesta": "Not authenticated."}, status_code=401)
    data = await request.json()
    user_query = data.get('pregunta')
    session_id = data.get('session_id')
    username = request.session['user']

    bogota_tz = pytz.timezone("America/Bogota")
    now_bogota = datetime.now(bogota_tz).isoformat()

    # Busca la última conversación de este usuario y sesión
    previous = ConversationChat.query(session_id=session_id, user_id=username)
    print(f"Previous conversations found: {len(previous)}")
    previous = sorted(previous, key=lambda x: x.datetime, reverse=True)
    previous_thread_id = None
    if previous:
        previous_thread_id = getattr(previous[0].response, "thread_id", None)

    conversation_status = "InProgress"
    updated_at = now_bogota
    if not previous:
        updated_at = now_bogota

    # Define thread_id_to_use antes de llamar a los agentes
    thread_id_to_use = previous_thread_id

    selected_agent_result = run_selector_agent(user_query)
    agents = get_user_agents(request.session['user'])
    result = None
    if selected_agent_result and "agent_interpreter" in (selected_agent_result.get("text") or "").lower():
        result = agents["interpreter"].send(user_query, thread_id=thread_id_to_use)
    elif selected_agent_result and "agent_ai_search" in (selected_agent_result.get("text") or "").lower():
        result = agents["ai_search"].send(user_query, thread_id=thread_id_to_use)
    else:
        result = selected_agent_result
        if isinstance(result, str):
            result = {
                "text": result,
                "images": [],
                "thread_id": selected_agent_result.get("thread_id"),
                "agent_id": selected_agent_result.get("agent_id"),
                "agent": "agent_selector"
            }
        if "images" not in result:
            result["images"] = []

    # Si no hay thread_id previo, usa el del resultado
    if not thread_id_to_use:
        thread_id_to_use = result.get("thread_id")

    # Siempre crea un nuevo documento para cada mensaje/interacción
    chat_obj = ConversationChat(
        conversation_status=conversation_status,
        session_id=session_id,
        user_id=username,
        datetime=now_bogota,
        updated_at=updated_at,
        token_usage=TokenUsage(
            total_tokens=result.get("token_usage", {}).get("total_tokens", 0),
            prompt_tokens=result.get("token_usage", {}).get("prompt_tokens", 0),
            completion_tokens=result.get("token_usage", {}).get("completion_tokens", 0),
        ),
        input=ConversationChatInput(
            session_id=session_id,
            user_id=User(user_id=username),
            message=user_query,
        ),
        response=ConversationChatResponse(
            thread_id=thread_id_to_use,
            agent=result.get("agent"),
            agent_id=result.get("agent_id"),
            agent_tools=result.get("agent_tools"),
            content=result["text"],
            images=result.get("images", [])
        )
    )
    chat_obj.save()
    with tracer.span(name="chat_message_sent"):
        print("Span enviado a App Insights: chat_message_sent")
        pass
    with tracer.span(name="chat_message_saved"):
        print("Span enviado a App Insights: chat_message_saved")
        pass
    return {"respuesta": result["text"], "imagenes": result.get("images", [])}


@router.get("/logout")
async def logout(request: Request):
    user_id = request.session.get('user')
    session_id = request.query_params.get('session_id') or None
    if session_id:
        try:
            conversations = ConversationChat.query(session_id=session_id)
            bogota_tz = pytz.timezone("America/Bogota")
            now_bogota = datetime.now(bogota_tz).isoformat()
            for conversation in conversations:
                conversation.conversation_status = "Completed"
                conversation.updated_at = now_bogota  # <-- Actualiza updated_at
                conversation.save()
            print(f"Conversations with session_id {session_id} marked as completed.")
        except Exception:
            pass
    if user_id and user_id in user_agents:
        agents = user_agents.pop(user_id)
        agents["ai_search"].close()
        agents["interpreter"].close()
    with tracer.span(name="user_logout"):
        print("Span enviado a App Insights: user_logout")
        pass
    request.session.clear()
    return RedirectResponse(url="/login")


@router.get("/conversations")
async def get_conversations(request: Request):
    user_id = request.session.get('user')
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Buscar todas las conversaciones por user_id, agrupadas por session_id
    conversations = ConversationChat.query(user_id=user_id)
    sessions = {}
    for c in conversations:
        if c.session_id not in sessions:
            sessions[c.session_id] = {
                "session_id": c.session_id,
                "last_message": c.input.message if hasattr(c, "input") else "",
                "datetime": c.datetime,
                "status": c.conversation_status
            }
        # Actualiza el último mensaje y fecha si es más reciente
        if c.datetime > sessions[c.session_id]["datetime"]:
            sessions[c.session_id]["last_message"] = c.input.message if hasattr(c, "input") else ""
            sessions[c.session_id]["datetime"] = c.datetime
            sessions[c.session_id]["status"] = c.conversation_status
    # Devuelve lista ordenada por fecha descendente
    return sorted(sessions.values(), key=lambda x: x["datetime"], reverse=True)


@router.get("/conversation/{session_id}")
async def get_conversation_messages(request: Request, session_id: str):
    user_id = request.session.get('user')
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    messages = ConversationChat.query(session_id=session_id, user_id=user_id)
    # Ordena por fecha ascendente
    messages = sorted(messages, key=lambda x: x.datetime)
    result = []
    for m in messages:
        result.append({
            "role": "user",
            "text": m.input.message if hasattr(m, "input") else "",
            "datetime": m.datetime
        })
        if hasattr(m, "response") and m.response and getattr(m.response, "content", None):
            # Aquí se revisa si hay imágenes en el atributo images de la respuesta
            result.append({
                "role": "bot",
                "text": m.response.content,
                "images": getattr(m.response, "images", []) or [],
                "datetime": m.datetime
            })
    return result
