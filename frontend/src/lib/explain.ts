/**
 * Dicionário central da "base de montagem" de cada número do portal.
 * Texto fiel ao que o backend realmente calcula (ver app/sync/portfolio.py,
 * intelligence/scoring.py, alerts.py, messages.py e main.py).
 */
export const EXPLAIN: Record<string, string> = {
  // ---- agregados do cliente ----
  revenue_12m:
    "Soma do valor de todos os pedidos (Orders) do cliente no histórico sincronizado do Ploomes (janela de ~18 meses).",
  orders_12m:
    "Quantidade de pedidos do cliente no histórico sincronizado (~18 meses).",
  days_without_purchase:
    "Dias desde a última compra. Calculado pela data do último pedido real; se não houver, usa o campo 'Dias sem compra' do Sankhya.",
  buy_frequency_days:
    "Cadência real de compra: mediana dos intervalos entre pedidos. Calculada pelo portal (precisa de ≥3 compras), pois o campo de frequência do Sankhya quase nunca vem preenchido.",
  open_quotes:
    "Cotações (Quotes) do cliente em aberto — status da nota diferente de Faturado/Cancelado/Concluído. Lido do Ploomes.",
  open_quotes_value:
    "Soma do valor das cotações em aberto do cliente (status ≠ Faturado/Cancelado). Lido do Ploomes.",
  open_deals_value:
    "Soma do valor dos negócios (Deals) em aberto no funil (StatusId = aberto).",
  priority_score:
    "Pontuação 0–100 de prioridade. Combina: recência vs. frequência (atraso na recompra), cotações abertas e seu valor, negócio aberto no funil e status do cliente. Quanto maior, mais merece atenção hoje.",
  client_status:
    "Status comercial do cliente vindo do Sankhya (ex.: Ativo, Inativo, Bloqueado).",
  segment:
    "Ramo/segmento do cliente — campo 'Perfil Principal (Segmento)' do Sankhya.",

  // ---- KPIs de carteira ----
  clients: "Total de clientes (Contatos PJ) sincronizados nesta carteira.",
  money_on_table:
    "Dinheiro na mesa = soma das cotações em aberto da carteira. Valor potencial ainda não faturado.",
  money_on_table_total:
    "Dinheiro na mesa = cotações em aberto + negócios em aberto no funil, somando todas as carteiras sincronizadas.",
  overdue:
    "Clientes que passaram do ciclo habitual: (dias sem comprar ÷ frequência) ≥ 1,3 — ou ≥ 45 dias quando não há frequência conhecida.",
  inactive:
    "Clientes com status comercial Inativo / Bloqueado / Suspenso no Sankhya.",
  alerts:
    "Total de avisos ativos na carteira: reativação (passou do ciclo), cotação parada e cliente inativo com histórico.",

  // ---- reativação ----
  at_risk:
    "Clientes esfriando: fora da frequência + inativos com histórico de compra + frios (90+ dias sem comprar e sem frequência conhecida).",
  revenue_at_risk:
    "Soma do faturamento (histórico ~18m) dos clientes em risco — o que pode escorrer se nada for feito.",
  potential:
    "Potencial de recuperação = faturamento do cliente ponderado pela urgência (quanto mais atrasado em relação ao ciclo, maior o peso).",
  reason:
    "Motivo pelo qual o cliente entrou na régua de reativação (ciclo estourado, status inativo ou tempo sem comprar).",

  // ---- oportunidades / cross-sell ----
  crosssell_recommend:
    "Produtos campeões do ramo deste cliente que ele ainda NÃO compra. Base: itens de pedido (OrderItems) agrupados por segmento, na sua carteira.",
  segment_total:
    "Valor total vendido neste ramo no histórico sincronizado (~18m) da sua carteira.",
  champion_total:
    "Quanto este produto vendeu no ramo (histórico ~18m da sua carteira).",
  champion_buyers:
    "Quantos clientes diferentes do ramo compram este produto.",
};
