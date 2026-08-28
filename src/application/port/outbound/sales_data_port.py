"""Output Port (Driven Port) for Sales Data persistence/retrieval."""
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from src.domain.model.sale_record import SaleRecord


class SalesDataPort(ABC):
    """Abstract interface defining required data access operations for sales analytics."""

    @abstractmethod
    def get_all_sales(self) -> Sequence[SaleRecord]:
        """Retrieves all sales records from persistence."""
        raise NotImplementedError

    @abstractmethod
    def get_sales_by_filter(
        self,
        product_id: Optional[str] = None,
        local: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Sequence[SaleRecord]:
        """Retrieves sales records matching specified filters."""
        raise NotImplementedError

    @abstractmethod
    def execute_read_only_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a validated read-only SQL query against the analytical engine."""
        raise NotImplementedError
