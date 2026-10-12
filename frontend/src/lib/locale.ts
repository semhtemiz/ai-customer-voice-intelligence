const limitations: Record<string, string> = {
  "The sentiment model was trained on English tweets, not clothing reviews; inputs are truncated to 256 tokens.": "Sentiment modeli İngilizce tweet’lerle eğitildi; giyim yorumlarında alan farkı vardır. Girdiler 256 token ile sınırlandırılır.",
  "Topics use a keyword baseline: negation, context and implicit complaints may be missed. Counts are observed labels, not ground truth.": "Topic etiketleri keyword baseline ile üretilir; olumsuzlama, bağlam ve dolaylı şikâyetler kaçırılabilir. Sayımlar gerçek etiket doğruluğu anlamına gelmez.",
  "No review dates or sales amounts are available.": "Yorum tarihi veya satış tutarı bilgisi bulunmuyor.",
  "Displayed review text uses baseline email/phone masking; it is not exhaustive PII detection.": "Gösterilen yorumlarda temel e-posta/telefon maskelemesi uygulanır; kapsamlı PII tespiti yapılmaz.",
  "No compatible completed sentiment analysis is selected; predictions are unknown.": "Uyumlu ve tamamlanmış bir sentiment analizi seçilmedi; tahminler unknown durumunda.",
  "Sentiment uses a rating heuristic, not an NLP model.": "Sentiment, NLP modeli yerine rating heuristic yöntemi kullanır.",
  "Sentiment coverage is partial for the matched text reviews.": "Eşleşen metinli yorumların yalnızca bir bölümü için sentiment analizi yapılmış.",
  "Topic run does not match the selected sentiment run and is excluded.": "Topic run, seçili sentiment run ile eşleşmediği için kapsam dışında bırakıldı.",
  "Incompatible selected sentiment run is excluded.": "Uyumsuz seçili sentiment run kapsam dışında bırakıldı.",
  "Incompatible selected topics run is excluded.": "Uyumsuz seçili topics run kapsam dışında bırakıldı.",
};

export function localizeLimitation(message: string) {
  return limitations[message] ?? message;
}

export const topicNames:Record<string,string>={sizing:'Beden ve kalıp',fabric_quality:'Kumaş ve dayanıklılık',color_appearance:'Renk ve görünüş',style_design:'Stil ve tasarım',value_price:'Fiyat ve değer',shipping:'Shipping',customer_service:'Müşteri hizmetleri',other:'Diğer / eşleşmeyen'};
const metricNames:Record<string,string>={total_reviews:'Toplam yorum',avg_rating:'Ortalama rating',recommendation_rate_pct:'Tavsiye oranı (%)',low_rating_count:'Düşük rating sayısı',low_rating_rate_pct:'Düşük rating oranı (%)',negative_prediction_count:'Negative sentiment tahmini',text_review_count:'Metinli yorum',sentiment_classified_count:'Sınıflandırılmış yorum',rating_sentiment_disagreement_count:'Rating–sentiment yön farkı',priority_product_low_rating_count:'Öncelikli ürünün düşük rating sayısı'};
export function evidenceLabel(metric:string){return metricNames[metric]??(metric.startsWith('topic_')?topicNames[metric.slice(6)]??'Topic kanıtı':'Hesaplanan kanıt');}
