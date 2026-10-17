# AI-File-Sorter!
# File Sorter Agent 🤖📂

A **LangGraph** chatbot powered by a **local Qwen 2.5:7B** model (via
**ChatOllama**) that describes its ability to sort files in a chosen directory.
The agent is fully debuggable in **LangGraph Studio** and traced with
**LangSmith**.

---

## ✨ Features

| Feature | Detail |
|---|---|
| **General purpose** | Sorts files in a user-selected directory |
| **File types** | Text (`.txt`, `.docx`), Scripts (`.cpp`, `.c`, `.py`), Images (`.png`, `.jpeg`, `.bpm`) |
| **Rename option** | Renames by default; keeps names if a specific flag is added |
| **Rollback** | Supports rollback of previous changes |
| **Off-topic guard** | Replies with the exact fallback sentence for any unrelated question |
| **Local LLM** | Qwen 2.5:7B served by Ollama — no cloud inference cost |
| **Observability** | LangSmith tracing + LangGraph Studio visual debugging |

---

## 🚀 Quick Start

### Prerequisites

1. **Python ≥ 3.12**
2. **[uv](https://docs.astral.sh/uv/)** — fast Python package manager
3. **[Ollama](https://ollama.com/)** — running locally with the model pulled
4. **LangSmith API key** — free account at [smith.langchain.com](https://smith.langchain.com)

### Step 1 — Install uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Step 2 — Clone & install

```bash
git clone https://github.com/<your-username>/file-sorter-agent.git
cd file-sorter-agent
uv sync
```

### Step 3 — Pull the model

```bash
ollama pull qwen2.5:7b
```

Make sure the Ollama server is running (`ollama serve`).

### Step 4 — Configure environment

```bash
cp .env.example .env
# Edit .env and paste your LangSmith API key
```

### Step 5 — Launch LangGraph Studio

```bash
uv run langgraph dev
```

Open the URL printed in the terminal (usually `http://127.0.0.1:2024`) and
select the **file_sorter_agent** graph.

---

## 🧪 Example Interactions

| User says | Agent replies |
|---|---|
| *"What do you do?"* | *"I am an AI agent that can sort your files in the selected directory."* |
| *"What file types can you sort?"* | Lists the three categories. |
| *"Do you rename files?"* | *"By default I rename files in the directory. I can keep the names if you add the specific flag."* |
| *"Can you undo?"* | *"I can rollback previous changes. if you don't like it."* |
| *"What's the weather?"* | *"I can't answer on your question. However, you can give me the path to the directory and i will sort the files in it!"* |

---

## 🛠 Development

### Run locally (without Studio)

```python
from src.agent.graph import graph

result = graph.invoke({"messages": [("user", "What do you do?")]})
print(result["messages"][-1].content)
```

### Enable LangSmith tracing

Ensure the following variables are set in `.env`:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=file-sorter-agent
```

Every invocation will then appear in your LangSmith dashboard.

---

## 📄 License

MIT