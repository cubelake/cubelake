import os

import duckdb
from pydantic import BaseModel, model_validator


def _extract_account_name(account_url: str) -> str:
    if "://" in account_url:
        return account_url.split("://")[1].split(".")[0]
    return account_url


class AzureToken(BaseModel):
    account_url: str
    sas_token: str

    @property
    def connection_string(self) -> str:
        account_name = _extract_account_name(self.account_url)
        return f"AccountName={account_name};SharedAccessSignature={self.sas_token}"

    def init_connection(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute("INSTALL azure; LOAD azure;")
        con.execute("SET azure_transport_option_type = 'curl';")
        con.execute("SET ca_cert_file = '/etc/ssl/certs/ca-certificates.crt';")
        con.execute(f"SET azure_storage_connection_string = '{self.connection_string}';")


class BronzeToken(AzureToken):
    @model_validator(mode="before")
    @classmethod
    def load_from_env(cls, values: dict) -> dict:
        if not values.get("account_url"):
            values["account_url"] = os.environ["ACCOUNT_URL"]
        if not values.get("sas_token"):
            values["sas_token"] = os.environ["BRONZE_SAS_TOKEN"]
        return values


class SilverToken(AzureToken):
    @model_validator(mode="before")
    @classmethod
    def load_from_env(cls, values: dict) -> dict:
        if not values.get("account_url"):
            values["account_url"] = os.environ["ACCOUNT_URL"]
        if not values.get("sas_token"):
            values["sas_token"] = os.environ["SILVER_SAS_TOKEN"]
        return values


class RssBronzeToken(AzureToken):
    @model_validator(mode="before")
    @classmethod
    def load_from_env(cls, values: dict) -> dict:
        if not values.get("account_url"):
            values["account_url"] = os.environ["ACCOUNT_URL"]
        if not values.get("sas_token"):
            values["sas_token"] = os.environ["BRONZE_RSS_SAS_TOKEN"]
        return values


class RssSilverToken(AzureToken):
    @model_validator(mode="before")
    @classmethod
    def load_from_env(cls, values: dict) -> dict:
        if not values.get("account_url"):
            values["account_url"] = os.environ["ACCOUNT_URL"]
        if not values.get("sas_token"):
            values["sas_token"] = os.environ["SILVER_RSS_SAS_TOKEN"]
        return values


class ItunesBronzeToken(AzureToken):
    @model_validator(mode="before")
    @classmethod
    def load_from_env(cls, values: dict) -> dict:
        if not values.get("account_url"):
            values["account_url"] = os.environ["ACCOUNT_URL"]
        if not values.get("sas_token"):
            values["sas_token"] = os.environ["BRONZE_ITUNES_SAS_TOKEN"]
        return values


class ItunesSilverToken(AzureToken):
    @model_validator(mode="before")
    @classmethod
    def load_from_env(cls, values: dict) -> dict:
        if not values.get("account_url"):
            values["account_url"] = os.environ["ACCOUNT_URL"]
        if not values.get("sas_token"):
            values["sas_token"] = os.environ["SILVER_ITUNES_SAS_TOKEN"]
        return values


class AdlsEnv(BaseModel):
    account_url: str
    bronze_sas_token: str
    silver_sas_token: str

    @model_validator(mode="before")
    @classmethod
    def load_from_env(cls, values: dict) -> dict:
        if not values.get("account_url"):
            values["account_url"] = os.environ["ACCOUNT_URL"]
        if not values.get("bronze_sas_token"):
            values["bronze_sas_token"] = os.environ["BRONZE_SAS_TOKEN"]
        if not values.get("silver_sas_token"):
            values["silver_sas_token"] = os.environ["SILVER_SAS_TOKEN"]
        return values

    def as_env(self) -> dict[str, str]:
        account_name = _extract_account_name(self.account_url)
        return {
            "ACCOUNT_URL": self.account_url,
            "ACCOUNT_NAME": account_name,
            "BRONZE_SAS_TOKEN": self.bronze_sas_token,
            "SILVER_SAS_TOKEN": self.silver_sas_token,
        }
