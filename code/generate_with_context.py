import os
import argparse
from dotenv import load_dotenv
from chromadb import PersistentClient
import openai
import json

# --- Load secrets ---
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY not found in .env file.")

# --- Persistent chat history ---
CHAT_HISTORY_FILE = "./testgen_chat_history.json"

def load_chat_history():
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_chat_history(history):
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# --- Embedding function ---
def get_embedding(text: str, model="text-embedding-3-small"):
    response = openai.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding

# --- Prompt templates ---
PROMPT_TEMPLATES = {
    "unit": """You are a professional software engineer.

Write both **positive and negative** unit tests for the following Python source code.

### Source code:
{source_code}

{context_block}

Use idiomatic Python (e.g. pytest or unittest). Include assertions and edge cases.
Return only the test code with necessary imports.
""",
    "api": """You are a professional backend QA engineer.

Given the API documentation and related context below, write automated tests **based on this prompt**:

▶️ {user_prompt}

### Related API docs and code:
{context_block}

Return only the test code. You can assume a standard test client like `requests` or a test framework.
""",
    "ui": """You are a frontend test automation engineer.

Write a **Playwright test** for the following user flow:

▶️ {user_prompt}

### Related frontend context (optional):
{context_block}

Return only the Playwright test code in Python. Include required imports.
"""
}

# --- Compose GPT prompt with context ---
def build_prompt(source_code, context_chunks, style, user_prompt=None):
    context_block = ""
    if context_chunks:
        context_block = "\n\n### Related context:\n" + "\n\n---\n\n".join(context_chunks)

    template = PROMPT_TEMPLATES.get(style, PROMPT_TEMPLATES["unit"])

    return template.format(
        source_code=source_code if source_code else "",
        context_block=context_block,
        user_prompt=user_prompt or ""
    )

# --- Ask OpenAI to generate tests ---
def generate_test_code(messages, model="gpt-4o"):
    response = openai.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2
    )
    return response.choices[0].message.content.strip()

# --- Main ---
parser = argparse.ArgumentParser(description="Generate test code using OpenAI + Chroma vector DB as context.")
parser.add_argument("--file", type=str, help="Path to source code file (used for unit tests only)")
parser.add_argument("--style", type=str, choices=["unit", "api", "ui"], default="unit", help="Type of test to generate")
parser.add_argument("--db", type=str, default="code_docs", help="Chroma collection name")
parser.add_argument("--top_k", type=int, default=4, help="Number of context chunks to retrieve")
parser.add_argument("--model", type=str, default="gpt-4o", help="OpenAI model to use (default: gpt-4o)")
parser.add_argument("--output", type=str, help="Optional file path to save generated test")

args = parser.parse_args()

# --- Handle file input or prompt depending on test type ---
source_code = ""
if args.style == "unit":
    if not args.file:
        raise ValueError("--file is required for unit tests")
    if not os.path.exists(args.file):
        raise FileNotFoundError(f"{args.file} not found")
    with open(args.file, "r", encoding="utf-8") as f:
        source_code = f.read()
    if not source_code.strip():
        raise ValueError("Source file is empty")

user_prompt = None
if args.style in ("api", "ui"):
    print(f"💬 Please describe what to test for the {args.style} test:")
    user_prompt = input("▶️  ")

# --- Retrieve context from Chroma ---
query_input = source_code if args.style == "unit" else user_prompt
query_embedding = get_embedding(query_input)

client = PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name=args.db)

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=args.top_k,
)
context_chunks = results["documents"][0]

# --- Load chat history ---
chat_history = load_chat_history()

# Add the new request to the conversation
initial_prompt = build_prompt(source_code, context_chunks, args.style, user_prompt)
chat_history.append({"role": "user", "content": initial_prompt})

# --- Interactive loop for generation and refinement ---
while True:
    generated_code = generate_test_code(chat_history, args.model)

    print("\n📄 Generated Code:\n")
    print(generated_code)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(generated_code)
        print(f"\n✅ Saved to {args.output}")

    print("\nOptions:")
    print("[1] Accept and exit")
    print("[2] Revise prompt and regenerate")
    print("[3] Add correction to the code and regenerate")
    choice = input("Select: ").strip()

    if choice == "1":
        break
    elif choice == "2":
        print("\n✏️ Enter revised request:")
        revised = input("▶️  ")
        chat_history.append({"role": "user", "content": revised})
    elif choice == "3":
        print("\n🔧 Describe correction to apply:")
        correction = input("▶️  ")
        chat_history.append({"role": "user", "content": f"Please apply this correction: {correction}"})
    else:
        print("Invalid choice. Please select 1, 2, or 3.")
        continue

save_chat_history(chat_history)
