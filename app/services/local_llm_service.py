"""Service layer for local LLM inspection and inference."""

from __future__ import annotations

import ctypes
import importlib.util
import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelInspection:
    model_path: Path | None
    model_path_display: str
    model_exists: bool
    has_genai_config: bool
    onnx_files: list[str]
    safetensors_files: list[str]
    gguf_files: list[str]
    detected_format: str
    model_size_bytes: int
    directml_viable: bool
    fallback_required: bool
    directml_blocker: str | None


@dataclass(frozen=True)
class RuntimeSelection:
    backend: str
    provider: str
    device: str
    fallback_required: bool
    directml_viable: bool
    directml_blocker: str | None


class LocalLLMService:
    """Lazy local LLM runtime that inspects model artifacts before loading them."""

    def __init__(self, runtime_settings: Settings = settings) -> None:
        self._settings = runtime_settings
        self._lock = threading.Lock()
        self._load_attempted = False
        self._load_success = False
        self._load_error: str | None = None
        self._runtime_backend = "unresolved"
        self._runtime_provider = "unresolved"
        self._runtime_device = "unresolved"
        self._gpu_path_active = False
        self._model: Any | None = None
        self._tokenizer: Any | None = None
        self._ort_module: Any | None = None
        self._ort_tokenizer_stream: Any | None = None

    def inspect_model(self) -> ModelInspection:
        model_path = self._settings.local_llm_model_dir
        if model_path is None:
            return ModelInspection(
                model_path=None,
                model_path_display="",
                model_exists=False,
                has_genai_config=False,
                onnx_files=[],
                safetensors_files=[],
                gguf_files=[],
                detected_format="missing",
                model_size_bytes=0,
                directml_viable=False,
                fallback_required=False,
                directml_blocker="LOCAL_LLM_MODEL_PATH is empty.",
            )

        root_path = model_path if model_path.is_dir() else model_path.parent
        if not model_path.exists():
            return ModelInspection(
                model_path=model_path,
                model_path_display=str(model_path),
                model_exists=False,
                has_genai_config=False,
                onnx_files=[],
                safetensors_files=[],
                gguf_files=[],
                detected_format="missing",
                model_size_bytes=0,
                directml_viable=False,
                fallback_required=False,
                directml_blocker=f"Configured model path does not exist: {model_path}",
            )

        has_genai_config = (root_path / "genai_config.json").exists()
        onnx_files = self._collect_model_files(root_path, "*.onnx")
        safetensors_files = self._collect_model_files(root_path, "*.safetensors")
        gguf_files = self._collect_model_files(root_path, "*.gguf")
        model_size_bytes = self._estimate_model_size(root_path, safetensors_files, onnx_files, gguf_files)

        if has_genai_config and onnx_files:
            detected_format = "ort-genai-onnx"
            directml_viable = True
            fallback_required = False
            directml_blocker = None
        elif onnx_files:
            detected_format = "onnx"
            directml_viable = False
            fallback_required = True
            directml_blocker = (
                "ONNX files were found, but genai_config.json is missing, so ONNX Runtime GenAI "
                "cannot be initialized from this folder."
            )
        elif safetensors_files:
            detected_format = "huggingface-safetensors"
            directml_viable = False
            fallback_required = True
            directml_blocker = (
                "The folder contains a Hugging Face safetensors checkpoint, not an ONNX Runtime "
                "GenAI export. DirectML is not available from this format without a separate conversion step."
            )
        elif gguf_files:
            detected_format = "gguf"
            directml_viable = False
            fallback_required = True
            directml_blocker = (
                "The folder contains GGUF artifacts. GGUF is a fallback runtime format, not an "
                "ONNX Runtime GenAI DirectML artifact."
            )
        else:
            detected_format = "unknown"
            directml_viable = False
            fallback_required = True
            directml_blocker = (
                "No GenAI-ready ONNX, safetensors, or GGUF artifacts were found under the configured model path."
            )

        return ModelInspection(
            model_path=model_path,
            model_path_display=str(model_path),
            model_exists=True,
            has_genai_config=has_genai_config,
            onnx_files=onnx_files,
            safetensors_files=safetensors_files,
            gguf_files=gguf_files,
            detected_format=detected_format,
            model_size_bytes=model_size_bytes,
            directml_viable=directml_viable,
            fallback_required=fallback_required,
            directml_blocker=directml_blocker,
        )

    def get_status(self) -> dict[str, Any]:
        inspection = self.inspect_model()
        selection = self._resolve_runtime(inspection)

        if not self._settings.local_llm_enabled:
            status = "disabled"
        elif not inspection.model_exists:
            status = "missing-model"
        elif self._load_success:
            status = "ready"
        elif self._load_attempted and self._load_error:
            status = "error"
        else:
            status = "inspected"

        return {
            "status": status,
            "enabled": self._settings.local_llm_enabled,
            "backend": selection.backend,
            "provider": self._runtime_provider if self._load_success else selection.provider,
            "model_path": inspection.model_path_display,
            "device": self._runtime_device if self._load_success else selection.device,
            "gpu_path_active": self._gpu_path_active,
            "load_attempted": self._load_attempted,
            "load_success": self._load_success,
            "model_format": inspection.detected_format,
            "has_genai_config": inspection.has_genai_config,
            "onnx_files": inspection.onnx_files,
            "safetensors_files": inspection.safetensors_files,
            "gguf_files": inspection.gguf_files,
            "directml_viable": selection.directml_viable,
            "fallback_required": selection.fallback_required,
            "directml_blocker": selection.directml_blocker,
            "load_error": self._load_error,
            "model_size_bytes": inspection.model_size_bytes,
        }

    def generate_response(
        self,
        message: str,
        system_prompt: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        inspection = self.inspect_model()
        selection = self._resolve_runtime(inspection)

        if not self._ensure_runtime_loaded(inspection, selection):
            return self._failure_response(inspection, selection)

        try:
            if self._runtime_backend == "ort-genai":
                answer = self._generate_with_ort_genai(
                    message=message,
                    system_prompt=system_prompt,
                    history=history or [],
                )
            elif self._runtime_backend == "llama-cpp":
                answer = self._generate_with_llama_cpp(
                    message=message,
                    system_prompt=system_prompt,
                    history=history or [],
                )
            elif self._runtime_backend == "transformers":
                answer = self._generate_with_transformers(
                    message=message,
                    system_prompt=system_prompt,
                    history=history or [],
                )
            else:
                raise RuntimeError(f"Unsupported backend selected: {self._runtime_backend}")
        except Exception as exc:  # pragma: no cover - runtime-path dependent
            self._load_error = str(exc)
            logger.exception("Local LLM generation failed.")
            return self._failure_response(inspection, selection)

        return {
            "answer": answer,
            "backend": self._runtime_backend,
            "provider": self._runtime_provider,
            "model_path": inspection.model_path_display,
            "device": self._runtime_device,
            "gpu_path_active": self._gpu_path_active,
            "load_success": True,
            "model_format": inspection.detected_format,
            "fallback_required": selection.fallback_required,
            "directml_viable": selection.directml_viable,
            "load_error": None,
        }

    def _ensure_runtime_loaded(
        self,
        inspection: ModelInspection,
        selection: RuntimeSelection,
    ) -> bool:
        if not self._settings.local_llm_enabled:
            self._load_error = "LOCAL_LLM_ENABLED is false."
            return False

        if not inspection.model_exists:
            self._load_error = inspection.directml_blocker
            return False

        if self._load_success:
            return True

        if self._load_attempted and self._load_error:
            return False

        with self._lock:
            if self._load_success:
                return True
            if self._load_attempted and self._load_error:
                return False

            self._load_attempted = True
            self._runtime_backend = selection.backend
            self._runtime_provider = selection.provider
            self._runtime_device = selection.device
            self._gpu_path_active = False

            logger.info(
                "Initializing local LLM backend=%s provider=%s device=%s model_path=%s",
                selection.backend,
                selection.provider,
                selection.device,
                inspection.model_path_display,
            )

            try:
                if selection.backend == "ort-genai":
                    if not inspection.directml_viable:
                        raise RuntimeError(
                            selection.directml_blocker
                            or "The configured model path is not ORT GenAI compatible."
                        )
                    self._initialize_ort_genai(inspection, selection)
                elif selection.backend == "llama-cpp":
                    self._initialize_llama_cpp(inspection)
                elif selection.backend == "transformers":
                    self._initialize_transformers(inspection)
                else:
                    raise RuntimeError(selection.directml_blocker or "No supported runtime is available.")
            except Exception as exc:  # pragma: no cover - runtime-path dependent
                self._load_success = False
                self._load_error = str(exc)
                logger.warning("Local LLM initialization failed: %s", exc)
                return False

            self._load_success = True
            self._load_error = None
            logger.info(
                "Local LLM ready backend=%s provider=%s device=%s gpu_path_active=%s",
                self._runtime_backend,
                self._runtime_provider,
                self._runtime_device,
                self._gpu_path_active,
            )
            return True

    def _initialize_ort_genai(
        self,
        inspection: ModelInspection,
        selection: RuntimeSelection,
    ) -> None:
        if not importlib.util.find_spec("onnxruntime_genai"):
            package_name = (
                "onnxruntime-genai-directml"
                if selection.provider == "directml"
                else "onnxruntime-genai"
            )
            raise RuntimeError(
                f"{package_name} is not installed. Install the correct ONNX Runtime GenAI package for this model format."
            )

        import onnxruntime_genai as og

        genai_config_path = inspection.model_path
        if genai_config_path is None:
            raise RuntimeError("Model path is unavailable for ORT GenAI initialization.")
        if genai_config_path.is_dir():
            genai_config_path = genai_config_path / "genai_config.json"

        config = og.Config(str(genai_config_path))
        config.clear_providers()
        if selection.provider == "directml":
            config.append_provider("DmlExecutionProvider")
        else:
            config.append_provider("CPUExecutionProvider")

        model = og.Model(config)
        tokenizer = og.Tokenizer(model)
        self._ort_module = og
        self._model = model
        self._tokenizer = tokenizer
        self._ort_tokenizer_stream = tokenizer.create_stream()
        self._runtime_backend = "ort-genai"
        self._runtime_provider = selection.provider
        self._runtime_device = selection.device
        self._gpu_path_active = selection.provider == "directml" and model.device_type.lower() != "cpu"

    def _initialize_llama_cpp(self, inspection: ModelInspection) -> None:
        from llama_cpp import Llama

        model_path = self._resolve_gguf_model_path(inspection)
        cpu_count = os.cpu_count() or 4

        self._model = Llama(
            model_path=str(model_path),
            n_ctx=2048,
            n_threads=max(1, cpu_count // 2),
            n_batch=512,
            n_gpu_layers=0,
            verbose=False,
        )
        self._runtime_backend = "llama-cpp"
        self._runtime_provider = "cpu"
        self._runtime_device = "cpu"
        self._gpu_path_active = False

    def _initialize_transformers(self, inspection: ModelInspection) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer, QuantoConfig

        if inspection.model_path is None:
            raise RuntimeError("Model path is unavailable for transformers initialization.")

        preflight_error = self._transformers_preflight_error(inspection)
        if preflight_error is not None:
            raise RuntimeError(preflight_error)

        offload_folder = self._settings.local_llm_offload_dir
        offload_folder.mkdir(parents=True, exist_ok=True)

        tokenizer = AutoTokenizer.from_pretrained(str(inspection.model_path))
        if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            str(inspection.model_path),
            device_map="auto",
            max_memory={"cpu": self._suggest_cpu_max_memory()},
            offload_folder=str(offload_folder),
            offload_state_dict=True,
            offload_buffers=True,
            low_cpu_mem_usage=True,
            dtype="auto",
            quantization_config=QuantoConfig(weights="int4"),
        )

        self._model = model
        self._tokenizer = tokenizer
        self._runtime_backend = "transformers"
        self._runtime_provider = "cpu"
        self._runtime_device = "cpu"
        self._gpu_path_active = False

    def _generate_with_transformers(
        self,
        *,
        message: str,
        system_prompt: str | None,
        history: list[dict[str, str]],
    ) -> str:
        import torch

        if self._model is None or self._tokenizer is None:
            raise RuntimeError("Transformers runtime is not initialized.")

        prompt = self._render_prompt(message=message, system_prompt=system_prompt, history=history)
        inputs = self._tokenizer(prompt, return_tensors="pt")

        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": self._settings.local_llm_max_new_tokens,
            "pad_token_id": self._tokenizer.pad_token_id or self._tokenizer.eos_token_id,
            "eos_token_id": self._tokenizer.eos_token_id,
        }
        if self._settings.local_llm_temperature > 0:
            generation_kwargs.update(
                {
                    "do_sample": True,
                    "temperature": self._settings.local_llm_temperature,
                    "top_p": self._settings.local_llm_top_p,
                }
            )
        else:
            generation_kwargs["do_sample"] = False

        with torch.inference_mode():
            output_ids = self._model.generate(**inputs, **generation_kwargs)

        prompt_token_count = inputs["input_ids"].shape[-1]
        new_token_ids = output_ids[0][prompt_token_count:]
        answer = self._tokenizer.decode(new_token_ids, skip_special_tokens=True).strip()
        if answer:
            return answer
        return self._tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()

    def _generate_with_llama_cpp(
        self,
        *,
        message: str,
        system_prompt: str | None,
        history: list[dict[str, str]],
    ) -> str:
        if self._model is None:
            raise RuntimeError("llama.cpp runtime is not initialized.")

        messages = self._build_messages(
            message=message,
            system_prompt=system_prompt,
            history=history,
        )
        response = self._model.create_chat_completion(
            messages=messages,
            max_tokens=self._settings.local_llm_max_new_tokens,
            temperature=self._settings.local_llm_temperature,
            top_p=self._settings.local_llm_top_p,
        )
        answer = (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not answer:
            raise RuntimeError("llama.cpp returned an empty response.")
        return answer

    def _generate_with_ort_genai(
        self,
        *,
        message: str,
        system_prompt: str | None,
        history: list[dict[str, str]],
    ) -> str:
        if self._ort_module is None or self._model is None or self._tokenizer is None:
            raise RuntimeError("ONNX Runtime GenAI is not initialized.")

        prompt = self._render_prompt(message=message, system_prompt=system_prompt, history=history)
        input_tokens = self._tokenizer.encode(prompt)
        params = self._ort_module.GeneratorParams(self._model)
        params.set_search_options(
            max_length=len(input_tokens) + self._settings.local_llm_max_new_tokens,
            temperature=self._settings.local_llm_temperature,
            top_p=self._settings.local_llm_top_p,
        )
        generator = self._ort_module.Generator(self._model, params)

        output_chunks: list[str] = []
        try:
            generator.append_tokens(input_tokens)
            while not generator.is_done():
                generator.generate_next_token()
                next_token = generator.get_next_tokens()[0]
                output_chunks.append(self._ort_tokenizer_stream.decode(next_token))
        finally:
            del generator

        return "".join(output_chunks).strip()

    def _resolve_runtime(self, inspection: ModelInspection) -> RuntimeSelection:
        if not self._settings.local_llm_enabled:
            return RuntimeSelection(
                backend="disabled",
                provider="cpu",
                device="cpu",
                fallback_required=False,
                directml_viable=inspection.directml_viable,
                directml_blocker="LOCAL_LLM_ENABLED is false.",
            )

        if not inspection.model_exists:
            return RuntimeSelection(
                backend="unavailable",
                provider="cpu",
                device="cpu",
                fallback_required=False,
                directml_viable=False,
                directml_blocker=inspection.directml_blocker,
            )

        requested_backend = self._settings.local_llm_backend
        requested_provider = self._settings.local_llm_provider
        requested_device = self._settings.local_llm_device

        if inspection.detected_format == "ort-genai-onnx" and requested_backend in {"auto", "ort-genai"}:
            provider = "directml" if requested_provider in {"auto", "directml"} else "cpu"
            device = "directml" if provider == "directml" else "cpu"
            return RuntimeSelection(
                backend="ort-genai",
                provider=provider,
                device=device if requested_device in {"auto", device} else device,
                fallback_required=False,
                directml_viable=True,
                directml_blocker=None,
            )

        if inspection.detected_format == "huggingface-safetensors" and requested_backend == "ort-genai":
            return RuntimeSelection(
                backend="ort-genai",
                provider="directml" if requested_provider == "directml" else "cpu",
                device="directml" if requested_device == "directml" else "cpu",
                fallback_required=False,
                directml_viable=False,
                directml_blocker=inspection.directml_blocker,
            )

        if inspection.detected_format == "huggingface-safetensors":
            blocker = inspection.directml_blocker
            if requested_provider == "directml" or requested_device == "directml":
                blocker = (
                    f"{inspection.directml_blocker} DirectML was requested, but the current repo only has a "
                    "Transformers CPU fallback for this checkpoint format."
                )
            return RuntimeSelection(
                backend="transformers",
                provider="cpu",
                device="cpu",
                fallback_required=True,
                directml_viable=False,
                directml_blocker=blocker,
            )

        if inspection.detected_format == "gguf":
            blocker = inspection.directml_blocker
            if requested_provider == "directml" or requested_device == "directml":
                blocker = (
                    f"{inspection.directml_blocker} The working runtime in this project uses llama.cpp "
                    "through a CPU wheel, so DirectML is not active for GGUF models."
                )
            return RuntimeSelection(
                backend="llama-cpp",
                provider="cpu",
                device="cpu",
                fallback_required=True,
                directml_viable=False,
                directml_blocker=blocker,
            )

        return RuntimeSelection(
            backend="unsupported",
            provider="cpu",
            device="cpu",
            fallback_required=inspection.fallback_required,
            directml_viable=inspection.directml_viable,
            directml_blocker=inspection.directml_blocker,
        )

    def _failure_response(
        self,
        inspection: ModelInspection,
        selection: RuntimeSelection,
    ) -> dict[str, Any]:
        return {
            "answer": "",
            "backend": self._runtime_backend if self._load_attempted else selection.backend,
            "provider": self._runtime_provider if self._load_attempted else selection.provider,
            "model_path": inspection.model_path_display,
            "device": self._runtime_device if self._load_attempted else selection.device,
            "gpu_path_active": self._gpu_path_active,
            "load_success": False,
            "model_format": inspection.detected_format,
            "fallback_required": selection.fallback_required,
            "directml_viable": selection.directml_viable,
            "load_error": self._load_error or selection.directml_blocker,
        }

    def _render_prompt(
        self,
        *,
        message: str,
        system_prompt: str | None,
        history: list[dict[str, str]],
    ) -> str:
        messages = self._build_messages(
            message=message,
            system_prompt=system_prompt,
            history=history,
        )

        if self._tokenizer is not None and hasattr(self._tokenizer, "apply_chat_template"):
            return str(
                self._tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            )

        prompt_parts = [f"{entry['role'].upper()}: {entry['content']}" for entry in messages]
        prompt_parts.append("ASSISTANT:")
        return "\n\n".join(prompt_parts)

    def _build_messages(
        self,
        *,
        message: str,
        system_prompt: str | None,
        history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        for item in history:
            role = str(item.get("role") or "").strip().lower()
            content = str(item.get("content") or "").strip()
            if role in {"system", "user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message.strip()})
        return messages

    def _resolve_gguf_model_path(self, inspection: ModelInspection) -> Path:
        if inspection.model_path is not None and inspection.model_path.is_file():
            return inspection.model_path
        if inspection.model_path is not None and inspection.model_path.suffix.lower() == ".gguf":
            return inspection.model_path
        if inspection.model_path is not None and inspection.model_path.is_dir() and inspection.gguf_files:
            return inspection.model_path / inspection.gguf_files[0]
        raise RuntimeError(
            "GGUF backend was selected, but LOCAL_LLM_MODEL_PATH does not point to a GGUF file or folder containing one."
        )

    def _collect_model_files(self, root_path: Path, pattern: str) -> list[str]:
        return sorted(str(path.relative_to(root_path)) for path in root_path.rglob(pattern))

    def _estimate_model_size(
        self,
        root_path: Path,
        safetensors_files: list[str],
        onnx_files: list[str],
        gguf_files: list[str],
    ) -> int:
        index_path = root_path / "model.safetensors.index.json"
        if index_path.exists():
            try:
                index_data = json.loads(index_path.read_text(encoding="utf-8"))
                total_size = int(index_data.get("metadata", {}).get("total_size") or 0)
                if total_size > 0:
                    return total_size
            except (OSError, ValueError, TypeError):
                logger.warning("Unable to parse safetensors index metadata from %s", index_path)

        candidate_files = safetensors_files or onnx_files or gguf_files
        total_size = 0
        for relative_path in candidate_files:
            total_size += (root_path / relative_path).stat().st_size
        return total_size

    def _suggest_cpu_max_memory(self) -> str:
        total_bytes = self._get_total_physical_memory_bytes()
        total_gib = max(8, total_bytes // (1024**3))
        if total_gib <= 16:
            usable_gib = 4
        else:
            usable_gib = max(6, min(10, total_gib - 6))
        return f"{usable_gib}GiB"

    def _transformers_preflight_error(self, inspection: ModelInspection) -> str | None:
        total_bytes = self._get_total_physical_memory_bytes()
        if total_bytes <= 0 or inspection.model_size_bytes <= 0:
            return None

        if inspection.model_size_bytes > total_bytes:
            total_gib = total_bytes / (1024**3)
            model_gib = inspection.model_size_bytes / (1024**3)
            return (
                f"The checkpoint reports about {model_gib:.2f} GiB of safetensors weights, but the host only has "
                f"about {total_gib:.2f} GiB of physical RAM. The current model format is not DirectML-ready, and "
                "attempting the transformers fallback on this machine is not safe."
            )

        return None

    def _get_total_physical_memory_bytes(self) -> int:
        if not hasattr(ctypes, "windll"):
            return 0

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
        return 0
