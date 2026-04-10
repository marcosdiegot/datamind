# CLAUDE.md — DataMind

> Arquivo de contexto permanente para o Claude Code.
> Leia este arquivo inteiro antes de executar qualquer tarefa neste repositório.

---

## Identidade do Projeto

**Repositório:** `marcosdiegot/datamind`
**URL:** https://marcosdiegot.github.io/datamind
**Produto principal:** DataMind AI Radar — dashboard de market intelligence em HTML puro (6 abas)
**Proprietário:** Marcos Diego Ribeiro — Founder & Head of Data, DataMind
**Stack de deploy:** GitHub Pages via REST API (sem CI/CD externo)

---

## Estrutura do Repositório

```
datamind/
├── radar.html          # Dashboard principal — 6 abas de market intelligence
├── index.html          # Hub do portfólio DataMind
├── assets/             # CSS, imagens, ícones
└── CLAUDE.md           # Este arquivo
```

---

## Regras Críticas — Leia Antes de Editar

### 1. Parser HTML — Caracteres Proibidos em JS
O parser do GitHub Pages quebra silenciosamente com `<` e `>` dentro de string literals JavaScript.

**SEMPRE use:**
- `\u003C` no lugar de `<`
- `\u003E` no lugar de `>`

Exemplo correto:
```js
const tag = '\u003Cdiv class="card"\u003E';
```

Nunca use:
```js
const tag = '<div class="card">';  // QUEBRA O PARSER
```

### 2. Deploy via GitHub REST API
Este repositório não usa `git push` local. Todo deploy é feito via REST API com SHA-chaining.

**Fluxo obrigatório:**
1. GET no arquivo atual para obter o SHA mais recente
2. Encode o novo conteúdo em Base64
3. PUT com `{ message, content, sha }` no endpoint correto

**Token:** `[TOKEN_GITHUB]`
**SHA de backup estável:** `8e20a69dbcccf9bc4fdb29923074e9ebc9b14571`

Se o SHA estiver desatualizado, o PUT retorna 409. Sempre busque o SHA atual antes de qualquer push.

### 3. Nunca Editar Estrutura sem Aprovação
Não adicione, remova ou renomeie abas, seções ou arquivos sem instrução explícita do Diego.
Alterações de conteúdo dentro de estruturas existentes são permitidas.

---

## Radar — Arquitetura das Abas

| Aba | ID | Descrição |
|-----|----|-----------|
| Feed | `#feed` | Atualizações de mercado IA — EM ALTA / EM BAIXA / MOVIMENTOS / NO RADAR |
| Squad | `#squad` | Ferramentas do AI Squad com hierarquia e casos de uso |
| Custos | `#custos` | Simulador por Segmento × Porte × Stack (redesign aprovado, pendente conteúdo) |
| Governança | `#governanca` | Gerador de política de IA por setor |
| Radar Setorial | `#setorial` | Inteligência por vertical de mercado |
| Sobre | `#sobre` | Contexto DataMind e metodologia |

---

## Identidade Visual

```
Background:     #07080D
EM ALTA:        #00E5A0
EM BAIXA:       #FF3D5A
MOVIMENTOS:     #FFB830
NO RADAR:       #4F8EF7
Cards:          liquid glass (backdrop-filter: blur)
```

Nunca alterar estas cores sem instrução explícita.

---

## Fluxo de Trabalho Padrão

### Edição do Radar HTML
1. Leia o `radar.html` completo antes de qualquer edição
2. Identifique a aba/seção alvo
3. Aplique a alteração respeitando as regras de parser
4. Valide que nenhum `<` ou `>` solto existe em strings JS
5. Encode em Base64 e faça o PUT via REST API

### Scripts GitHub REST API
- Sempre use o endpoint: `https://api.github.com/repos/marcosdiegot/datamind/contents/{path}`
- Header obrigatório: `Authorization: token [TOKEN_GITHUB]`
- Nunca faça PUT sem GET prévio para capturar o SHA

### Automações n8n
- Arquivos de workflow ficam em `/n8n/` (criar se não existir)
- Sempre exportar como JSON antes de editar
- Nunca modificar credenciais — deixar placeholder `{{CREDENTIAL}}`

---

## Comportamento Esperado do Claude Code

- **Executor, não decisor.** Todas as decisões editoriais, estruturais e de processo são do Diego.
- **Sem substituições.** Nunca trocar uma abordagem por outra sem aprovação explícita.
- **Sem avanços automáticos.** Concluída uma tarefa, pare e aguarde instrução.
- **3 tentativas.** Se após 3 tentativas uma entrega falhar, pare, diagnostique e proponha mudança de abordagem.
- **Entregas copy-paste ready.** Código, scripts e conteúdo sempre prontos para uso direto.
- **Sem elogio, sem filler.** Respostas diretas, sem "ótima pergunta" ou validações desnecessárias.

---

## Contexto de Negócio

**DataMind** é uma consultoria AI-First baseada em Osasco, SP.
Filosofia central: IA de resultado exige fundação de dados correta primeiro — "IA de vitrine" falha porque a camada de dados está quebrada.

O Radar é o principal artefato de demonstração da metodologia DataMind e é atualizado periodicamente via AI Squad (Perplexity, Grok, GPT-4o, Gemini).

---

## Contato / Referências

- **LinkedIn:** https://www.linkedin.com/in/marcos-diego-ribeiro-b89a8352
- **Portfolio:** https://marcosdiegot.github.io/datamind
- **Radar:** https://marcosdiegot.github.io/datamind/radar.html
