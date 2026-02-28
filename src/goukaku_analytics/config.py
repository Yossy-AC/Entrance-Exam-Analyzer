from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import re

# プロジェクトルート（src/goukaku_analytics/config.py の 3 階層上）
_PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    excel_2026: str = ""
    excel_2025: str = ""
    excel_2024: str = ""

    def get_year_paths(self) -> dict[int, Path]:
        result = {}

        # .env 設定を最優先
        for year in [2026, 2025, 2024]:
            path_str = getattr(self, f"excel_{year}", "")
            if path_str:
                p = Path(path_str)
                if p.exists():
                    result[year] = p

        # プロジェクトルートの EntranceExam_Results_YYYY.xlsx を自動検出
        # .env で設定済みの年度は上書きしない
        for xlsx in sorted(_PROJECT_ROOT.glob("EntranceExam_Results_*.xlsx")):
            m = re.search(r"(\d{4})", xlsx.stem)
            if m:
                year = int(m.group(1))
                if year not in result:
                    result[year] = xlsx

        return result


settings = Settings()
