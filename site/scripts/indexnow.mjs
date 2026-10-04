// Avvisa i motori che supportano IndexNow (Bing, Yandex, Seznam, Naver…) delle pagine cambiate con l'ultimo deploy:
// quelle della sitemap pubblicata con il lastmod più recente, cioè tutto ciò che dipende dall'ultimo concorso.
// La chiave è pubblica per costruzione: il file public/<chiave>.txt dimostra che il sito è nostro.
const SITE = "https://lascimmiavince.federicodiluca.com";
const KEY = "4a57653f2880d1ec8c287d180df2ea69";

const xml = await (await fetch(`${SITE}/sitemap-0.xml`)).text();
const entries = [...xml.matchAll(/<url><loc>([^<]+)<\/loc><lastmod>([^<]+)<\/lastmod>/g)].map((m) => ({ url: m[1], lastmod: m[2] }));
if (!entries.length) throw new Error("sitemap vuota o senza lastmod");
const latest = entries.reduce((a, e) => (e.lastmod > a ? e.lastmod : a), "");
const urlList = entries.filter((e) => e.lastmod === latest).map((e) => e.url);

const res = await fetch("https://api.indexnow.org/indexnow", {
  method: "POST",
  headers: { "Content-Type": "application/json; charset=utf-8" },
  body: JSON.stringify({ host: new URL(SITE).host, key: KEY, keyLocation: `${SITE}/${KEY}.txt`, urlList }),
});
console.log(`IndexNow: ${urlList.length} pagine (lastmod ${latest}) → HTTP ${res.status}`);
if (!res.ok) throw new Error(await res.text());
