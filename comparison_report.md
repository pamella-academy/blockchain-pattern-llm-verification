# 📊 Comparação: Novo Pipeline vs. Original

## Resumo Executivo

**Dataset analisado:** Primeiras 70 issues de `web3_all_issues.csv`

### Novo Pipeline (Hierárquico com `evidence_mechanism`)
- ✅ **3 issues** com patterns identificados (4.3%)
- ⊗ **62 issues** com early stop (88.6%)
- 📝 **6 pattern candidates** no total

### Original (`issue_results.xlsx`)
- Dos 3 casos encontrados pelo novo pipeline:
  - **1 caso** tinha pattern diferente no original
  - **2 casos** não tinham patterns no original

---

## 🔍 Análise Caso a Caso

### CASO 1: graphprotocol/graph-node#3373

| Aspecto | Novo Pipeline | Original |
|---------|---------------|----------|
| **Patterns** | 4x **X-confirmation** | 1x **Reverse Oracle** |
| **Confiança** | High | N/A |
| **Evidence mechanism** | ✅ "Checked task item in PR description" | ❌ Não tinha |
| **Relevant to study** | - | "llm: no; A1: yes" |
| **Stage1 candidates** | 4 | 1 |

**🚨 DIVERGÊNCIA:** O novo pipeline identificou **X-confirmation** (checklist items), mas o original identificou **Reverse Oracle** (oracle pattern). São patterns completamente diferentes!

---

### CASO 2: MoralisWeb3/react-moralis#142

| Aspecto | Novo Pipeline | Original |
|---------|---------------|----------|
| **Patterns** | 1x **Dual Resolution** | ❌ Nenhum |
| **Confiança** | High | - |
| **Evidence mechanism** | ✅ "Provides both forward resolution from a domain name to an address/data and reverse resolution from an address back to a domain name." | ❌ Não tinha |
| **Relevant to study** | - | "llm: no; A1: no" |
| **Stage1 candidates** | 1 | 1 (mas não passou Stage2) |

**✅ NOVO ACHADO:** O novo pipeline encontrou **Dual Resolution** (ENS domain resolution) que o original não detectou!

**Evidence text:** "resolve or reverse resolve `.eth` address to ethereum address, text records..."

---

### CASO 3: Uniswap/web3-react#104

| Aspecto | Novo Pipeline | Original |
|---------|---------------|----------|
| **Patterns** | 1x **X-confirmation** | ❌ Nenhum |
| **Confiança** | High | - |
| **Evidence mechanism** | ✅ "The code listens for the transaction confirmation event and waits for a block confirmation before treating the smart contract call as successful." | ❌ Não tinha |
| **Relevant to study** | - | "llm: no; A1: no" |
| **Stage1 candidates** | 1 | 0 |

**✅ NOVO ACHADO:** O novo pipeline encontrou **X-confirmation** que o original não detectou!

**Evidence text:** "and dispatch success(after 1 confirmation) or error"

---

## 🎯 Insights Principais

### 1. **Campo `evidence_mechanism` está funcionando!** ✅
Todos os 3 casos têm `evidence_mechanism` preenchido com descrições específicas e relevantes do mecanismo discutido.

### 2. **Divergência no CASO 1** 🚨
- **Novo:** 4x X-confirmation (checklist de tasks concluídos)
- **Original:** 1x Reverse Oracle
- **Possível causa:** O novo pipeline está detectando checklist items `[x]` como "confirmations", mas isso pode ser um **false positive** (X-confirmation é sobre blockchain confirmations, não checkbox confirmations).

### 3. **Novos achados nos CASOS 2 e 3** ✅
O novo pipeline encontrou patterns legítimos que o original não detectou:
- **Dual Resolution** em MoralisWeb3/react-moralis#142 (ENS naming)
- **X-confirmation** em Uniswap/web3-react#104 (transaction confirmations)

### 4. **Early stopping economiza custos** 💰
88.6% das issues pararam no Call 1, evitando ~66% das chamadas de API.

---

## ⚠️ Problemas Identificados

### 1. **False Positive: X-confirmation no CASO 1**
O pattern "X-confirmation" está sendo ativado por checklist items `[x]` em PR descriptions, mas deveria detectar apenas **blockchain transaction confirmations**.

**Recomendação:** Ajustar o prompt do X-confirmation para diferenciar:
- ✅ Blockchain confirmations (número de blocos)
- ❌ Checklist confirmations (tasks concluídos)

### 2. **Recall ainda baixo (4.3%)**
Apenas 3 em 70 issues tiveram patterns identificados. Possíveis causas:
- Dataset realmente tem poucos patterns
- Prompts muito conservadores
- Early stopping muito agressivo no Call 1

---

## 📈 Métricas Comparativas

| Métrica | Novo Pipeline (70 issues) | Original (70 issues) |
|---------|---------------------------|----------------------|
| Issues com patterns | 3 (4.3%) | ? (precisa filtrar) |
| Pattern candidates | 6 | ? |
| Early stops | 62 (88.6%) | N/A |
| Issues processadas | 70 | 70 |

---

## 🔄 Próximas Ações Sugeridas

1. **Refinar prompt de X-confirmation** para evitar false positives com checklist items
2. **Validar manualmente** os 3 casos para confirmar se os patterns estão corretos
3. **Comparar recall completo** entre novo e original pipeline (processar todas as 200 issues)
4. **Analisar os 62 early stops** para ver se realmente não têm patterns relevantes

---

**Data:** 2026-09-18  
**Pipeline:** `classify.py` (hierárquico com `evidence_mechanism`)  
**Model:** gemini-3.6-flash, temperature=0.3  
