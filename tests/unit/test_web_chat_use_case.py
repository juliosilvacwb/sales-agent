"""Unit tests for WebChatUseCase abstract port contract."""
import pytest
from src.application.port.inbound.web_chat_use_case import WebChatUseCase


def test_web_chat_use_case_abstract_contract():
    """Verify WebChatUseCase is an abstract class and cannot be instantiated directly."""
    # Attempting to instantiate the abstract class directly
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        WebChatUseCase()  # type: ignore[abstract]

    # Attempting to instantiate an incomplete subclass
    class IncompleteUseCase(WebChatUseCase):
        pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteUseCase()  # type: ignore[abstract]
