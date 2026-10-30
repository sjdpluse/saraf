// Faithful original Python in_person_pass_service input validation.
export function originalPassInput({action,asset,code}={}){
 const type=String(action||'');
 const token=String(asset||'').trim().toUpperCase();
 const digits=String(code||'');
 if(type!=='buy'&&type!=='sell')throw Error('نوع مراجعه نامعتبر است.');
 if(token!=='USDT'&&token!=='USDC')throw Error('دارایی مراجعه نامعتبر است.');
 if(!/^[0-9]{4}$/.test(digits))throw Error('کد مراجعه باید ۴ رقم باشد.');
 return {action:type,asset:token,code:digits,
  actionFa:type==='buy'?'پرداخت حضوری':'دریافت حضوری',
  fileName:'saraf-'+type+'-'+token+'-'+digits+'.png',
 };
}
