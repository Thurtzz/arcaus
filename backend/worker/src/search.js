// Port of ember/search.py. Tokenizer rules come from the bundle so both sides agree;
// scoring uses only stored IDF values and + - * / in the same order as Python,
// so scores are bit-identical. tests/test_parity.py + worker/test/parity.test.mjs enforce this.

export function makeTokenizer(config) {
  const stop = new Set(config.stopwords);
  const syn = config.synonyms;
  const stem = (tok) => {
    if (tok.length > 5 && tok.endsWith("ing")) return tok.slice(0, -3);
    if (tok.length > 4 && tok.endsWith("ies")) return tok.slice(0, -3) + "y";
    if (tok.length > 3 && tok.endsWith("s") && !tok.endsWith("ss") && !tok.endsWith("us")) return tok.slice(0, -1);
    return tok;
  };
  return (text) => {
    const out = [];
    for (const raw of String(text).toLowerCase().split(/[^a-z0-9.]+/)) {
      let tok = raw.replace(/^\.+|\.+$/g, "");
      if (!tok || stop.has(tok)) continue;
      tok = Object.prototype.hasOwnProperty.call(syn, tok) ? syn[tok] : tok;
      tok = stem(tok);
      if (tok && !stop.has(tok)) out.push(tok);
    }
    return out;
  };
}

export function queryTerms(tokenize, q) {
  return [...new Set(tokenize(q))].sort();
}

export function round4(x) {
  return Math.floor(x * 10000 + 0.5) / 10000;
}

export function scoreDoc(doc, terms, index) {
  const k1 = index.config.k1, b = index.config.b, avgdl = index.avgdl;
  let s = 0.0;
  const matched = [];
  for (const t of terms) {
    const tf = Object.prototype.hasOwnProperty.call(doc.tf, t) ? doc.tf[t] : 0;
    if (!tf) continue;
    matched.push(t);
    s = s + index.idf[t] * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc.length / avgdl));
  }
  return [s, matched];
}
