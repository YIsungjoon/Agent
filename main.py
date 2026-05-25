import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()  # Load from Agent/.env

# Also load from Agent_tools/.env if it exists
agent_tools_env = Path("/home/leehm/linux_project/Agent_tools/.env")
if agent_tools_env.exists():
    load_dotenv(dotenv_path=agent_tools_env)

# Verify API keys
if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
    print("=" * 60)
    print("⚠️  Warning: GEMINI_API_KEY or GOOGLE_API_KEY is not set!")
    print("Please create a '.env' file or set the environment variable:")
    print("GEMINI_API_KEY=your_gemini_api_key_here")
    print("=" * 60)

try:
    from fractal_system.engine import fractal_graph
    from fractal_system.models import Workspace
except ImportError as e:
    print(f"Failed to import fractal engine: {e}")
    sys.exit(1)

def print_divider(char="─", length=60, color="\033[90m"):
    print(f"{color}{char * length}\033[0m")

def main():
    print("\033[1;35m" + "="*60)
    print("🧬  Fractal IRAC Multi-Agent Core Engine CLI  🧬")
    print("="*60 + "\033[0m")
    print("Type your complex reasoning question to trigger the Fractal system.")
    print("Type 'exit', 'quit', or 'q' to end the session.")
    print_divider()

    while True:
        try:
            user_input = input("\n👤 \033[1;32mYou:\033[0m ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q"]:
            print("Exiting. Goodbye!")
            break

        print("\n\033[1;33m🧠 Starting Fractal IRAC Engine... (Decomposing and running multi-agents)\033[0m")
        print_divider("┄")

        # Track printed log count to show only new updates in real-time
        printed_logs = 0
        final_workspace = None

        try:
            # We initialize the workspace state
            initial_state = {
                "workspace": {
                    "question": user_input,
                    "run_id": "",
                    "nodes": [],
                    "edges": [],
                    "shared_entries": [],
                    "status": "open"
                }
            }

            # Stream LangGraph state updates
            for event in fractal_graph.stream(initial_state, stream_mode="updates"):
                for node_name, state_update in event.items():
                    # Display node transition indicator
                    print(f"\n\033[1;34m▶ [Entering LangGraph Node: {node_name}]\033[0m")
                    # Check if there are new logs to print
                    step_logs = state_update.get("step_logs", [])
                    if step_logs and len(step_logs) > printed_logs:
                        for i in range(printed_logs, len(step_logs)):
                            log_line = step_logs[i]
                            # Style certain emojis or headers
                            if "🏁" in log_line or "👑" in log_line:
                                print(f"\033[1;36m{log_line}\033[0m")
                            elif "📋" in log_line:
                                print(f"\033[1;35m{log_line}\033[0m")
                            elif "🤖" in log_line:
                                print(f"\033[93m{log_line}\033[0m")
                            elif "🛠️" in log_line or "📦" in log_line:
                                print(f"\033[1;33m{log_line}\033[0m")
                            elif "🔬" in log_line:
                                print(f"\033[1;34m{log_line}\033[0m")
                            elif "❌" in log_line:
                                print(f"\033[1;31m{log_line}\033[0m")
                            else:
                                print(log_line)
                        printed_logs = len(step_logs)
                    
                    # Track latest workspace object
                    if "workspace" in state_update:
                        final_workspace = state_update["workspace"]

            print_divider("┄")
            
            # Print final results
            if final_workspace:
                print("\n📄 \033[1;32m[Final Answer Synthesis Report]\033[0m")
                print_divider("━", color="\033[32m")
                print(final_workspace.answer_draft)
                print_divider("━", color="\033[32m")
                
                print(f"\n📂 Files saved successfully to WSL disk:")
                print(f"  - JSON Workspace: \033[1mruntime/runs/{final_workspace.run_id}.json\033[0m")
                print(f"  - Markdown Report: \033[1mruntime/runs/{final_workspace.run_id}.md\033[0m")
            else:
                print("\n⚠️ Failed to retrieve finalized workspace.")
                
            print_divider()

        except Exception as e:
            print(f"\n❌ Error during graph execution: {e}")
            import traceback
            traceback.print_exc()
            print_divider()

if __name__ == "__main__":
    main()
