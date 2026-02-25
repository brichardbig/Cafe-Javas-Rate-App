import streamlit as st
import joblib
import re
from pathlib import Path

# ── Page config (must be first) ──────────────────────────────────────────────
st.set_page_config(page_title="Cafe Javas · Review Rater", page_icon="☕", layout="centered")

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #fdf8f2 !important;
    font-family: 'DM Sans', sans-serif;
    color: #2c1f0e;
}
[data-testid="stHeader"], footer { display: none !important; }

.hero { text-align:center; padding: 2.5rem 1rem 1rem; }
.hero-icon {
    font-size: 3.5rem; display:block; margin-bottom:.5rem;
    filter: drop-shadow(0 0 14px #c9943a66);
    animation: float 3s ease-in-out infinite;
}
@keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-7px)} }
.hero h1 {
    font-family:'Playfair Display',serif; font-size:2.6rem;
    color:#7a4a1a; letter-spacing:-.5px; margin:0 0 .3rem;
}
.hero p { color:#a07850; font-size:1rem; margin:0; }

.divider {
    height:1px;
    background: linear-gradient(90deg, transparent, #c9943a88, transparent);
    margin: 1.5rem 0;
}

textarea {
    background: #ffffff !important;
    border: 1.5px solid #ddc9a8 !important;
    border-radius: 12px !important;
    color: #2c1f0e !important;
    font-family: 'DM Sans', sans-serif !important;
}
textarea:focus { border-color: #c9943a !important; }

[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #c9943a, #a0722a) !important;
    color: #fff !important; font-weight: 600 !important;
    border: none !important; border-radius: 12px !important;
    width: 100%; font-size: 1rem !important;
    box-shadow: 0 4px 20px #c9943a33 !important;
    transition: transform .15s, box-shadow .15s !important;
}
[data-testid="stButton"] > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px #c9943a55 !important;
}

.result-card {
    background: #ffffff; border-radius:18px; padding:2rem 1.8rem 1.8rem;
    margin-top:1.4rem; border:1px solid #e8d5b5;
    box-shadow:0 4px 24px #c9943a18;
    animation: slideUp .4s ease;
    text-align: center;
}
@keyframes slideUp { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
.result-stars { font-size:2.4rem; letter-spacing:4px; margin-bottom:.4rem; }
.result-label {
    font-family:'Playfair Display',serif; font-size:2.2rem; font-weight:700; margin:.2rem 0 .4rem;
}
.result-conf { color:#a07850; font-size:.95rem; }
.result-conf span { color:#a0722a; font-weight:600; }

.app-footer { text-align:center; color:#b89870; font-size:.78rem; margin-top:2.5rem; padding-bottom:1.5rem; }
.app-footer strong { color:#c9943a; }
.err-box {
    background:#fff5f5; border:1px solid #f5c0c0; border-radius:12px;
    padding:1.2rem 1.4rem; color:#c0392b; font-size:.9rem; line-height:1.8;
}
.err-box code { background:#ffe8e8; padding:.1rem .4rem; border-radius:4px; }
</style>
""", unsafe_allow_html=True)

# ── Preprocessing (mirrors notebook exactly) ─────────────────────────────────
STOPWORDS = set([
    'i','me','my','myself','we','our','ours','you','your','yours','he','him','his',
    'she','her','hers','it','its','they','them','their','what','which','who','this',
    'that','these','those','am','is','are','was','were','be','been','being','have',
    'has','had','do','does','did','a','an','the','and','but','if','or','as','of',
    'at','by','for','with','about','to','from','in','out','on','off','so','than',
    'too','very','s','t','can','will','just','now','also','get','go','us','like',
    'much','always','every','one','two','back','come','came','went','well','day',
    'times','first','last','said','know','want','need','going','around','still',
    'already','usually','often','never','sometimes','definitely','would','could',
    'should','shall','might','must','even','really','though','however','since',
])
STOPWORDS -= {'not', 'no'}

NOISE_WORDS = set([
    'cafe','java','javas','cj','cjs','place','restaurant','food','also','would',
    'got','get','went','us','one','even','really','read','kampala','ice',
    'breakfast','lunch','dinner','coffee','tea','bombo','road','ntv','ugandans',
    'ugandan','uganda','city','center','downtown','oasis','meal','mall','menu',
    'drink','drinks','dessert','branch','visit','acacia',
])

IRREGULARS = {
    'ate':'eat','eaten':'eat','eats':'eat','eating':'eat',
    'drank':'drink','drunk':'drink','drinking':'drink',
    'went':'go','goes':'go','came':'come','comes':'come','coming':'come',
    'took':'take','takes':'take','taking':'take',
    'gave':'give','gives':'give','giving':'give',
    'felt':'feel','feels':'feel','feeling':'feel',
    'told':'tell','tells':'tell','telling':'tell',
    'worse':'bad','worst':'bad','better':'good','best':'good',
    'enjoyed':'enjoy','enjoys':'enjoy','enjoying':'enjoy',
    'visited':'visit','visits':'visit','visiting':'visit',
    'ordered':'order','orders':'order','ordering':'order',
    'served':'serve','serves':'serve','serving':'serve',
    'recommended':'recommend','recommends':'recommend','recommending':'recommend',
    'tasted':'taste','tastes':'taste','tasting':'taste',
    'tried':'try','tries':'try','trying':'try',
    'waited':'wait','waiting':'wait',
    'loved':'love','loves':'love','loving':'love',
    'liked':'like','likes':'like',
    'hated':'hate','hates':'hate','hating':'hate',
    'dishes':'dish','prices':'price','tables':'table','waiters':'waiter',
    'menus':'menu','portions':'portion','customers':'customer',
    'experiences':'experience','services':'service','places':'place',
    'meals':'meal','foods':'food','coffees':'coffee',
    'restaurants':'restaurant','cafes':'cafe','staff':'staff',
    'disappointing':'disappoint','disappointed':'disappoint','disappoints':'disappoint',
}

def lemmatize_word(word):
    w = word.lower()
    if w in IRREGULARS: return IRREGULARS[w]
    if len(w) <= 3: return w
    if w.endswith('ing') and len(w) > 6:
        stem = w[:-3]
        if len(stem) > 2 and stem[-1] == stem[-2]: return stem[:-1]
        return stem
    if w.endswith('ed') and len(w) > 5:
        stem = w[:-2]
        if stem.endswith('i'): return stem[:-1] + 'y'
        if len(stem) > 2 and stem[-1] == stem[-2]: return stem[:-1]
        return stem
    if w.endswith('ies') and len(w) > 5: return w[:-3] + 'y'
    if w.endswith('es') and len(w) > 5 and not w.endswith('ss'): return w[:-2]
    if w.endswith('s') and not w.endswith('ss') and len(w) > 4: return w[:-1]
    return w

def clean_body_text(text):
    text = str(text).lower()
    text = re.sub(r'Read more$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'http\S+|www\S+', '', text)
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def preprocess(text):
    text   = clean_body_text(text)
    tokens = text.split()
    tokens = [w for w in tokens if w not in STOPWORDS]
    tokens = [lemmatize_word(w) for w in tokens]
    tokens = [w for w in tokens if w not in STOPWORDS and w not in NOISE_WORDS and len(w) > 2]
    return ' '.join(tokens)

# ── Model loading ─────────────────────────────────────────────────────────────
@st.cache_resource
def load_models():
    app_dir = Path(__file__).parent.resolve()
    files   = ["svm_review_classifier.pkl", "tfidf_vectorizer.pkl", "svd_transformer.pkl"]
    paths   = {}
    for f in files:
        for folder in [app_dir, Path.cwd()]:
            p = folder / f
            if p.exists():
                paths[f] = str(p)
                break
    missing = [f for f in files if f not in paths]
    if missing:
        return None, None, None, missing
    try:
        svm   = joblib.load(paths["svm_review_classifier.pkl"])
        tfidf = joblib.load(paths["tfidf_vectorizer.pkl"])
        svd   = joblib.load(paths["svd_transformer.pkl"])
        return svm, tfidf, svd, []
    except Exception as e:
        return None, None, None, [str(e)]

def predict(text, svm, tfidf, svd):
    vec    = tfidf.transform([preprocess(text)])
    svd_v  = svd.transform(vec)
    rating = int(svm.predict(svd_v)[0])
    proba  = svm.predict_proba(svd_v)[0]
    return rating, float(proba.max())

# ── Rating metadata ───────────────────────────────────────────────────────────
META = {
    1: ("Terrible",  "#e74c3c"),
    2: ("Poor",      "#e67e22"),
    3: ("Average",   "#d4ac0d"),
    4: ("Good",      "#27ae60"),
    5: ("Excellent", "#1a9a50"),
}

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <span class="hero-icon">☕</span>
  <h1>Cafe Javas Review Rater</h1>
  <p>Type your review and i rate it</p>
</div>
<div class="divider"></div>
""", unsafe_allow_html=True)

svm, tfidf, svd, errors = load_models()

if errors:
    st.markdown(f"""
    <div class="err-box">
      <b>❌ Model files not found.</b><br><br>
      Place these three files in the <b>same folder</b> as <code>app.py</code>, then re-run:<br><br>
      &nbsp;&nbsp;• <code>svm_review_classifier.pkl</code><br>
      &nbsp;&nbsp;• <code>tfidf_vectorizer.pkl</code><br>
      &nbsp;&nbsp;• <code>svd_transformer.pkl</code><br><br>
      <i>Detail: {errors}</i>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

review = st.text_area(
    "Customer Review",
    placeholder='e.g. "The food was delicious and the staff were so welcoming!"',
    height=150,
    label_visibility="collapsed",
)

_, mid, _ = st.columns([1, 2, 1])
with mid:
    go = st.button("⭐  Predict Rating")

if go:
    if not review.strip():
        st.warning("Please enter a review first.")
    else:
        with st.spinner("Analysing…"):
            try:
                rating, confidence = predict(review, svm, tfidf, svd)
            except Exception as e:
                st.error(f"Prediction error: {e}")
                st.stop()

        label, color = META[rating]
        stars = "⭐" * rating

        st.markdown(f"""
        <div class="result-card">
          <div class="result-stars">{stars}</div>
          <div class="result-label" style="color:{color}">{rating} / 5 — {label}</div>
          <div class="result-conf">Model confidence: <span>{confidence*100:.1f}%</span></div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("""
<div class="app-footer">
  <strong>SVM</strong> · TF-IDF + SVD · Trained on Cafe Javas TripAdvisor reviews
</div>
""", unsafe_allow_html=True)