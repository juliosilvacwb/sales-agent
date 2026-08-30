"""Integration tests for distributed session scalability and multi-replica continuity (T004)."""
from unittest.mock import MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from src.application.dto.chat_dto import ChatRequestDTO
from src.application.service.web_chat_application_service import WebChatApplicationService
from src.adapter.outbound.redis.redis_session_adapter import RedisSessionAdapter


def test_distributed_multi_replica_session_continuity():
    """Verify that requests across simulated independent pod replicas maintain 100% context parity via Redis."""
    # Shared in-memory mock for Redis storage across pods
    redis_storage = {}

    mock_redis_client = MagicMock()
    mock_redis_client.set.side_effect = lambda k, v, ex=None: redis_storage.update({k: v})
    mock_redis_client.get.side_effect = lambda k: redis_storage.get(k)
    mock_redis_client.exists.side_effect = lambda k: 1 if k in redis_storage else 0
    mock_redis_client.delete.side_effect = lambda k: redis_storage.pop(k, None)

    # Shared Redis Adapter across pods
    shared_redis_store = RedisSessionAdapter(redis_client=mock_redis_client, ttl_seconds=86400)

    session_id = "cluster-user-session-999"

    # --- SIMULATE POD REPLICA A ---
    agent_a = MagicMock()
    agent_a.ask.return_value = "Top 3 produtos: P1, P2, P3."
    app_service_pod_a = WebChatApplicationService(
        agent_factory=lambda: agent_a,
        session_store=shared_redis_store,
    )

    req_turn_1 = ChatRequestDTO(message="Quais os produtos mais vendidos?", session_id=session_id)
    resp_turn_1 = app_service_pod_a.process_chat_message(req_turn_1)

    assert resp_turn_1.status == "success"
    assert resp_turn_1.response == "Top 3 produtos: P1, P2, P3."
    assert f"sales_agent:session:{session_id}" in redis_storage

    # --- SIMULATE POD REPLICA B (Completely separate compute node receiving turn 2) ---
    agent_b = MagicMock()
    agent_b.ask.return_value = "A receita somada de P1, P2 e P3 foi R$ 50.000,00."
    app_service_pod_b = WebChatApplicationService(
        agent_factory=lambda: agent_b,
        session_store=shared_redis_store,
    )

    req_turn_2 = ChatRequestDTO(message="E qual foi a receita somada deles?", session_id=session_id)
    resp_turn_2 = app_service_pod_b.process_chat_message(req_turn_2)

    assert resp_turn_2.status == "success"
    assert resp_turn_2.response == "A receita somada de P1, P2 e P3 foi R$ 50.000,00."

    # Verify Pod B received the full conversational history from Pod A via Redis
    history_passed_to_agent_b = agent_b.ask.call_args[1]["chat_history"]
    assert len(history_passed_to_agent_b) == 2
    assert isinstance(history_passed_to_agent_b[0], HumanMessage)
    assert history_passed_to_agent_b[0].content == "Quais os produtos mais vendidos?"
    assert isinstance(history_passed_to_agent_b[1], AIMessage)
    assert history_passed_to_agent_b[1].content == "Top 3 produtos: P1, P2, P3."

    # Verify final state in Redis contains all 4 messages
    final_history = shared_redis_store.get_history(session_id)
    assert len(final_history.messages) == 4
