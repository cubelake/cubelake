from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IngestionConfig:
    batch_size: int = 10
    batch_delay_seconds: float = 4.0
    timeout_seconds: float = 15.0
    max_retries: int = 2
    retry_delay_seconds: float = 5.0
