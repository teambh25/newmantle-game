import datetime
from zoneinfo import ZoneInfo

CONSONANTS = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']    


def extract_initial_consonant(word: str) -> str:
    return "".join([CONSONANTS[get_initial_consonant_index(c)] for c in word])


def get_today_date():
    return datetime.datetime.now(ZoneInfo("Asia/Seoul")).date()


def get_day_after_tomorrow_1am(date: datetime.date):
    return datetime.datetime.combine(
        date + datetime.timedelta(days=1),
        datetime.time(hour=16, minute=0, second=0)
    )  # two days later 1 am (KST, UTC+9)


def get_initial_consonant_index(ch: str):
    return (ord(ch) - ord('가')) // (21 * 28)  # 한국어 유니코드 시작은 "가", 중성과 종성의 조합의 수 = 21 * 28


def is_hangul_char(ch: str) -> bool:
    """ function currently returns True only for 가~힣 """
    code = ord(ch)
    return 0xAC00 <= code <= 0xD7A3  # 가 ~ 힣


def is_hangul_string(s: str) -> bool:
    return s != "" and all(is_hangul_char(ch) for ch in s)