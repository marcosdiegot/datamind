#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataMind — Estudo de sazonalidade de contratações efetivas (SP)
Fonte: Novo CAGED / MTE — microdados de movimentação (FTP PDET)
Período: 2023-01 a 2025-12 (36 meses)
Filtros:
  - UF = 35 (São Paulo)
  - Admissões: saldomovimentacao == 1 | Desligamentos: == -1
  - "Típicos" (aprox. definição MTE): exclui categoria 105 (temporário Lei 6.019),
    106 (aprendiz), intermitentes, parciais e horas contratuais <= 30
  - Cesto TI/dados (proxy CBO 2002): famílias 1425, 2123, 2124, 3171, 3172
Saída: estudos/caged/resultado_sazonalidade_sp.csv (agregado mensal)
"""
import os, subprocess, sys, time
import pandas as pd

FTP_BASE = "ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED"
OUT = "estudos/caged/resultado_sazonalidade_sp.csv"
CBO_TI_PREFIX = ("1425", "2123", "2124", "3171", "3172")
MONTHS = [(y, m) for y in (2023, 2024, 2025) for m in range(1, 13)]

import unicodedata
def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s).strip().lower())
                   if unicodedata.category(c) != "Mn")

USECOLS = {"uf", "saldomovimentacao", "cbo2002ocupacao", "categoria",
           "horascontratuais", "indtrabintermitente", "indtrabparcial",
           "indicadoraprendiz"}

def download(y, m):
    name = f"CAGEDMOV{y}{m:02d}"
    url = f"{FTP_BASE}/{y}/{y}{m:02d}/{name}.7z"
    for attempt in range(4):
        r = subprocess.run(["curl", "-sS", "--retry", "5", "--retry-all-errors", "--max-time", "600",
                            "--speed-limit", "50000", "--speed-time", "60",
                            "--ftp-method", "nocwd", "-o", f"{name}.7z", url])
        if r.returncode == 0 and os.path.getsize(f"{name}.7z") > 1_000_000:
            return name
        time.sleep(20 * (attempt + 1))
    raise RuntimeError(f"download falhou: {url}")

def process(y, m):
    name = download(y, m)
    subprocess.run(["7z", "x", "-y", f"{name}.7z"], check=True,
                   stdout=subprocess.DEVNULL)
    txt = f"{name}.txt"
    rows = {"ano": y, "mes": m, "adm_total": 0, "deslig_total": 0,
            "adm_tipica": 0, "deslig_tipico": 0,
            "adm_tipica_ti": 0, "deslig_tipico_ti": 0}
    first = True
    for chunk in pd.read_csv(txt, sep=";", encoding="latin-1", decimal=",",
                             usecols=lambda c: norm(c) in USECOLS,
                             chunksize=500_000, low_memory=True):
        chunk.columns = [norm(c) for c in chunk.columns]
        if first:
            print("colunas selecionadas:", list(chunk.columns), flush=True)
            first = False
        sp = chunk[pd.to_numeric(chunk["uf"], errors="coerce") == 35]
        if sp.empty:
            continue
        saldo = pd.to_numeric(sp["saldomovimentacao"], errors="coerce")
        adm = saldo == 1
        des = saldo == -1
        hc = pd.to_numeric(sp["horascontratuais"], errors="coerce").fillna(44)
        cat = pd.to_numeric(sp["categoria"], errors="coerce")
        tipico = (~cat.isin([105, 106])
                  & (pd.to_numeric(sp["indtrabintermitente"], errors="coerce").fillna(0) != 1)
                  & (pd.to_numeric(sp["indtrabparcial"], errors="coerce").fillna(0) != 1)
                  & (pd.to_numeric(sp["indicadoraprendiz"], errors="coerce").fillna(0) != 1)
                  & (hc > 30))
        cbo = sp["cbo2002ocupacao"].astype(str).str.strip()
        ti = cbo.str.startswith(CBO_TI_PREFIX)
        rows["adm_total"] += int(adm.sum())
        rows["deslig_total"] += int(des.sum())
        rows["adm_tipica"] += int((adm & tipico).sum())
        rows["deslig_tipico"] += int((des & tipico).sum())
        rows["adm_tipica_ti"] += int((adm & tipico & ti).sum())
        rows["deslig_tipico_ti"] += int((des & tipico & ti).sum())
    os.remove(f"{name}.7z"); os.remove(txt)
    return rows

def main():
    comp = os.environ.get("COMP")  # modo job único: YYYYMM
    if comp:
        y, m = int(comp[:4]), int(comp[4:])
        print(f"Processando {y}-{m:02d}...", flush=True)
        pd.DataFrame([process(y, m)]).to_csv(f"parcial_{comp}.csv", index=False)
        print("Concluído.")
        return
    os.makedirs("estudos/caged", exist_ok=True)
    results = []
    if os.path.exists(OUT):
        results = pd.read_csv(OUT).to_dict("records")
    done = {(r["ano"], r["mes"]) for r in results}
    for y, m in MONTHS:
        if (y, m) in done:
            continue
        print(f"Processando {y}-{m:02d}...", flush=True)
        results.append(process(y, m))
        pd.DataFrame(results).to_csv(OUT, index=False)
    print("Concluído.")

if __name__ == "__main__":
    sys.exit(main())
