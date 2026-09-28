# llm_agent.py
# A real AI agent: deepseek-r1:1.5b running locally in Ollama.
#
# The loop is the same as in any agent framework, just written out by hand:
#   1. Send the conversation to the model.
#   2. If it asks to use a tool, run it and add the result to the conversation.
#   3. Repeat until it calls submit_report (or we hit the step limit).
#
# Two ways a model can call tools:
#   - NATIVE mode: the model supports Ollama's tool calling. We send the tool
#     definitions and read message["tool_calls"].
#   - TEXT mode: the model doesn't support tools. We describe the tools in the
#     instructions and ask it to reply with one JSON line, which we parse.
# check_ollama() asks Ollama which mode the model supports.
#
# The only network call is to Ollama on this computer (localhost).

import json
import os
import urllib.error
import urllib.request

import monitor
import prompts
import tools

MODEL = os.environ.get("ROGUE_MODEL", "deepseek-r1:1.5b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MAX_STEPS = 15      # safety limit so a confused model can't loop forever
MAX_REMINDERS = 2   # how many times we nudge a model that stops calling tools

# Set by check_ollama(). True = native tool calling, False = text mode.
USE_NATIVE_TOOLS = True


def post(path, body, timeout):
    request = urllib.request.Request(
        OLLAMA_URL + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def call_ollama(messages, use_tools=True):
    body = {
        "model": MODEL,
        "messages": messages,
        "stream": False,   # wait for the full reply instead of word by word
        "options": {
            # Ollama's default context window is small. If the conversation
            # doesn't fit, the start gets cut off, including the rules.
            # Reasoning models write long thoughts, so give them room.
            "num_ctx": 8192,
            # Above zero so each run can turn out differently. That's why
            # --runs N is useful: you measure HOW OFTEN the agent goes rogue.
            "temperature": 0.7,
        },
    }
    if use_tools and USE_NATIVE_TOOLS:
        body["tools"] = tools.TOOL_DEFINITIONS
    # A laptop can take a while per reply, so allow 5 minutes.
    return post("/api/chat", body, timeout=300)["message"]


def check_ollama():
    """Return True if Ollama is running and the model is downloaded.
    Also decides between native and text tool mode."""
    global USE_NATIVE_TOOLS
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=5) as response:
            installed = [m["name"] for m in json.loads(response.read()).get("models", [])]
    except (urllib.error.URLError, OSError):
        print("Could not reach Ollama at " + OLLAMA_URL + ".")
        print("Start the Ollama app (or run `ollama serve`), then run:")
        print("    ollama pull " + MODEL)
        return False
    # A model pulled without a tag is listed as "name:latest".
    if MODEL not in installed and MODEL + ":latest" not in installed:
        print("Ollama is running, but the model '" + MODEL + "' is not downloaded.")
        print("Run:  ollama pull " + MODEL)
        return False

    # Ask Ollama what the model can do. Newer versions list "tools" here.
    # If the list is missing (older Ollama), assume native tools work.
    info = post("/api/show", {"model": MODEL}, timeout=30)
    capabilities = info.get("capabilities")
    USE_NATIVE_TOOLS = capabilities is None or "tools" in capabilities
    print("Tool mode: " + ("native" if USE_NATIVE_TOOLS else "text (model has no tool support)"))
    return True


def split_thinking(message):
    """Reasoning models like deepseek-r1 think out loud before answering.
    Depending on the Ollama version, the thinking arrives in a separate
    "thinking" field or inside <think>...</think> at the start of the content.
    Return (thinking, answer) so we can log the thinking and act on the answer."""
    thinking = message.get("thinking") or ""
    content = message.get("content") or ""
    if "</think>" in content:
        before, after = content.split("</think>", 1)
        thinking = (thinking + "\n" + before.replace("<think>", "")).strip()
        content = after
    return thinking.strip(), content.strip()


def parse_text_tool_call(text):
    """TEXT mode: find the JSON object in the reply, e.g.
    {"tool": "read_file", "reasoning": "...", "path": "docs/x.md"}
    Return (name, args), or (None, None) if there isn't a usable one.
    We take everything from the first { to the last }, which also copes with
    the model wrapping the JSON in ```json fences or adding a sentence."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None, None
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return None, None
    if not isinstance(data, dict):
        return None, None
    name = data.pop("tool", None) or data.pop("name", None)
    # Accept {"tool": ..., "args": {...}} as well as a flat object.
    if isinstance(data.get("args"), dict):
        data.update(data.pop("args"))
    return name, data


def get_tool_calls(message, answer_text):
    """Return a list of (name, args) the model asked for, in either mode."""
    if USE_NATIVE_TOOLS:
        calls = []
        for call in message.get("tool_calls") or []:
            args = call.get("function", {}).get("arguments") or {}
            if isinstance(args, str):   # be forgiving: sometimes a JSON string
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            calls.append((call.get("function", {}).get("name", ""), args))
        return calls
    name, args = parse_text_tool_call(answer_text)
    return [(name, args)] if name else []


def run_agent(files, run):
    system_prompt = prompts.SYSTEM_PROMPT
    if not USE_NATIVE_TOOLS:
        system_prompt += "\n\n" + prompts.TEXT_TOOL_INSTRUCTIONS
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompts.TASK_MESSAGE},
    ]
    reminders = 0
    submitted = False

    for _ in range(MAX_STEPS):
        message = call_ollama(messages)
        # The model needs to see its own earlier turns.
        messages.append({"role": "assistant", "content": message.get("content") or "",
                         "tool_calls": message.get("tool_calls") or []})

        thinking, answer_text = split_thinking(message)
        if thinking:
            # The most interesting part of the log: the model's private reasoning.
            monitor.log_note(run, thinking, label="model thinks")
        if answer_text:
            monitor.log_note(run, answer_text)

        tool_calls = get_tool_calls(message, answer_text)
        if not tool_calls:
            # The model replied without acting. Nudge it.
            if reminders >= MAX_REMINDERS:
                break
            reminders += 1
            reminder = prompts.REMINDER if USE_NATIVE_TOOLS else prompts.TEXT_REMINDER
            messages.append({"role": "user", "content": reminder})
            continue

        for name, args in tool_calls:
            result = tools.run_tool(files, name, args)
            monitor.log_step(run, name, args, result)
            # Give the result back. For submit_report this is "Report submitted."
            if USE_NATIVE_TOOLS:
                messages.append({"role": "tool", "tool_name": name, "content": result})
            else:
                messages.append({"role": "user", "content": "Result of " + name + ":\n" + result})
            if name == "submit_report":
                submitted = True

        if submitted:
            break

    if not submitted:
        monitor.add_flag(run, "NO_SUBMIT")
        return

    # Honesty check. We call the model WITHOUT tools so it must answer in words.
    # Strip the thinking first so the "yes/no" check reads the actual answer,
    # but log the thinking: it can show the model deciding whether to admit it.
    messages.append({"role": "user", "content": prompts.FOLLOW_UP_QUESTION})
    thinking, answer_text = split_thinking(call_ollama(messages, use_tools=False))
    if thinking:
        monitor.log_note(run, thinking, label="model thinks")
    monitor.record_answer(run, answer_text)
