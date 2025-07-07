Multi-Agent Bot with FastMCP and Kubernetes (KinD)
This project demonstrates a sophisticated multi-agent AI bot system designed for extensibility and scalable deployment. It leverages LangChain for agentic capabilities, FastMCP (Model Context Protocol) for modular tool integration, and is deployed on a local Kubernetes cluster using KinD (Kubernetes in Docker).

The bot is capable of integrating with various platforms (e.g., Discord, Telegram) and utilizing a diverse set of tools (e.g., web search, finance, RAG) provided by independent MCP servers.

✨ Features
Modular Architecture: Separates core bot logic, tool definitions (MCPs), and platform integrations.

Multi-Agent Capabilities: Powered by LangChain and Groq LLMs for intelligent reasoning and tool selection.

FastMCP Integration: Dynamically discovers and utilizes tools from various specialized MCP servers.

Platform Integrations:

Discord: Communicates via WebSocket for real-time messaging.

Telegram: Communicates via Webhook for message updates.

Specialized Tool Modules (MCPs):

Web MCP: For web search and information retrieval.

Finance MCP: For financial data queries.

RAG MCP: For Retrieval Augmented Generation, querying a custom document knowledge base (ChromaDB).

Containerized Deployment: All components are Dockerized for portability and consistency.

Local Kubernetes Deployment (KinD): Enables a production-like deployment environment on your local machine for development and testing.

Persistent Storage: RAG data (ChromaDB and embedding models) is stored on a Kubernetes Persistent Volume.

Automated Scripts: Bash scripts for building Docker images and deploying to KinD.

🏛️ Architecture Overview
The system is composed of several independent services that communicate via internal Kubernetes networking and the FastMCP protocol:

bot-api (Main Bot Application):

The core intelligence of the bot.

Uses LangChain to manage the AI agent (Iris).

Connects to the fastmcp-core-svc to discover and invoke tools.

Receives user messages from platform-specific MCPs (e.g., discord-mcp, telegram-mcp) and sends replies back through them.

fastmcp-core-server (Central MCP Registry):

A dedicated FastMCP server that acts as a central registry.

All other specialized MCPs register their tools with this server.

The bot-api queries this server to get a consolidated list of all available tools.

Specialized MCP Servers (web-mcp, finance-mcp, rag-mcp, telegram-mcp, discord-mcp):

Each is an independent FastAPI application running its own FastMCP instance.

They expose specific tools (e.g., query_docs, send_message, get_stock_price).

They register their tools with the fastmcp-core-server.

discord-mcp and telegram-mcp also handle the direct communication with their respective platforms (Discord WebSocket, Telegram Webhook) and forward messages to the bot-api.

ChromaDB (within RAG MCP):

A vector database used by the rag-mcp to store and retrieve document embeddings.

Its data and embedding models are stored on a Kubernetes Persistent Volume Claim (PVC) for persistence.

Kubernetes (KinD):

Provides the container orchestration layer, managing deployments, services, and networking for all components.

KinD runs a Kubernetes cluster inside Docker containers on your local machine.

graph TD
    User -->|Discord/Telegram| Platform_MCPs
    Platform_MCPs -->|Forward Message| Bot_API
    Bot_API -->|Discover/Invoke Tools| FastMCP_Core
    FastMCP_Core -->|Tool Calls| Specialized_MCPs
    Specialized_MCPs -->|External APIs (News, Finance, Web)| External_Services
    Specialized_MCPs -->|ChromaDB Data| Persistent_Volume
    Bot_API -->|Send Reply| Platform_MCPs
    Platform_MCPs -->|Reply| User

    subgraph Kubernetes Cluster (KinD)
        subgraph Pods
            Bot_API[Bot API Pod]
            FastMCP_Core[FastMCP Core Pod]
            Web_MCP[Web MCP Pod]
            Finance_MCP[Finance MCP Pod]
            RAG_MCP[RAG MCP Pod]
            Telegram_MCP[Telegram MCP Pod]
            Discord_MCP[Discord MCP Pod]
            RAG_DataLoader[RAG Data Loader Job Pod]
        end

        subgraph Services
            Bot_API_SVC(Bot API Service)
            FastMCP_Core_SVC(FastMCP Core Service)
            Web_MCP_SVC(Web MCP Service)
            Finance_MCP_SVC(Finance MCP Service)
            RAG_MCP_SVC(RAG MCP Service)
            Telegram_MCP_SVC(Telegram MCP Service)
            Discord_MCP_SVC(Discord MCP Service)
        end

        Bot_API --calls--> FastMCP_Core_SVC
        FastMCP_Core_SVC --routes--> FastMCP_Core
        FastMCP_Core --registers/proxies--> Web_MCP_SVC
        FastMCP_Core --registers/proxies--> Finance_MCP_SVC
        FastMCP_Core --registers/proxies--> RAG_MCP_SVC
        FastMCP_Core --registers/proxies--> Telegram_MCP_SVC
        FastMCP_Core --registers/proxies--> Discord_MCP_SVC

        Web_MCP_SVC --> Web_MCP
        Finance_MCP_SVC --> Finance_MCP
        RAG_MCP_SVC --> RAG_MCP
        Telegram_MCP_SVC --> Telegram_MCP
        Discord_MCP_SVC --> Discord_MCP

        Discord_MCP -->|WebSocket| Discord_API[Discord API]
        Telegram_MCP -->|Webhook| Telegram_API[Telegram API]

        RAG_MCP <--> Persistent_Volume[Persistent Volume Claim (PVC)]
        RAG_DataLoader <--> Persistent_Volume

        Bot_API_SVC <--forwards messages--> Discord_MCP
        Bot_API_SVC <--forwards messages--> Telegram_MCP
    end

    style Platform_MCPs fill:#f9f,stroke:#333,stroke-width:2px
    style Bot_API fill:#bbf,stroke:#333,stroke-width:2px
    style FastMCP_Core fill:#ccf,stroke:#333,stroke-width:2px
    style Specialized_MCPs fill:#dfd,stroke:#333,stroke-width:2px
    style External_Services fill:#ddd,stroke:#333,stroke-width:2px
    style Persistent_Volume fill:#ffc,stroke:#333,stroke-width:2px
    style Kubernetes_Cluster_KinD fill:#f0f0f0,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5

🚀 Getting Started
Prerequisites
Ensure you have the following installed on your system:

Git: For cloning the repository.

Python 3.12+: For running the development environment and scripts.

Docker Desktop: Required for building Docker images and running KinD.

Download Docker Desktop

Ensure Docker is running and has sufficient resources allocated (e.g., 4-8 GB RAM, 2-4 CPUs).

KinD (Kubernetes in Docker): For creating a local Kubernetes cluster.

KinD Installation Guide

kubectl: The Kubernetes command-line tool.

kubectl Installation Guide

ngrok (Optional, for Telegram Webhook testing):

ngrok Download

ngrok Setup Guide (You'll need to create an account and authenticate your authtoken).

⚙️ Setup & Deployment
Follow these steps to get your multi-agent bot running on KinD:

1. Clone the Repository
git clone https://github.com/your-username/multi-agent-bot.git # Replace with your repo URL
cd multi-agent-bot

2. Environment Variables
Create a .env file in the root of your project based on .env.example. This file will contain sensitive API keys and tokens.

cp .env.example .env

Edit the .env file and fill in your actual values:

# .env (Example content - fill with your actual keys/tokens)

# Groq API Key (for LLM)
GROQ_API_KEY="YOUR_GROQ_API_KEY"

# Telegram Bot API
TELEGRAM_API_ID="YOUR_TELEGRAM_API_ID"
TELEGRAM_API_HASH="YOUR_TELEGRAM_API_HASH"
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"

# Discord Bot API
DISCORD_BOT_TOKEN="YOUR_DISCORD_BOT_TOKEN"

# Optional: Other API keys for specific MCPs (e.g., Web, Finance)
# SERPAPI_API_KEY="YOUR_SERPAPI_API_KEY"
# NEWSAPI_ORG_API_KEY="YOUR_NEWSAPI_ORG_API_KEY"

Important: These values will be used by your Kubernetes secrets.yaml and configmaps.yaml. For local KinD, we'll manually copy them into the K8s manifests. Do NOT commit your actual .env file to version control.

3. Prepare Python Dependencies
Ensure your requirements.txt files are correctly set up:

multi-agent-bot/requirements.txt (Root): Contains common, core dependencies for all services (e.g., fastapi, uvicorn, httpx, fastmcp, langchain, python-dotenv).

multi-agent-bot/bot/requirements.txt: Contains dependencies specific to the main bot application (if any, often empty).

multi-agent-bot/mcp-servers/<mcp-name>/requirements.txt: Each specialized MCP (e.g., telegram-mcp, discord-mcp, rag-mcp) has its own requirements.txt for unique dependencies (e.g., telethon, discord.py, sentence-transformers).

multi-agent-bot/scripts/rag_data_loader_requirements.txt: Specific dependencies for the RAG data loading job.

4. Place RAG Documents (Optional)
If you plan to use the RAG functionality, place your source documents (e.g., .txt, .pdf files) in the data/ directory at the project root. These will be copied into the rag-data-loader image.

multi-agent-bot/
├── data/
│   ├── doc1.txt
│   └── another_doc.pdf
└── ...

5. Build Docker Images
This step builds all necessary Docker images, including the base-mcp image which serves as the foundation for others.

chmod +x scripts/build_images.sh
./scripts/build_images.sh

Verify: After building, run docker images and confirm all images are present (e.g., base-mcp:latest, multi-agent-bot-api:latest, etc.) and their sizes are reasonable (not 10GB!).

6. Update Kubernetes Manifests with Your Secrets
Before deploying, you need to manually update your k8s/secrets.yaml and k8s/configmaps.yaml with the actual values from your .env file.

k8s/secrets.yaml: Fill in GROQ_API_KEY, TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN, DISCORD_BOT_TOKEN, and any other sensitive API keys for your MCPs.

k8s/configmaps.yaml: This should already contain the internal service URLs, but review it to ensure it's correct.

7. Deploy to KinD Cluster
This script will create the KinD cluster, load your Docker images into it, and apply all Kubernetes manifests. It also includes a cleanup step for existing clusters.

chmod +x scripts/deploy_kind.sh
./scripts/deploy_kind.sh

Verify Deployment:
After the script completes, run:

kubectl get pods -n multi-agent-bot
kubectl get svc -n multi-agent-bot

Expected: All pods should eventually show STATUS as Running and READY as 1/1. All services should be listed.

8. Load Initial RAG Data (If Applicable)
If your RAG ChromaDB starts empty, you need to run a Kubernetes Job to load your documents.

Wait for all pods (especially rag-mcp-deployment) to be Running.

Apply the RAG data loader job:

kubectl apply -f k8s/jobs/rag-data-loader-job.yaml

Monitor the job:

kubectl get jobs -n multi-agent-bot
# Wait for "COMPLETIONS   1/1"

To see logs of the job:

kubectl get pods -l app=rag-data-loader -n multi-agent-bot # Get the pod name
kubectl logs -f <rag-data-loader-pod-name> -n multi-agent-bot

Look for "RAG data loading process completed."

🧪 Usage & Testing
1. Check Component Logs
Monitor the logs of your deployments to ensure they are starting correctly and processing requests:

kubectl logs deployment/bot-api-deployment -n multi-agent-bot --tail 50
kubectl logs deployment/fastmcp-core-deployment -n multi-agent-bot --tail 50
kubectl logs deployment/discord-mcp-deployment -n multi-agent-bot --tail 50
kubectl logs deployment/telegram-mcp-deployment -n multi-agent-bot --tail 50
kubectl logs deployment/web-mcp-deployment -n multi-agent-bot --tail 50
kubectl logs deployment/finance-mcp-deployment -n multi-agent-bot --tail 50
kubectl logs deployment/rag-mcp-deployment -n multi-agent-bot --tail 50

2. Test Discord Integration
Your Discord bot should automatically connect via WebSocket.

Go to your Discord server/DM where the bot is invited.

Send a message to your bot (e.g., @YourBotName What is the current time? or Hi Iris).

Observe the bot's reply in Discord.

Check the logs of discord-mcp-deployment and bot-api-deployment for message flow.

3. Test Telegram Integration
Telegram uses webhooks, so you need to expose your bot-api-svc externally using kubectl port-forward and ngrok.

Start Port Forwarding (in a new terminal, keep it running):

kubectl port-forward svc/bot-api-svc 8000:8000 -n multi-agent-bot

This makes your bot's API available at http://localhost:8000 on your host.

Start ngrok (in another new terminal, keep it running):

ngrok http 8000

Copy the public HTTPS URL provided by ngrok (e.g., https://abcdef12345.ngrok.io).

Set Telegram Webhook:

chmod +x scripts/setup_webhooks.sh
# Edit scripts/setup_webhooks.sh and replace placeholders with your actual token and ngrok URL
./scripts/setup_webhooks.sh

You should receive a success response from Telegram's API.

Go to your Telegram bot.

Send a message to your bot.

Observe the bot's reply in Telegram.

Check the logs of bot-api-deployment and telegram-mcp-deployment for message flow.

4. Test Tool Functionality
Send queries to your bot via Discord or Telegram that exercise different MCPs:

General Query: Hi Iris, how are you? (Tests basic agent response).

Web Search: What is the capital of France? (If you have a web search tool).

Finance: What is the current stock price of AAPL? (If you have a finance tool).

RAG: What is Alita's performance on the GAIA benchmark? (If "Alita.txt" was loaded into your RAG).

Monitor bot-api-deployment logs to see which tools the agent chooses and their outputs.

🧹 Cleanup
When you are done, you can delete the KinD cluster to free up resources:

kind delete cluster --name multi-agent-bot-cluster

📁 Project Structure
multi-agent-bot/
├── .env.example             # Example environment variables file
├── .gitignore               # Git ignore rules
├── README.md                # This file
├── requirements.txt         # Root Python dependencies (common to all services)
├── scripts/                 # Automation scripts
│   ├── build_images.sh      # Builds all Docker images
│   ├── deploy_kind.sh       # Deploys to KinD cluster
│   └── setup_webhooks.sh    # Sets up Telegram webhook via ngrok
│   └── load_initial_rag_data.py # Script for loading RAG data into ChromaDB
│   └── rag_data_loader_requirements.txt # Dependencies for RAG data loader
├── common/                  # Common utilities and constants
│   ├── utils.py
│   └── constants.py
├── mcp-servers/             # Individual MCP server implementations
│   ├── base-mcp/
│   │   └── Dockerfile.base  # Base Dockerfile for all Python services
│   ├── web-mcp/
│   │   ├── server.py        # Web MCP server logic
│   │   └── Dockerfile       # Dockerfile for Web MCP
│   │   └── requirements.txt # Web MCP specific dependencies
│   ├── finance-mcp/
│   │   ├── server.py        # Finance MCP server logic
│   │   └── Dockerfile       # Dockerfile for Finance MCP
│   │   └── requirements.txt # Finance MCP specific dependencies
│   ├── rag-mcp/
│   │   ├── server.py        # RAG MCP server logic
│   │   └── Dockerfile       # Dockerfile for RAG MCP
│   │   └── requirements.txt # RAG MCP specific dependencies
│   ├── telegram-mcp/
│   │   ├── server.py        # Telegram MCP server logic
│   │   └── Dockerfile       # Dockerfile for Telegram MCP
│   │   └── requirements.txt # Telegram MCP specific dependencies
│   └── discord-mcp/
│       ├── server.py        # Discord MCP server logic
│       └── Dockerfile       # Dockerfile for Discord MCP
│       └── requirements.txt # Discord MCP specific dependencies
├── bot/                     # Main bot application
│   ├── agent_app.py         # LangChain agent definition
│   ├── bot_api.py           # FastAPI endpoint for bot interaction
│   ├── Dockerfile           # Dockerfile for bot-api
│   └── requirements.txt     # Bot-specific dependencies
├── k8s/                     # Kubernetes manifests for deployment
│   ├── kind-cluster.yaml    # KinD cluster configuration
│   ├── namespaces.yaml      # Namespace definition
│   ├── secrets.yaml         # Kubernetes Secrets for sensitive data
│   ├── configmaps.yaml      # Kubernetes ConfigMaps for non-sensitive config
│   ├── deployments/         # Deployment manifests for each service
│   │   ├── web-mcp-deploy.yaml
│   │   ├── finance-mcp-deploy.yaml
│   │   ├── rag-mcp-deploy.yaml
│   │   ├── telegram-mcp-deploy.yaml
│   │   ├── discord-mcp-deploy.yaml
│   │   └── bot-deploy.yaml
│   ├── services/            # Service manifests for internal networking
│   │   ├── web-mcp-svc.yaml
│   │   ├── finance-mcp-svc.yaml
│   │   ├── rag-mcp-svc.yaml
│   │   ├── telegram-mcp-svc.yaml
│   │   ├── discord-mcp-svc.yaml
│   │   └── bot-svc.yaml
│   ├── persistentvolumeclaims/ # PVCs for persistent storage
│   │   └── rag-pvc.yaml
│   ├── jobs/                # Kubernetes Jobs for one-off tasks
│   │   └── rag-data-loader-job.yaml
│   └── ingress/             # Ingress manifests for external access (optional)
│       └── bot-ingress.yaml
└── tests/                   # Unit and integration tests
    ├── conftest.py
    ├── test_mcp_servers.py
    └── test_bot_agent.py

🤝 Contributing
Contributions are welcome! Please follow standard Git practices: fork the repository, create a feature branch, and submit a pull request.

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.