"""On-chain tools (category 3).

Wraps `/v1/onchain/*` — Etherscan V2, Helius, DefiLlama free tiers.
All query-string shape in backend (see
`blockchainacademics-api/app/api/v1/onchain.py`). Ports `src/tools/onchain.ts`
— `get_wallet_profile`, `get_tx`, `get_token_holders` (batch 1),
`get_defi_protocol` (batch 3).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from bca_mcp.client import get_client
from bca_mcp.types import SLUG_REGEX, EvmChain, OnchainChain, ResponseEnvelope

# --- get_wallet_profile ----------------------------------------------------

GET_WALLET_PROFILE_TOOL_NAME = "get_wallet_profile"

GET_WALLET_PROFILE_TOOL_DESCRIPTION = (
    "Wallet summary: native balance, ERC-20/SPL token list, labels. "
    "Starter tier. Use for wallet research and clustering."
)


class GetWalletProfileInput(BaseModel):
    model_config = {"extra": "forbid"}

    address: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9]+$",
        description="Wallet address (EVM 0x… or Solana base58).",
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
    "Decode a transaction: sender, receiver, value, decoded events, status. "
    "Starter tier."
)


class GetTxInput(BaseModel):
    model_config = {"extra": "forbid"}

    hash: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9]+$",
        description="Transaction hash.",
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
    "Top token holders with balance and %-supply. EVM-only, Pro tier. Use "
    "for concentration/risk analysis."
)


class GetTokenHoldersInput(BaseModel):
    model_config = {"extra": "forbid"}

    contract: str = Field(
        min_length=1,
        max_length=128,
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
    "DeFi protocol snapshot: TVL, chains, volume, fees. Via DefiLlama. "
    "Free tier."
)


class GetDefiProtocolInput(BaseModel):
    model_config = {"extra": "forbid"}

    protocol: str = Field(
        min_length=1,
        max_length=240,
        pattern=SLUG_REGEX,
        description="DefiLlama protocol slug (e.g. 'aave', 'uniswap').",
    )


def get_defi_protocol_input_schema() -> dict[str, Any]:
    return GetDefiProtocolInput.model_json_schema()


async def run_get_defi_protocol(args: dict[str, Any]) -> ResponseEnvelope[Any]:
    parsed = GetDefiProtocolInput.model_validate(args)
    return await get_client().request(
        "/v1/onchain/defi",
        {"protocol": parsed.protocol},
    )
