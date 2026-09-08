-- Remittance V2: support additional assets and preserve the USD value used for settlement.

alter table public.remittance_orders
    drop constraint if exists remittance_orders_asset_check;

alter table public.remittance_orders
    add constraint remittance_orders_asset_check
    check (asset in (
        'USDT','USDC','DAI','TUSD','TRX','BNB','ETH','SOL','WBTC','PAXG','PYUSD','WETH','BTCB','POL','BTC'
    ));

alter table public.remittance_orders
    add column if not exists asset_price_usd numeric(30,10),
    add column if not exists usd_value numeric(30,8);

update public.remittance_orders
set asset_price_usd = coalesce(asset_price_usd, 1),
    usd_value = coalesce(usd_value, crypto_amount)
where asset in ('USDT','USDC')
  and (asset_price_usd is null or usd_value is null);

alter table public.remittance_orders
    add constraint remittance_orders_asset_price_usd_positive
    check (asset_price_usd is null or asset_price_usd > 0);

alter table public.remittance_orders
    add constraint remittance_orders_usd_value_positive
    check (usd_value is null or usd_value > 0);
