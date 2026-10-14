from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated
from langchain_ollama import ChatOllama

def main():
    llm = ChatOllama (model = "qwen2.5:7b", temperature=0)
    class State(TypedDict):
        messages: Annotated[list, add_messages]

    def chatbot(state: State):
        return {"messages": [llm.invoke(state["messages"])]}

    graph = StateGraph(State)
    graph.add_node("chatbot", chatbot)
    graph.add_edge(START, "chatbot")
    graph.add_edge("chatbot", END)
    app = graph.compile()

    result = app.invoke({"messages": [("user", "Say hi in five words.")]})
    print(result["messages"][-1].content)
    return

if __name__ == "__main__":
    main()