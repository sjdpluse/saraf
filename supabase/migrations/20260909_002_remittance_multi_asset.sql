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
set usd_value = coalesce(usd_value, gross_afn / nullif(usd_rate, 0)),
    asset_price_usd = coalesce(
        asset_price_usd,
        (gross_afn / nullif(usd_rate, 0)) / nullif(crypto_amount, 0)
    )
where asset_price_usd is null or usd_value is null;

create or replace function public.set_remittance_asset_valuation()
returns trigger
language plpgsql
as $$
begin
    if new.usd_value is null and new.usd_rate > 0 then
        new.usd_value := new.gross_afn / new.usd_rate;
    end if;
    if new.asset_price_usd is null and new.crypto_amount > 0 and new.usd_value is not null then
        new.asset_price_usd := new.usd_value / new.crypto_amount;
    end if;
    return new;
end;
$$;

drop trigger if exists trg_remittance_asset_valuation on public.remittance_orders;
create trigger trg_remittance_asset_valuation
before insert or update of crypto_amount, usd_rate, gross_afn, usd_value, asset_price_usd
on public.remittance_orders
for each row execute function public.set_remittance_asset_valuation();

alter table public.remittance_orders
    add constraint remittance_orders_asset_price_usd_positive
    check (asset_price_usd is null or asset_price_usd > 0);

alter table public.remittance_orders
    add constraint remittance_orders_usd_value_positive
    check (usd_value is null or usd_value > 0);
