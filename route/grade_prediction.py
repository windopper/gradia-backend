from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv
import re
from typing import Optional
from jinja2 import Environment, FileSystemLoader
from utils.learning_pattern_analyser import LearningPatternAnalyzer
from db.study_session import get_study_sessions_by_subject_id
from db.subject import get_subject_by_id
from firebase_admin import firestore_async
from dependencies import get_db
load_dotenv()

router = APIRouter()

current_script_path = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(current_script_path, 'templates')

project_root = os.path.dirname(current_script_path)
template_search_path = os.path.join(project_root, 'templates')

if not os.path.isdir(template_search_path):
    # fallback: route 폴더 내의 templates 폴더 (이전 커밋에서 생성한 위치일 수도 있음)
    template_search_path = os.path.join(current_script_path, 'templates')
    if not os.path.isdir(template_search_path):
        # fallback: 현재 작업 디렉토리 기준 (main.py 등에서 실행될 때)
        template_search_path = 'templates'

env = Environment(loader=FileSystemLoader(
    searchpath=template_search_path), trim_blocks=True, lstrip_blocks=True)


def parse_v2_prediction_response(prediction_text: str) -> Optional[dict]:
    """
    v2 템플릿에 맞는 XML 응답을 파싱하여 구조화된 데이터로 변환

    Args:
        prediction_text (str): AI 모델로부터 받은 XML 형식의 예측 결과

    Returns:
        Optional[dict]: 파싱된 구조화된 예측 데이터, 파싱 실패 시 None
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


class GradePredictionRequest(BaseModel):
    subject_name: str
    understanding_level: int = Field(..., ge=1, le=5)
    study_time_hours: float
    assignment_quiz_avg_score: Optional[float] = Field(
        default=None, ge=0, le=100)


class PredictionResponse(BaseModel):
    raw_prediction: str
    structured_prediction: Optional[dict] = None


@router.post("/")
async def predict_grade(request: GradePredictionRequest):
    """
    과목 성적 예측 서비스
    입력: 과목명, 이해 수준, 학습 시간, 과제/퀴즈 평균 점수
    출력: XML 원본 및 파싱된 JSON 형식의 예측 결과 (예상 점수, 예측 근거, 구체적 조언)
    """
    try:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            return {"prediction": f"{request.subject_name} 과목의 예상 점수를 계산할 수 없습니다. API 키가 설정되지 않았습니다."}

        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-04-17",
                                       temperature=0.4)

        # Jinja2 템플릿 로드 및 렌더링
        try:
            template = env.get_template("prompt_template.jinja2")
            final_prompt_str = template.render(
                subject_name=request.subject_name,
                understanding_level=request.understanding_level,
                study_time_hours=request.study_time_hours,
                assignment_quiz_avg_score=request.assignment_quiz_avg_score
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"프롬프트 템플릿 처리 중 오류 발생: {str(e)}")

        prompt_template = ChatPromptTemplate.from_template(final_prompt_str)
        output_parser = StrOutputParser()
        chain = prompt_template | model | output_parser

        prediction_text = await chain.ainvoke({})
        # XML 응답 파싱 시도
        structured_prediction = None
        try:
            score_match = re.search(r"<score>(.*?)</score>", prediction_text)
            score_range_match = re.search(
                r"<score_range>(.*?)</score_range>", prediction_text)
            grade_match = re.search(r"<grade>(.*?)</grade>", prediction_text)
            factors_matches = re.findall(
                r"<factor>(.*?)</factor>", prediction_text)
            advice_matches = re.findall(
                r"<point>(.*?)</point>", prediction_text)

            structured_prediction = {
                "score": score_match.group(1) if score_match else None,
                "score_range": score_range_match.group(1) if score_range_match else None,
                "grade": grade_match.group(1) if grade_match else None,
                "factors": factors_matches,
                "advice": advice_matches
            }
        except Exception as regex_error:
            print(f"정규식 처리 오류: {regex_error}")
            pass

        return PredictionResponse(raw_prediction=prediction_text, structured_prediction=structured_prediction)

    except HTTPException as http_exc:  # HTTPException을 다시 발생시키기 전에 그대로 전달
        raise http_exc
    except Exception as e:
        # 다른 예외들에 대한 로깅을 추가할 수 있습니다.
        print(f"예상치 못한 오류 발생: {e}")
        raise HTTPException(
            status_code=500, detail=f"성적 예측 중 내부 서버 오류 발생: {str(e)}")


class GradePredictionRequestV2(BaseModel):
    # 기본 정보
    subject_id: str
    understanding_level: int = Field(..., ge=1, le=5)


class PredictionResponseV2(BaseModel):
    raw_prediction: str
    learning_pattern_analysis: dict
    structured_prediction: Optional[dict] = None


@router.post("/v2")
async def predict_grade_v2(request: GradePredictionRequestV2,
                           db_client: firestore_async.AsyncClient = Depends(get_db)):
    """
    향상된 과목 성적 예측 서비스 (v2)
    입력: 기본 정보 + 학습 세션 로그 분석 데이터 + 학습 패턴 분석
    출력: 더 정확한 예측과 개인화된 학습 조언
    """
    try:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            return {"prediction": f"{request.subject_name} 과목의 예상 점수를 계산할 수 없습니다. API 키가 설정되지 않았습니다."}

        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-04-17",
                                       temperature=0.2)

        subject_data = await get_subject_by_id(request.subject_id, db_client)
        study_sessions = await get_study_sessions_by_subject_id(
            request.subject_id, db_client)
        analayzer = LearningPatternAnalyzer(study_sessions)
        learning_pattern_analysis = analayzer.analyze_all_patterns()

        # Jinja2 템플릿 로드 및 렌더링
        try:
            template = env.get_template("grade_prediction_template_v2.jinja2")
            final_prompt_str = template.render(
                subject_name=subject_data["name"],
                understanding_level=request.understanding_level,
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
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"프롬프트 템플릿 처리 중 오류 발생: {str(e)}")

        prompt_template = ChatPromptTemplate.from_template(final_prompt_str)
        output_parser = StrOutputParser()
        chain = prompt_template | model | output_parser

        prediction_text = await chain.ainvoke({})

        # v2 템플릿 파싱 로직을 분리된 함수로 호출
        structured_prediction = parse_v2_prediction_response(prediction_text)

        return PredictionResponseV2(raw_prediction=prediction_text, learning_pattern_analysis=learning_pattern_analysis, structured_prediction=structured_prediction)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
        raise HTTPException(
            status_code=500, detail=f"성적 예측 v2 중 내부 서버 오류 발생: {str(e)}")
