"""
summarize.py
─────────────────────────────────────────────────────
Gemini 2.5 Flash로 영상 자막을 요약.
"""

import os
import google.generativeai as genai


SUMMARY_PROMPT = """당신은 경제·금융 영상의 핵심을 정확하고 간결하게 추출하는 분석가입니다.
사용자는 국제금융을 전공한 연구자로, 시간이 제한적이며 핵심 인사이트만 빠르게 파악하길 원합니다.

아래는 유튜브 영상의 자막입니다. 다음 형식으로 한국어로 요약해주세요:

【한 줄 요약】
영상의 핵심 메시지를 한 문장으로.

【핵심 포인트 3가지】
1. 첫 번째 핵심 (구체적 수치·인과관계 포함)
2. 두 번째 핵심
3. 세 번째 핵심

【주목할 만한 인용】
영상에서 가장 인상적인 발언 한 문장 (있다면, 없으면 생략)

【투자/정책 시사점】
연구자·투자자에게 의미 있는 한두 줄 (해당사항 없으면 생략)

────────────────────
영상 제목: {title}
채널: {channel}
────────────────────

[자막 시작]
{transcript}
[자막 끝]

위 형식을 정확히 따르되, 불필요한 수식어는 배제하고 정보 밀도를 높여주세요.
"""


SHORT_PROMPT = """다음 유튜브 영상 정보만으로 무엇에 관한 영상인지 한 문장으로 추측해주세요.
자막이 없어 정확한 요약은 불가능합니다. 추측이라는 점을 명시해주세요.

제목: {title}
채널: {channel}
"""


def summarize_video(
    title: str,
    channel: str,
    transcript: str,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
) -> str:
    """
    영상을 요약. 자막이 있으면 본격 요약, 없으면 제목만으로 짧은 추측.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    if transcript and len(transcript.strip()) > 100:
        prompt = SUMMARY_PROMPT.format(
            title=title,
            channel=channel,
            transcript=transcript,
        )
        print(f"[summarize] '{title[:40]}...' 본격 요약 중...")
    else:
        prompt = SHORT_PROMPT.format(title=title, channel=channel)
        print(f"[summarize] '{title[:40]}...' 자막 없음, 제목 기반 추측")
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[summarize] ❌ Gemini API 오류: {type(e).__name__}: {e}")
        return f"⚠️ 요약 생성 실패: {e}"


if __name__ == "__main__":
    # 단독 실행 시 테스트 (API 키는 환경변수에서)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("환경변수 GEMINI_API_KEY가 필요합니다.")
        exit(1)
    
    result = summarize_video(
        title="테스트 영상",
        channel="테스트 채널",
        transcript="이것은 테스트 자막입니다. " * 20,
        api_key=api_key,
    )
    print(result)
