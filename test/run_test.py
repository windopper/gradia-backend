#!/usr/bin/env python
"""
Grade Prediction V2 테스트 실행 스크립트

사용법:
  python test/run_test.py

또는 프로젝트 루트에서:
  python -m test.run_test
"""
import os
import sys
import subprocess


def main():
    # 현재 스크립트의 디렉토리 경로
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    test_script = os.path.join(current_dir, "test_grade_prediction_v2.py")

    # 환경 변수 설정
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root

    print("=== Grade Prediction V2 테스트 시작 ===")
    print(f"프로젝트 루트: {project_root}")
    print(f"테스트 스크립트: {test_script}")
    print("=" * 50)

    try:
        # 테스트 실행
        result = subprocess.run(
            [sys.executable, test_script],
            env=env,
            cwd=project_root,
            check=True
        )
        print("\n✅ 테스트 실행 완료!")
        return result.returncode

    except subprocess.CalledProcessError as e:
        print(f"\n❌ 테스트 실행 실패: {e}")
        return e.returncode
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
