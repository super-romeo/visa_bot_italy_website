/* Прибор замера. Страна меняет ровно два значения ниже. */
var METRIKA_ID = "113161887";   // номер счётчика Яндекс.Метрики
var GA4_ID     = "";   // поток GA4, здесь не нужен

(function () {
  if (!METRIKA_ID && !GA4_ID) {
    console.warn("[smoke] аналитика не подключена: визиты и цели НЕ собираются");
    return;
  }
  if (METRIKA_ID) {
    (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
    m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0];
    k.async=1;k.src=r;a.parentNode.insertBefore(k,a)})
    (window,document,"script","https://mc.yandex.ru/metrika/tag.js","ym");
    ym(METRIKA_ID,"init",{clickmap:true,trackLinks:true,accurateTrackBounce:true,webvisor:true});
  }
  if (GA4_ID) {
    var s=document.createElement("script");
    s.async=1;s.src="https://www.googletagmanager.com/gtag/js?id="+GA4_ID;
    document.head.appendChild(s);
    window.dataLayer=window.dataLayer||[];
    window.gtag=function(){dataLayer.push(arguments)};
    gtag("js",new Date());gtag("config",GA4_ID);
  }
})();

function track(goal) {
  try { if (METRIKA_ID && window.ym) ym(METRIKA_ID, "reachGoal", goal); } catch (e) {}
  try { if (GA4_ID && window.gtag) gtag("event", goal); } catch (e) {}
  console.log("[smoke] цель: " + goal);
}
