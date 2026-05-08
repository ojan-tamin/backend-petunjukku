"""Interactive Flow Intra stage test with OpenRouter, without auth/register and without DB.

Run from project root:
    PYTHONPATH=. python scripts/test_flow_intra_openrouter_no_auth.py

Windows PowerShell:
    $env:PYTHONPATH="."
    python scripts/test_flow_intra_openrouter_no_auth.py

This script calls the real FlowIntraAIService, so it requires LLM_API_KEY or
OPENROUTER_API_KEY in .env and internet/DNS access to OpenRouter.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from app.ai.llm_client import LLMConfigurationError, LLMUpstreamError
from app.ai.stage_manager import missing_fields
from app.ai.workflow import initial_stage
from app.core.config import settings
from app.services.flow_intra_ai_service import FlowIntraAIError, FlowIntraAIService


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def print_help() -> None:
    print(
        """
Perintah terminal:
  /help      tampilkan bantuan
  /stage     tampilkan stage aktif
  /fields    tampilkan collected_fields
  /missing   tampilkan missing_fields
  /summary   generate ringkasan sementara
  /generate  generate dokumen intrakurikuler
  /reset     mulai ulang state dari stage_1
  /exit      keluar
"""
    )


def print_state(
    current_stage: str,
    collected_fields: dict[str, Any],
    missing: list[str],
) -> None:
    print("\n" + "-" * 72)
    print(f"CURRENT STAGE : {current_stage}")
    print(f"MISSING FIELD : {missing if missing else 'Tidak ada'}")
    print("-" * 72)


def main() -> int:
    print("=== Flow Intra OpenRouter interactive test: no auth, no register, no DB ===")
    print(f"Provider : {settings.llm_provider}")
    print(f"Model    : {settings.llm_model}")
    print(f"Base URL : {settings.llm_base_url}")
    print(f"API key  : {'SET' if settings.llm_api_key else 'MISSING'}")

    print_help()

    current_stage = initial_stage("intrakurikuler")
    collected_fields: dict[str, Any] = {}
    missing = missing_fields("intrakurikuler", current_stage, collected_fields)
    chat_history: list[dict[str, str]] = []
    service = FlowIntraAIService()
    turn_index = 1

    while True:
        try:
            print_state(current_stage, collected_fields, missing)
            user_message = input(f"TURN {turn_index} | Guru > ").strip()

            if not user_message:
                print("Input kosong. Masukkan pesan guru atau gunakan /exit untuk keluar.")
                continue

            command = user_message.lower()

            if command in {"/exit", "/quit"}:
                print("Keluar dari pengujian.")
                return 0

            if command == "/help":
                print_help()
                continue

            if command == "/stage":
                print(f"Stage aktif: {current_stage}")
                continue

            if command == "/fields":
                print("\nCOLLECTED FIELDS:")
                print(compact(collected_fields))
                continue

            if command == "/missing":
                print("\nMISSING FIELDS:")
                print(compact(missing))
                continue

            if command == "/reset":
                current_stage = initial_stage("intrakurikuler")
                collected_fields = {}
                missing = missing_fields("intrakurikuler", current_stage, collected_fields)
                chat_history = []
                turn_index = 1
                print("State berhasil di-reset ke stage_1.")
                continue

            if command == "/summary":
                print("\nSUMMARY TEST:")
                summary = service.generate_summary(
                    collected_fields=collected_fields,
                    missing_fields=missing,
                )
                print(summary)
                continue

            if command == "/generate":
                if current_stage != "stage_5":
                    print(
                        "Dokumen sebaiknya digenerate setelah masuk stage_5. "
                        "Jika masih ada field penting yang kosong, hasil dokumen bisa tidak lengkap."
                    )

                print("\nDOCUMENT GENERATION TEST:")
                document = service.generate_intrakurikuler_document(
                    collected_fields=collected_fields
                )
                print(compact({
                    "title": document.get("title"),
                    "content": document.get("content"),
                }))
                continue

            print("\nMengirim input ke FlowIntraAIService...")

            result = service.process_turn(
                user_message=user_message,
                current_stage=current_stage,
                collected_fields=collected_fields,
                missing_fields=missing,
                chat_history=chat_history,
            )

            chat_history.append({"role": "user", "content": user_message})
            chat_history.append({"role": "assistant", "content": result.assistant_message})

            current_stage = result.next_stage
            collected_fields = result.collected_fields
            missing = result.missing_fields

            print("\n" + "=" * 72)
            print(f"TURN {turn_index} RESULT")
            print(f"NEXT STAGE           : {result.next_stage}")
            print(f"COMPLETION SCORE     : {result.completion_score}")
            print(f"READY FOR SUMMARY    : {result.is_ready_for_summary}")
            print(f"READY FOR GENERATION : {result.is_ready_for_generation}")

            print("\nUPDATED FIELDS:")
            print(compact(result.updated_fields))

            print("\nMISSING FIELDS:")
            print(compact(result.missing_fields))

            print("\nASSISTANT MESSAGE:")
            print(result.assistant_message)

            turn_index += 1

        except KeyboardInterrupt:
            print("\nPengujian dihentikan.")
            return 0

        except LLMConfigurationError as exc:
            print(f"\nCONFIG ERROR: {exc}", file=sys.stderr)
            return 2

        except LLMUpstreamError as exc:
            print(f"\nOPENROUTER/NETWORK ERROR: {exc}", file=sys.stderr)
            print(
                "Cek koneksi internet/DNS, OpenRouter API key, model availability, "
                "dan sisa credits.",
                file=sys.stderr,
            )
            return 3

        except FlowIntraAIError as exc:
            print(f"\nFLOW INTRA ERROR: {exc}", file=sys.stderr)
            return 4


if __name__ == "__main__":
    raise SystemExit(main())