import pandas as pd
from collections import Counter
from datetime import datetime, timedelta
import numpy as np


class LearningPatternAnalyzer:
    def __init__(self, sessions_data):
        """
        sessions_data: DB에서 가져온 학습 세션 로그 리스트
        [
            {
                "id": "string",
                "user_id": "string", 
                "subject_id": "string",
                "date": "2025-05-28",
                "study_time": 90,  # 분 단위
                "start_time": "2025-05-28T09:00:00.000Z",
                "end_time": "2025-05-28T10:30:00.000Z",
                "rest_time": 10,  # 분 단위
                "focus_level": 4,
                "memo": "string"
            },
            ...
        ]
        """
        self.sessions = pd.DataFrame(sessions_data)
        if len(self.sessions) == 0:
            return

        # 데이터 타입 변환
        self.sessions['start_time'] = pd.to_datetime(
            self.sessions['start_time'])
        self.sessions['end_time'] = pd.to_datetime(self.sessions['end_time'])
        self.sessions['date'] = pd.to_datetime(self.sessions['date']).dt.date

        # study_time을 사용 (실제 순수 학습 시간, 휴식 시간 제외)
        self.sessions['duration'] = self.sessions['study_time']  # 이미 분 단위
        self.sessions['hour'] = self.sessions['start_time'].dt.hour

    def get_time_distribution(self):
        """학습 시간대 분포 분석"""
        hour_counts = Counter(self.sessions['hour'])

        # 시간대별 구분
        morning = sum(hour_counts.get(h, 0) for h in range(6, 12))    # 06-11시
        afternoon = sum(hour_counts.get(h, 0) for h in range(12, 18))  # 12-17시
        evening = sum(hour_counts.get(h, 0) for h in range(18, 22))   # 18-21시
        night = sum(hour_counts.get(h, 0) for h in range(22, 24)) + \
            sum(hour_counts.get(h, 0) for h in range(0, 6))  # 22-05시

        total = morning + afternoon + evening + night
        if total == 0:
            return "데이터 없음"

        # 가장 높은 비율의 시간대 찾기
        time_ratios = {
            "오전 집중형": morning / total,
            "오후 집중형": afternoon / total,
            "저녁 집중형": evening / total,
            "야간 집중형": night / total
        }

        max_ratio = max(time_ratios.values())

        # 균등하게 분산된 경우 (가장 높은 비율이 40% 미만)
        if max_ratio < 0.4:
            return "균등 분포"
        elif max_ratio < 0.5:
            return "분산형"
        else:
            return max(time_ratios, key=time_ratios.get)

    def get_study_days_per_week(self):
        """주간 평균 학습 일수"""
        if len(self.sessions) == 0:
            return 0

        study_dates = set(self.sessions['date'])

        # 전체 기간의 주 수 계산
        min_date = min(study_dates)
        max_date = max(study_dates)
        total_weeks = max(1, (max_date - min_date).days / 7)

        return min(7, round(len(study_dates) / total_weeks, 1))

    def get_consistency_score(self):
        """학습 일관성 점수 (1-5점)"""
        if len(self.sessions) == 0:
            return 1

        study_dates = sorted(set(self.sessions['date']))

        if len(study_dates) < 3:
            return 1  # 데이터 부족

        # 1. 연속 학습일 분석
        consecutive_streaks = []
        current_streak = 1

        for i in range(1, len(study_dates)):
            days_diff = (study_dates[i] - study_dates[i-1]).days
            if days_diff == 1:
                current_streak += 1
            else:
                consecutive_streaks.append(current_streak)
                current_streak = 1
        consecutive_streaks.append(current_streak)

        # 2. 학습 간격의 표준편차 (낮을수록 일관적)
        gaps = [(study_dates[i] - study_dates[i-1]
                 ).days for i in range(1, len(study_dates))]
        gap_std = np.std(gaps) if gaps else 0

        # 3. 주별 학습 빈도 분석
        study_weeks = {}
        for date in study_dates:
            week_key = date.isocalendar()[:2]  # (year, week_number)
            study_weeks[week_key] = study_weeks.get(week_key, 0) + 1

        weekly_consistency = np.std(
            list(study_weeks.values())) if study_weeks else 10

        # 점수 계산 (여러 요소 종합)
        max_streak = max(consecutive_streaks)
        avg_streak = np.mean(consecutive_streaks)

        score = 1

        # 연속 학습일 점수
        if max_streak >= 7:
            score += 1.5
        elif max_streak >= 4:
            score += 1
        elif max_streak >= 2:
            score += 0.5

        # 평균 연속일 점수
        if avg_streak >= 3:
            score += 1
        elif avg_streak >= 2:
            score += 0.5

        # 간격 일관성 점수 (표준편차가 낮을수록 좋음)
        if gap_std <= 1:
            score += 1
        elif gap_std <= 2:
            score += 0.5

        # 주별 일관성 점수
        if weekly_consistency <= 1:
            score += 0.5

        return min(5, max(1, round(score)))

    def get_focus_trend(self, recent_days=14):
        """집중도 트렌드 분석"""
        # focus_level이 -1인 세션 제외
        valid_focus_sessions = self.sessions[self.sessions['focus_level'] != -1]

        if len(valid_focus_sessions) < 5:
            return "유지"  # 데이터 부족

        # 최근 N일과 그 이전 기간 비교
        recent_date = max(valid_focus_sessions['date'])
        cutoff_date = recent_date - timedelta(days=recent_days)

        recent_sessions = valid_focus_sessions[valid_focus_sessions['date'] > cutoff_date]
        older_sessions = valid_focus_sessions[valid_focus_sessions['date'] <= cutoff_date]

        if len(recent_sessions) < 3 or len(older_sessions) < 3:
            # 시간순으로 전반부/후반부 비교
            mid_point = len(valid_focus_sessions) // 2
            first_half = valid_focus_sessions.iloc[:mid_point]
            second_half = valid_focus_sessions.iloc[mid_point:]

            if len(first_half) == 0 or len(second_half) == 0:
                return "유지"

            first_avg = first_half['focus_level'].mean()
            second_avg = second_half['focus_level'].mean()
        else:
            first_avg = older_sessions['focus_level'].mean()
            second_avg = recent_sessions['focus_level'].mean()

        diff = second_avg - first_avg

        # 트렌드 판정 (0.3 이상 차이가 나야 의미있는 변화로 판정)
        if diff >= 0.3:
            return "향상"
        elif diff <= -0.3:
            return "하락"
        else:
            return "유지"

    def get_recent_week_data(self, days=7):
        """최근 N일 데이터"""
        recent_date = max(self.sessions['date'])
        cutoff_date = recent_date - timedelta(days=days-1)

        recent_sessions = self.sessions[self.sessions['date'] >= cutoff_date]

        total_hours = recent_sessions['duration'].sum() / 60  # 시간 단위

        # focus_level이 -1인 세션 제외하여 평균 집중도 계산
        valid_focus_sessions = recent_sessions[recent_sessions['focus_level'] != -1]
        avg_focus = valid_focus_sessions['focus_level'].mean() if len(
            valid_focus_sessions) > 0 else 0

        return {
            "recent_week_hours": round(total_hours, 1),
            "recent_week_focus": round(avg_focus, 1)
        }

    def _get_empty_analysis(self):
        """데이터가 없을 때 기본값"""
        return {
            "total_sessions": 0,
            "total_actual_hours": 0,
            "avg_focus_level": 0,
            "recent_week_hours": 0,
            "recent_week_focus": 0,
            "time_distribution": "데이터 없음",
            "study_days_per_week": 0,
            "avg_session_length": 0,
            "consistency_score": 1,
            "focus_trend": "유지"
        }

    def analyze_all_patterns(self, subject_id=None):
        """전체 패턴 분석 결과 반환"""

        # 특정 과목 필터링
        if subject_id:
            filtered_sessions = self.sessions[self.sessions['subject_id'] == subject_id]
            if len(filtered_sessions) > 0:
                analyzer = LearningPatternAnalyzer(
                    filtered_sessions.to_dict('records'))
                return analyzer.analyze_all_patterns()

        if len(self.sessions) == 0:
            return self._get_empty_analysis()

        recent_data = self.get_recent_week_data()

        # focus_level이 -1인 세션 제외하여 평균 집중도 계산
        valid_focus_sessions = self.sessions[self.sessions['focus_level'] != -1]
        avg_focus_level = valid_focus_sessions['focus_level'].mean() if len(
            valid_focus_sessions) > 0 else 0

        return {
            "total_sessions": len(self.sessions),
            "total_actual_hours": round(self.sessions['duration'].sum() / 60, 1),
            "avg_focus_level": round(avg_focus_level, 1),
            "recent_week_hours": recent_data["recent_week_hours"],
            "recent_week_focus": recent_data["recent_week_focus"],
            "time_distribution": self.get_time_distribution(),
            "study_days_per_week": self.get_study_days_per_week(),
            "avg_session_length": round(self.sessions['duration'].mean()),
            "consistency_score": self.get_consistency_score(),
            "focus_trend": self.get_focus_trend()
        }


if __name__ == "__main__":
    # DB에서 가져온 샘플 세션 데이터 (약 2개월간의 학습 패턴)
    sample_sessions = [
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
            "subject_id": "english_101",
            "date": "2025-04-04",
            "study_time": 45,
            "start_time": "2025-04-04T19:00:00.000Z",
            "end_time": "2025-04-04T19:45:00.000Z",
            "rest_time": 0,
            "focus_level": 3,
            "memo": "영단어 암기"
        },

        # 4월 둘째 주 - 학습 패턴 형성
        {
            "id": "session_004",
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
            "id": "session_005",
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
            "id": "session_006",
            "user_id": "user_123",
            "subject_id": "english_101",
            "date": "2025-04-09",
            "study_time": 75,
            "start_time": "2025-04-09T20:00:00.000Z",
            "end_time": "2025-04-09T21:15:00.000Z",
            "rest_time": 0,
            "focus_level": 3,
            "memo": "문법 정리"
        },
        {
            "id": "session_007",
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

        # 4월 셋째 주 - 연속 학습 시작
        {
            "id": "session_008",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-04-14",
            "study_time": 135,
            "start_time": "2025-04-14T09:00:00.000Z",
            "end_time": "2025-04-14T11:30:00.000Z",
            "rest_time": 15,
            "focus_level": 5,
            "memo": "정적분 계산"
        },
        {
            "id": "session_009",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-04-15",
            "study_time": 120,
            "start_time": "2025-04-15T09:30:00.000Z",
            "end_time": "2025-04-15T11:30:00.000Z",
            "rest_time": 0,
            "focus_level": 4,
            "memo": "부분적분"
        },
        {
            "id": "session_010",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-04-16",
            "study_time": 90,
            "start_time": "2025-04-16T10:00:00.000Z",
            "end_time": "2025-04-16T11:30:00.000Z",
            "rest_time": 0,
            "focus_level": 5,
            "memo": "치환적분"
        },
        {
            "id": "session_011",
            "user_id": "user_123",
            "subject_id": "english_101",
            "date": "2025-04-17",
            "study_time": 60,
            "start_time": "2025-04-17T19:30:00.000Z",
            "end_time": "2025-04-17T20:30:00.000Z",
            "rest_time": 0,
            "focus_level": 4,
            "memo": "독해 연습"
        },
        {
            "id": "session_012",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-04-18",
            "study_time": 105,
            "start_time": "2025-04-18T09:00:00.000Z",
            "end_time": "2025-04-18T10:45:00.000Z",
            "rest_time": 0,
            "focus_level": 4,
            "memo": "종합 문제 풀이"
        },

        # 4월 넷째 주 - 집중도 향상 기간
        {
            "id": "session_013",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-04-21",
            "study_time": 150,
            "start_time": "2025-04-21T08:30:00.000Z",
            "end_time": "2025-04-21T11:00:00.000Z",
            "rest_time": 0,
            "focus_level": 5,
            "memo": "미적분 종합 정리"
        },
        {
            "id": "session_014",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-04-22",
            "study_time": 120,
            "start_time": "2025-04-22T09:00:00.000Z",
            "end_time": "2025-04-22T11:00:00.000Z",
            "rest_time": 0,
            "focus_level": 5,
            "memo": "고급 문제 도전"
        },
        {
            "id": "session_015",
            "user_id": "user_123",
            "subject_id": "english_101",
            "date": "2025-04-23",
            "study_time": 90,
            "start_time": "2025-04-23T20:00:00.000Z",
            "end_time": "2025-04-23T21:30:00.000Z",
            "rest_time": 0,
            "focus_level": 4,
            "memo": "작문 연습"
        },
        {
            "id": "session_016",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-04-24",
            "study_time": 135,
            "start_time": "2025-04-24T09:00:00.000Z",
            "end_time": "2025-04-24T11:15:00.000Z",
            "rest_time": 0,
            "focus_level": 5,
            "memo": "모의고사 풀이"
        },
        {
            "id": "session_017",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-04-25",
            "study_time": 90,
            "start_time": "2025-04-25T10:00:00.000Z",
            "end_time": "2025-04-25T11:30:00.000Z",
            "rest_time": 0,
            "focus_level": 4,
            "memo": "오답 정리"
        },

        # 5월 첫째 주 - 안정적 학습 패턴
        {
            "id": "session_018",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-05-01",
            "study_time": 120,
            "start_time": "2025-05-01T09:00:00.000Z",
            "end_time": "2025-05-01T11:00:00.000Z",
            "rest_time": 0,
            "focus_level": 5,
            "memo": "새 단원 시작"
        },
        {
            "id": "session_019",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-05-02",
            "study_time": 105,
            "start_time": "2025-05-02T09:30:00.000Z",
            "end_time": "2025-05-02T11:15:00.000Z",
            "rest_time": 0,
            "focus_level": 4,
            "memo": "벡터 기초"
        },
        {
            "id": "session_020",
            "user_id": "user_123",
            "subject_id": "english_101",
            "date": "2025-05-03",
            "study_time": 75,
            "start_time": "2025-05-03T19:00:00.000Z",
            "end_time": "2025-05-03T20:15:00.000Z",
            "rest_time": 0,
            "focus_level": 4,
            "memo": "리스닝 연습"
        },
        {
            "id": "session_021",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-05-05",
            "study_time": 90,
            "start_time": "2025-05-05T10:00:00.000Z",
            "end_time": "2025-05-05T11:30:00.000Z",
            "rest_time": 0,
            "focus_level": 5,
            "memo": "벡터 연산"
        },

        # 5월 둘째 주 - 일부 집중도 하락
        {
            "id": "session_022",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-05-07",
            "study_time": 75,
            "start_time": "2025-05-07T14:00:00.000Z",
            "end_time": "2025-05-07T15:15:00.000Z",
            "rest_time": 0,
            "focus_level": 3,
            "memo": "컨디션 난조"
        },
        {
            "id": "session_023",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-05-09",
            "study_time": 60,
            "start_time": "2025-05-09T15:00:00.000Z",
            "end_time": "2025-05-09T16:00:00.000Z",
            "rest_time": 0,
            "focus_level": 3,
            "memo": "복습"
        },
        {
            "id": "session_024",
            "user_id": "user_123",
            "subject_id": "english_101",
            "date": "2025-05-10",
            "study_time": 45,
            "start_time": "2025-05-10T20:30:00.000Z",
            "end_time": "2025-05-10T21:15:00.000Z",
            "rest_time": 0,
            "focus_level": 2,
            "memo": "피곤함"
        },

        # 5월 셋째 주 - 회복 및 향상
        {
            "id": "session_025",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-05-14",
            "study_time": 120,
            "start_time": "2025-05-14T09:00:00.000Z",
            "end_time": "2025-05-14T11:00:00.000Z",
            "rest_time": 0,
            "focus_level": 4,
            "memo": "컨디션 회복"
        },
        {
            "id": "session_026",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-05-15",
            "study_time": 135,
            "start_time": "2025-05-15T09:00:00.000Z",
            "end_time": "2025-05-15T11:15:00.000Z",
            "rest_time": 0,
            "focus_level": 5,
            "memo": "집중력 최고조"
        },
        {
            "id": "session_027",
            "user_id": "user_123",
            "subject_id": "math_101",
            "date": "2025-05-16",
            "study_time": 105,
            "start_time": "2025-05-16T09:30:00.000Z",
            "end_time": "2025-05-16T11:15:00.000Z",
            "rest_time": 0,
            "focus_level": 5,
            "memo": "심화 문제"
        },
        {
            "id": "session_028",
            "user_id": "user_123",
            "subject_id": "english_101",
            "date": "2025-05-17",
            "study_time": 90,
            "start_time": "2025-05-17T19:00:00.000Z",
            "end_time": "2025-05-17T20:30:00.000Z",
            "rest_time": 0,
            "focus_level": 4,
            "memo": "스피킹 연습"
        },

        # 5월 넷째 주 - 최근 데이터 (고집중도 유지)
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
            "subject_id": "english_101",
            "date": "2025-05-23",
            "study_time": 105,
            "start_time": "2025-05-23T19:00:00.000Z",
            "end_time": "2025-05-23T20:45:00.000Z",
            "rest_time": 0,
            "focus_level": 5,
            "memo": "종합 평가"
        },
        {
            "id": "session_032",
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
            "id": "session_033",
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

    analyzer = LearningPatternAnalyzer(sample_sessions)

    print("=== 전체 학습 패턴 분석 ===")
    result = analyzer.analyze_all_patterns()

    # --- result ---
    print(f"총 세션 수: {result['total_sessions']}")
    print(f"총 실제 학습 시간: {result['total_actual_hours']}시간")
    print(f"평균 집중도: {result['avg_focus_level']}")
    print(f"최근 일주일 학습 시간: {result['recent_week_hours']}시간")
    print(f"최근 일주일 평균 집중도: {result['recent_week_focus']}")
    print(f"학습 시간대 분포: {result['time_distribution']}")
    print(f"주간 평균 학습 일수: {result['study_days_per_week']}일")
    print(f"평균 세션 길이: {result['avg_session_length']}분")
    print(f"학습 일관성 점수: {result['consistency_score']}/5")
    print(f"집중도 트렌드: {result['focus_trend']}")

    print("\n=== 수학 과목별 분석 ===")
    math_result = analyzer.analyze_all_patterns(subject_id="math_101")
    print(f"수학 총 세션 수: {math_result['total_sessions']}")
    print(f"수학 총 학습 시간: {math_result['total_actual_hours']}시간")
    print(f"수학 평균 집중도: {math_result['avg_focus_level']}")
    print(f"수학 최근 일주일 학습 시간: {math_result['recent_week_hours']}시간")
    print(f"수학 최근 일주일 평균 집중도: {math_result['recent_week_focus']}")
    print(f"수학 학습 시간대 분포: {math_result['time_distribution']}")
    print(f"수학 주간 평균 학습 일수: {math_result['study_days_per_week']}일")
    print(f"수학 평균 세션 길이: {math_result['avg_session_length']}분")
    print(f"수학 학습 일관성: {math_result['consistency_score']}/5")
    print(f"수학 집중도 트렌드: {math_result['focus_trend']}")

    print("\n=== 영어 과목별 분석 ===")
    english_result = analyzer.analyze_all_patterns(subject_id="english_101")
    print(f"영어 총 세션 수: {english_result['total_sessions']}")
    print(f"영어 총 학습 시간: {english_result['total_actual_hours']}시간")
    print(f"영어 평균 집중도: {english_result['avg_focus_level']}")
    print(f"영어 최근 일주일 학습 시간: {english_result['recent_week_hours']}시간")
    print(f"영어 최근 일주일 평균 집중도: {english_result['recent_week_focus']}")
    print(f"영어 학습 시간대 분포: {english_result['time_distribution']}")
    print(f"영어 주간 평균 학습 일수: {english_result['study_days_per_week']}일")
    print(f"영어 평균 세션 길이: {english_result['avg_session_length']}분")
    print(f"영어 학습 일관성: {english_result['consistency_score']}/5")
    print(f"영어 집중도 트렌드: {english_result['focus_trend']}")
    # --- result ---
