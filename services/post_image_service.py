"""
سرویس تولید تصویر پست شبکه‌های اجتماعی صراف.

پوستر از نرخ دالر، صرافی‌های محلی، طلا، نقره و نرخ خرید/فروش USDT ساخته می‌شود.
نمودارها فقط از تاریخچهٔ واقعی ذخیره‌شده استفاده می‌کنند؛ اگر دادهٔ تاریخی کافی
نباشد، به‌جای ساختن نوسان جعلی، وضعیت «دادهٔ کافی نیست» نمایش داده می‌شود.
"""
import base64
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

import httpx
from playwright.async_api import async_playwright

from config import SARAF_LOGO_URL
from services import local_market_service, supabase_service as db
from services.money import D, quantize_rate, to_float

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = BASE_DIR / "assets" / "fonts"
TEMPLATE_PATH = BASE_DIR / "services" / "templates" / "facebook_post_template.html"

_FONT_FILES = {
    400: "Peyda-Regular.ttf",
    500: "Peyda-Medium.ttf",
    600: "Peyda-SemiBold.ttf",
    700: "Peyda-Bold.ttf",
    900: "Peyda-Black.ttf",
}

_LOGO_CACHE_TTL_SECONDS = 3600
_logo_cache: dict = {"data_uri": None, "fetched_at": 0.0}
_fonts_css_cache: Optional[str] = None

# نرخ خرید نمایشی USDT در پوستر برای پلهٔ اول خرید است.
# این همان تخفیف فعلی ۲٪ روی نرخ فروش دالر صرافی است.
_POSTER_USDT_BUY_FEE_PERCENT = Decimal("2")


def _load_fonts_css() -> str:
    global _fonts_css_cache
    if _fonts_css_cache is not None:
        return _fonts_css_cache

    rules = []
    for weight, filename in _FONT_FILES.items():
        path = FONTS_DIR / filename
        if not path.exists():
            raise FileNotFoundError(
                f"فایل فونت یافت نشد: {path}. مطمئن شوید پوشهٔ assets/fonts در ریپازیتوری موجود است."
            )
        b64 = base64.b64encode(path.read_bytes()).decode()
        rules.append(
            f"@font-face {{ font-family:'Peyda'; font-weight:{weight}; "
            f"src:url(data:font/ttf;base64,{b64}) format('truetype'); }}"
        )
    _fonts_css_cache = "\n  ".join(rules)
    return _fonts_css_cache


async def _get_logo_data_uri(force_refresh: bool = False) -> str:
    now = time.monotonic()
    is_fresh = _logo_cache["data_uri"] is not None and (now - _logo_cache["fetched_at"]) < _LOGO_CACHE_TTL_SECONDS

    if not force_refresh and is_fresh:
        return _logo_cache["data_uri"]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(SARAF_LOGO_URL)
            resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/webp").split(";")[0].strip()
        b64 = base64.b64encode(resp.content).decode()
        data_uri = f"data:{content_type};base64,{b64}"
        _logo_cache["data_uri"] = data_uri
        _logo_cache["fetched_at"] = now
        return data_uri
    except Exception:
        logger.warning("خطا در بارگیری لوگوی صراف از %s", SARAF_LOGO_URL, exc_info=True)
        if _logo_cache["data_uri"] is not None:
            return _logo_cache["data_uri"]
        raise RuntimeError(
            f"دریافت لوگو از {SARAF_LOGO_URL} ناموفق بود و نسخهٔ کش‌شده‌ای هم در دسترس نیست."
        )


def _fmt2(value: float) -> str:
    return f"{value:,.2f}"


def _series_json(points: list, live_value: Optional[float] = None) -> Optional[str]:
    """فقط نقاط واقعی موجود را به سری نمودار تبدیل می‌کند.

    live_value یک نقطهٔ واقعی لحظهٔ ساخت پوستر است و در صورت متفاوت بودن از آخرین
    snapshot تاریخی به انتهای سری اضافه می‌شود. هیچ interpolation یا نقطهٔ ساختگی
    در این مرحله تولید نمی‌شود.
    """
    values = []
    for value in points or []:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if not values or abs(values[-1] - number) > 1e-12:
            values.append(number)

    if live_value is not None:
        live = float(live_value)
        if not values or abs(values[-1] - live) > 1e-9:
            values.append(live)

    if len(values) < 2:
        return None
    return json.dumps(values, separators=(",", ":"))


def _build_weekly_series(quote: dict, gold_breakdown: dict, silver_breakdown: Optional[dict]) -> dict:
    """سری ۷ روزه را فقط از تاریخچهٔ واقعی دیتابیس می‌سازد."""
    since_7d = datetime.now(timezone.utc) - timedelta(days=7)
    series: dict = {}

    try:
        local = quote.get("local") or {}
        primary_market = local_market_service.PRIMARY_MARKET
        local_live = None
        if local.get("buy") is not None and local.get("sell") is not None:
            local_live = (local["buy"] + local["sell"]) / 2

        local_hist = db.get_local_market_rate_series(primary_market, "usd", since_7d)
        local_json = _series_json(local_hist, local_live)
        if local_json:
            series["__LOCAL_SERIES__"] = local_json
            series["__USD_SERIES__"] = local_json
        else:
            ref_live = quote.get("reference_rate")
            ref_hist = db.get_currency_rate_series("usd", since_7d)
            ref_json = _series_json(ref_hist, ref_live)
            if ref_json:
                series["__USD_SERIES__"] = ref_json
    except Exception:
        logger.exception("خطا در ساخت سری ۷ روزهٔ دالر برای پست")

    try:
        gold_live = gold_breakdown["karats"][24]["afn_per_gram"]
        gold_hist = db.get_gold_rate_series(since_7d)
        gold_json = _series_json(gold_hist, gold_live)
        if gold_json:
            series["__GOLD_SERIES__"] = gold_json
    except Exception:
        logger.exception("خطا در ساخت سری ۷ روزهٔ طلا برای پست")

    if silver_breakdown:
        try:
            silver_live = silver_breakdown["afn_per_gram"]
            silver_hist = db.get_silver_rate_series(since_7d)
            silver_json = _series_json(silver_hist, silver_live)
            if silver_json:
                series["__SILVER_SERIES__"] = silver_json
        except Exception:
            logger.exception("خطا در ساخت سری ۷ روزهٔ نقره برای پست")

    return series


def _usdt_poster_rates(saraf_quote: dict) -> tuple[float, float]:
    """نرخ هر ۱ USDT در پوستر.

    خرید کاربر: نرخ فروش دالر صرافی + ۲٪ کارمزد.
    فروش کاربر: نرخ خرید دالر صرافی، بدون کارمزد اضافه.
    """
    usd_sell = D(saraf_quote["sell"])
    usd_buy = D(saraf_quote["buy"])
    buy_rate = usd_sell * (D(1) + _POSTER_USDT_BUY_FEE_PERCENT / D(100))
    return (
        to_float(quantize_rate(buy_rate)),
        to_float(quantize_rate(usd_buy)),
    )


def _inject_poster_enhancements(template: str) -> str:
    """بدون دست‌زدن به ساختار اصلی قالب، کارت USDT و renderer دقیق نمودار را تزریق می‌کند."""
    css = r"""
  /* USDT quote — compact, inside the local-exchange card */
  .usdt-quote{
    position:absolute;
    left:24px;
    top:19px;
    z-index:5;
    width:430px;
    min-height:64px;
    display:grid;
    grid-template-columns:118px 1fr 1fr;
    align-items:center;
    direction:rtl;
    border-radius:20px;
    padding:9px 13px;
    background:linear-gradient(145deg,rgba(255,255,255,.92),rgba(239,248,246,.84));
    border:1px solid rgba(39,42,48,.08);
    box-shadow:0 9px 24px rgba(23,27,36,.065);
    backdrop-filter:blur(16px);
  }
  .usdt-brand{display:flex;align-items:center;gap:8px;border-left:1px solid rgba(39,42,48,.09);padding-left:10px;}
  .usdt-symbol{width:31px;height:31px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#26A17B;color:white;font-size:20px;font-weight:900;line-height:1;}
  .usdt-name{font-size:17px;font-weight:900;line-height:1.05;}
  .usdt-sub{font-size:10px;font-weight:700;color:var(--ink-3);margin-top:3px;white-space:nowrap;}
  .usdt-rate{padding:0 11px;text-align:right;}
  .usdt-rate + .usdt-rate{border-right:1px solid rgba(39,42,48,.08);}
  .usdt-label{font-size:11px;font-weight:800;color:var(--ink-3);}
  .usdt-num{font-size:25px;font-weight:900;letter-spacing:-.8px;line-height:1;margin-top:3px;direction:ltr;text-align:right;}
  .usdt-fee{font-size:9px;font-weight:750;color:#218D52;margin-top:3px;white-space:nowrap;}
  .chart-empty{font-family:'Peyda',sans-serif;font-size:12px;font-weight:700;fill:#9C9B92;}
"""
    template = template.replace("</style>", css + "\n</style>")

    usdt_html = r"""
        <div class="usdt-quote" aria-label="نرخ خرید و فروش تتر">
          <div class="usdt-brand">
            <div class="usdt-symbol">₮</div>
            <div><div class="usdt-name">تتر</div><div class="usdt-sub">USDT / AFN</div></div>
          </div>
          <div class="usdt-rate">
            <div class="usdt-label">خرید تتر</div>
            <div class="usdt-num">__USDT_BUY__ ؋</div>
            <div class="usdt-fee">شامل ۲٪ کارمزد</div>
          </div>
          <div class="usdt-rate">
            <div class="usdt-label">فروش تتر</div>
            <div class="usdt-num">__USDT_SELL__ ؋</div>
            <div class="usdt-fee" style="color:var(--ink-3)">بدون کارمزد اضافه</div>
          </div>
        </div>
"""
    template = template.replace(
        "        <div class=\"local-main\">",
        usdt_html + "\n        <div class=\"local-main\">",
        1,
    )

    # Renderer دوم بعد از renderer قدیمی اجرا می‌شود و خروجی نمودار را با نسخهٔ
    # دقیق جایگزین می‌کند. مسیر بین هر دو نقطه خطی است؛ بنابراین overshoot یا
    # قله/درهٔ ساختگی ناشی از Bezier ایجاد نمی‌شود.
    exact_js = r"""
<script>
(function(){
  function strictSeries(v){
    try{
      if(typeof v !== 'string' || v.indexOf('SERIES') > -1) return [];
      var a=JSON.parse(v);
      if(!Array.isArray(a)) return [];
      return a.map(Number).filter(Number.isFinite);
    }catch(e){ return []; }
  }

  function exactDraw(id,data,opts){
    var svg=document.getElementById(id);
    if(!svg) return null;
    svg.innerHTML='';
    if(!data || data.length < 2){
      var vb0=svg.getAttribute('viewBox').split(' ').map(Number);
      svg.innerHTML='<text class="chart-empty" x="'+(vb0[2]/2)+'" y="'+(vb0[3]/2)+'" text-anchor="middle">دادهٔ تاریخی کافی نیست</text>';
      return null;
    }

    var vb=svg.getAttribute('viewBox').split(' ').map(Number), W=vb[2], H=vb[3];
    var pad=opts.pad||8;
    var lo=Math.min.apply(null,data), hi=Math.max.apply(null,data);
    var rawSpan=hi-lo;
    var center=(hi+lo)/2;
    var minVisualSpan=Math.max(Math.abs(center)*0.0015, opts.minSpan||0);
    var span=Math.max(rawSpan,minVisualSpan,1e-9);
    var visualLo=center-span/2, visualHi=center+span/2;
    var verticalPad=pad+4;
    var up=data[data.length-1] >= data[0];
    var color=up?'#2FBF71':'#FF453A';

    var pts=data.map(function(v,i){
      return [
        pad+(W-pad*2)*(i/(data.length-1)),
        H-verticalPad-((v-visualLo)/(visualHi-visualLo))*(H-verticalPad*2)
      ];
    });

    var d='M'+pts[0][0].toFixed(1)+' '+pts[0][1].toFixed(1);
    for(var i=1;i<pts.length;i++) d+=' L'+pts[i][0].toFixed(1)+' '+pts[i][1].toFixed(1);

    var gid=id+'-exact-g', grid='';
    if(opts.grid){
      for(var g=0;g<3;g++){
        var gy=(pad+(H-pad*2)*(g/2)).toFixed(1);
        grid+='<line x1="'+pad+'" y1="'+gy+'" x2="'+(W-pad)+'" y2="'+gy+'" stroke="rgba(60,60,67,.08)" stroke-width="1"/>';
      }
    }
    var area=opts.area?'<path d="'+d+' L'+(W-pad)+' '+(H-pad)+' L'+pad+' '+(H-pad)+' Z" fill="url(#'+gid+')"/>':'';
    svg.innerHTML='<defs><linearGradient id="'+gid+'" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="'+color+'" stop-opacity=".20"/><stop offset="100%" stop-color="'+color+'" stop-opacity="0"/></linearGradient></defs>'+grid+area+'<path d="'+d+'" fill="none" stroke="'+color+'" stroke-width="'+(opts.sw||3)+'" stroke-linecap="round" stroke-linejoin="round"/>'+(opts.dot?'<circle cx="'+pts[pts.length-1][0].toFixed(1)+'" cy="'+pts[pts.length-1][1].toFixed(1)+'" r="4.5" fill="'+color+'" stroke="#fff" stroke-width="2.5"/>':'');
    return ((data[data.length-1]-data[0])/(data[0]||1))*100;
  }

  function exactHistory(id,data,opts){
    var el=document.getElementById(id); if(!el) return;
    if(!data || data.length < 2){ el.innerHTML=''; return; }
    var step=opts.step||1,max=opts.max||7,fmt=opts.fmt;
    var items=[];
    for(var i=data.length-2;i>=0 && items.length<max;i-=step){
      var back=data.length-1-i;
      items.push('<div class="h-item"><div class="h-v">'+fmt(data[i])+'</div><div class="h-d">'+back+'d</div></div>');
    }
    el.innerHTML=items.reverse().join('');
  }

  var usd=strictSeries(RAW.usd), gold=strictSeries(RAW.gold), silver=strictSeries(RAW.silver);
  var pctExact=exactDraw('sparkUsd',usd,{area:true,dot:true,sw:4.2,pad:12,grid:true,minSpan:.08});
  exactDraw('sparkGold',gold,{area:true,dot:true,sw:3,pad:8,grid:true,minSpan:10});
  exactDraw('sparkSilver',silver,{area:true,dot:true,sw:3,pad:8,grid:true,minSpan:.2});

  exactHistory('histUsd',usd,{step:1,max:7,fmt:function(v){return v.toFixed(2);}});
  exactHistory('histGold',gold,{step:2,max:4,fmt:function(v){return String(Math.round(v));}});
  exactHistory('histSilver',silver,{step:2,max:4,fmt:function(v){return v.toFixed(1);}});

  var box=document.getElementById('usdDelta'), val=document.getElementById('usdDeltaVal');
  if(box && val){
    if(pctExact === null){ box.style.display='none'; }
    else{
      box.style.display='inline-flex';
      var down=pctExact<0;
      box.classList.toggle('down',down);
      val.textContent=(down?'−':'+')+toFa(Math.abs(pctExact).toFixed(2))+'٪';
    }
  }
})();
</script>
"""
    template = template.replace("</body>", exact_js + "\n</body>")
    return template


def _build_html(quote: dict, gold_breakdown: dict, silver_breakdown: Optional[dict], logo_data_uri: str,
                 date_str: str) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    template = _inject_poster_enhancements(template)

    local = quote.get("local") or {}
    saraf = quote["saraf_quote"]
    reference_rate = quote.get("reference_rate")

    ss_buy = local.get("buy")
    ss_sell = local.get("sell")
    if ss_buy is None or ss_sell is None:
        ss_buy, ss_sell = saraf["buy"], saraf["sell"]

    gold_24k = gold_breakdown["karats"][24]
    usdt_buy, usdt_sell = _usdt_poster_rates(saraf)

    values = {
        "__FONTS_CSS__": _load_fonts_css(),
        "__LOGO_SRC__": logo_data_uri,
        "__DATE__": date_str,
        "__SS_BUY__": _fmt2(ss_buy),
        "__SS_SELL__": _fmt2(ss_sell),
        "__LOC_BUY__": _fmt2(saraf["buy"]),
        "__LOC_SELL__": _fmt2(saraf["sell"]),
        "__REF_RATE__": _fmt2(reference_rate) if reference_rate else "—",
        "__USDT_BUY__": _fmt2(usdt_buy),
        "__USDT_SELL__": _fmt2(usdt_sell),
        "__GOLD_AFN__": f"{gold_24k['afn_per_gram']:,.0f} افغانی",
        "__GOLD_USD__": f"{gold_24k['usd_per_gram']:,.2f} دالر",
    }
    if silver_breakdown:
        values["__SILVER_AFN__"] = f"{silver_breakdown['afn_per_gram']:,.0f} افغانی"
        values["__SILVER_USD__"] = f"{silver_breakdown['usd_per_gram']:,.2f} دالر"
    else:
        values["__SILVER_AFN__"] = "—"
        values["__SILVER_USD__"] = ""

    # همیشه placeholderهای سری را مقداردهی می‌کنیم. آرایهٔ خالی یعنی «داده کافی
    # نیست» و renderer دقیق آن را به‌عنوان نمودار جعلی تفسیر نمی‌کند.
    values.update({
        "__USD_SERIES__": "[]",
        "__LOCAL_SERIES__": "[]",
        "__GOLD_SERIES__": "[]",
        "__SILVER_SERIES__": "[]",
    })
    values.update(_build_weekly_series(quote, gold_breakdown, silver_breakdown))

    for key, val in values.items():
        template = template.replace(key, val)
    return template


async def generate_facebook_post_image(
    quote: dict, gold_breakdown: dict, date_str: str, silver_breakdown: Optional[dict] = None
) -> bytes:
    """تصویر PNG نهایی را برای فیسبوک و اینستاگرام تولید می‌کند."""
    logo_data_uri = await _get_logo_data_uri()
    html = _build_html(quote, gold_breakdown, silver_breakdown, logo_data_uri, date_str)

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            page = await browser.new_page(
                viewport={"width": 1080, "height": 1080}, device_scale_factor=2
            )
            await page.set_content(html, wait_until="load")
            png_bytes = await page.screenshot(type="png")
            return png_bytes
        finally:
            await browser.close()
