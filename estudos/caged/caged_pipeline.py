#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataMind — Pipeline CAGED v2: base permanente de sazonalidade e termômetro de mercado (SP)
Fonte: Novo CAGED/MTE — microdados de movimentação (FTP PDET)
Período: jan/2023 em diante (40 meses até abr/2026; extensível conforme publicação)
Filtro base: UF=35 (SP). Vínculos "típicos" = exclui categoria 105 (temporário Lei 6.019),
106 (aprendiz), intermitentes, parciais e horas contratuais <= 30 (classificação MTE).
Senioridade: NÃO existe no CAGED — proxy declarado por faixa salarial em salários mínimos
(SM por ano: 2023=1320, 2024=1412, 2025=1518, 2026=1621).
Cesto TI/dados (proxy): famílias CBO 1425, 2123, 2124, 3171, 3172.

Saídas (modo job único, COMP=YYYYMM):
  parcial_resumo_YYYYMM.csv  — agregado mensal (compatível com v1)
  parcial_cnae_YYYYMM.csv    — mes x secao CNAE x tipico x movimento
  parcial_cbo4_YYYYMM.csv    — mes x familia CBO 4 dig. x movimento (so tipicos) + salario medio
  parcial_ti6_YYYYMM.csv     — universo TI: mes x CBO 6 dig. x faixa salarial x movimento
  parcial_tipomov_YYYYMM.csv — universo TI: mes x tipo de movimentacao
"""
import os, subprocess, sys, time, unicodedata
import pandas as pd

FTP_BASE = "ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED"
CBO_TI_PREFIX = ("1425", "2123", "2124", "3171", "3172")
SM = {2023: 1320.0, 2024: 1412.0, 2025: 1518.0, 2026: 1621.0}
MONTHS = [(y, m) for y in (2023, 2024, 2025) for m in range(1, 13)] + \
         [(2026, m) for m in range(1, 5)]

def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s).strip().lower())
                   if unicodedata.category(c) != "Mn")

USECOLS = {"uf", "saldomovimentacao", "cbo2002ocupacao", "categoria",
           "horascontratuais", "indtrabintermitente", "indtrabparcial",
           "indicadoraprendiz", "secao", "salario", "tipomovimentacao"}

def download(y, m):
    name = f"CAGEDMOV{y}{m:02d}"
    url = f"{FTP_BASE}/{y}/{y}{m:02d}/{name}.7z"
    for attempt in range(4):
        r = subprocess.run(["curl", "-sS", "--retry", "3", "--max-time", "900",
                            "-o", f"{name}.7z", url])
        if r.returncode == 0 and os.path.exists(f"{name}.7z") and os.path.getsize(f"{name}.7z") > 1_000_000:
            return name
        time.sleep(20 * (attempt + 1))
    raise RuntimeError(f"download falhou: {url}")

def faixa_sm(salario, y):
    sm = SM[y]
    if salario != salario:  # NaN
        return "sem_info"
    r = salario / sm
    if r <= 3: return "ate_3SM"
    if r <= 6: return "3_a_6SM"
    if r <= 10: return "6_a_10SM"
    return "acima_10SM"

def process(y, m):
    name = download(y, m)
    subprocess.run(["7z", "x", "-y", f"{name}.7z"], check=True, stdout=subprocess.DEVNULL)
    txt = f"{name}.txt"
    with open(txt, "rb") as f:
        head = f.read(2048)
    enc = "utf-8" if b"\xc3" in head or head[:3] == b"\xef\xbb\xbf" else "latin-1"
    print("encoding detectado:", enc, flush=True)

    resumo = {"ano": y, "mes": m, "adm_total": 0, "adm_tipica": 0,
              "deslig_total": 0, "deslig_tipico": 0,
              "adm_tipica_ti": 0, "deslig_tipico_ti": 0}
    acc_cnae, acc_cbo4, acc_ti6, acc_tipo = {}, {}, {}, {}

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
        sp["tipico"] = (~cat.isin([105, 106])
                        & (pd.to_numeric(sp["indtrabintermitente"], errors="coerce").fillna(0) != 1)
                        & (pd.to_numeric(sp["indtrabparcial"], errors="coerce").fillna(0) != 1)
                        & (pd.to_numeric(sp["indicadoraprendiz"], errors="coerce").fillna(0) != 1)
                        & (hc > 30))
        sp["cbo"] = sp["cbo2002ocupacao"].astype(str).str.strip()
        sp["ti"] = sp["cbo"].str.startswith(CBO_TI_PREFIX)
        sp["sal"] = pd.to_numeric(sp["salario"], errors="coerce")

        # resumo (compatível v1)
        for mov, t, ti in [("adm", False, False)]:
            pass
        resumo["adm_total"] += int((sp["mov"] == "adm").sum())
        resumo["deslig_total"] += int((sp["mov"] == "deslig").sum())
        resumo["adm_tipica"] += int(((sp["mov"] == "adm") & sp["tipico"]).sum())
        resumo["deslig_tipico"] += int(((sp["mov"] == "deslig") & sp["tipico"]).sum())
        resumo["adm_tipica_ti"] += int(((sp["mov"] == "adm") & sp["tipico"] & sp["ti"]).sum())
        resumo["deslig_tipico_ti"] += int(((sp["mov"] == "deslig") & sp["tipico"] & sp["ti"]).sum())

        # 1) mes x secao CNAE x tipico x movimento
        g = sp.groupby([sp["secao"].astype(str).str.strip(), "tipico", "mov"]).size()
        for k, v in g.items():
            acc_cnae[k] = acc_cnae.get(k, 0) + int(v)

        # 2) mes x familia CBO4 x movimento (tipicos) + soma salarial de admissao
        tp = sp[sp["tipico"]]
        g = tp.groupby([tp["cbo"].str[:4], "mov"]).agg(n=("cbo", "size"), sal_sum=("sal", "sum"), sal_n=("sal", "count"))
        for k, row in g.iterrows():
            cur = acc_cbo4.get(k, [0, 0.0, 0])
            acc_cbo4[k] = [cur[0] + int(row["n"]), cur[1] + float(row["sal_sum"] or 0), cur[2] + int(row["sal_n"])]

        # 3) universo TI tipico: mes x CBO6 x faixa SM x movimento
        ti = tp[tp["ti"]].copy()
        if not ti.empty:
            ti["faixa"] = ti["sal"].map(lambda s: faixa_sm(s, y))
            g = ti.groupby(["cbo", "faixa", "mov"]).agg(n=("cbo", "size"), sal_sum=("sal", "sum"), sal_n=("sal", "count"))
            for k, row in g.iterrows():
                cur = acc_ti6.get(k, [0, 0.0, 0])
                acc_ti6[k] = [cur[0] + int(row["n"]), cur[1] + float(row["sal_sum"] or 0), cur[2] + int(row["sal_n"])]
            # 4) tipo de movimentacao no universo TI
            g = ti.groupby([ti["tipomovimentacao"].astype(str).str.strip(), "mov"]).size()
            for k, v in g.items():
                acc_tipo[k] = acc_tipo.get(k, 0) + int(v)

    os.remove(f"{name}.7z"); os.remove(txt)
    comp = f"{y}{m:02d}"
    pd.DataFrame([resumo]).to_csv(f"parcial_resumo_{comp}.csv", index=False)
    pd.DataFrame([{"ano": y, "mes": m, "secao": k[0], "tipico": k[1], "mov": k[2], "n": v}
                  for k, v in acc_cnae.items()]).to_csv(f"parcial_cnae_{comp}.csv", index=False)
    pd.DataFrame([{"ano": y, "mes": m, "cbo4": k[0], "mov": k[1], "n": v[0],
                   "sal_medio": round(v[1] / v[2], 2) if v[2] else None}
                  for k, v in acc_cbo4.items()]).to_csv(f"parcial_cbo4_{comp}.csv", index=False)
    pd.DataFrame([{"ano": y, "mes": m, "cbo6": k[0], "faixa_sm": k[1], "mov": k[2], "n": v[0],
                   "sal_medio": round(v[1] / v[2], 2) if v[2] else None}
                  for k, v in acc_ti6.items()]).to_csv(f"parcial_ti6_{comp}.csv", index=False)
    pd.DataFrame([{"ano": y, "mes": m, "tipomovimentacao": k[0], "mov": k[1], "n": v}
                  for k, v in acc_tipo.items()]).to_csv(f"parcial_tipomov_{comp}.csv", index=False)
    print(f"OK {comp}: resumo + 4 tabelas", flush=True)

def main():
    comp = os.environ.get("COMP")
    if comp:
        y, m = int(comp[:4]), int(comp[4:])
        process(y, m)
        return 0
    for y, m in MONTHS:
        try:
            process(y, m)
        except RuntimeError as e:
            print(f"FTP indisponível ({e}); encerrando para retomada.", flush=True)
            break
    return 0

if __name__ == "__main__":
    sys.exit(main())
