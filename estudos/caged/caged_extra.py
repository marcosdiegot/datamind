#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataMind — CAGED EXTRA: tabelas de porte e demografia para os testes do squad
(concentração HHI por porte + convergência demográfica TI->Financeiro).
Autocontido: NÃO altera o pipeline principal. Reusa a mesma fonte (FTP PDET),
os mesmos filtros (SP, vínculo típico) e a mesma cesta de DADOS.

Saídas (em estudos/caged/):
  base_dados_porte_sp.csv  — ano,mes,cbo6,secao,mov,porte,n,sal_medio   (cesta DADOS típica)
  base_dados_demog_sp.csv  — ano,mes,secao,mov,idade,grau,bin_sal,n     (apenas seções J e K)
"""
import os, subprocess, sys, time, unicodedata
import pandas as pd

FTP_BASE = "ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED"
CBO_DADOS_PREFIX = ("2112", "2122")
CBO_DADOS_CODES = ("212305", "212405", "212410", "212425", "203105")
MONTHS = [(y, m) for y in (2023, 2024, 2025) for m in range(1, 13)] + [(2026, m) for m in range(1, 5)]
OUTDIR = os.environ.get("OUTDIR", "estudos/caged")

def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s).strip().lower())
                   if unicodedata.category(c) != "Mn")

# colunas originais + as 3 novas (porte, idade, escolaridade)
USECOLS = {"uf", "saldomovimentacao", "cbo2002ocupacao", "categoria",
           "horascontratuais", "indtrabintermitente", "indtrabparcial",
           "indicadoraprendiz", "secao", "salario",
           "tamestabjan", "idade", "graudeinstrucao"}

def download(y, m):
    name = f"CAGEDMOV{y}{m:02d}"
    url = f"{FTP_BASE}/{y}/{y}{m:02d}/{name}.7z"
    for attempt in range(4):
        subprocess.run(["curl", "-sS", "--retry", "3", "--max-time", "900", "-o", f"{name}.7z", url])
        if os.path.exists(f"{name}.7z") and os.path.getsize(f"{name}.7z") > 1_000_000:
            return name
        time.sleep(20 * (attempt + 1))
    raise RuntimeError(f"download falhou: {url}")

def process(y, m, acc_porte, acc_demog):
    name = download(y, m)
    subprocess.run(["7z", "x", "-y", f"{name}.7z"], check=True, stdout=subprocess.DEVNULL)
    txt = f"{name}.txt"
    with open(txt, "rb") as f:
        head = f.read(2048)
    enc = "utf-8" if b"\xc3" in head or head[:3] == b"\xef\xbb\xbf" else "latin-1"

    for chunk in pd.read_csv(txt, sep=";", encoding=enc, decimal=",",
                             usecols=lambda c: norm(c) in USECOLS,
                             chunksize=500_000, low_memory=True):
        chunk.columns = [norm(c) for c in chunk.columns]
        sp = chunk[pd.to_numeric(chunk["uf"], errors="coerce") == 35].copy()
        if sp.empty:
            continue
        saldo = pd.to_numeric(sp["saldomovimentacao"], errors="coerce")
        sp["mov"] = saldo.map({1: "adm", -1: "deslig"})
        sp = sp[sp["mov"].notna()]
        hc = pd.to_numeric(sp["horascontratuais"], errors="coerce").fillna(44)
        cat = pd.to_numeric(sp["categoria"], errors="coerce")
        tipico = (~cat.isin([105, 106])
                  & (pd.to_numeric(sp["indtrabintermitente"], errors="coerce").fillna(0) != 1)
                  & (pd.to_numeric(sp["indtrabparcial"], errors="coerce").fillna(0) != 1)
                  & (pd.to_numeric(sp["indicadoraprendiz"], errors="coerce").fillna(0) != 1)
                  & (hc > 30))
        sp["cbo"] = sp["cbo2002ocupacao"].astype(str).str.strip()
        dados = sp["cbo"].str.startswith(CBO_DADOS_PREFIX) | sp["cbo"].isin(CBO_DADOS_CODES)
        dd = sp[tipico & dados].copy()
        if dd.empty:
            continue
        dd["sal"] = pd.to_numeric(dd["salario"], errors="coerce")
        dd["sec"] = dd["secao"].astype(str).str.strip()

        # ---- tabela PORTE (cesta dados típica) ----
        dd["porte"] = pd.to_numeric(dd["tamestabjan"], errors="coerce").fillna(-1).astype(int)
        g = dd.groupby(["cbo", "sec", "mov", "porte"]).agg(
            n=("cbo", "size"), ss=("sal", "sum"), sn=("sal", "count"))
        for k, row in g.iterrows():
            key = (y, m) + k
            cur = acc_porte.get(key, [0, 0.0, 0])
            acc_porte[key] = [cur[0] + int(row["n"]), cur[1] + float(row["ss"] or 0), cur[2] + int(row["sn"])]

        # ---- tabela DEMOGRAFIA (apenas J e K) ----
        jk = dd[dd["sec"].isin(["J", "K"])].copy()
        if not jk.empty:
            jk["idade"] = pd.to_numeric(jk["idade"], errors="coerce").fillna(-1).astype(int)
            jk["grau"] = pd.to_numeric(jk["graudeinstrucao"], errors="coerce").fillna(-1).astype(int)
            jk["bin_sal"] = (jk["sal"].clip(upper=50_000) // 500 * 500).where(jk["sal"].notna(), -1).astype(int)
            g = jk.groupby(["cbo", "sec", "mov", "idade", "grau", "bin_sal"]).size()
            for k, v in g.items():
                key = (y, m) + tuple(k)
                acc_demog[key] = acc_demog.get(key, 0) + int(v)

    os.remove(f"{name}.7z"); os.remove(txt)
    print(f"OK {y}{m:02d}", flush=True)

def main():
    os.makedirs(OUTDIR, exist_ok=True)
    acc_porte, acc_demog, falhas = {}, {}, []
    comp = os.environ.get("COMP")
    months = [(int(comp[:4]), int(comp[4:]))] if comp else MONTHS
    for y, m in months:
        try:
            process(y, m, acc_porte, acc_demog)
        except Exception as e:
            print(f"FALHA {y}{m:02d}: {e}", flush=True)
            falhas.append(f"{y}{m:02d}")

    pd.DataFrame([{"ano": k[0], "mes": k[1], "cbo6": k[2], "secao": k[3], "mov": k[4],
                   "porte": k[5], "n": v[0], "sal_medio": round(v[1] / v[2], 2) if v[2] else None}
                  for k, v in acc_porte.items()]).to_csv(f"{OUTDIR}/base_dados_porte_sp.csv", index=False)
    pd.DataFrame([{"ano": k[0], "mes": k[1], "cbo6": k[2], "secao": k[3], "mov": k[4], "idade": k[5],
                   "grau": k[6], "bin_sal": k[7], "n": v}
                  for k, v in acc_demog.items()]).to_csv(f"{OUTDIR}/base_dados_demog_sp.csv", index=False)
    # diagnóstico do código de porte (para auditoria do dicionário)
    dp = {}
    for k, v in acc_porte.items():
        dp[k[5]] = dp.get(k[5], 0) + v[0]
    print("DISTRIBUIÇÃO tamestabjan (confira contra o dicionário oficial do Novo CAGED):", dict(sorted(dp.items())), flush=True)
    print(f"CONCLUÍDO. Falhas: {falhas or 'nenhuma'}", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
