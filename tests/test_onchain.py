"""Tests for batch-1 on-chain tools.

Covers `get_wallet_profile`, `get_tx`, `get_token_holders`. Mocks the
httpx transport via `pytest-httpx` — never hits a live upstream. For
each tool we assert:

  1. Happy path — validates URL shape + query args match the FastAPI
     route signatures in `blockchainacademics-api/app/api/v1/onchain.py`.
  2. Validation — malformed address / chain / bounds are rejected before
     the client ever dials out.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bca_mcp.client import BcaClient, set_client
from bca_mcp.tools.onchain import (
    GetTokenHoldersInput,
    GetTxInput,
    GetWalletProfileInput,
    run_get_token_holders,
    run_get_tx,
    run_get_wallet_profile,
)


# --- get_wallet_profile ----------------------------------------------------


@pytest.mark.asyncio
async def test_get_wallet_profile_hits_expected_path(httpx_mock) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/onchain/wallet"
            "?address=0x1234567890abcdef1234567890abcdef12345678&chain=ethereum"
        ),
        json={
            "data": {
                "address": "0x1234567890abcdef1234567890abcdef12345678",
                "chain": "ethereum",
                "balance": {"native": "1.5"},
                "tokens": [],
            }
        },
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_wallet_profile(
        {"address": "0x1234567890abcdef1234567890abcdef12345678"}
    )
    assert out.get("data", {}).get("chain") == "ethereum"


def test_get_wallet_profile_rejects_bad_address_and_chain() -> None:
    # non-alphanumeric address
    with pytest.raises(ValidationError):
        GetWalletProfileInput.model_validate({"address": "0xBAD-ADDRESS!"})
    # unknown chain enum
    with pytest.raises(ValidationError):
        GetWalletProfileInput.model_validate(
            {"address": "0xabc123", "chain": "cardano"}
        )


# --- get_tx ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_tx_defaults_to_ethereum_chain(httpx_mock) -> None:
    tx_hash = "0x" + ("a" * 64)
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/onchain/tx"
            f"?hash={tx_hash}&chain=ethereum"
        ),
        json={"data": {"hash": tx_hash, "status": "success"}},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_tx({"hash": tx_hash})
    assert out.get("data", {}).get("status") == "success"


def test_get_tx_rejects_invalid_hash_chars() -> None:
    with pytest.raises(ValidationError):
        GetTxInput.model_validate({"hash": "not a hash with spaces"})
    with pytest.raises(ValidationError):
        GetTxInput.model_validate({"hash": "0xabc", "chain": "tron"})


# --- get_token_holders -----------------------------------------------------


@pytest.mark.asyncio
async def test_get_token_holders_defaults_limit_and_chain(httpx_mock) -> None:
    contract = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    httpx_mock.add_response(
        url=(
            "https://api.blockchainacademics.com/v1/onchain/holders"
            f"?contract={contract}&chain=ethereum&limit=50"
        ),
        json={"data": [{"address": "0x" + "b" * 40, "balance": "1000"}]},
        status_code=200,
    )
    set_client(BcaClient(api_key="k"))
    out = await run_get_token_holders({"contract": contract})
    assert isinstance(out.get("data"), list)


def test_get_token_holders_requires_evm_contract_and_evm_chain() -> None:
    # Solana-shaped address / non-EVM contract rejected by the strict
    # 0x + 40-hex regex — mirror TS zod behaviour.
    with pytest.raises(ValidationError):
        GetTokenHoldersInput.model_validate(
            {"contract": "So11111111111111111111111111111111111111112"}
        )
    # limit over 200 rejected.
    with pytest.raises(ValidationError):
        GetTokenHoldersInput.model_validate(
            {"contract": "0x" + "a" * 40, "limit": 500}
        )
    # solana explicitly excluded from the EVM-only chain enum.
    with pytest.raises(ValidationError):
        GetTokenHoldersInput.model_validate(
            {"contract": "0x" + "a" * 40, "chain": "solana"}
        )
