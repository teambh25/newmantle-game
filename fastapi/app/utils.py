import datetime
from zoneinfo import ZoneInfo

CONSONANTS = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']    


def extract_initial_consonant(word: str) -> str:
    return "".join([CONSONANTS[get_initial_consonant_index(c)] for c in word])


def get_today_date():
    return datetime.datetime.now(ZoneInfo("Asia/Seoul")).date()


def get_initial_consonant_index(c: str):
    return (ord(c) - ord('가')) // (21 * 28)  # 한국어 유니코드 시작은 "가", 중성과 종성의 조합의 수 = 21 * 28