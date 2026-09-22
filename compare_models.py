#!/usr/bin/env python3
"""
Script de comparação entre resultados Gemini e Mistral

Compara:
- Número de candidatos encontrados
- Patterns identificados
- Precision (após Stage 2)
- Custos (tokens)
- Tempo de execução
"""

import pandas as pd
import sys
from pathlib import Path


def analyze_results(stage2_csv: str, provider: str) -> dict:
    """
    Analisa resultados de um provider
    
    Args:
        stage2_csv: CSV com resultados Stage 2
        provider: Nome do provider (Gemini/Mistral)
        
    Returns:
        Dicionário com métricas
    """
    df = pd.read_csv(stage2_csv)
    
    # Estatísticas gerais
    total_issues = len(df[df['pattern'] == ''].dropna()) + len(df[df['pattern'] != ''])
    
    # Filtrar apenas linhas com patterns
    with_patterns = df[df['pattern'] != '']
    
    # Candidatos Stage 1
    stage1_candidates = len(with_patterns)
    
    # Confirmados Stage 2
    confirmed = with_patterns[with_patterns['stage2_verdict'] == 'yes']
    rejected = with_patterns[with_patterns['stage2_verdict'] == 'no']
    
    # Patterns únicos
    unique_patterns = confirmed['pattern'].unique().tolist()
    
    # Tokens
    total_tokens = df['total_tokens'].sum() if 'total_tokens' in df.columns else 0
    
    # Custo estimado (Gemini Flash: $0.10/M input, $0.40/M output)
    # Mistral: varia por modelo
    if provider == "Gemini":
        cost = total_tokens / 1_000_000 * 0.10  # Estimativa conservadora
    else:
        cost = total_tokens / 1_000_000 * 0.15  # Estimativa Mistral
    
    return {
        "provider": provider,
        "total_issues": total_issues,
        "stage1_candidates": stage1_candidates,
        "stage2_confirmed": len(confirmed),
        "stage2_rejected": len(rejected),
        "precision": len(confirmed) / len(with_patterns) * 100 if len(with_patterns) > 0 else 0,
        "unique_patterns": unique_patterns,
        "total_tokens": total_tokens,
        "estimated_cost_usd": cost,
    }


def compare_results(gemini_csv: str, mistral_csv: str):
    """
    Compara resultados entre Gemini e Mistral
    
    Args:
        gemini_csv: CSV Stage 2 do Gemini
        mistral_csv: CSV Stage 2 do Mistral
    """
    print("=" * 80)
    print(" COMPARAÇÃO GEMINI vs MISTRAL - 200 ISSUES")
    print("=" * 80)
    
    # Analisar ambos
    gemini_metrics = analyze_results(gemini_csv, "Gemini")
    mistral_metrics = analyze_results(mistral_csv, "Mistral")
    
    # Tabela comparativa
    print("\n### MÉTRICAS GERAIS\n")
    print(f"{'Métrica':<30} {'Gemini':<20} {'Mistral':<20} {'Diferença':<20}")
    print("-" * 90)
    
    metrics_to_compare = [
        ("Issues processadas", "total_issues", ""),
        ("Candidatos Stage 1", "stage1_candidates", ""),
        ("Confirmados Stage 2", "stage2_confirmed", ""),
        ("Rejeitados Stage 2", "stage2_rejected", ""),
        ("Precision Stage 2 (%)", "precision", "%"),
        ("Total tokens", "total_tokens", ""),
        ("Custo estimado (USD)", "estimated_cost_usd", "$"),
    ]
    
    for label, key, suffix in metrics_to_compare:
        g_val = gemini_metrics[key]
        m_val = mistral_metrics[key]
        
        if suffix == "%":
            diff = f"{m_val - g_val:+.1f}%"
            print(f"{label:<30} {g_val:.1f}%{'':<13} {m_val:.1f}%{'':<13} {diff}")
        elif suffix == "$":
            diff = f"${m_val - g_val:+.2f}"
            print(f"{label:<30} ${g_val:.2f}{'':<15} ${m_val:.2f}{'':<15} {diff}")
        else:
            diff = f"{int(m_val - g_val):+d}" if isinstance(g_val, (int, float)) else ""
            print(f"{label:<30} {int(g_val) if isinstance(g_val, float) else g_val:<20} {int(m_val) if isinstance(m_val, float) else m_val:<20} {diff}")
    
    # Patterns únicos
    print("\n### PATTERNS IDENTIFICADOS\n")
    
    gemini_patterns = set(gemini_metrics["unique_patterns"])
    mistral_patterns = set(mistral_metrics["unique_patterns"])
    
    only_gemini = gemini_patterns - mistral_patterns
    only_mistral = mistral_patterns - gemini_patterns
    both = gemini_patterns & mistral_patterns
    
    print(f"✅ Encontrados por ambos: {len(both)}")
    for p in sorted(both):
        print(f"   - {p}")
    
    if only_gemini:
        print(f"\n🔵 Apenas Gemini: {len(only_gemini)}")
        for p in sorted(only_gemini):
            print(f"   - {p}")
    
    if only_mistral:
        print(f"\n🔴 Apenas Mistral: {len(only_mistral)}")
        for p in sorted(only_mistral):
            print(f"   - {p}")
    
    # Concordância
    print("\n### CONCORDÂNCIA\n")
    
    # Carregar DataFrames completos para comparação detalhada
    df_gemini = pd.read_csv(gemini_csv)
    df_mistral = pd.read_csv(mistral_csv)
    
    # Merge por issue_key
    df_gemini_patterns = df_gemini[df_gemini['pattern'] != ''][['issue_key', 'pattern', 'stage2_verdict']]
    df_mistral_patterns = df_mistral[df_mistral['pattern'] != ''][['issue_key', 'pattern', 'stage2_verdict']]
    
    # Comparar decisões
    merged = pd.merge(
        df_gemini_patterns,
        df_mistral_patterns,
        on=['issue_key', 'pattern'],
        how='outer',
        suffixes=('_gemini', '_mistral')
    )
    
    agree_yes = len(merged[
        (merged['stage2_verdict_gemini'] == 'yes') & 
        (merged['stage2_verdict_mistral'] == 'yes')
    ])
    agree_no = len(merged[
        (merged['stage2_verdict_gemini'] == 'no') & 
        (merged['stage2_verdict_mistral'] == 'no')
    ])
    disagree = len(merged) - agree_yes - agree_no
    
    print(f"Concordam (yes): {agree_yes}")
    print(f"Concordam (no): {agree_no}")
    print(f"Discordam: {disagree}")
    print(f"Taxa de concordância: {(agree_yes + agree_no) / len(merged) * 100:.1f}%")
    
    print("\n" + "=" * 80)
    print("✓ COMPARAÇÃO COMPLETA")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python compare_models.py <gemini_stage2.csv> <mistral_stage2.csv>")
        print("\nExemplo:")
        print("  python compare_models.py results/full_200_prod_stage2.csv results_mistral/web3_all_issues_<timestamp>_stage2.csv")
        sys.exit(1)
    
    gemini_csv = sys.argv[1]
    mistral_csv = sys.argv[2]
    
    if not Path(gemini_csv).exists():
        print(f"❌ Arquivo não encontrado: {gemini_csv}")
        sys.exit(1)
    
    if not Path(mistral_csv).exists():
        print(f"❌ Arquivo não encontrado: {mistral_csv}")
        sys.exit(1)
    
    compare_results(gemini_csv, mistral_csv)
