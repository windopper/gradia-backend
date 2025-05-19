from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv
import re
from typing import Optional
from jinja2 import Environment, FileSystemLoader

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
