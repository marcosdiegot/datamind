name: CAGED Extra (porte + demografia)

on:
  workflow_dispatch:
    inputs:
      comp:
        description: "Mês único AAAAMM para teste rápido (vazio = roda todos os 40 meses)"
        required: false
        default: ""

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 360
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Instalar dependências
        run: |
          sudo apt-get update && sudo apt-get install -y p7zip-full
          pip install pandas

      - name: Rodar pipeline extra
        env:
          COMP: ${{ github.event.inputs.comp }}
        run: python estudos/caged/caged_extra.py

      - name: Commitar tabelas
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add estudos/caged/base_dados_porte_sp.csv estudos/caged/base_dados_demog_sp.csv
          git commit -m "feat: tabelas porte+demografia (teste concentracao e convergencia)" || echo "nada a commitar"
          git push
