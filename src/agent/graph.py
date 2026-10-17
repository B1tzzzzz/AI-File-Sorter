"""
File Sorter Agent — a LangGraph chatbot powered by Qwen 2.5:7B via ChatOllama.

The agent is a single-node StateGraph.  Its system prompt constrains it to
answer only questions about:
  1. Its general purpose (sorting files in a chosen directory).
  2. The specific file types it handles (.txt/.docx, .cpp/.c/.py, .png/.jpeg/.bmp).
  3. The rename flag behaviour (renames by default; keeps names if a flag is added).
  4. The rollback capability.

Anything else receives the exact fallback message required by the spec.
"""

import os
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv()                         # reads .env if present

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# ---------------------------------------------------------------------------
# System prompt – this is the *entire* behaviour spec of the agent.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are an AI agent that can sort files in the selected directory.

You MUST answer ONLY the questions described below.  For ANY other question
you MUST reply with exactly this sentence (no extra text):

"I can't answer on your question. However, you can give me the path to the directory and i will sort the files in it!"

--- Allowed topics and the ONLY facts you may state about them ---

1. GENERAL PURPOSE
   "I am an AI agent that can sort your files in the selected directory."

2. SPECIFICS OF YOUR PURPOSE

   2.1 What type of files it is sorting:
       "I can sort:
        - text files (.txt, .docx)
        - script files (.cpp, .c, .py)
        - images (.png, .jpeg, .bpm)"

   2.2 Rename option:
       "By default I rename files in the directory.
        I can keep the names if you add the specific flag."

   2.3 Rollback option:
       "I can rollback previous changes if you don't like them."

--- Rules ---
- If the user asks something that is not connected with the questions described
  above, answer with the fallback sentence shown above.
- Do NOT invent any additional features, file types, flags, or capabilities.
- Keep answers short and direct.
"""

class AgentState(TypedDict):
    """Conversation state – a simple list of messages."""
    messages: Annotated[list[BaseMessage], add_messages]

llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0,
)

def chatbot_node(state: AgentState) -> dict:
    """Prepend the system prompt and call the LLM."""
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


graph = StateGraph(AgentState)
graph.add_node("chatbot", chatbot_node)
graph.add_edge(START, "chatbot")
graph.add_edge("chatbot", END)

app = graph.compile()