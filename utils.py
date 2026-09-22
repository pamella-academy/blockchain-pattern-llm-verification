#!/usr/bin/env python3
"""
utils.py - Funções auxiliares para o pipeline de classificação hierárquica

Contém todas as funções utilitárias para:
- Leitura e escrita de arquivos CSV/JSONL
- Carregamento de variáveis de ambiente
- Preparação de artefatos (issues/PRs) para classificação
- Normalização e validação de respostas
- Agregação de resultados do Stage 2
- Checkpoint (salvar e retomar progresso)
"""

import csv
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# 1. FUNÇÕES DE I/O E CARREGAMENTO
# ═══════════════════════════════════════════════════════════════════════════

def load_env_file(path: str = ".env") -> None:
    """
    Carrega variáveis de ambiente de um arquivo .env
    
    Args:
        path: Caminho para o arquivo .env
    """
    env_path = Path(path)
    if not env_path.exists():
        return
    
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


def read_csv_dicts(path: str) -> List[Dict[str, str]]:
    """
    Lê um arquivo CSV e retorna lista de dicionários
    
    Args:
        path: Caminho do arquivo CSV
        
    Returns:
        Lista de dicionários, um por linha
    """
    with open(path, encoding="utf-8-sig") as f:  # utf-8-sig remove BOM automaticamente
        rows = list(csv.DictReader(f))
    
    # Limpar BOM residual nos nomes das colunas
    cleaned_rows = []
    for row in rows:
        cleaned = {}
        for key, value in row.items():
            clean_key = key.lstrip('\ufeff').strip('"')
            cleaned[clean_key] = value
        cleaned_rows.append(cleaned)
    
    return cleaned_rows


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    """
    Lê um arquivo JSONL e retorna lista de objetos
    
    Args:
        path: Caminho do arquivo JSONL
        
    Returns:
        Lista de objetos JSON
    """
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(path: str, obj: Any) -> None:
    """
    Adiciona um objeto JSON a um arquivo JSONL
    
    Args:
        path: Caminho do arquivo JSONL
        obj: Objeto Python a ser serializado
    """
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def write_csv_dicts(path: str, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    """
    Escreve lista de dicionários em arquivo CSV
    
    Args:
        path: Caminho do arquivo CSV
        rows: Lista de dicionários
        fieldnames: Nomes das colunas
    """
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ═══════════════════════════════════════════════════════════════════════════
# 2. PREPARAÇÃO DE ARTEFATOS
# ═══════════════════════════════════════════════════════════════════════════

class PreparedIssue:
    """
    Representa um artefato (issue/PR) preparado para classificação
    """
    def __init__(
        self,
        issue_key: str,
        custom_id_stage1: str,
        artifact_text: str,
        artifact_type: str,
        repo: str,
        number: int,
        metadata: Dict[str, Any],
    ):
        self.issue_key = issue_key
        self.custom_id_stage1 = custom_id_stage1
        self.artifact_text = artifact_text
        self.artifact_type = artifact_type
        self.repo = repo
        self.number = number
        self.metadata = metadata


def prepare_issues(
    web3_csv_path: str,
    limit: Optional[int] = None,
    shuffle_seed: Optional[int] = None,
) -> List[PreparedIssue]:
    """
    Carrega e prepara issues/PRs para classificação
    
    Suporta múltiplos formatos de CSV automaticamente:
    - Formato 1: repo, number, type, title, body
    - Formato 2: repository_full_name, issue_number, issue_title, issue_body
    
    Args:
        web3_csv_path: Caminho do CSV com issues
        limit: Número máximo de issues (None = todas)
        shuffle_seed: Seed para shuffle aleatório (None = sem shuffle)
        
    Returns:
        Lista de PreparedIssue
    """
    rows = read_csv_dicts(web3_csv_path)
    
    if not rows:
        return []
    
    # Detectar formato do CSV
    first_row = rows[0]
    
    # Mapear colunas flexivelmente
    def get_col(row, *alternatives):
        """Pega primeira coluna que existir"""
        for col in alternatives:
            if col in row and row[col]:
                return row[col]
        return ""
    
    # Shuffle se solicitado
    if shuffle_seed is not None:
        import random
        random.Random(shuffle_seed).shuffle(rows)
    
    # Limitar se solicitado
    if limit is not None:
        rows = rows[:limit]
    
    prepared = []
    for row in rows:
        # Detectar colunas flexivelmente
        repo = get_col(row, "repo", "repository", "repository_full_name")
        number_str = get_col(row, "number", "issue_number", "pr_number")
        number = int(number_str) if number_str else 0
        artifact_type = get_col(row, "type", "artifact_type") or "Issue"
        title = get_col(row, "title", "issue_title", "pr_title")
        body = get_col(row, "body", "issue_body", "pr_body", "description")
        
        issue_key = f"{repo}#{number}"
        custom_id = f"stage1_{repo.replace('/', '_')}_{number}"
        
        # Montar texto do artefato
        parts = []
        if artifact_type.lower() in ["issue", "issues"]:
            parts.append(f"<issue_title>\n{title}\n</issue_title>")
            if body:
                parts.append(f"<issue_body>\n{body}\n</issue_body>")
        else:  # pull_request
            parts.append(f"<pull_request_title>\n{title}\n</pull_request_title>")
            if body:
                parts.append(f"<pull_request_description>\n{body}\n</pull_request_description>")
        
        artifact_text = "\n\n".join(parts)
        
        prepared.append(
            PreparedIssue(
                issue_key=issue_key,
                custom_id_stage1=custom_id,
                artifact_text=artifact_text,
                artifact_type=artifact_type,
                repo=repo,
                number=number,
                metadata={"title": title},
            )
        )
    
    return prepared


# ═══════════════════════════════════════════════════════════════════════════
# 3. CHECKPOINT - SALVAR E RETOMAR PROGRESSO
# ═══════════════════════════════════════════════════════════════════════════

class Checkpoint:
    """
    Gerencia checkpoint para retomar execuções interrompidas
    """
    def __init__(self, path: str):
        self.path = path
        self.completed: Set[str] = set()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._load()
    
    def _load(self) -> None:
        """Carrega IDs completados do arquivo"""
        if Path(self.path).exists():
            with open(self.path) as f:
                self.completed = {line.strip() for line in f if line.strip()}
    
    def mark_completed(self, custom_id: str) -> None:
        """Marca um custom_id como completo"""
        if custom_id not in self.completed:
            self.completed.add(custom_id)
            with open(self.path, "a") as f:
                f.write(custom_id + "\n")
    
    def is_completed(self, custom_id: str) -> bool:
        """Verifica se um custom_id já foi processado"""
        return custom_id in self.completed


# ═══════════════════════════════════════════════════════════════════════════
# 4. NORMALIZAÇÃO E VALIDAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

def normalize_stage1(payload: Dict[str, Any], catalog: "PatternCatalog") -> Dict[str, Any]:
    """
    Normaliza respostas do Stage 1 (hierárquico Call 3 ou flat)
    
    Args:
        payload: Resposta crua da API
        catalog: Catálogo de patterns
        
    Returns:
        Dicionário normalizado
    """
    if "candidates" not in payload:
        return {"candidates": []}
    
    normalized = []
    for c in payload["candidates"]:
        # Normalizar nome do pattern
        pattern_name = c.get("pattern", "")
        canonical = catalog.normalize_pattern_name(pattern_name)
        
        normalized.append({
            "pattern": canonical,
            "confidence": c.get("confidence", "unknown"),
            "evidence_text": c.get("evidence_text", ""),
            "evidence_mechanism": c.get("evidence_mechanism", ""),
            "evidence_location": c.get("evidence_location", ""),
            "false_friend_detected": c.get("false_friend_detected", "no"),
        })
    
    return {"candidates": normalized}


def object_to_dict(obj: Any) -> Dict[str, Any]:
    """
    Converte objetos Gemini API para dicionário
    
    Args:
        obj: Objeto da API
        
    Returns:
        Dicionário equivalente
    """
    if hasattr(obj, "_pb"):
        # Objeto protobuf do Gemini
        from google.protobuf.json_format import MessageToDict
        return MessageToDict(obj._pb)
    return obj


def parse_response_payload(response: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Extrai payload JSON e metadados de uma resposta da API (Gemini ou Mistral)
    
    Args:
        response: Resposta da API (Gemini ou Mistral)
        
    Returns:
        Tupla (payload, metadata)
    """
    # Se é resposta normalizada do Mistral (dict com 'text' e 'usage')
    if isinstance(response, dict) and "text" in response and "usage" in response:
        try:
            payload = json.loads(response["text"])
        except json.JSONDecodeError:
            payload = {"error": "json_decode_failed", "raw": response["text"]}
        
        metadata = {
            "prompt_tokens": response["usage"]["prompt_tokens"],
            "completion_tokens": response["usage"]["completion_tokens"],
            "total_tokens": response["usage"]["total_tokens"],
        }
        return payload, metadata
    
    # Gemini (original)
    if not hasattr(response, "candidates") or not response.candidates:
        return {"error": "no_candidates"}, {}
    
    candidate = response.candidates[0]
    if not hasattr(candidate.content, "parts") or not candidate.content.parts:
        return {"error": "no_parts"}, {}
    
    part = candidate.content.parts[0]
    payload_text = part.text if hasattr(part, "text") else ""
    
    # Tentar parsear JSON
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        payload = {"error": "json_decode_failed", "raw": payload_text}
    
    # Metadados de uso
    metadata = {}
    if hasattr(response, "usage_metadata"):
        metadata = {
            "prompt_tokens": response.usage_metadata.prompt_token_count,
            "completion_tokens": response.usage_metadata.candidates_token_count,
            "total_tokens": response.usage_metadata.total_token_count,
        }
    
    return payload, metadata


# ═══════════════════════════════════════════════════════════════════════════
# 5. AGREGAÇÃO DE RESULTADOS DO STAGE 2
# ═══════════════════════════════════════════════════════════════════════════

def aggregate_stage2_results(
    stage1_flat_path: str,
    stage2_batch_path: str,
) -> List[Dict[str, Any]]:
    """
    Agrega resultados do Stage 1 com Stage 2
    
    Args:
        stage1_flat_path: CSV com resultados do Stage 1
        stage2_batch_path: JSONL com respostas do Stage 2
        
    Returns:
        Lista de dicionários agregados
    """
    stage1_rows = read_csv_dicts(stage1_flat_path)
    stage2_responses = read_jsonl(stage2_batch_path)
    
    # Indexar Stage 2 por custom_id
    stage2_by_id = {r["custom_id"]: r for r in stage2_responses}
    
    aggregated = []
    for row in stage1_rows:
        # Se não há candidatos, adicionar linha única sem Stage 2
        if not row.get("call3_candidates"):
            base = dict(row)
            base.update({
                "pattern": "",
                "stage2_verdict": "",
                "stage2_confidence": "",
                "stage2_mechanism_match": "",
                "stage2_scope_match": "",
                "stage2_focus_match": "",
                "stage2_evidence_text": "",
                "stage2_evidence_location": "",
                "stage2_prompt_tokens": 0,
                "stage2_completion_tokens": 0,
            })
            aggregated.append(base)
            continue
        
        # Para cada candidato, criar uma linha com resultado do Stage 2
        candidates = row["call3_candidates"].split(";")
        for pattern in candidates:
            if not pattern:
                continue
            
            base = dict(row)
            base["pattern"] = pattern
            
            # Construir custom_id_stage2
            issue_key = row["issue_key"]
            custom_id = f"stage2_{issue_key.replace('/', '_').replace('#', '_')}_{pattern}"
            
            if custom_id not in stage2_by_id:
                base.update({
                    "stage2_verdict": "MISSING",
                    "stage2_confidence": "",
                    "stage2_mechanism_match": "",
                    "stage2_scope_match": "",
                    "stage2_focus_match": "",
                    "stage2_evidence_text": "",
                    "stage2_evidence_location": "",
                    "stage2_prompt_tokens": 0,
                    "stage2_completion_tokens": 0,
                })
                aggregated.append(base)
                continue
            
            resp = stage2_by_id[custom_id]
            payload = resp.get("response", {})
            metadata = resp.get("metadata", {})
            
            base.update({
                "stage2_verdict": payload.get("verdict", "ERROR"),
                "stage2_confidence": payload.get("confidence", ""),
                "stage2_mechanism_match": str(payload.get("mechanism_match", "")),
                "stage2_scope_match": str(payload.get("scope_match", "")),
                "stage2_focus_match": str(payload.get("focus_match", "")),
                "stage2_evidence_text": payload.get("evidence_text", ""),
                "stage2_evidence_location": payload.get("evidence_location", ""),
                "stage2_prompt_tokens": metadata.get("prompt_tokens", 0),
                "stage2_completion_tokens": metadata.get("completion_tokens", 0),
            })
            aggregated.append(base)
    
    return aggregated


# ═══════════════════════════════════════════════════════════════════════════
# 6. PADRÃO CATALOG E TAXONOMIA
# ═══════════════════════════════════════════════════════════════════════════

class PatternCatalog:
    """
    Catálogo de patterns blockchain carregado do CSV
    """
    def __init__(self, csv_path: str):
        rows = read_csv_dicts(csv_path)
        self.by_name: Dict[str, Dict[str, str]] = {}
        self.all_names: List[str] = []
        
        for r in rows:
            # Coluna pode ser "name" ou "pattern"
            name = r.get("pattern", r.get("name", "")).strip()
            if not name:
                continue
            self.all_names.append(name)
            self.by_name[name] = {
                "name": name,
                "category": r["category"].strip(),
                "subcategory": r["subcategory"].strip(),
                "description": r["description"].strip(),
                "keywords": r.get("keywords", "").strip(),
            }
    
    def normalize_pattern_name(self, name: str) -> str:
        """Normaliza nome de pattern (case-insensitive match)"""
        name_lower = name.strip().lower()
        for canonical in self.all_names:
            if canonical.lower() == name_lower:
                return canonical
        return name.strip()


class TaxonomyTree:
    """
    Árvore hierárquica de categorias -> subcategorias -> patterns
    """
    def __init__(self, catalog: PatternCatalog, definitions_csv_path: str):
        self.catalog = catalog
        self.categories: List[str] = []
        self.subcategories: List[str] = []
        self.category_definitions: Dict[str, str] = {}
        self.subcategory_definitions: Dict[str, str] = {}
        self.category_to_subcategories: Dict[str, List[str]] = defaultdict(list)
        self.subcategory_to_patterns: Dict[str, List[str]] = defaultdict(list)
        self.patterns_by_category: Dict[str, List[str]] = defaultdict(list)
        
        # Carregar definições
        defs = read_csv_dicts(definitions_csv_path)
        for row in defs:
            level = row["level"]
            name = row["name"].strip()
            definition = row["definition"].strip()
            parent = row.get("parent", "").strip()
            
            if level == "category":
                self.categories.append(name)
                self.category_definitions[name] = definition
            elif level == "subcategory":
                self.subcategories.append(name)
                self.subcategory_definitions[name] = definition
                if parent:
                    self.category_to_subcategories[parent].append(name)
        
        # Mapear patterns para subcategorias e categorias
        for pattern_name, info in catalog.by_name.items():
            cat = info["category"]
            subcat = info["subcategory"]
            
            if subcat:
                self.subcategory_to_patterns[subcat].append(pattern_name)
            else:
                # Pattern diretamente na categoria (sem subcategoria)
                self.patterns_by_category[cat].append(pattern_name)
    
    def subcategories_in_categories(self, categories: List[str]) -> List[str]:
        """Retorna subcategorias que pertencem às categorias gateadas"""
        result = []
        for cat in categories:
            result.extend(self.category_to_subcategories.get(cat, []))
        return result
    
    def patterns_in_subcategories(self, subcategories: List[str]) -> List[str]:
        """Retorna patterns que pertencem às subcategorias gateadas"""
        result = []
        for subcat in subcategories:
            result.extend(self.subcategory_to_patterns.get(subcat, []))
        return result
    
    def patterns_in_categories(self, categories: List[str]) -> List[str]:
        """Retorna patterns diretamente nas categorias (sem subcategoria)"""
        result = []
        for cat in categories:
            result.extend(self.patterns_by_category.get(cat, []))
        return result
    
    def call1_category_catalog_text(self) -> str:
        """Formata catálogo de categorias para Call 1"""
        lines = []
        for cat in self.categories:
            definition = self.category_definitions.get(cat, "")
            lines.append(f"- {cat}: {definition}")
        return "\n".join(lines)
    
    def call2_subcategory_catalog_text(self, categories: List[str]) -> str:
        """Formata catálogo de subcategorias gateadas para Call 2"""
        blocks = []
        for cat in categories:
            blocks.append(f"CATEGORY: {cat}")
            subcats = self.category_to_subcategories.get(cat, [])
            if not subcats:
                blocks.append("  (No subcategories)")
            else:
                for subcat in subcats:
                    definition = self.subcategory_definitions.get(subcat, "")
                    blocks.append(f"  - {subcat}: {definition}")
            blocks.append("")
        return "\n".join(blocks).rstrip()
    
    def call3_pattern_catalog_text(self, subcategories: List[str]) -> str:
        """Formata catálogo de patterns gateados para Call 3"""
        blocks = []
        for subcat in subcategories:
            blocks.append(f"SUBCATEGORY: {subcat}")
            patterns = self.subcategory_to_patterns.get(subcat, [])
            if not patterns:
                blocks.append("  (No patterns)")
            else:
                for name in patterns:
                    desc = self.catalog.by_name[name]["description"]
                    blocks.append(f"  - {name}: {desc}")
            blocks.append("")
        return "\n".join(blocks).rstrip()
    
    def call3_pattern_catalog_from_categories_text(
        self,
        categories: List[str],
    ) -> str:
        """Formata patterns diretamente de categorias (sem subcategorias)"""
        blocks = []
        for cat in categories:
            blocks.append(f"CATEGORY: {cat}")
            patterns = self.patterns_by_category.get(cat, [])
            if not patterns:
                blocks.append("  (No patterns in this category)")
            else:
                for name in patterns:
                    desc = self.catalog.by_name[name]["description"]
                    blocks.append(f"  - {name}: {desc}")
            blocks.append("")
        return "\n".join(blocks).rstrip()


# ═══════════════════════════════════════════════════════════════════════════
# 7. ANÁLISE E VALIDAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

def annotate_false_friends(prepared: PreparedIssue, call_result: Dict[str, Any]) -> None:
    """
    Detecta false friends (termos que aparecem no texto mas com outro significado)
    
    Args:
        prepared: Issue preparada
        call_result: Resultado da chamada (modificado in-place)
    """
    text_lower = prepared.artifact_text.lower()
    
    # Padrões conhecidos de false friends
    false_friend_patterns = [
        (r"\boracle\s+database\b", "Oracle"),
        (r"\bnginx\s+reverse\s+proxy\b", "Proxy"),
        (r"\brelay\s+chain\b", "Relay"),
        (r"\btest\s+snapshot\b", "Snapshotting"),
    ]
    
    for candidate in call_result.get("candidates", []):
        pattern = candidate["pattern"]
        for regex, friend_pattern in false_friend_patterns:
            if friend_pattern.lower() in pattern.lower():
                if re.search(regex, text_lower):
                    candidate["false_friend_detected"] = "yes"
                    break
