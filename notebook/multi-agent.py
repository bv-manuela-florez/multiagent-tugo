import asyncio
from dotenv import load_dotenv

from agent_ai_search import AISearchAgent
from agent_interpreter import InterpreterAgent
from agent_selector import run_selector_agent

load_dotenv()

async def main():
    ai_search_agent = AISearchAgent()
    interpreter_agent = InterpreterAgent()

    try:
        while True:
            user_query = input("Ingrese su consulta (o escriba 'salir' para terminar): ")
            if user_query.strip().lower() == "salir":
                break

            selected_agent = run_selector_agent(user_query)
            print(f"\n[Selector Agent Response]: {selected_agent}")

            if selected_agent and "interpreter" in selected_agent.lower():
                interpreter_agent.send(user_query)
            elif selected_agent and "ai_search" in selected_agent.lower():
                ai_search_agent.send(user_query)
            else:
                print("No valid agent selected or selector agent did not understand the query.")
    finally:
        ai_search_agent.close()
        interpreter_agent.close()

if __name__ == "__main__":
    asyncio.run(main())
