from agent_ai_search import AISearchAgent

if __name__ == "__main__":
    agent = AISearchAgent()
    query = "¿Cuál es la capital de Francia?"
    respuesta = agent.send(query)
    print("Respuesta del agente:", respuesta)