import os
import json
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3

from agent import CONTRACT_ABI, CONTRACT_ADDRESS


def _load_env() -> None:
    """Load environment variables from .env / .env.txt next to this file."""
    script_dir = Path(__file__).resolve().parent

    # Load default environment (if any)
    load_dotenv(override=False)

    for filename in (".env", ".env.txt"):
        p = script_dir / filename
        if p.exists():
            load_dotenv(dotenv_path=p, override=False)


def _connect_web3() -> Web3:
    """Create a Web3 HTTP client for BSC Testnet."""
    rpc_url = os.getenv(
        "BSC_TESTNET_RPC",
        "https://data-seed-prebsc-1-s1.binance.org:8545/",
    )
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    return w3


def _load_latest_invoice_hash() -> str | None:
    """
    Try to load the most recent real-looking document hash from invoices_db.json.

    Returns a 64-char hex string if found, otherwise None.
    """
    db_path = Path(__file__).with_name("invoices_db.json")
    if not db_path.exists():
        return None

    try:
        with db_path.open("r", encoding="utf-8") as f:
            invoices = json.load(f)
    except Exception:
        return None

    # Iterate from the end (most recent) to find a 64-char hex hash
    for entry in reversed(invoices):
        h = entry.get("document_hash")
        if isinstance(h, str) and len(h) == 64:
            try:
                int(h, 16)
                return h
            except ValueError:
                continue
    return None


def main() -> None:
    print("=== Contract Connectivity Test ===")

    _load_env()

    w3 = _connect_web3()
    rpc_url = os.getenv(
        "BSC_TESTNET_RPC",
        "https://data-seed-prebsc-1-s1.binance.org:8545/",
    )
    print(f"RPC URL: {rpc_url}")

    if not w3.is_connected():
        print("[X] Failed to connect to BSC Testnet RPC")
        return

    print("[OK] Connected to BSC Testnet RPC")

    try:
        latest_block = w3.eth.block_number
        print(f"[OK] Latest block: {latest_block}")
    except Exception as e:
        print(f"[X] Could not fetch latest block: {e}")

    print(f"Contract address: {CONTRACT_ADDRESS}")

    # Wallet information (optional)
    private_key = os.getenv("WALLET_PRIVATE_KEY")
    if private_key:
        try:
            account = w3.eth.account.from_key(private_key)
            balance_wei = w3.eth.get_balance(account.address)
            balance = w3.from_wei(balance_wei, "ether")
            print(f"[OK] Wallet: {account.address}")
            print(f"[OK] Balance: {balance} tBNB")
        except Exception as e:
            print(f"[X] Failed to derive wallet / balance: {e}")
    else:
        print("[!] WALLET_PRIVATE_KEY not set (only read-only tests will run)")

    # Instantiate contract
    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI,
        )
        print("[OK] Contract instance created")
    except Exception as e:
        print(f"[X] Failed to create contract instance: {e}")
        return

    # Try verifying the latest known invoice hash (if any)
    doc_hash = _load_latest_invoice_hash()
    if not doc_hash:
        print("[!] No suitable 64-char hex document_hash found in invoices_db.json")
        print("    Skipping on-chain invoice verification test.")
        return

    print(f"[OK] Using document_hash from invoices_db.json: {doc_hash}")

    try:
        hash_bytes = bytes.fromhex(doc_hash)
    except ValueError as e:
        print(f"[X] document_hash is not valid hex: {e}")
        return

    # Call verifyInvoice (view)
    try:
        exists = contract.functions.verifyInvoice(hash_bytes).call()
        print(f"[OK] verifyInvoice(...) returned: {exists}")
    except Exception as e:
        print(f"[X] verifyInvoice call failed: {e}")
        return

    # If it exists, fetch full invoice metadata
    if exists:
        try:
            timestamp, registrar, metadata = contract.functions.getInvoice(
                hash_bytes
            ).call()
            print("[OK] getInvoice(...) result:")
            print(f"   timestamp: {timestamp}")
            print(f"   registrar: {registrar}")
            print(f"   metadata:  {metadata}")
        except Exception as e:
            print(f"[X] getInvoice call failed: {e}")
    else:
        print("[!] Invoice hash not found on-chain (verifyInvoice == False)")


if __name__ == "__main__":
    main()