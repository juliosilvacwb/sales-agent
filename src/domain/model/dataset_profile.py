"""Domain models and value objects for dataset profiling and dynamic insights."""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def _sanitize_metadata_value(val: Any, max_len: int = 64) -> str:
    """Sanitizes metadata values against indirect prompt injection (CRLF, markdown headers, excessive length)."""
    if val is None:
        return ""
    text = str(val)
    # Strip CRLF and control characters, replacing with single space
    text = re.sub(r"[\r\n\t]+", " ", text).strip()
    # Strip markdown header hashes to avoid layout hijacking
    text = re.sub(r"#+", "", text).strip()
    # Limit length to prevent buffer/token bloating
    if len(text) > max_len:
        text = text[:max_len].rstrip()
    return text


def _sanitize_column_name(col: Any, max_len: int = 64) -> str:
    """Sanitizes column name identifiers."""
    cleaned = re.sub(r"[^\w\.-]", "_", str(col).strip())
    return cleaned[:max_len]


@dataclass(frozen=True)
class DataInsights:
    """Encapsulates empirical data insights such as sentinel nulls and constant columns."""
    null_representations: Dict[str, Any] = field(default_factory=dict)
    constant_columns: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DatasetProfile:
    """Empirical metadata profile of the sales dataset discovered at startup."""
    total_records: int = 0
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    distinct_products: int = 0
    distinct_locations: int = 0
    null_representations: Dict[str, Any] = field(default_factory=dict)
    constant_columns: Dict[str, Any] = field(default_factory=dict)

    def to_markdown_block(self) -> str:
        """Formats the empirical profile into a concise dynamic markdown insight block for LLM prompt injection."""
        if self.total_records == 0:
            return ""

        lines = ["### DYNAMIC DATA INSIGHTS:"]
        lines.append(f"- Total de registros no dataset: {self.total_records:,}")
        if self.min_date and self.max_date:
            clean_min_date = _sanitize_metadata_value(self.min_date, 32)
            clean_max_date = _sanitize_metadata_value(self.max_date, 32)
            lines.append(f"- Período temporal coberto: {clean_min_date} até {clean_max_date}.")
        if self.distinct_products > 0:
            lines.append(f"- Produtos distintos catalogados: {self.distinct_products}.")
        if self.distinct_locations > 0:
            lines.append(f"- Localidades/Armazéns distintos: {self.distinct_locations}.")

        if self.null_representations:
            for raw_col, sentinels in sorted(self.null_representations.items()):
                col = _sanitize_column_name(raw_col)
                if isinstance(sentinels, (list, tuple, set)):
                    sanitized_items = [_sanitize_metadata_value(s) for s in sentinels]
                    sent_str = ", ".join([f"'{s}'" for s in sanitized_items if s])
                else:
                    sanitized_val = _sanitize_metadata_value(sentinels)
                    sent_str = f"'{sanitized_val}'"
                if sent_str and sent_str != "''":
                    lines.append(
                        f"- '{col}': Vendas não promocionais/valores nulos utilizam a string {sent_str} (e não SQL NULL). "
                        f"Utilize WHERE {col} = {sent_str} para consultas sobre dados sem promoção/nulos."
                    )

        if self.constant_columns:
            for raw_col, raw_val in sorted(self.constant_columns.items()):
                col = _sanitize_column_name(raw_col)
                val = _sanitize_metadata_value(raw_val)
                if val:
                    lines.append(f"- '{col}': Coluna constante com valor fixo {val} em todos os registros.")

        return "\n".join(lines)

