# OBS Auto Scheduler

OBS Auto Scheduler는 OBS Studio의 방송 및 녹화를 자동으로 예약하고 관리할 수 있는 프로그램입니다.  
복잡한 설정 없이 직관적인 GUI를 통해 요일별, 날짜별, 매일 반복되는 작업을 예약하세요.

## ✨ 주요 기능

- **OBS 자동 연결**: OBS WebSocket을 통해 OBS와 안전하게 통신합니다.
- **다양한 예약 모드**:
  - **매일 (Daily)**: 매일 지정된 시간에 실행
  - **매주 (Weekly)**: 특정 요일의 지정된 시간에 실행 (다중 요일 선택 가능)
  - **특정 날짜 (Specific Date)**: 지정한 날짜와 시간에 한 번만 실행
- **지원 동작**:
  - 방송 시작 / 중단 (Start/Stop Streaming)
  - 녹화 시작 / 중단 (Start/Stop Recording)
- **프리셋 (Preset) 관리**: 자주 사용하는 예약 목록을 저장하고 언제든지 불러올 수 있습니다.
- **자동 연결**: 프로그램 시작 시 OBS에 자동으로 연결하도록 설정할 수 있습니다.

## 🛠️ 설치 및 실행 방법

## 🛠️ 설치 및 실행 방법

### 1. 일반 사용자 (Windows PC)
복잡한 설치 과정 없이 실행 파일만으로 프로그램을 사용할 수 있습니다.

1. 이 저장소의 **[Releases]** 페이지로 이동합니다.
2. 최신 버전의 `OBS_Auto_Scheduler.exe` (또는 압축 파일)을 다운로드합니다.
3. 다운로드한 파일을 실행하면 바로 프로그램이 시작됩니다.
   - *경고 창이 뜰 경우*: '추가 정보' -> '실행'을 클릭하세요. (서명되지 않은 앱이라 뜰 수 있습니다.)

### 2. 개발자 (소스 코드 실행)
파이썬 환경에서 직접 실행하거나 코드를 수정하고 싶은 경우에만 해당됩니다.

**사전 준비**
- **Python 3.x** 설치 필요
- **Git** 설치 필요

**설치 및 실행**
```bash
# 1. 저장소 클론
git clone https://github.com/xnculture/autobs.git
cd autobs

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 실행
python main.py
```

## 📖 사용 가이드

### 1. OBS 연결
1. 프로그램 상단의 **OBS WebSocket Connection** 영역을 확인합니다.
2. OBS에서 설정한 **Host** (기본: localhost), **Port** (기본: 4455), **Password**를 입력합니다.
3. `Connect` 버튼을 누릅니다. 연결이 성공하면 상태가 **Connected**로 변경됩니다.

### 2. 작업 예약하기 (Schedule Task)
1. **Freq (빈도)**: Daily, Weekly, Specific Date 중 하나를 선택합니다.
   - **Weekly**: 실행할 요일을 체크합니다.
   - **Specific Date**: 실행할 날짜(YYYY-MM-DD)를 입력합니다.
2. **Time (시간)**: 실행할 시간을 시:분:초 단위로 설정하고 AM/PM을 선택합니다.
3. **Action (동작)**: 방송 시작/중단, 녹화 시작/중단 중 원하는 동작을 선택합니다.
4. `Add Task` 버튼을 눌러 예약 목록에 추가합니다.

### 3. 예약 관리
- **목록 확인**: 하단의 리스트에서 예약된 작업들을 확인할 수 있습니다.
- **삭제**: 리스트에서 항목을 선택하고 `Remove Selected`를 누르면 삭제됩니다. `Clear All`은 모든 작업을 삭제합니다.

### 4. 프리셋 (Presets)
- 현재 설정된 예약 목록을 저장해두고 싶다면 **Preset Name**에 이름을 입력하고 `Save Preset`을 누르세요.
- 저장된 프리셋은 콤보박스에서 선택 후 `Load` 버튼으로 불러오거나 `Delete` 버튼으로 삭제할 수 있습니다.

## ⚙️ 설정 파일
- `obs_scheduler_config.json`: 현재 설정과 예약 목록이 자동으로 저장됩니다.
- `presets.json`: 저장된 프리셋 목록이 관리됩니다.

> **주의**: `obs_scheduler_config.json` 파일에는 OBS 비밀번호가 포함될 수 있으므로, 깃허브 등에 업로드할 때는 주의하세요. (이 저장소에는 예시 파일인 `obs_scheduler_config.example.json`만 포함되어 있습니다.)
