from locust import HttpUser, task, between
import urllib.parse
import random
import logging
import uuid
from datetime import datetime, timezone, timedelta

# 테스트에 사용할 에브리타임 URL 샘플들
# 이 URL을 실제 테스트할 에브리타임 URL로 변경하세요
EVERYTIME_SAMPLE_URLS = [
    'https://everytime.kr/@Gpm4hmWAGNlbWwIKAaGa'
]


class TimeTableApiUser(HttpUser):
    """에브리타임 시간표 API에 부하 테스트를 수행하는 가상 사용자 클래스"""

    # 요청 사이의 대기 시간 (1초~3초 사이)
    wait_time = between(1, 3)

    def on_start(self):
        """사용자 세션 시작 시 호출되는 메서드"""
        logging.info("New user started")

    @task(1)
    def test_timetable_endpoint(self):
        """
        /timetable 엔드포인트 테스트
        샘플 URL 중 하나를 무작위로 선택하여 요청
        """
        # 샘플 URL 중 하나를 무작위로 선택
        url = random.choice(EVERYTIME_SAMPLE_URLS)

        # URL 인코딩
        encoded_url = urllib.parse.quote(url, safe='')

        # 요청 보내기
        with self.client.get(
            f"/timetable?url={encoded_url}",
            name="/timetable",
            catch_response=True
        ) as response:
            # 응답 검증
            if response.status_code != 200:
                response.failure(
                    f"Failed with status code: {response.status_code}, Response: {response.text}")
            else:
                try:
                    # JSON 응답 확인
                    json_data = response.json()
                    if "timetable" not in json_data or "message" not in json_data:
                        response.failure("잘못된 응답 형식입니다.")
                except Exception as e:
                    response.failure(f"JSON 파싱 오류: {str(e)}")


class SubjectStudySessionUser(HttpUser):
    """
    Subject 및 Study Session API에 대한 CRUD 및 정리 작업을 수행하는 가상 사용자 클래스.
    테스트 시작 시 임시 사용자를 생성하고, 테스트 종료 시 모든 생성된 데이터와 임시 사용자를 삭제합니다.
    """
    wait_time = between(1, 3)

    def on_start(self):
        """
        사용자 세션 시작 시 호출됩니다.
        임시 사용자를 생성하고, 인증 토큰을 헤더에 설정합니다.
        생성된 subject_id와 session_id를 저장할 리스트를 초기화합니다.
        """
        logging.info("SubjectStudySessionUser 시작: 임시 사용자 생성 중...")
        response = self.client.post("/auth/common/temp_user_for_test")
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            # 실제 API 호출에는 토큰만 필요하지만, 로깅 등을 위해 저장
            self.user_id = data["user_id"]
            self.headers = {"Authorization": f"Bearer {self.access_token}"}
            logging.info(f"임시 사용자 생성 성공 (User ID: {self.user_id}). 토큰 설정 완료.")
        else:
            logging.error(
                f"임시 사용자 생성 실패: {response.status_code} - {response.text}")
            # 사용자를 생성하지 못하면 테스트를 진행할 수 없으므로 여기서 중단하거나,
            # Locust의 stop() 메서드를 호출하여 이 사용자의 실행을 중지할 수 있습니다.
            # 여기서는 간단히 에러 로그만 남깁니다.
            self.environment.runner.quit()  # 전체 테스트 중단
            return

        self.subject_ids = []
        self.session_ids = []
        # 삭제 시 user_id 확인을 위해 필요할 수 있음 (API 설계에 따라)
        self.created_subjects_data = []
        # 삭제 시 user_id 확인을 위해 필요할 수 있음 (API 설계에 따라)
        self.created_sessions_data = []
        logging.info("SubjectStudySessionUser 초기화 완료.")

    def on_stop(self):
        """
        사용자 세션 종료 시 호출됩니다.
        생성된 모든 학습 세션, 과목, 그리고 임시 사용자 계정을 삭제합니다.
        """
        if not hasattr(self, 'headers'):
            logging.warning("Token이 없어 on_stop 정리 작업을 건너<0xEB><0x9C><0x84>니다.")
            return

        logging.info(
            f"SubjectStudySessionUser (User ID: {self.user_id}) 정리 작업 시작...")

        # 생성된 학습 세션 삭제 (생성된 역순으로 삭제 시도)
        if self.session_ids:
            logging.info(f"총 {len(self.session_ids)}개의 학습 세션 삭제 시도...")
            for session_id in reversed(self.session_ids):
                with self.client.delete(f"/study-sessions/{session_id}", headers=self.headers, name="/study-sessions/{id} (DELETE)", catch_response=True) as response:
                    if response.status_code == 200:
                        logging.info(f"Study Session {session_id} 삭제 성공")
                    elif response.status_code == 404:
                        logging.warning(
                            f"Study Session {session_id} 삭제 시 404 (이미 없음)")
                    else:
                        # 실패해도 다음 삭제 시도 계속
                        logging.error(
                            f"Study Session {session_id} 삭제 실패: {response.status_code} - {response.text}")
            self.session_ids.clear()
        else:
            logging.info("삭제할 학습 세션이 없습니다.")

        # 생성된 과목 삭제 (생성된 역순으로 삭제 시도)
        if self.subject_ids:
            logging.info(f"총 {len(self.subject_ids)}개의 과목 삭제 시도...")
            for subject_id in reversed(self.subject_ids):
                # 먼저 해당 과목의 모든 세션이 삭제되었는지 확인하거나, API에서 자동 처리하는지 확인 필요.
                # 여기서는 일단 과목만 삭제 시도.
                with self.client.delete(f"/subjects/{subject_id}", headers=self.headers, name="/subjects/{id} (DELETE)", catch_response=True) as response:
                    if response.status_code == 200:
                        logging.info(f"Subject {subject_id} 삭제 성공")
                    elif response.status_code == 404:
                        logging.warning(
                            f"Subject {subject_id} 삭제 시 404 (이미 없음)")
                    # 예: 하위 항목(세션)이 있어 삭제 못하는 경우 등
                    elif response.status_code == 500:
                        logging.error(
                            f"Subject {subject_id} 삭제 실패 (500): {response.status_code} - {response.text}. 세션이 남아있을 수 있습니다.")
                    else:
                        logging.error(
                            f"Subject {subject_id} 삭제 실패: {response.status_code} - {response.text}")
            self.subject_ids.clear()
        else:
            logging.info("삭제할 과목이 없습니다.")

        # 임시 사용자 계정 삭제
        logging.info(f"임시 사용자 (User ID: {self.user_id}) 삭제 시도...")
        with self.client.delete("/auth/common/temp_user_for_test", headers=self.headers, name="/auth/common/temp_user_for_test (DELETE)", catch_response=True) as response:
            if response.status_code == 200:
                logging.info(f"임시 사용자 (User ID: {self.user_id}) 삭제 성공")
            elif response.status_code == 401 or response.status_code == 404:  # 토큰 만료 또는 이미 삭제된 경우
                logging.warning(
                    f"임시 사용자 (User ID: {self.user_id}) 삭제 시 {response.status_code} (이미 삭제되었거나 권한 문제일 수 있음)")
            else:
                logging.error(
                    f"임시 사용자 (User ID: {self.user_id}) 삭제 실패: {response.status_code} - {response.text}")

        logging.info(
            f"SubjectStudySessionUser (User ID: {self.user_id}) 정리 작업 완료.")

    @task(5)  # 높은 가중치로 더 자주 실행
    def create_subject_task(self):
        """새로운 과목을 생성하는 태스크"""
        if not hasattr(self, 'headers'):  # on_start에서 실패했을 경우
            logging.warning(
                "Token이 없어 create_subject_task를 건너<0xEB><0x9C><0x84>니다.")
            return

        subject_data = {
            "name": f"Test Subject {uuid.uuid4()}",
            "type": random.choice([0, 1, 2]),  # 0: 전필, 1: 전선, 2: 교양
            "credit": random.randint(1, 3),
            "difficulty": random.randint(1, 5),
            "mid_term_schedule": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "final_term_schedule": (datetime.now(timezone.utc) + timedelta(days=60)).isoformat(),
            "evaluation_ratio": {
                "mid_term_ratio": 30,
                "final_term_ratio": 40,
                "quiz_ratio": 10,
                "assignment_ratio": 15,
                "attendance_ratio": 5
            },
            "target_study_time": {
                "daily_target_study_time": 60,  # 분 단위
                "weekly_target_study_time": 300,
                "monthly_target_study_time": 1200
            },
            "color": f"#{random.randint(0, 0xFFFFFF):06x}"
        }
        with self.client.post("/subjects/", json=subject_data, headers=self.headers, name="/subjects/ (POST)", catch_response=True) as response:
            if response.status_code == 201:
                created_subject = response.json()
                self.subject_ids.append(created_subject["id"])
                self.created_subjects_data.append(
                    created_subject)  # 삭제 검증 또는 다른 작업에 사용 가능
                logging.info(f"Subject 생성 성공: ID {created_subject['id']}")
            else:
                response.failure(
                    f"Subject 생성 실패: {response.status_code} - {response.text}")

    @task(2)
    def get_all_subjects_task(self):
        """모든 과목을 조회하는 태스크"""
        if not hasattr(self, 'headers'):
            logging.warning(
                "Token이 없어 get_all_subjects_task를 건너<0xEB><0x9C><0x84>니다.")
            return

        with self.client.get("/subjects/", headers=self.headers, name="/subjects/ (GET all)", catch_response=True) as response:
            if response.status_code == 200:
                # logging.info(f"모든 Subject 조회 성공: {len(response.json().get('subjects', []))}개")
                pass  # 성공 로깅은 너무 많을 수 있어 생략
            else:
                response.failure(
                    f"모든 Subject 조회 실패: {response.status_code} - {response.text}")

    @task(3)
    def get_specific_subject_task(self):
        """특정 과목을 조회하는 태스크"""
        if not hasattr(self, 'headers') or not self.subject_ids:
            # logging.warning("Token이 없거나 생성된 Subject가 없어 get_specific_subject_task를 건너<0xEB><0x9C><0x84>니다.")
            return

        subject_id = random.choice(self.subject_ids)
        with self.client.get(f"/subjects/{subject_id}", headers=self.headers, name="/subjects/{id} (GET specific)", catch_response=True) as response:
            if response.status_code == 200:
                # logging.info(f"Subject {subject_id} 조회 성공")
                pass
            elif response.status_code == 404:
                # 이미 삭제되었거나 잘못된 ID일 수 있음, 정상적인 실패로 간주 가능
                response.success()
                logging.warning(
                    f"Subject {subject_id} 조회 시 404 (이미 삭제되었을 수 있음)")
            else:
                response.failure(
                    f"Subject {subject_id} 조회 실패: {response.status_code} - {response.text}")

    @task(2)
    def update_subject_task(self):
        """기존 과목을 업데이트하는 태스크"""
        if not hasattr(self, 'headers') or not self.subject_ids:
            # logging.warning("Token이 없거나 생성된 Subject가 없어 update_subject_task를 건너<0xEB><0x9C><0x84>니다.")
            return

        subject_id = random.choice(self.subject_ids)
        update_data = {
            "name": f"Updated Subject Name {uuid.uuid4()}",
            "difficulty": random.randint(1, 5),
            "color": f"#{random.randint(0, 0xFFFFFF):06x}"
        }
        with self.client.patch(f"/subjects/{subject_id}", json=update_data, headers=self.headers, name="/subjects/{id} (PATCH)", catch_response=True) as response:
            if response.status_code == 200:
                # logging.info(f"Subject {subject_id} 업데이트 성공")
                pass
            elif response.status_code == 404:
                response.success()
                logging.warning(
                    f"Subject {subject_id} 업데이트 시 404 (이미 삭제되었을 수 있음)")
            else:
                response.failure(
                    f"Subject {subject_id} 업데이트 실패: {response.status_code} - {response.text}")

    @task(4)  # 과목 생성 후 실행될 가능성 높도록 가중치 조절
    def create_study_session_task(self):
        """새로운 학습 세션을 생성하는 태스크"""
        if not hasattr(self, 'headers') or not self.subject_ids:
            # logging.warning("Token이 없거나 생성된 Subject가 없어 create_study_session_task를 건너<0xEB><0x9C><0x84>니다.")
            return

        subject_id = random.choice(self.subject_ids)
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=random.randint(1, 2))
        end_time = now
        study_time_seconds = (
            # 약간의 휴식시간 고려
            end_time - start_time).total_seconds() - random.randint(0, 600)
        if study_time_seconds < 60:  # 최소 학습 시간 보장
            study_time_seconds = 60

        session_data = {
            "subject_id": subject_id,
            "date": now.strftime("%Y-%m-%d"),
            "study_time": int(study_time_seconds),  # 초 단위 정수
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "rest_time": random.randint(0, 600)  # 초 단위 정수
        }
        with self.client.post("/study-sessions/", json=session_data, headers=self.headers, name="/study-sessions/ (POST)", catch_response=True) as response:
            if response.status_code == 201:
                created_session = response.json()
                self.session_ids.append(created_session["id"])
                self.created_sessions_data.append(created_session)
                logging.info(
                    f"Study Session 생성 성공: ID {created_session['id']} for Subject ID {subject_id}")
            else:
                response.failure(
                    f"Study Session 생성 실패: {response.status_code} - {response.text} (Data: {session_data})")

    @task(2)
    def get_all_study_sessions_task(self):
        """모든 학습 세션을 조회하는 태스크"""
        if not hasattr(self, 'headers'):
            logging.warning(
                "Token이 없어 get_all_study_sessions_task를 건너<0xEB><0x9C><0x84>니다.")
            return

        # 모든 세션 조회 또는 특정 과목 세션 조회 (랜덤 선택)
        name_suffix = "(GET all)"
        url = "/study-sessions/"
        if self.subject_ids and random.choice([True, False]):
            subject_id_for_filter = random.choice(self.subject_ids)
            url = f"/study-sessions/?subject_id={subject_id_for_filter}"
            name_suffix = f"(GET by subject_id {subject_id_for_filter})"

        with self.client.get(url, headers=self.headers, name=f"/study-sessions/ {name_suffix}", catch_response=True) as response:
            if response.status_code == 200:
                # logging.info(f"Study Sessions 조회 성공 ({name_suffix}): {len(response.json().get('sessions', []))}개")
                pass
            else:
                response.failure(
                    f"Study Sessions 조회 실패 ({name_suffix}): {response.status_code} - {response.text}")

    @task(1)
    def get_specific_study_session_task(self):
        """특정 학습 세션을 조회하는 태스크"""
        if not hasattr(self, 'headers') or not self.session_ids:
            # logging.warning("Token이 없거나 생성된 Session이 없어 get_specific_study_session_task를 건너<0xEB><0x9C><0x84>니다.")
            return

        session_id = random.choice(self.session_ids)
        with self.client.get(f"/study-sessions/{session_id}", headers=self.headers, name="/study-sessions/{id} (GET specific)", catch_response=True) as response:
            if response.status_code == 200:
                # logging.info(f"Study Session {session_id} 조회 성공")
                pass
            elif response.status_code == 404:
                response.success()
                logging.warning(
                    f"Study Session {session_id} 조회 시 404 (이미 삭제되었을 수 있음)")
            else:
                response.failure(
                    f"Study Session {session_id} 조회 실패: {response.status_code} - {response.text}")

    @task(1)
    def update_study_session_task(self):
        """기존 학습 세션을 업데이트하는 태스크"""
        if not hasattr(self, 'headers') or not self.session_ids:
            # logging.warning("Token이 없거나 생성된 Session이 없어 update_study_session_task를 건너<0xEB><0x9C><0x84>니다.")
            return

        session_id = random.choice(self.session_ids)
        update_data = {
            "study_time": random.randint(600, 3600),  # 10분 ~ 1시간 사이 값으로 업데이트
            "rest_time": random.randint(0, 300)
        }
        with self.client.patch(f"/study-sessions/{session_id}", json=update_data, headers=self.headers, name="/study-sessions/{id} (PATCH)", catch_response=True) as response:
            if response.status_code == 200:
                # logging.info(f"Study Session {session_id} 업데이트 성공")
                pass
            elif response.status_code == 404:
                response.success()
                logging.warning(
                    f"Study Session {session_id} 업데이트 시 404 (이미 삭제되었을 수 있음)")
            else:
                response.failure(
                    f"Study Session {session_id} 업데이트 실패: {response.status_code} - {response.text}")

    @task(1)  # 다른 작업에 비해 낮은 빈도로 실행
    def delete_random_subject_task(self):
        """무작위로 선택된 기존 과목을 삭제하는 태스크"""
        if not hasattr(self, 'headers') or not self.subject_ids:
            # logging.warning("Token이 없거나 생성된 Subject가 없어 delete_random_subject_task를 건너<0xEB><0x9C><0x84>니다.")
            return

        subject_id_to_delete = random.choice(self.subject_ids)

        # 주의: 해당 과목에 연결된 학습 세션이 있다면 삭제가 실패할 수 있습니다 (API 정책에 따라 다름).
        # API가 하위 리소스 자동 삭제를 지원하지 않는다면, 관련 세션을 먼저 삭제하는 로직이 필요할 수 있으나,
        # 여기서는 단순 삭제 시도만 합니다.
        with self.client.delete(f"/subjects/{subject_id_to_delete}", headers=self.headers, name="/subjects/{id} (DELETE random)", catch_response=True) as response:
            if response.status_code == 200:
                logging.info(f"Random Subject {subject_id_to_delete} 삭제 성공")
                self.subject_ids.remove(subject_id_to_delete)
                # self.created_subjects_data 에서도 해당 항목 제거 로직 추가 가능 (필요시)
            elif response.status_code == 404:  # 이미 다른 경로로 삭제되었을 수 있음
                logging.warning(
                    f"Random Subject {subject_id_to_delete} 삭제 시 404 (이미 없음)")
                if subject_id_to_delete in self.subject_ids:  # 리스트에 아직 있다면 제거
                    self.subject_ids.remove(subject_id_to_delete)
                response.success()  # Locust에서는 성공으로 처리
            elif response.status_code == 500:  # 일반적으로 하위 리소스(세션) 때문에 발생 가능
                response.failure(
                    f"Random Subject {subject_id_to_delete} 삭제 실패 (500 - 하위 리소스 문제일 수 있음): {response.text}")
                # 이 경우 subject_id를 self.subject_ids에서 제거하지 않아 on_stop에서 다시 시도하게 할 수 있음
            else:
                response.failure(
                    f"Random Subject {subject_id_to_delete} 삭제 실패: {response.status_code} - {response.text}")

    @task(1)  # 다른 작업에 비해 낮은 빈도로 실행
    def delete_random_study_session_task(self):
        """무작위로 선택된 기존 학습 세션을 삭제하는 태스크"""
        if not hasattr(self, 'headers') or not self.session_ids:
            # logging.warning("Token이 없거나 생성된 Session이 없어 delete_random_study_session_task를 건너<0xEB><0x9C><0x84>니다.")
            return

        session_id_to_delete = random.choice(self.session_ids)
        with self.client.delete(f"/study-sessions/{session_id_to_delete}", headers=self.headers, name="/study-sessions/{id} (DELETE random)", catch_response=True) as response:
            if response.status_code == 200:
                logging.info(
                    f"Random Study Session {session_id_to_delete} 삭제 성공")
                self.session_ids.remove(session_id_to_delete)
                # self.created_sessions_data 에서도 해당 항목 제거 로직 추가 가능 (필요시)
            elif response.status_code == 404:  # 이미 다른 경로로 삭제되었을 수 있음
                logging.warning(
                    f"Random Study Session {session_id_to_delete} 삭제 시 404 (이미 없음)")
                if session_id_to_delete in self.session_ids:  # 리스트에 아직 있다면 제거
                    self.session_ids.remove(session_id_to_delete)
                response.success()  # Locust에서는 성공으로 처리
            else:
                response.failure(
                    f"Random Study Session {session_id_to_delete} 삭제 실패: {response.status_code} - {response.text}")

# 사용법:
# 1. 터미널에서 FastAPI 서버 실행: uvicorn main:app --host 0.0.0.0 --port 8000
# 2. 다른 터미널에서 Locust 실행: locust -f locustfile.py --host=http://localhost:8000
# 3. 웹 브라우저에서 http://localhost:8089 접속하여 테스트 구성 및 시작
