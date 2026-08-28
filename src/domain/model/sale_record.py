"""Domain entity for a single Sale Record."""
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class SaleRecord:
    """Represents a transaction/record in the sales analytical dataset.
    
    Zero framework dependencies - pure Python dataclass.
    """
    product_id: str
    local: str
    date: date
    planned_quantity: float
    actual_quantity: float
    planned_price: float
    actual_price: float
    service_level: float
    promotion_type: Optional[str] = None

    @property
    def planned_revenue(self) -> float:
        """Calculates expected revenue: planned_quantity * planned_price."""
        return float(self.planned_quantity * self.planned_price)

    @property
    def actual_revenue(self) -> float:
        """Calculates realized revenue: actual_quantity * actual_price."""
        return float(self.actual_quantity * self.actual_price)

    @property
    def quantity_difference(self) -> float:
        """Difference between actual and planned quantity (actual - planned)."""
        return float(self.actual_quantity - self.planned_quantity)

    @property
    def revenue_difference(self) -> float:
        """Difference between actual and planned revenue (actual - planned)."""
        return float(self.actual_revenue - self.planned_revenue)

    @property
    def is_promoted(self) -> bool:
        """Check if any valid promotion was applied."""
        if not self.promotion_type:
            return False
        cleaned = str(self.promotion_type).strip().lower()
        return cleaned not in ("", "none", "null", "nan", "0")

    @property
    def discount_rate(self) -> float:
        """Relative discount rate (planned_price - actual_price) / planned_price."""
        if self.planned_price <= 0:
            return 0.0
        return float((self.planned_price - self.actual_price) / self.planned_price)
