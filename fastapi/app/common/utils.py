import datetime
from zoneinfo import ZoneInfo

def dist_to_score(min_dist: float, max_dist: float, dist: float):
    return round((max_dist-dist) / (max_dist-min_dist) * 100, 2) # min-max scaling for cosine distance

CONSONANTS = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ','ㅎ']
get_initial_consonant_index = lambda c: (ord(c) - ord('가')) // (21 * 28) # 한국어 유니코드 시작은 "가", 중성과 종성의 조합의 수 = 21 * 28
def extract_initial_consonant(word:str)->str:   
    return "".join([CONSONANTS[get_initial_consonant_index(c)] for c in word])