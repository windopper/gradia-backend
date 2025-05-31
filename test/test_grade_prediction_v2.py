from typing import Optional
import re
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from utils.learning_pattern_analyser import LearningPatternAnalyzer
import os
import sys
from datetime import datetime

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 현재 작업 디렉토리도 추가
if project_root not in sys.path:
    sys.path.append(project_root)

# 환경 변수 로드
load_dotenv()


def parse_v2_prediction_response(prediction_text: str) -> Optional[dict]:
    """
    v2 템플릿에 맞는 XML 응답을 파싱하여 구조화된 데이터로 변환
    """
    try:
        # 기본 예측 정보
        score_match = re.search(r"<score>(.*?)</score>", prediction_text)
        score_range_match = re.search(
            r"<score_range>(.*?)</score_range>", prediction_text)
        grade_match = re.search(r"<grade>(.*?)</grade>", prediction_text)
        confidence_match = re.search(
            r"<confidence>(.*?)</confidence>", prediction_text)

        # 분석 정보
        learning_volume_match = re.search(
            r"<learning_volume>(.*?)</learning_volume>", prediction_text, re.DOTALL)
        learning_quality_match = re.search(
            r"<learning_quality>(.*?)</learning_quality>", prediction_text, re.DOTALL)
        learning_consistency_match = re.search(
            r"<learning_consistency>(.*?)</learning_consistency>", prediction_text, re.DOTALL)

        # 주요 요인들
        factors_matches = re.findall(
            r"<factor>(.*?)</factor>", prediction_text)

        # 개인화된 조언
        priority_high_match = re.search(
            r"<priority_high>.*?<point>(.*?)</point>.*?</priority_high>", prediction_text, re.DOTALL)
        optimization_match = re.search(
            r"<optimization>.*?<point>(.*?)</point>.*?</optimization>", prediction_text, re.DOTALL)
        maintenance_match = re.search(
            r"<maintenance>.*?<point>(.*?)</point>.*?</maintenance>", prediction_text, re.DOTALL)

        # 주간 계획
        target_hours_match = re.search(
            r"<target_hours>(.*?)</target_hours>", prediction_text)
        target_sessions_match = re.search(
            r"<target_sessions>(.*?)</target_sessions>", prediction_text)
        focus_areas_match = re.search(
            r"<focus_areas>(.*?)</focus_areas>", prediction_text)

        structured_prediction = {
            "score": score_match.group(1) if score_match else None,
            "score_range": score_range_match.group(1) if score_range_match else None,
            "grade": grade_match.group(1) if grade_match else None,
            "confidence": confidence_match.group(1) if confidence_match else None,
            "analysis": {
                "learning_volume": learning_volume_match.group(1).strip() if learning_volume_match else None,
                "learning_quality": learning_quality_match.group(1).strip() if learning_quality_match else None,
                "learning_consistency": learning_consistency_match.group(1).strip() if learning_consistency_match else None
            },
            "key_factors": factors_matches,
            "personalized_advice": {
                "priority_high": priority_high_match.group(1).strip() if priority_high_match else None,
                "optimization": optimization_match.group(1).strip() if optimization_match else None,
                "maintenance": maintenance_match.group(1).strip() if maintenance_match else None
            },
            "weekly_plan": {
                "target_hours": target_hours_match.group(1) if target_hours_match else None,
                "target_sessions": target_sessions_match.group(1) if target_sessions_match else None,
                "focus_areas": focus_areas_match.group(1) if focus_areas_match else None
            }
        }

        return structured_prediction

    except Exception as regex_error:
        print(f"v2 템플릿 파싱 오류: {regex_error}")
        return None


def get_mock_subject_data():
    """Mock 과목 데이터"""
    return {
        "id": "math_101",
        "name": "미적분학",
        "description": "대학 수학 기초 과목"
    }


def get_mock_study_sessions():
    """Mock 학습 세션 데이터 - learning_pattern_analyser.py의 샘플 데이터 사용"""
    return [
        # 4월 첫째 주 - 초기 학습 시작
        {
            "id": "session_001",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-04-01",
            "study_time": 60,
            "start_time": "2025-04-01T09:00:00.000Z",
            "end_time": "2025-04-01T10:00:00.000Z",
            "rest_time": 0,
            "focus_level": 3,
            "memo": "미적분 기초 개념"
        },
        {
            "id": "session_002",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-04-03",
            "study_time": 90,
            "start_time": "2025-04-03T14:00:00.000Z",
            "end_time": "2025-04-03T15:30:00.000Z",
            "rest_time": 0,
            "focus_level": 4,
            "memo": "극한 개념 학습"
        },
        {
            "id": "session_003",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-04-07",
            "study_time": 120,
            "start_time": "2025-04-07T09:30:00.000Z",
            "end_time": "2025-04-07T11:45:00.000Z",
            "rest_time": 15,
            "focus_level": 4,
            "memo": "미분 연습문제"
        },
        {
            "id": "session_004",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-04-08",
            "study_time": 105,
            "start_time": "2025-04-08T10:00:00.000Z",
            "end_time": "2025-04-08T11:45:00.000Z",
            "rest_time": 0,
            "focus_level": 5,
            "memo": "연쇄법칙 마스터"
        },
        {
            "id": "session_005",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-04-10",
            "study_time": 90,
            "start_time": "2025-04-10T09:00:00.000Z",
            "end_time": "2025-04-10T10:30:00.000Z",
            "rest_time": 0,
            "focus_level": 4,
            "memo": "적분 기초"
        },
        # 최근 데이터 (더 높은 집중도)
        {
            "id": "session_029",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-05-21",
            "study_time": 150,
            "start_time": "2025-05-21T08:30:00.000Z",
            "end_time": "2025-05-21T11:00:00.000Z",
            "rest_time": 0,
            "focus_level": 5,
            "memo": "종합 실력 테스트"
        },
        {
            "id": "session_030",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-05-22",
            "study_time": 120,
            "start_time": "2025-05-22T09:00:00.000Z",
            "end_time": "2025-05-22T11:00:00.000Z",
            "rest_time": 0,
            "focus_level": 5,
            "memo": "최고 난이도 도전"
        },
        {
            "id": "session_031",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-05-24",
            "study_time": 135,
            "start_time": "2025-05-24T09:00:00.000Z",
            "end_time": "2025-05-24T11:15:00.000Z",
            "rest_time": 0,
            "focus_level": 5,
            "memo": "완벽 마스터"
        },
        {
            "id": "session_032",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-05-25",
            "study_time": 90,
            "start_time": "2025-05-25T10:00:00.000Z",
            "end_time": "2025-05-25T11:30:00.000Z",
            "rest_time": 0,
            "focus_level": 4,
            "memo": "마무리 정리"
        }
    ]


async def test_grade_prediction_v2():
    """Grade Prediction V2 로직 테스트"""

    print("=== Grade Prediction V2 테스트 시작 ===\n")

    # Mock 데이터 준비
    subject_data = get_mock_subject_data()
    study_sessions = get_mock_study_sessions()
    understanding_level = 4  # 1-5 범위

    print(f"과목: {subject_data['name']}")
    print(f"이해도 수준: {understanding_level}/5")
    print(f"학습 세션 수: {len(study_sessions)}개")
    print("-" * 50)

    # 학습 패턴 분석
    analyzer = LearningPatternAnalyzer(study_sessions)
    learning_pattern_analysis = analyzer.analyze_all_patterns()

    print("=== 학습 패턴 분석 결과 ===")
    print(f"총 세션 수: {learning_pattern_analysis['total_sessions']}")
    print(f"총 실제 학습 시간: {learning_pattern_analysis['total_actual_hours']}시간")
    print(f"평균 집중도: {learning_pattern_analysis['avg_focus_level']}")
    print(f"최근 일주일 학습 시간: {learning_pattern_analysis['recent_week_hours']}시간")
    print(f"최근 일주일 평균 집중도: {learning_pattern_analysis['recent_week_focus']}")
    print(f"학습 시간대 분포: {learning_pattern_analysis['time_distribution']}")
    print(f"주간 평균 학습 일수: {learning_pattern_analysis['study_days_per_week']}일")
    print(f"평균 세션 길이: {learning_pattern_analysis['avg_session_length']}분")
    print(f"학습 일관성 점수: {learning_pattern_analysis['consistency_score']}/5")
    print(f"집중도 트렌드: {learning_pattern_analysis['focus_trend']}")
    print("-" * 50)

    # Google API 키 확인
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("⚠️  GOOGLE_API_KEY가 설정되지 않았습니다. AI 예측을 건너뜁니다.")
        return

    try:
        # AI 모델 설정
        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-preview-04-17", temperature=0.4)

        # Jinja2 템플릿 로드 및 렌더링
        template_search_path = os.path.join(project_root, 'templates')
        env = Environment(loader=FileSystemLoader(
            searchpath=template_search_path), trim_blocks=True, lstrip_blocks=True)

        template = env.get_template("grade_prediction_template_v2.jinja2")
        final_prompt_str = template.render(
            subject_name=subject_data["name"],
            understanding_level=understanding_level,
            total_sessions=learning_pattern_analysis["total_sessions"],
            total_actual_hours=learning_pattern_analysis["total_actual_hours"],
            avg_focus_level=learning_pattern_analysis["avg_focus_level"],
            recent_week_hours=learning_pattern_analysis["recent_week_hours"],
            recent_week_focus=learning_pattern_analysis["recent_week_focus"],
            time_distribution=learning_pattern_analysis["time_distribution"],
            study_days_per_week=learning_pattern_analysis["study_days_per_week"],
            avg_session_length=learning_pattern_analysis["avg_session_length"],
            consistency_score=learning_pattern_analysis["consistency_score"],
            focus_trend=learning_pattern_analysis["focus_trend"]
        )

        print("=== 생성된 프롬프트 미리보기 ===")
        print(final_prompt_str[:500] +
              "..." if len(final_prompt_str) > 500 else final_prompt_str)
        print("-" * 50)

        # AI 예측 실행
        prompt_template = ChatPromptTemplate.from_template(final_prompt_str)
        output_parser = StrOutputParser()
        chain = prompt_template | model | output_parser

        print("=== AI 예측 실행 중... ===")
        prediction_text = await chain.ainvoke({})

        print("=== AI 원본 응답 ===")
        print(prediction_text)
        print("-" * 50)

        # 구조화된 파싱
        structured_prediction = parse_v2_prediction_response(prediction_text)

        if structured_prediction:
            print("=== 구조화된 예측 결과 ===")
            print(f"예상 점수: {structured_prediction.get('score', 'N/A')}")
            print(f"점수 범위: {structured_prediction.get('score_range', 'N/A')}")
            print(f"예상 등급: {structured_prediction.get('grade', 'N/A')}")
            print(f"신뢰도: {structured_prediction.get('confidence', 'N/A')}")

            if structured_prediction.get('analysis'):
                print("\n📊 분석 결과:")
                print(
                    f"  학습량: {structured_prediction['analysis'].get('learning_volume', 'N/A')}")
                print(
                    f"  학습품질: {structured_prediction['analysis'].get('learning_quality', 'N/A')}")
                print(
                    f"  학습일관성: {structured_prediction['analysis'].get('learning_consistency', 'N/A')}")

            if structured_prediction.get('key_factors'):
                print(f"\n🔑 주요 요인들:")
                for i, factor in enumerate(structured_prediction['key_factors'], 1):
                    print(f"  {i}. {factor}")

            if structured_prediction.get('personalized_advice'):
                advice = structured_prediction['personalized_advice']
                print(f"\n💡 개인화된 조언:")
                if advice.get('priority_high'):
                    print(f"  우선순위 높음: {advice['priority_high']}")
                if advice.get('optimization'):
                    print(f"  최적화 방안: {advice['optimization']}")
                if advice.get('maintenance'):
                    print(f"  유지 방안: {advice['maintenance']}")

            if structured_prediction.get('weekly_plan'):
                plan = structured_prediction['weekly_plan']
                print(f"\n📅 주간 계획:")
                print(f"  목표 시간: {plan.get('target_hours', 'N/A')}")
                print(f"  목표 세션 수: {plan.get('target_sessions', 'N/A')}")
                print(f"  집중 영역: {plan.get('focus_areas', 'N/A')}")
        else:
            print("⚠️  구조화된 파싱에 실패했습니다.")

        print("\n=== 테스트 완료 ===")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_grade_prediction_v2())
