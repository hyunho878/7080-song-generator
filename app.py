import os  
import re  
import json  
import html  
from datetime import datetime  
  
import streamlit as st  
import streamlit.components.v1 as components  
  
try:  
    from openai import OpenAI  
except ImportError:  
    OpenAI = None  
  
  
APP_TITLE = "추억의 7080 노래 생성기"  
DEFAULT_MODEL = "gpt-5.2-mini"  
  
  
MOOD_OPTIONS = [  
    "그리운 첫사랑",  
    "고향 생각",  
    "비 오는 다방",  
    "밤기차와 이별",  
    "통기타 청춘",  
    "황혼의 사랑",  
    "인생 회상",  
    "따뜻한 위로",  
    "봄날의 추억",  
    "가을 편지",  
]  
  
STYLE_OPTIONS = [  
    "7080 포크",  
    "7080 발라드",  
    "통기타 가요",  
    "옛날 다방 음악",  
    "트로트 발라드",  
    "LP 감성 팝",  
    "라디오 감성 가요",  
]  
  
VOCAL_OPTIONS = [  
    "남성 보컬",  
    "여성 보컬",  
    "중년 남성 보컬",  
    "중년 여성 보컬",  
    "부드러운 남녀 듀엣",  
]  
  
LENGTH_OPTIONS = ["2분", "3분", "4분"]  
  
THEME_WORDS = [  
    "다방",  
    "편지",  
    "밤기차",  
    "골목길",  
    "라디오",  
    "통기타",  
    "LP",  
    "첫사랑",  
    "고향",  
    "낡은 사진",  
    "비 오는 창가",  
    "버스 정류장",  
]  
  
  
def get_openai_api_key():  
    for key_name in ("OPENAI_API_KEY", "OpenAI_key", "openai_api_key"):  
        try:  
            value = st.secrets.get(key_name, "")  
        except Exception:  
            value = ""  
        if value:  
            return str(value).strip()  
  
    return os.getenv("OPENAI_API_KEY", "").strip()  
  
  
def parse_json(raw_text):  
    text = str(raw_text).strip()  
    text = re.sub(r"^```(?:json)?\s*", "", text)  
    text = re.sub(r"\s*```$", "", text)  
  
    try:  
        return json.loads(text)  
    except json.JSONDecodeError:  
        match = re.search(r"\{.*\}", text, flags=re.S)  
        if match:  
            return json.loads(match.group(0))  
        raise  
  
  
def render_copy_button(label, text, key):  
    safe_key = re.sub(r"[^0-9A-Za-z_-]", "_", str(key))  
    payload = json.dumps(str(text), ensure_ascii=False)  
  
    components.html(  
        f"""  
        <button id="copy-{safe_key}" style="  
            width:100%;  
            min-height:48px;  
            border-radius:14px;  
            border:1px solid #92400e;  
            background:#b45309;  
            color:#fff7ed;  
            font-weight:800;  
            font-size:17px;  
            cursor:pointer;  
        ">{html.escape(label)}</button>  
  
        <script>  
        const button = document.getElementById("copy-{safe_key}");  
        button.addEventListener("click", async () => {{  
            await navigator.clipboard.writeText({payload});  
            button.innerText = "복사 완료";  
            setTimeout(() => button.innerText = {json.dumps(label, ensure_ascii=False)}, 1300);  
        }});  
        </script>  
        """,  
        height=58,  
    )  
  
  
def clean_result(data):  
    titles = data.get("title_options", [])  
    if isinstance(titles, str):  
        titles = [line.strip(" -0123456789.") for line in titles.splitlines() if line.strip()]  
  
    titles = [str(t).strip() for t in titles if str(t).strip()]  
  
    return {  
        "title_options": titles[:5],  
        "suno_prompt": str(data.get("suno_prompt", "")).strip(),  
        "style_prompt": str(data.get("style_prompt", "")).strip(),  
        "lyrics": str(data.get("lyrics", "")).strip(),  
    }  
  
  
def generate_with_openai(api_key, model, mood, style, vocal, length, user_note):  
    if OpenAI is None:  
        raise RuntimeError("openai 패키지가 설치되어 있지 않습니다.")  
  
    client = OpenAI(api_key=api_key)  
  
    system_prompt = """  
너는 7080 한국 가요 감성의 노래를 만드는 작사가이자 음악 프롬프트 전문가다.  
  
목표:  
60~70대가 편하게 들을 수 있는 추억, 고향, 사랑, 인생 회상 중심의 노래를 만든다.  
  
절대 금지:  
- 실제 가수 이름 언급 금지  
- 실제 노래 제목 모방 금지  
- 기존 가사 인용 금지  
- 랩, EDM, 아이돌, 힙합 표현 금지  
- 너무 어려운 시어 금지  
- 과도하게 젊은 유행어 금지  
- 특정 실존 곡과 비슷하게 쓰지 말 것  
  
반드시:  
- 쉬운 한국어  
- 따라 부르기 쉬운 후렴  
- 7080 포크/발라드/통기타/다방 음악 감성  
- 완전히 새로운 창작 가사  
- Suno에서 바로 쓸 수 있는 짧은 영어 태그 프롬프트 작성  
- 반환은 반드시 JSON만 한다.  
"""  
  
    user_prompt = f"""  
아래 선택값으로 새로운 7080 감성 노래를 만들어줘.  
  
[선택값]  
분위기: {mood}  
음악 스타일: {style}  
보컬: {vocal}  
곡 길이: {length}  
사용자 메모: {user_note or "없음"}  
  
[반환 형식]  
{{  
  "title_options": ["제목1", "제목2", "제목3", "제목4", "제목5"],  
  "suno_prompt": "영어 태그 8~12개, 쉼표로 구분",  
  "style_prompt": "Suno/Udio에 넣을 음악 스타일 설명",  
  "lyrics": "한국어 가사"  
}}  
  
가사 구조:  
[Verse 1]  
[Chorus]  
[Verse 2]  
[Bridge]  
[Final Chorus]  
  
가사 방향:  
- 7080 한국 가요처럼 따뜻하고 선명하게  
- 고향, 첫사랑, 다방, 편지, 밤기차, 골목길, 라디오, 통기타, LP 같은 이미지를 자연스럽게 사용  
- 후렴은 짧고 반복하기 쉽게  
- 슬프더라도 너무 절망적이지 않게  
- 듣고 나면 오래된 사진첩을 넘기는 느낌  
- 전체 가사는 {length} 분량에 어울리게 작성  
"""  
  
    response = client.responses.create(  
        model=model,  
        input=[  
            {"role": "system", "content": system_prompt},  
            {"role": "user", "content": user_prompt},  
        ],  
    )  
  
    return clean_result(parse_json(response.output_text))  
  
  
def generate_rule_based(mood, style, vocal, length, user_note):  
    note = user_note.strip() if user_note else ""  
    main_image = {  
        "그리운 첫사랑": "낡은 사진 속 첫사랑",  
        "고향 생각": "저녁 연기 피어오르던 고향집",  
        "비 오는 다방": "비 내리는 창가의 작은 다방",  
        "밤기차와 이별": "멀어지는 밤기차의 불빛",  
        "통기타 청춘": "통기타 하나에 기대던 젊은 날",  
        "황혼의 사랑": "해질녘 손을 잡은 두 사람",  
        "인생 회상": "굽이굽이 지나온 인생길",  
        "따뜻한 위로": "말없이 곁을 지켜준 사람",  
        "봄날의 추억": "꽃잎 흩날리던 봄날",  
        "가을 편지": "가을 바람에 접어 보낸 편지",  
    }.get(mood, "오래된 추억")  
  
    title_options = [  
        f"{main_image}",  
        f"{mood}의 노래",  
        f"그 시절 그 사람",  
        f"라디오에 남은 마음",  
        f"오래된 편지 한 장",  
    ]  
  
    suno_prompt = (  
        f"70s Korean folk ballad, nostalgic, warm {vocal.lower()}, "  
        f"acoustic guitar, vintage radio, soft drums, emotional melody, "  
        f"easy chorus, old cafe mood, analog LP texture"  
    )  
  
    style_prompt = (  
        f"{style} 스타일의 {vocal} 곡. "  
        f"7080 한국 가요 감성, 통기타와 잔잔한 드럼, 따뜻한 아날로그 질감, "  
        f"라디오에서 흘러나오는 듯한 보컬, 따라 부르기 쉬운 후렴. "  
        f"분위기는 '{mood}'이며 곡 길이는 {length}. "  
        f"실제 7080 가수나 기존 곡을 모방하지 않고 완전히 새로운 창작곡으로 만든다."  
    )  
  
    if note:  
        style_prompt += f" 사용자 메모 반영: {note}."  
  
    lyrics = f"""[Verse 1]  
비 오는 창가에 앉아  
오래된 찻잔을 바라보네  
라디오에 흐르던 그 노래처럼  
그 시절 마음이 다시 찾아와  
  
{main_image}이 떠오르면  
말없이 웃던 그대 생각나  
보내지 못한 편지 한 장이  
아직도 서랍 속에 잠들어 있네  
  
[Chorus]  
그리워라 그 시절이여  
내 마음에 남은 사람아  
세월은 강물처럼 흘러도  
그 이름은 지워지지 않네  
  
그리워라 그 시절이여  
다시 못 올 나의 청춘아  
바람이 불어오는 저 길 끝에서  
오늘도 그대를 불러보네  
  
[Verse 2]  
골목길 작은 불빛 아래  
우리는 꿈처럼 걸었지  
통기타 소리 번지던 밤  
말보다 깊은 마음이 있었네  
  
이제는 멀리 지나온 날  
사진처럼 희미해져도  
가슴 한켠 따뜻한 자리엔  
그대의 미소가 남아 있네  
  
[Bridge]  
돌아갈 수 없는 날이라 해도  
후회만 남기고 싶진 않아  
사랑했던 모든 순간들이  
내 인생의 노래가 되었네  
  
[Final Chorus]  
그리워라 그 시절이여  
내 마음에 남은 사람아  
세월은 강물처럼 흘러도  
그 이름은 지워지지 않네  
  
그리워라 그 시절이여  
다시 못 올 나의 청춘아  
바람이 불어오는 저 길 끝에서  
오늘도 그대를 불러보네"""  
  
    return {  
        "title_options": title_options,  
        "suno_prompt": suno_prompt,  
        "style_prompt": style_prompt,  
        "lyrics": lyrics,  
    }  
  
  
st.set_page_config(  
    page_title=APP_TITLE,  
    page_icon="🎸",  
    layout="centered",  
)  
  
  
st.markdown(  
    """  
<style>  
.stApp {  
    background: #fff7ed;  
    color: #2f1b0c;  
}  
  
.block-container {  
    max-width: 980px;  
    padding-top: 2rem;  
    padding-bottom: 4rem;  
}  
  
h1, h2, h3, h4, p, label, span, div {  
    color: #2f1b0c !important;  
}  
  
.main-card {  
    background: #ffedd5;  
    border: 2px solid #fed7aa;  
    border-radius: 24px;  
    padding: 26px;  
    margin-bottom: 22px;  
}  
  
.result-card {  
    background: #ffffff;  
    border: 2px solid #f59e0b;  
    border-radius: 24px;  
    padding: 26px;  
    margin-top: 24px;  
}  
  
.help-box {  
    background: #fef3c7;  
    border-left: 7px solid #d97706;  
    border-radius: 16px;  
    padding: 16px;  
    font-size: 18px;  
    line-height: 1.7;  
    margin-bottom: 20px;  
}  
  
textarea, input {  
    background-color: #ffffff !important;  
    color: #2f1b0c !important;  
    border: 2px solid #f59e0b !important;  
    border-radius: 14px !important;  
    font-size: 18px !important;  
}  
  
div[data-baseweb="select"] > div {  
    background-color: #ffffff !important;  
    border: 2px solid #f59e0b !important;  
    border-radius: 14px !important;  
    min-height: 58px !important;  
    font-size: 18px !important;  
}  
  
.stButton > button,  
.stDownloadButton > button,  
div[data-testid="stFormSubmitButton"] button {  
    background: #b45309 !important;  
    color: #fff7ed !important;  
    border: 2px solid #92400e !important;  
    border-radius: 16px !important;  
    min-height: 58px !important;  
    font-weight: 900 !important;  
    font-size: 19px !important;  
}  
  
.stTextArea textarea {  
    font-size: 18px !important;  
    line-height: 1.6 !important;  
}  
  
.small-caption {  
    font-size: 16px;  
    color: #7c2d12 !important;  
}  
</style>  
""",  
    unsafe_allow_html=True,  
)  
  
  
st.title("🎸 추억의 7080 노래 생성기")  
st.caption("몇 번만 선택하면 제목, Suno 프롬프트, 스타일 프롬프트, 가사가 바로 만들어집니다.")  
  
  
api_key = get_openai_api_key()  
  
with st.sidebar:  
    st.header("설정")  
    use_openai = st.checkbox("OpenAI로 생성하기", value=True)  
    model = st.text_input("OpenAI 모델", value=os.getenv("OPENAI_MODEL", DEFAULT_MODEL))  
  
    if api_key:  
        st.success("OpenAI API 키가 연결되어 있습니다.")  
    else:  
        st.warning("API 키가 없으면 기본 예시 방식으로 생성됩니다.")  
  
    st.markdown("---")  
    st.caption("초보자용 앱이므로 복잡한 설정은 숨겼습니다.")  
  
  
st.markdown(  
    """  
<div class="help-box">  
    아래 항목을 차례대로 고른 뒤 <b>노래 만들기</b> 버튼만 누르세요.  
    실제 7080 노래를 따라 하지 않고, 그 시절의 정서만 담아 새 노래를 만듭니다.  
</div>  
""",  
    unsafe_allow_html=True,  
)  
  
  
with st.container():  
    st.markdown('<div class="main-card">', unsafe_allow_html=True)  
  
    mood = st.selectbox("1. 어떤 분위기의 노래를 만들까요?", MOOD_OPTIONS)  
    style = st.selectbox("2. 음악 스타일을 골라주세요", STYLE_OPTIONS)  
    vocal = st.selectbox("3. 보컬을 골라주세요", VOCAL_OPTIONS)  
    length = st.selectbox("4. 곡 길이", LENGTH_OPTIONS, index=1)  
  
    user_note = st.text_area(  
        "5. 넣고 싶은 말이 있다면 적어주세요",  
        placeholder="예: 오래전 첫사랑을 떠올리는 노래 / 부모님께 들려드리고 싶은 따뜻한 노래",  
        height=120,  
    )  
  
    st.markdown("</div>", unsafe_allow_html=True)  
  
  
generate = st.button("🎵 노래 만들기", type="primary", use_container_width=True)  
  
  
if generate:  
    try:  
        with st.spinner("노래를 만들고 있습니다..."):  
            if use_openai and api_key:  
                result = generate_with_openai(  
                    api_key=api_key,  
                    model=model.strip() or DEFAULT_MODEL,  
                    mood=mood,  
                    style=style,  
                    vocal=vocal,  
                    length=length,  
                    user_note=user_note,  
                )  
                source = f"OpenAI 생성 · {model.strip() or DEFAULT_MODEL}"  
            else:  
                result = generate_rule_based(  
                    mood=mood,  
                    style=style,  
                    vocal=vocal,  
                    length=length,  
                    user_note=user_note,  
                )  
                source = "기본 예시 생성"  
  
    except Exception as e:  
        st.warning(f"OpenAI 생성에 실패해 기본 예시 방식으로 만들었습니다. 오류: {e}")  
        result = generate_rule_based(  
            mood=mood,  
            style=style,  
            vocal=vocal,  
            length=length,  
            user_note=user_note,  
        )  
        source = "기본 예시 생성"  
  
    titles_text = "\n".join(  
        [f"{idx}. {title}" for idx, title in enumerate(result["title_options"], start=1)]  
    )  
  
    full_text = f"""[제목 후보]  
{titles_text}  
  
[Suno 프롬프트]  
{result["suno_prompt"]}  
  
[음악 스타일 프롬프트]  
{result["style_prompt"]}  
  
[가사]  
{result["lyrics"]}  
"""  
  
    style_and_lyrics = f"""[음악 스타일 프롬프트]  
{result["style_prompt"]}  
  
[가사]  
{result["lyrics"]}  
"""  
  
    st.markdown('<div class="result-card">', unsafe_allow_html=True)  
    st.header("🎧 생성 결과")  
    st.caption(f"생성 방식: {source} · {datetime.now().strftime('%Y-%m-%d %H:%M')}")  
  
    st.subheader("1. 제목 후보")  
    col1, col2 = st.columns([0.7, 0.3])  
    with col2:  
        render_copy_button("제목 복사", titles_text, "copy_titles")  
    st.text_area("제목 후보 결과", value=titles_text, height=160)  
  
    st.subheader("2. Suno 프롬프트")  
    col1, col2 = st.columns([0.7, 0.3])  
    with col2:  
        render_copy_button("Suno 복사", result["suno_prompt"], "copy_suno")  
    st.text_area("Suno 프롬프트 결과", value=result["suno_prompt"], height=130)  
  
    st.subheader("3. 음악 스타일 프롬프트")  
    col1, col2 = st.columns([0.7, 0.3])  
    with col2:  
        render_copy_button("스타일 복사", result["style_prompt"], "copy_style")  
    st.text_area("음악 스타일 프롬프트 결과", value=result["style_prompt"], height=220)  
  
    st.subheader("4. 가사")  
    col1, col2 = st.columns([0.7, 0.3])  
    with col2:  
        render_copy_button("가사 복사", result["lyrics"], "copy_lyrics")  
    st.text_area("가사 결과", value=result["lyrics"], height=560)  
  
    st.subheader("5. 한 번에 복사")  
    render_copy_button("음악 스타일 + 가사 한 번에 복사", style_and_lyrics, "copy_all")  
  
    st.download_button(  
        "📄 텍스트 파일로 저장",  
        data=full_text,  
        file_name="7080_song_result.txt",  
        mime="text/plain",  
        use_container_width=True,  
    )  
  
    st.markdown("</div>", unsafe_allow_html=True)  
