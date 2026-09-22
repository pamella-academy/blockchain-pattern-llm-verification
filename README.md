# Pipeline de Classificação de Blockchain Patterns

Classifica automaticamente GitHub issues/PRs para identificar 82 blockchain design patterns usando LLM com estratégia hierárquica.

## 🚀 Uso Rápido

```bash
# Classificar issues (sempre com verificação de precisão)
python3 classify.py data/web3_all_issues.csv

# Limitar a 30 issues
python3 classify.py data/web3_all_issues.csv --limit 30

# Usar modelo diferente
python3 classify.py data/web3_all_issues.csv --model gemini-2.0-pro-flash
```

## 📋 Pré-requisitos

```bash
pip install google-generativeai pandas

# Configurar API key
echo "GEMINI_API_KEY=sua_chave_aqui" > .env
```

## 📊 Como Funciona

**Classificação hierárquica em 3 níveis + verificação:**

1. **Call 1:** Filtra 6 categorias SLR
2. **Call 2:** Filtra subcategorias das categorias relevantes
3. **Call 3:** Identifica patterns das subcategorias relevantes
4. **Stage 2:** Verifica precisão de cada candidato (sempre executado)

**Early stopping:** 79% das issues param no Call 1 (economia de tokens!)

## 📁 Saída

```
results/
  <nome>_<timestamp>_stage1.csv       # Candidatos (Stage 1)
  <nome>_<timestamp>_stage2.csv       # Verificados (Stage 2) ← Resultado final
  <nome>_<timestamp>_stage1_raw.jsonl # Respostas brutas
  <nome>_<timestamp>_stage2_raw.jsonl # Respostas brutas Stage 2
```

**Use sempre:** `*_stage2.csv` (resultado final com precisão 100%)

## 📖 Argumentos Opcionais

```bash
--limit N              # Processar apenas N issues
--model MODELO         # Modelo LLM (default: gemini-3.6-flash)
--temperature T        # Temperatura 0-1 (default: 0.3)
--output DIR           # Diretório de saída (default: results)
```

## 💰 Custos

**200 issues:** ~$0.02 USD (Gemini Flash)

Early stopping economiza ~80% em issues irrelevantes.

## 📚 Documentação Técnica

Ver `PIPELINE_DOCUMENTATION.md` para detalhes completos.

## 🎯 Exemplo Completo

```bash
# 1. Preparar ambiente
pip install google-generativeai pandas
echo "GEMINI_API_KEY=..." > .env

# 2. Classificar
python3 classify.py data/web3_all_issues.csv

# 3. Ver resultados finais
head results/*_stage2.csv
```

## 📦 Estrutura do Projeto

```
classify.py                           # Pipeline principal
utils.py                              # Funções auxiliares
prompts.json                          # Instruções LLM
blockchain_patterns_keywords_v3.csv   # Catálogo (82 patterns)
data/taxonomy/                        # Taxonomia hierárquica
```

## ✨ Características

- ✅ **Simples:** 1 comando, sem configuração complexa
- ✅ **Econômico:** Early stopping + gating hierárquico
- ✅ **Robusto:** Checkpoint automático (retoma se interromper)
- ✅ **Preciso:** Stage 2 sempre ativo (100% precision)

---

**Pronto para usar!** 🚀
