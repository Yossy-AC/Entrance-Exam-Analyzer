from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    excel_2026: str = ""
    excel_2025: str = ""
    excel_2024: str = ""

    def get_year_paths(self) -> dict[int, Path]:
        result = {}
        for year in [2026, 2025, 2024]:
            path_str = getattr(self, f"excel_{year}", "")
            if path_str:
                p = Path(path_str)
                if p.exists():
                    result[year] = p
        return result


settings = Settings()
