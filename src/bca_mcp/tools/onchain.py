"""On-chain tools (category 3).

Wraps `/v1/onchain/*` — Etherscan V2, Helius, DefiLlama free tiers.
All query-string shape in backend (see
`blockchainacademics-api/app/api/v1/onchain.py`). Ports `src/tools/onchain.ts`
— `get_wallet_profile`, `get_tx`, `get_token_holders` (batch 1),
`get_defi_protocol` (batch 3).
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from bca_mcp.client import get_client
from bca_mcp.types import SLUG_REGEX, EvmChain, OnchainChain, ResponseEnvelope

# --- get_wallet_profile ----------------------------------------------------

GET_WALLET_PROFILE_TOOL_NAME = "get_wallet_profile"

GET_WALLET_PROFILE_TOOL_DESCRIPTION = (
    "Wallet summary: native balance (in wei and in the chain coin, for example "
    "ETH) and up to 25 token holdings. EVM holdings are the net of the newest "
    "1,000 token transfers with likely spam dropped (partial when older "
    "history exists); Solana holdings are current SPL balances. No address "
    "labels. Starter tier."
)


class GetWalletProfileInput(BaseModel):
    model_config = {"extra": "forbid"}

    address: str = Field(
        min_length=32,
        max_length=64,
        pattern=r"^(0x[a-fA-F0-9]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})$",
        description="Wallet address (EVM 0x plus 40 hex, or Solana base58).",
    )
    chain: OnchainChain = Field(
        default="ethereum",
        description=(
            "Chain slug: ethereum, solana, arbitrum, base, optimism, polygon, bsc."
        ),
    )


def get_wallet_profile_input_schema() -> dict[str, Any]:
    return GetWalletProfileInput.model_json_schema()


async def run_get_wallet_profile(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetWalletProfileInput.model_validate(args)
    return await get_client().request(
        "/v1/onchain/wallet",
        {"address": parsed.address, "chain": parsed.chain},
    )


# --- get_tx ----------------------------------------------------------------

GET_TX_TOOL_NAME = "get_tx"

GET_TX_TOOL_DESCRIPTION = (
    "Decode a transaction: sender, receiver, value, gas and fee, status, "
    "and the ERC-20 and ERC-721 transfer events (EVM via Etherscan; Solana "
    "parsed via Helius). An unknown hash is an error (HTTP 404). Starter "
    "tier."
)


class GetTxInput(BaseModel):
    model_config = {"extra": "forbid"}

    hash: str = Field(
        min_length=64,
        max_length=128,
        pattern=r"^(0x[a-fA-F0-9]{64}|[1-9A-HJ-NP-Za-km-z]{64,128})$",
        description="Transaction hash (EVM 0x plus 64 hex) or Solana signature.",
    )
    chain: OnchainChain = Field(
        default="ethereum",
        description=(
            "Chain slug: ethereum, solana, arbitrum, base, optimism, polygon, bsc."
        ),
    )


def get_tx_input_schema() -> dict[str, Any]:
    return GetTxInput.model_json_schema()


async def run_get_tx(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetTxInput.model_validate(args)
    return await get_client().request(
        "/v1/onchain/tx",
        {"hash": parsed.hash, "chain": parsed.chain},
    )


# --- get_token_holders -----------------------------------------------------

GET_TOKEN_HOLDERS_TOOL_NAME = "get_token_holders"

GET_TOKEN_HOLDERS_TOOL_DESCRIPTION = (
    "Top holders of an ERC-20 token with balance and share of supply, via "
    "Etherscan, for holder concentration and risk analysis. EVM chains only, "
    "Pro tier. Etherscan serves holder lists on its paid plan only, so this "
    "usually answers partial today (meta.diagnostic names the upstream error)."
)


class GetTokenHoldersInput(BaseModel):
    model_config = {"extra": "forbid"}

    contract: str = Field(
        min_length=42,
        max_length=42,
        pattern=r"^0x[a-fA-F0-9]{40}$",
        description="Token contract address (EVM).",
    )
    chain: EvmChain = Field(
        default="ethereum",
        description="EVM chain only.",
    )
    limit: int = Field(default=50, ge=1, le=200)


def get_token_holders_input_schema() -> dict[str, Any]:
    return GetTokenHoldersInput.model_json_schema()


async def run_get_token_holders(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetTokenHoldersInput.model_validate(args)
    return await get_client().request(
        "/v1/onchain/holders",
        {
            "contract": parsed.contract,
            "chain": parsed.chain,
            "limit": parsed.limit,
        },
    )


# --- get_defi_protocol -----------------------------------------------------

GET_DEFI_PROTOCOL_TOOL_NAME = "get_defi_protocol"

GET_DEFI_PROTOCOL_TOOL_DESCRIPTION = (
    "Compact DefiLlama snapshot of a DeFi protocol: TVL in total and per "
    "chain, 1d, 7d and 30d TVL change, market cap, category, audit links, "
    "raise and hack counts, and optional daily TVL history (history_days). "
    "Fees and revenue are in compare_protocols. A slug DefiLlama does not "
    "know is an error. Free tier."
)


class GetDefiProtocolInput(BaseModel):
    model_config = {"extra": "forbid"}

    protocol: str = Field(
        min_length=1,
        max_length=64,
        pattern=SLUG_REGEX,
        description="DefiLlama protocol slug (e.g. 'aave', 'uniswap').",
    )
    history_days: Optional[int] = Field(
        default=None,
        ge=0,
        le=90,
        description="Daily TVL points to include, newest last (0 to 90; default 0, no history).",
    )


def get_defi_protocol_input_schema() -> dict[str, Any]:
    return GetDefiProtocolInput.model_json_schema()


async def run_get_defi_protocol(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetDefiProtocolInput.model_validate(args)
    return await get_client().request(
        "/v1/onchain/defi",
        {"protocol": parsed.protocol, "history_days": parsed.history_days},
    )
