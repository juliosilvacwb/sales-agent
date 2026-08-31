"""CLI Entrypoint for the Sales Data Analysis Agent."""
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

from src.adapter.inbound.llm.domain_tools import create_domain_tools
from src.adapter.inbound.llm.sales_agent import SalesAgent
from src.adapter.inbound.llm.sql_fallback_tool import create_sql_fallback_tool
from src.adapter.outbound.llm.llm_factory import LLMFactory
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.application.service.sales_metrics_service import SalesMetricsApplicationService

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configures application logging based on environment variables."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def bootstrap_agent(dataset_path: Optional[str] = None) -> SalesAgent:
    """Bootstraps the hexagonal architecture components and returns an active SalesAgent."""
    csv_path = dataset_path or os.getenv("DATASET_PATH", "dataset/sales.csv")
    
    # 1. Outbound persistence adapter (DuckDB)
    persistence_adapter = DuckDbSalesAdapter(dataset_path=csv_path)

    # 2. Application Core Service
    metrics_service = SalesMetricsApplicationService(sales_data_port=persistence_adapter)

    # 3. Inbound Domain and Fallback Tools
    domain_tools = create_domain_tools(metrics_service)
    sql_tool = create_sql_fallback_tool(metrics_service)
    all_tools = [*domain_tools, sql_tool]

    # 4. Outbound LLM Factory
    llm = LLMFactory.create_llm()

    # 5. Dynamic Dataset Profiling
    profile = persistence_adapter.profile_dataset()

    # 6. Agent Orchestrator with dynamic dataset insights
    return SalesAgent(llm=llm, tools=all_tools, dataset_profile=profile)


def main() -> None:
    """Interactive command-line chat loop."""
    load_dotenv()
    setup_logging()

    print("=" * 70)
    print(" 🚀 Sales Data Analysis Agent - Conversational Interface")
    print("=" * 70)
    print("Digite sua pergunta de negócio sobre o dataset de vendas.")
    print("Digite 'sair', 'exit' ou 'quit' para encerrar a sessão.\n")

    try:
        agent = bootstrap_agent()
    except Exception as e:
        print(f"\n❌ Erro ao inicializar o Agente: {e}")
        logger.error("Failed to bootstrap agent: %s", e, exc_info=True)
        return

    while True:
        try:
            user_input = input("\n👤 Usuário > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("sair", "exit", "quit", "q"):
                print("\n👋 Encerrando sessão. Até logo!")
                break

            print("\n🤖 Agente pensando...")
            response = agent.ask(user_input)
            print(f"\n🤖 Agente:\n{response}")

        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Sessão finalizada pelo usuário. Até logo!")
            break
        except Exception as e:
            print(f"\n⚠️ Ocorreu um erro ao processar sua pergunta: {e}")
            logger.error("Error processing user input: %s", e, exc_info=True)


if __name__ == "__main__":
    main()
