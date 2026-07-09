# 컬드셉트 리볼트 (3DS) — 한글 패치 & CULDCEPT.DAT 툴

**컬드셉트 리볼트**(カルドセプト リボルト, 닌텐도 3DS 일본판, 타이틀 ID
`00040000000F5700`)의 **오프닝(스테이지 1) 한글 패치**와, 그것을 만들기 위해
`CULDCEPT.DAT` 아카이브를 처음부터 리버스 엔지니어링한 툴 모음입니다.

게임 시작 직후의 오프닝 컷신 전체(주인공 ↔ 의문의 목소리 대화)와 튜토리얼 안내,
그리고 전투 HUD·카드명 등 UI 라벨을 한국어로 표시합니다.

## ⚠️ 먼저 읽어주세요

- **게임 콘텐츠는 포함되어 있지 않습니다.** ROM, `CULDCEPT.DAT`, 실행 파일, 스토리
  대사, 카드 텍스트, 이미지·오디오 자산은 없습니다. 다만 UI를 제자리 교체하기 위한
  **검색 키**로, 짧은 기능성 UI/HUD/카드명 라벨(예: `ラウンド`, `手札`) 약 17개의 원문
  SJIS 문자열이 `opening_ko.py`에 들어 있습니다 — 스토리 텍스트가 아니라 위치를 찾기
  위한 라벨입니다. 게임을 정식으로 소유한 상태에서 **본인의 파일**로 사용하세요.
  한글 글리프는 시스템 폰트(맑은 고딕 등)에서 그려지고, 대사 원문은 전부 본인의
  `CULDCEPT.DAT`에서 읽어옵니다.
- **부분 패치입니다.** 오프닝 이후 아직 번역하지 않은 화면에서는, 한글 표시를 위해
  재활용한 한자 자리에 한글 글리프가 보일 수 있습니다(완성형 부분 패치의 알려진
  특성). 오프닝 장면 안에서는 대사·HUD를 모두 번역했으므로 충돌이 없습니다.
- 연구·개인용. 게임의 저작권을 존중하세요.

## 적용 방법

두 가지 방법이 있습니다. 같은 한글 폰트(기본: 맑은 고딕)를 쓰면 결과가 동일합니다
— xdelta 패치는 맑은 고딕으로 만든 것이므로, 방법 A에서 다른 TTF를 지정하면 글리프
모양만 달라집니다.

### 방법 A — 파이썬 툴 (권장, 어떤 판본이든 구조가 같으면 동작)

필요: 파이썬 3, [Pillow](https://pypi.org/project/Pillow/), 한글 TTF
(윈도우 `C:\Windows\Fonts\malgun.ttf` 맑은 고딕, 또는 나눔고딕).

```bash
pip install pillow
python apply_korean_opening.py 원본/CULDCEPT.DAT 출력/CULDCEPT.DAT --font malgun.ttf
```

툴이 본인 파일에서 폰트·대사·UI 위치를 자동으로 찾아 한글로 교체합니다.

### 방법 B — xdelta 패치 (빠름, 원본이 정확히 일치할 때)

[릴리즈](../../releases)의 `culdcept-korean-opening.xdelta`는 일본판(Rev 2) RomFS의
`CULDCEPT.DAT`에 대한 **차이(diff)**입니다. 원본 파일 없이는 사용할 수 없습니다.

- **DeltaPatcher**(GUI): Original = 본인 `CULDCEPT.DAT`, Patch = `.xdelta` → Apply
- **명령줄**:
  ```
  xdelta3 -d -s CULDCEPT.DAT culdcept-korean-opening.xdelta out_CULDCEPT.DAT
  ```
  (일부 xdelta 빌드는 `xdelta` 로 실행. `unknown secondary compressor` 오류가 나면
  최신 xdelta3 또는 DeltaPatcher를 쓰세요.)

### 적용 결과 넣기 — LayeredFS

패치된 파일을 `CULDCEPT.DAT` 이름 그대로 아래 경로에 넣고 게임을 새로 실행:

```
<에뮬레이터 사용자 폴더>/load/mods/00040000000F5700/romfs/CULDCEPT.DAT
```

정상 적용 시 에뮬 로그에 `LayeredFS replacement file in use for /CULDCEPT.DAT`
가 출력됩니다. (실기는 이 파일로 RomFS를 재빌드해 ROM/CIA를 만드세요.)

## 무엇을 분석했나

- **`CULDCEPT.DAT` 컨테이너** — `(u32 오프셋, u32 크기)` 레코드 테이블 뒤에 엔트리
  데이터. 엔트리 개수 = `첫_오프셋 / 8`.
- **코덱** — `0x08`/`0x0c` = DEFLATE 계열 **canonical Huffman + LZ**(텍스트·폰트).
  이 타입은 디컴프레서·컴프레서 모두 순수 파이썬으로 구현(`culdcept/huffman.py`).
  `0x0d`/`0x8d` = 커스텀 **LZMA 레인지 코더**(포맷은 규명했으나 이 패치에는 불필요해
  파이썬 구현은 포함하지 않음).
- **비트맵 폰트** — CMAP(글리프 인덱스 → SJIS/ASCII 코드) + 여러 크기 섹션의 고정 셀
  **A4(4비트 알파)** 글리프. 위치 = `섹션 + 0xCE + 인덱스*bpg`.
- **시나리오 컨테이너** — 스토리 대사가 있는 곳. 코덱 엔트리가 아니라 자체
  `(섹션 오프셋, 크기)` 헤더로 시작하는 컨테이너이며, 각 섹션은 `0x08` 압축.
  대사 섹션은 `[스크립트][텍스트]` 구조, 텍스트는 null 종료 이벤트의 연속
  (`0x07`=페이지, `0x0a`=줄바꿈, `03 30 2f`=이름 삽입).

자세한 내용은 [`docs/FORMAT.md`](docs/FORMAT.md) 참고.

## 라이브러리

```python
from culdcept import huffman, dat, font, scen, wansung
d = dat.Dat(open("CULDCEPT.DAT", "rb").read())
raw = huffman.decompress(d.entry(1054))     # -> 압축 해제된 폰트 리소스
```

## 번역 데이터

`opening_ko.py` 에 오프닝 대사(이벤트 인덱스 기준)와 UI 라벨의 한국어가 들어 있습니다.
원문 일본어 대사는 담겨 있지 않으며, 적용 시 본인 파일에서 읽어옵니다.

> 참고: `apply_korean_font.py` 는 v0.1의 **발음 한글 폰트 데모**(가나 글리프를 발음이
> 비슷한 한글로 교체, 번역 아님)입니다. 실제 번역은 `apply_korean_opening.py` 입니다.

## 크레딧

컨테이너·코덱·폰트·시나리오 포맷을 처음부터 리버스 엔지니어링했습니다. 툴과 번역은
원저작물이며 MIT 라이선스입니다(`LICENSE` 참고). 컬드셉트 리볼트는
© Omiya Soft / Nintendo. 이 저장소에는 게임 코드나 데이터가 포함되어 있지 않습니다.
