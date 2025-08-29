
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from keyword_maker import extract_keywords

sample_text = "일론 머스크 테슬라 최고경영자(CEO)가 설립한 인공지능(AI) 스타트업 xAI가 애플과 오픈AI에 반독점 소송을 제기했다. 두 회사가 AI기업 간 경쟁을 불법적으로 방해한다는 이유다. 25일(현지시간) 월스트리트저널에 따르면 xAI는 아이폰 제조사인 애플이 오픈AI를"

keywords = extract_keywords(sample_text)
print(keywords)
