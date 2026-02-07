import os
import time
import json
import numpy as np
from datetime import datetime
from typing import Generator, Dict, List, Optional, Union
from pathlib import Path
from llama_cpp import Llama
import machine_engine_handshake

class VoxAPI:
    """
    A clean API wrapper for the VOX-AI Engine.
    Features: Smart context management with disk archiving and RAG retrieval.
    """
    
    def __init__(self, model_path: str = None, verbose: bool = False, n_ctx: int = 4096,
                 archive_path: str = None, max_archive_size_mb: int = 100,
                 enable_rag: bool = True, rag_retrieve_count: int = 5):
        """
        Initialize the VOX Engine with automatic hardware optimization.
        
        Args:
            model_path: Path to the .gguf model file. If None, auto-detects from ./models
            verbose: Enable detailed logging
            n_ctx: Context window size (default 4096)
            archive_path: Path to store archived conversation history (default: ./context_archive)
            max_archive_size_mb: Maximum size in MB for archive folder (default: 100MB)
            enable_rag: Enable RAG retrieval from archives (default: True)
            rag_retrieve_count: Number of relevant messages to retrieve from archives (default: 5)
        """
        self.verbose = verbose
        self.history: List[Dict[str, str]] = []
        self.n_ctx = n_ctx
        self.max_tokens_per_response = 2048
        
        # Archive settings
        self.archive_path = archive_path or "./context_archive"
        self.max_archive_size_bytes = max_archive_size_mb * 1024 * 1024
        self.current_fantasy_id = None
        
        # RAG settings
        self.enable_rag = enable_rag
        self.rag_retrieve_count = rag_retrieve_count
        self.embedding_cache = {}  # Cache embeddings to avoid recomputation
        
        # Create archive directory
        Path(self.archive_path).mkdir(parents=True, exist_ok=True)
        
        # Reserve tokens for system prompt and safety buffer
        self.context_reserve = 512
        
        # Statistics
        self.total_archived_messages = 0
        self.total_rag_retrievals = 0
        
        # 1. Hardware Handshake
        self.mode, self.phys_cores, self.config = machine_engine_handshake.get_hardware_config()
        if self.verbose:
            print(f"[VOX API] Mode: {self.mode}")
            print(f"[VOX API] Config: {self.config}")
            print(f"[VOX API] Archive Path: {self.archive_path}")
            print(f"[VOX API] Max Archive Size: {max_archive_size_mb}MB")
            print(f"[VOX API] RAG Enabled: {enable_rag}")
            
        # 2. Apply Environment Optimizations
        self._apply_env_optimizations()
        
        # 3. Model Loading
        if model_path is None:
            model_path = self._auto_find_model()
            
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at: {model_path}")
            
        self.model_name = os.path.basename(model_path)
        
        # 4. Initialize Llama
        self.llm = Llama(
            model_path=model_path,
            n_ctx=self.n_ctx,
            embedding=True,  # Enable embeddings for RAG
            
            # Hardware Config
            n_gpu_layers=self.config['n_gpu_layers'],
            n_threads=self.config['n_threads'],
            n_threads_batch=self.config['n_threads_batch'],
            n_batch=self.config['n_batch'],
            flash_attn=self.config['flash_attn'],
            use_mlock=self.config['use_mlock'],
            cache_type_k=self.config['cache_type_k'],
            cache_type_v=self.config['cache_type_v'],
            
            use_mmap=True,
            verbose=self.verbose
        )
        
        # 5. Warmup
        self.warmup()

    def _apply_env_optimizations(self):
        """Apply environment variables for APU performance and load Backend"""
        import ctypes
        root_path = os.path.abspath(".")
        
        # 1. Performance Variables
        if "busy_wait" in self.config:
            os.environ["GGML_VK_FORCE_BUSY_WAIT"] = self.config["busy_wait"]
        
        # 2. DLL Override (Game-Style Engine)
        local_dll = os.path.join(root_path, "llama.dll")
        
        if os.path.exists(local_dll):
            if hasattr(os, 'add_dll_directory'): 
                try: os.add_dll_directory(root_path)
                except: pass
            
            os.environ["GGML_NUMA"] = "0"
            os.environ["GGML_BACKEND_SEARCH_PATH"] = root_path
            os.environ["LLAMA_CPP_LIB"] = local_dll
            
            # 3. Explicit Backend Loading
            try:
                ggml_path = os.path.join(root_path, "ggml.dll")
                if os.path.exists(ggml_path):
                    ggml = ctypes.CDLL(ggml_path)
                    if hasattr(ggml, 'ggml_backend_load_all'):
                        ggml.ggml_backend_load_all()
                    if self.verbose:
                        print(f"[VOX API] Loaded backends from {ggml_path}")
            except Exception as e:
                print(f"[VOX API] Warning: Failed to load backends: {e}")
                
        else:
            if self.verbose:
                print("[VOX API] Using system/pip installed llama-cpp-python binaries.")

    def _auto_find_model(self) -> str:
        """Find the first .gguf file in ./models"""
        models_dir = os.path.abspath("./models")
        if not os.path.exists(models_dir):
            raise FileNotFoundError("Models directory './models' not found")
            
        files = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]
        if not files:
            raise FileNotFoundError("No .gguf models found in ./models")
            
        return os.path.join(models_dir, files[0])

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate of tokens in text (4 chars per token)"""
        return len(text) // 4

    def _get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding vector for text using the model.
        Caches embeddings to avoid recomputation.
        """
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        
        try:
            # Use llama-cpp-python's embedding function
            embedding = self.llm.create_embedding(text)['data'][0]['embedding']
            embedding_array = np.array(embedding)
            
            # Normalize for cosine similarity
            norm = np.linalg.norm(embedding_array)
            if norm > 0:
                embedding_array = embedding_array / norm
            
            # Cache it
            self.embedding_cache[text] = embedding_array
            return embedding_array
            
        except Exception as e:
            if self.verbose:
                print(f"[VOX RAG] Embedding error: {e}")
            # Return zero vector on error
            return np.zeros(4096)

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        return np.dot(vec1, vec2)

    def _load_archives_for_fantasy(self) -> List[Dict]:
        """Load all archived messages for the current fantasy"""
        if not self.current_fantasy_id:
            return []
        
        fantasy_folder = Path(self.archive_path) / self.current_fantasy_id
        
        if not fantasy_folder.exists():
            return []
        
        all_messages = []
        
        # Load all archive files
        for archive_file in sorted(fantasy_folder.glob("archive_*.json")):
            try:
                with open(archive_file, 'r', encoding='utf-8') as f:
                    archive_data = json.load(f)
                    messages = archive_data.get('messages', [])
                    
                    # Add metadata to each message
                    for msg in messages:
                        msg['archive_file'] = archive_file.name
                        msg['timestamp'] = archive_data.get('timestamp', '')
                    
                    all_messages.extend(messages)
            except Exception as e:
                if self.verbose:
                    print(f"[VOX RAG] Error loading {archive_file.name}: {e}")
        
        return all_messages

    def _retrieve_relevant_context(self, query: str) -> List[Dict[str, str]]:
        """
        RAG: Retrieve most relevant archived messages based on semantic similarity.
        
        Args:
            query: The current user query to find relevant context for
            
        Returns:
            List of relevant messages with their content and metadata
        """
        if not self.enable_rag:
            return []
        
        if self.verbose:
            print(f"[VOX RAG] Searching archives for relevant context...")
        
        # Load all archived messages
        archived_messages = self._load_archives_for_fantasy()
        
        if not archived_messages:
            if self.verbose:
                print(f"[VOX RAG] No archived messages found")
            return []
        
        # Get query embedding
        query_embedding = self._get_embedding(query)
        
        # Calculate similarity scores for all archived messages
        scored_messages = []
        
        for msg in archived_messages:
            # Skip system messages
            if msg.get('role') == 'system':
                continue
            
            # Get message embedding
            msg_text = msg.get('content', '')
            if not msg_text:
                continue
            
            msg_embedding = self._get_embedding(msg_text)
            
            # Calculate similarity
            similarity = self._cosine_similarity(query_embedding, msg_embedding)
            
            scored_messages.append({
                'message': msg,
                'similarity': similarity
            })
        
        # Sort by similarity (highest first)
        scored_messages.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Get top N most relevant
        top_messages = scored_messages[:self.rag_retrieve_count]
        
        if self.verbose and top_messages:
            print(f"[VOX RAG] Retrieved {len(top_messages)} relevant messages")
            for i, item in enumerate(top_messages[:3], 1):
                preview = item['message']['content'][:60].replace('\n', ' ')
                print(f"  {i}. [{item['similarity']:.3f}] {preview}...")
        
        self.total_rag_retrievals += len(top_messages)
        
        return [item['message'] for item in top_messages]

    def _inject_rag_context(self, retrieved_messages: List[Dict[str, str]]) -> str:
        """Format retrieved messages as context injection"""
        if not retrieved_messages:
            return ""
        
        context_parts = ["[Retrieved Context from Past Conversation:]"]
        
        for msg in retrieved_messages:
            role_label = "User" if msg['role'] == 'user' else "Assistant"
            content = msg['content'][:200]  # Limit length
            context_parts.append(f"- {role_label}: {content}")
        
        context_parts.append("[End Retrieved Context]\n")
        
        return "\n".join(context_parts)

    def _get_archive_folder_size(self) -> int:
        """Calculate total size of archive folder in bytes"""
        total_size = 0
        archive_path = Path(self.archive_path)
        
        if not archive_path.exists():
            return 0
            
        for file in archive_path.rglob('*'):
            if file.is_file():
                total_size += file.stat().st_size
                
        return total_size

    def _cleanup_old_archives(self):
        """Remove oldest archive files if folder exceeds size limit"""
        current_size = self._get_archive_folder_size()
        
        if current_size <= self.max_archive_size_bytes:
            return
            
        if self.verbose:
            print(f"[VOX ARCHIVE] Archive folder is {current_size / 1024 / 1024:.2f}MB, cleaning up...")
        
        archive_files = []
        for file in Path(self.archive_path).rglob('*.json'):
            archive_files.append((file, file.stat().st_mtime))
        
        archive_files.sort(key=lambda x: x[1])
        
        for file_path, _ in archive_files:
            if current_size <= self.max_archive_size_bytes * 0.9:
                break
                
            file_size = file_path.stat().st_size
            file_path.unlink()
            current_size -= file_size
            
            if self.verbose:
                print(f"[VOX ARCHIVE] Deleted old archive: {file_path.name}")

    def _archive_messages(self, messages: List[Dict[str, str]]):
        """Save messages to disk archive"""
        if not messages:
            return
            
        fantasy_folder = Path(self.archive_path)
        if self.current_fantasy_id:
            fantasy_folder = fantasy_folder / self.current_fantasy_id
        fantasy_folder.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = fantasy_folder / f"archive_{timestamp}.json"
        
        archive_data = {
            "fantasy_id": self.current_fantasy_id,
            "timestamp": timestamp,
            "message_count": len(messages),
            "messages": messages
        }
        
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(archive_data, f, indent=2, ensure_ascii=False)
        
        self.total_archived_messages += len(messages)
        
        if self.verbose:
            print(f"[VOX ARCHIVE] Archived {len(messages)} messages to {archive_file.name}")
        
        # Pre-compute embeddings for archived messages if RAG enabled
        if self.enable_rag:
            for msg in messages:
                if msg.get('role') != 'system':
                    self._get_embedding(msg.get('content', ''))
        
        self._cleanup_old_archives()

    def set_fantasy_context(self, fantasy_id: str):
        """Set the current fantasy ID for organized archiving"""
        self.current_fantasy_id = fantasy_id

    def _trim_history_with_archive(self):
        """Smart context management: archive 25% when 80% full"""
        if not self.history:
            return
        
        available_tokens = self.n_ctx - self.max_tokens_per_response - self.context_reserve
        
        total_tokens = 0
        for msg in self.history:
            total_tokens += self._estimate_tokens(msg['content']) + 50
        
        threshold = available_tokens * 0.80
        
        if total_tokens < threshold:
            return
        
        if self.verbose:
            print(f"[VOX CONTEXT] Usage: {total_tokens}/{available_tokens} tokens ({total_tokens/available_tokens*100:.1f}%)")
        
        system_prompt = self.history[0] if self.history and self.history[0]['role'] == 'system' else None
        messages = self.history[1:] if system_prompt else self.history
        
        num_to_archive = max(1, len(messages) // 4)
        
        messages_to_archive = messages[:num_to_archive]
        messages_to_keep = messages[num_to_archive:]
        
        self._archive_messages(messages_to_archive)
        
        new_history = []
        if system_prompt:
            new_history.append(system_prompt)
        new_history.extend(messages_to_keep)
        
        self.history = new_history
        
        if self.verbose:
            print(f"[VOX CONTEXT] Archived {num_to_archive} messages, kept {len(messages_to_keep)} in memory")

    def warmup(self):
        """Run a silent inference to load weights into RAM/VRAM"""
        if self.verbose: print("[VOX API] Warming up...")
        try:
            self.llm.create_chat_completion(
                messages=[{"role": "user", "content": "."}], 
                max_tokens=1
            )
        except Exception as e:
            if self.verbose:
                print(f"[VOX API] Warmup error (non-critical): {e}")

    def chat(self, user_message: str, stream: bool = True, system_prompt: str = None) -> Union[str, Generator[str, None, None]]:
        """
        Send a message to the AI with RAG retrieval from archives.
        
        Args:
            user_message: The text input from the user
            stream: If True, returns a generator yielding tokens
            system_prompt: Optional override for system prompt
        """
        
        # RAG: Retrieve relevant context from archives
        retrieved_context = []
        if self.enable_rag and self.current_fantasy_id:
            retrieved_context = self._retrieve_relevant_context(user_message)
        
        # Initialize history if empty
        if not self.history:
            sys_msg = system_prompt or "You are a helpful assistant."
            
            # Inject RAG context into system prompt
            if retrieved_context:
                rag_injection = self._inject_rag_context(retrieved_context)
                sys_msg = rag_injection + "\n" + sys_msg
            
            self.history.append({"role": "system", "content": sys_msg})
        else:
            # Update system prompt with RAG context for this turn
            if retrieved_context and self.history[0]['role'] == 'system':
                original_system = self.history[0]['content']
                # Remove old RAG injections
                if "[Retrieved Context from Past Conversation:]" in original_system:
                    parts = original_system.split("[End Retrieved Context]\n")
                    original_system = parts[-1] if len(parts) > 1 else original_system
                
                # Add new RAG context
                rag_injection = self._inject_rag_context(retrieved_context)
                self.history[0]['content'] = rag_injection + "\n" + original_system
            
        # Add user message
        self.history.append({"role": "user", "content": user_message})
        
        # Trim history with archiving if needed
        self._trim_history_with_archive()
        
        if stream:
            return self._stream_response()
        else:
            return self._full_response()

    def _stream_response(self) -> Generator[str, None, None]:
        """Internal generator for streaming responses"""
        full_response = ""
        
        try:
            stream = self.llm.create_chat_completion(
                messages=self.history,
                max_tokens=self.max_tokens_per_response,
                temperature=0.7,
                top_k=40,
                repeat_penalty=1.1,
                stream=True
            )
            
            for chunk in stream:
                if "content" in chunk["choices"][0]["delta"]:
                    token = chunk["choices"][0]["delta"]["content"]
                    full_response += token
                    yield token
                    
        except ValueError as e:
            if "exceed context window" in str(e):
                if self.verbose:
                    print(f"[VOX EMERGENCY] Context overflow! Emergency archiving...")
                
                system_msg = self.history[0] if self.history[0]['role'] == 'system' else None
                messages = self.history[1:] if system_msg else self.history
                
                num_to_archive = len(messages) // 2
                messages_to_archive = messages[:num_to_archive]
                messages_to_keep = messages[num_to_archive:]
                
                self._archive_messages(messages_to_archive)
                
                self.history = [system_msg] + messages_to_keep if system_msg else messages_to_keep
                
                # Retry
                stream = self.llm.create_chat_completion(
                    messages=self.history,
                    max_tokens=self.max_tokens_per_response,
                    temperature=0.7,
                    top_k=40,
                    repeat_penalty=1.1,
                    stream=True
                )
                
                for chunk in stream:
                    if "content" in chunk["choices"][0]["delta"]:
                        token = chunk["choices"][0]["delta"]["content"]
                        full_response += token
                        yield token
            else:
                raise
                
        self.history.append({"role": "assistant", "content": full_response})

    def _full_response(self) -> str:
        """Internal method for non-streaming response"""
        try:
            response = self.llm.create_chat_completion(
                messages=self.history,
                max_tokens=self.max_tokens_per_response,
                temperature=0.7,
                top_k=40,
                repeat_penalty=1.1,
                stream=False
            )
            
            text = response["choices"][0]["message"]["content"]
            self.history.append({"role": "assistant", "content": text})
            return text
            
        except ValueError as e:
            if "exceed context window" in str(e):
                self._trim_history_with_archive()
                
                response = self.llm.create_chat_completion(
                    messages=self.history,
                    max_tokens=self.max_tokens_per_response,
                    temperature=0.7,
                    top_k=40,
                    repeat_penalty=1.1,
                    stream=False
                )
                
                text = response["choices"][0]["message"]["content"]
                self.history.append({"role": "assistant", "content": text})
                return text
            else:
                raise

    def clear_history(self):
        """Reset conversation context"""
        self.history = []
        self.embedding_cache.clear()

    def get_stats(self):
        """Get info about the loaded model and hardware"""
        archive_size = self._get_archive_folder_size()
        
        return {
            "model": self.model_name,
            "mode": self.mode,
            "cores": self.phys_cores,
            "gpu_layers": self.config['n_gpu_layers'],
            "context_size": self.n_ctx,
            "messages_in_history": len(self.history),
            "total_archived_messages": self.total_archived_messages,
            "total_rag_retrievals": self.total_rag_retrievals,
            "archive_size_mb": archive_size / 1024 / 1024,
            "archive_path": self.archive_path,
            "rag_enabled": self.enable_rag,
            "embedding_cache_size": len(self.embedding_cache)
        }
