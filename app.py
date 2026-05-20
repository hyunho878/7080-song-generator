import os
import re
import json
import html
import random
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

APP_TITLE = "추억의 7080 노래 생성기"
DEFAULT_MODEL = "gpt-5.2-mini"

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

MOOD_HELP_TEXT = """
예시를 참고해서 한 문장 또는 여러 줄로 자유롭게 적어주세요.<br><br>
<b>예시 1</b><br>
새벽 첫차가 지나간 뒤 우동집 불빛 아래 혼자 앉아 있는 느낌. 겨울 골목 감성.<br><br>
<b>예시 2</b><br>
여름 운동회가 끝난 저녁 학교 운동장. 먼 곳으로 떠난 친구들을 떠올리는 분위기.<br><br>
<b>예시 3</b><br>
가을 저녁 시외버스터미널에서 누군가를 기다리는 마음. 오래된 스피커 방송 소리와 낡은 벤치 느낌.
"""

CLICHE_BAN = """
같은 이미지 반복 금지:
- 비 오는 창가
- 식은 커피
- 보내지 못한 편지
- 라디오만 반복 등장
- 다방만 반복 등장
- 같은 후렴 반복 복사

매번 새로운 장소와 생활 장면 사용할 것:
시장 골목, 시외버스터미널, 운동회,
포장마차, 공장 퇴근길, 문방구,
연탄불, 기차 건널목, 옥상 평상,
여름 선풍기 바람, 작은 극장 앞,
동네 이발소, 오래된 사진관 등.
"""


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
            min-height:52px;
            border-radius:15px;
            border:1px solid #92400e;
            background:#b45309;
            color:#fff7ed;
            font-weight:900;
            font-size:18px;
            cursor:pointer;
        ">{html.escape(label)}</button>
        <script>
        const button = document.getElementById("copy-{safe_key}");
        button.addEventListener("click", async () => {{
            await navigator.clipboard.writeText({payload});
            button.innerText = "복사 완료";
            setTimeout(() => {{ button.innerText = {json.dumps(label, ensure_ascii=False)}; }}, 1300);
        }});
        </script>
        """,
        height=64,
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

    system_prompt = f"""
너는 7080 한국 가요 감성의 노래를 만드는 작사가이자 음악 프롬프트 전문가다.

목표:
60~70대가 편하게 들을 수 있는 추억, 고향, 사랑, 인생 회상 중심의 노래를 만든다.

절대 금지:
- 실제 가수 이름 언급 금지
- 실제 노래 제목 모방 금지
- 기존 가사 인용 금지
- 랩, EDM, 아이돌, 힙합 표현 금지
- 과도하게 뻔한 표현 반복 금지

{CLICHE_BAN}

반드시:
- 쉬운 한국어
- 생활감 있는 장면 중심
- 따라 부르기 쉬운 후렴
- 새로운 장소와 기억 사용
- 완전히 새로운 창작 가사
- 반환은 반드시 JSON만 한다.
"""

    user_prompt = f"""
아래 입력값으로 새로운 7080 감성 노래를 만들어줘.

[입력값]
사용자가 직접 쓴 노래 분위기: {mood}
음악 스타일: {style}
보컬: {vocal}
곡 길이: {length}
추가 요청: {user_note or "없음"}

[반환 형식]
{{
  "title_options": ["제목1", "제목2", "제목3", "제목4", "제목5"],
  "suno_prompt": "영어 태그",
  "style_prompt": "스타일 설명",
  "lyrics": "한국어 가사"
}}

가사 구조:
[Verse 1]
[Chorus]
[Verse 2]
[Bridge]
[Final Chorus]

중요:
- 생활감 있는 장면 사용
- 같은 소재 반복 금지
- 실제 7080처럼 담백하게
- 억지로 슬프게 만들지 말 것
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
    scene_pool = [
        "겨울 연탄불 앞 골목",
        "시외버스터미널 마지막 버스",
        "늦은 밤 포장마차 불빛",
        "학교 운동장 조회대",
        "옥상 평상 위 선풍기 바람",
        "동네 문방구 앞 노을",
        "공장 퇴근길 작업복",
        "기차 건널목 종소리",
        "작은 극장 앞 매표소",
        "시장 골목 생선가게 불빛",
    ]

    selected_scene = random.choice(scene_pool)
    note = user_note.strip() if user_note else ""
    main_image = mood.strip() or selected_scene

    title_options = [
        "그날의 골목길",
        "늦은 버스 정류장",
        "우리 동네 저녁빛",
        "지나간 여름 냄새",
        "다시 듣는 그 목소리",
    ]

    suno_prompt = (
        "70s Korean folk ballad, nostalgic, acoustic guitar, "
        "warm vintage vocal, emotional melody, retro atmosphere"
    )

    style_prompt = (
        f"{style} 스타일의 {vocal} 곡. "
        f"사용자가 입력한 분위기 '{main_image}' 중심의 생활형 7080 감성. "
        f"반복적인 다방/편지/비 이미지 대신 현실적인 장면과 추억 사용."
    )

    if note:
        style_prompt += f" 추가 요청 반영: {note}"

    lyrics = f"""
[Verse 1]
{selected_scene} 지나가던 바람 아래
낡은 운동화 끝이 천천히 멈춰 서네
멀리 들려오는 저녁 장사 소리
괜히 마음 한쪽이 뜨거워지네

{main_image}
그 시절 우리 모습 같아서
말없이 하늘만 바라보다가
괜히 이름 한번 불러보네

[Chorus]
세월 따라 멀어져 가도
마음은 아직 그 자리에
지워질 듯 흐려져 가도
추억은 다시 빛나네

세월 따라 흘러가도
우린 서로 기억하겠지
늦은 바람 스쳐 지나가면
그때 그 웃음 떠오르네

[Verse 2]
골목 끝 작은 불빛 아래
하루를 접던 사람들 웃음소리
돌아갈 수 없는 시간이라도
가끔은 꿈처럼 떠오르네

[Bridge]
바쁘게 살아온 시간 속에도
문득 멈춰 서는 밤이 있네
사라진 줄 알았던 마음들이
조용히 다시 살아나네

[Final Chorus]
세월 따라 멀어져 가도
우리 마음 남아 있으니
오늘도 오래된 기억 하나
조용히 꺼내어 본다
"""

    return {
        "title_options": title_options,
        "suno_prompt": suno_prompt,
        "style_prompt": style_prompt,
        "lyrics": lyrics,
    }


st.set_page_config(page_title=APP_TITLE, page_icon="🎸", layout="centered")

st.markdown(
    """
<style>
.stApp { background: #fff7ed; color: #2f1b0c; }
.block-container { max-width: 980px; padding-top: 1.4rem; padding-bottom: 4rem; }
.main-card { background: #ffedd5; border: 2px solid #fed7aa; border-radius: 24px; padding: 26px; margin-bottom: 22px; }
.result-card { background: #ffffff; border: 2px solid #f59e0b; border-radius: 24px; padding: 26px; margin-top: 24px; }
.help-box { background: #fef3c7; border-left: 7px solid #d97706; border-radius: 16px; padding: 16px; font-size: 18px; line-height: 1.7; margin-bottom: 20px; }
textarea, input { background-color: #ffffff !important; color: #2f1b0c !important; border: 2px solid #f59e0b !important; border-radius: 14px !important; font-size: 18px !important; }
.stButton > button { background: #b45309 !important; color: #fff7ed !important; border-radius: 16px !important; min-height: 60px !important; font-weight: 900 !important; font-size: 20px !important; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🎸 추억의 7080 노래 생성기")
st.caption("분위기를 직접 적으면 제목, Suno 프롬프트, 스타일 프롬프트, 가사가 생성됩니다.")

api_key = get_openai_api_key()

with st.sidebar:
    st.header("설정")
    use_openai = st.checkbox("OpenAI로 생성하기", value=True)
    model = st.text_input("OpenAI 모델", value=os.getenv("OPENAI_MODEL", DEFAULT_MODEL))

    if api_key:
        st.success("OpenAI API 키 연결 완료")
    else:
        st.warning("API 키가 없으면 기본 예시 방식으로 생성됩니다.")

st.markdown(
    """
<div class="help-box">
시간 + 장소 + 계절 + 감정을 함께 적으면 훨씬 자연스럽습니다.
</div>
""",
    unsafe_allow_html=True,
)

with st.container():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)

    st.markdown(MOOD_HELP_TEXT, unsafe_allow_html=True)

    mood = st.text_area(
        "1. 어떤 분위기의 노래를 만들까요?",
        height=180,
        placeholder="""
예:
겨울 새벽 우동집에서 혼자 창밖을 바라보는 느낌.
밖에는 첫눈이 내리고 오래된 난로가 있는 분위기.
""",
    ).strip()

    style = st.selectbox("2. 음악 스타일", STYLE_OPTIONS)
    vocal = st.selectbox("3. 보컬", VOCAL_OPTIONS)
    length = st.selectbox("4. 곡 길이", LENGTH_OPTIONS, index=1)

    user_note = st.text_area(
        "5. 추가 요청",
        height=130,
        placeholder="""
예:
너무 신파적이지 않게.
담백하고 현실적인 느낌.
후렴은 따라 부르기 쉽게.
""",
    )

    st.markdown("</div>", unsafe_allow_html=True)

generate = st.button("🎵 노래 만들기", use_container_width=True)

if generate:
    if not mood:
        st.warning("분위기를 먼저 입력해주세요.")
    else:
        try:
            with st.spinner("노래 생성 중..."):
                if use_openai and api_key:
                    result = generate_with_openai(
                        api_key,
                        model.strip() or DEFAULT_MODEL,
                        mood,
                        style,
                        vocal,
                        length,
                        user_note,
                    )
                    source = f"OpenAI 생성 · {model}"
                else:
                    result = generate_rule_based(mood, style, vocal, length, user_note)
                    source = "기본 생성"
        except Exception as e:
            st.warning(f"오류 발생: {e}")
            result = generate_rule_based(mood, style, vocal, length, user_note)
            source = "기본 생성"

        titles_text = "\n".join([f"{idx}. {title}" for idx, title in enumerate(result["title_options"], start=1)])

        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        st.header("🎧 생성 결과")
        st.caption(f"{source} · {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        st.subheader("제목 후보")
        render_copy_button("제목 복사", titles_text, "copy_titles")
        st.text_area("제목 결과", value=titles_text, height=150)

        st.subheader("Suno 프롬프트")
        render_copy_button("Suno 복사", result["suno_prompt"], "copy_suno")
        st.text_area("Suno 결과", value=result["suno_prompt"], height=120)

        st.subheader("스타일 프롬프트")
        render_copy_button("스타일 복사", result["style_prompt"], "copy_style")
        st.text_area("스타일 결과", value=result["style_prompt"], height=180)

        st.subheader("가사")
        render_copy_button("가사 복사", result["lyrics"], "copy_lyrics")
        st.text_area("가사 결과", value=result["lyrics"], height=650)

        st.markdown("</div>", unsafe_allow_html=True)
