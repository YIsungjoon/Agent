import os
from pathlib import Path
from dotenv import load_dotenv

def load_environment():
    """Loads environment variables from Agent/.env and dynamically merges Agent_tools/.env if available."""
    # 1. Load from primary Agent/.env
    load_dotenv()
    
    # 2. Merging from Agent_tools/.env
    agent_tools_env = Path("/home/leehm/linux_project/Agent_tools/.env")
    if agent_tools_env.exists():
        load_dotenv(dotenv_path=agent_tools_env)
        
    # 3. Synchronize LAW_API_OC with LAW_GO_OC
    if "LAW_API_OC" in os.environ and "LAW_GO_OC" not in os.environ:
        os.environ["LAW_GO_OC"] = os.environ["LAW_API_OC"]
        
    # Check credentials status
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not gemini_key:
        print("=" * 60)
        print("⚠️  Warning: GEMINI_API_KEY or GOOGLE_API_KEY is not set!")
        print("Please create a '.env' file or set the environment variable:")
        print("GEMINI_API_KEY=your_gemini_api_key_here")
        print("=" * 60)
