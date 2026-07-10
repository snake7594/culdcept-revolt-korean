# 컬드셉트 리볼트 (3DS) — 한글 패치 & CULDCEPT.DAT 툴

**컬드셉트 리볼트**(カルドセプト リボルト, 닌텐도 3DS 일본판, 타이틀 ID
`00040000000F5700`)의 **전체 스토리 대사 + 카드 데이터베이스 + 캐릭터 전투 대사
한글 패치**와, 그것을 만들기 위해 `CULDCEPT.DAT` 아카이브를 처음부터 리버스
엔지니어링한 툴 모음입니다.

오프닝부터 각 스테이지의 스토리 이벤트(13개 시나리오 컨테이너 / 약 4,500개 대화
이벤트)까지 게임 진행 중 등장하는 대화를 한국어로 표시합니다. **카드 데이터베이스
(엔트리 1190)의 카드 능력·설명·플레이버 텍스트 약 4,300개 문자열**, **대전 상대·아군
등 캐릭터 전투 대사(엔트리 1849~1945, 약 12,000개 이벤트 / 상점·UI 도움말 포함)**,
시작 설정 화면 UI, 전투 HUD·카드명 라벨까지 포함합니다. 한글은 **나눔스퀘어 네오
Bold**로 렌더링합니다.

## ⚠️ 먼저 읽어주세요

- **게임 콘텐츠는 포함되어 있지 않습니다.** ROM, `CULDCEPT.DAT`, 실행 파일, 스토리
  대사, 카드 텍스트, 이미지·오디오 자산은 없습니다. 다만 UI를 제자리 교체하기 위한
  **검색 키**로, 짧은 기능성 UI/HUD/카드명 라벨(예: `ラウンド`, `手札`) 약 17개의 원문
  SJIS 문자열이 `opening_ko.py`에 들어 있습니다 — 스토리 텍스트가 아니라 위치를 찾기
  위한 라벨입니다. 게임을 정식으로 소유한 상태에서 **본인의 파일**로 사용하세요.
  한글 글리프는 시스템 폰트(맑은 고딕 등)에서 그려지고, 대사 원문은 전부 본인의
  `CULDCEPT.DAT`에서 읽어옵니다.
- **한국어 번역은 `dialogue_ko.json`(스토리 대사)·`cards_ko.json`(카드 텍스트)·
  `block_ko.json`(캐릭터 전투 대사)에 있습니다** — 한국어만 담기며, 일본어 원문은
  포함하지 않습니다(적용 시 본인 파일에서 읽음). 카드·대사는 위치(인덱스)로만
  매핑되고, 아이콘·제어코드·이름삽입 코드 등 원문 바이트는 적용 시 본인 파일에서
  다시 읽어 보존합니다. 완성형 2350자 폰트를 쓰므로 대부분의 한글이 표시됩니다.
- **아직 번역하지 않은 화면**(일부 텍스처 라벨·미크랙 나레이션 등)에서는, 한글 표시를
  위해 재활용한 한자 자리에 한글 글리프가 보일 수 있습니다(완성형 방식의 알려진 특성).
- **길이 제약**으로 일부 대사·카드 텍스트는 원문 바이트 한도에 맞춰 간결하게 축약되어
  있습니다. 카드 능력 키워드 `巻物`(두루마리) 계열은 좁은 능력창에 맞추려고 압축형
  `권물`(卷物)로 통일했습니다.
- 연구·개인용. 게임의 저작권을 존중하세요.

## 적용 방법

두 가지 방법이 있습니다. 같은 한글 폰트를 쓰면 결과가 동일합니다 — xdelta 패치는
**나눔스퀘어 네오 Bold**로 만든 것이므로, 방법 A에서 그 폰트를 `fonts/`에 두거나
`--font`로 지정하면 릴리즈와 똑같이 나옵니다(다른 TTF면 글리프 모양만 달라짐).

### 방법 A — 파이썬 툴 (권장, 어떤 판본이든 구조가 같으면 동작)

필요: 파이썬 3, [Pillow](https://pypi.org/project/Pillow/), 한글 TTF.
릴리즈 패치는 **나눔스퀘어 네오 Bold**로 렌더링합니다 — 릴리즈와 똑같은 모양을
원하면 그 폰트를 `fonts/NanumSquareNeo-cBd.ttf` 로 두세요([`fonts/README.md`](fonts/README.md),
[네이버 배포처](https://hangeul.naver.com/font)). 없으면 시스템 폰트(맑은 고딕 등)로
대체됩니다.

```bash
pip install pillow
# 전체 스토리 대사 + UI:
python apply_korean_full.py 원본/CULDCEPT.DAT 출력/CULDCEPT.DAT
# (오프닝만 원하면 apply_korean_opening.py)
# 폰트 지정:  --font <TTF 경로>
```

`apply_korean_full.py` 는 본인 파일에서 대사·UI 위치를 찾아, `dialogue_ko.json`(한국어
번역만 담김, 일본어 원문 없음)의 번역으로 교체합니다. 게임이 대사를 절대 오프셋으로
참조하므로 각 대화창의 한국어는 원문 바이트 한도에 맞춰져 있습니다(부족분은 공백 패딩).

### 방법 B — xdelta 패치 (빠름, 원본이 정확히 일치할 때)

[릴리즈](../../releases)의 `culdcept-korean.xdelta`는 일본판(Rev 2) RomFS의
`CULDCEPT.DAT`에 대한 **차이(diff)**입니다. 원본 파일 없이는 사용할 수 없습니다.

- **DeltaPatcher**(GUI): Original = 본인 `CULDCEPT.DAT`, Patch = `.xdelta` → Apply
- **명령줄**:
  ```
  xdelta3 -d -s CULDCEPT.DAT culdcept-korean.xdelta out_CULDCEPT.DAT
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

- `dialogue_ko.json` — **전체 스토리 대사**의 한국어(섹션·이벤트·페이지 인덱스 기준).
- `opening_ko.py` — 오프닝 대사(다듬은 버전) + UI/시작설정 라벨 한국어.

둘 다 한국어 번역만 담으며, 일본어 원문은 없습니다(적용 시 본인 파일에서 읽음).

> 참고: `apply_korean_font.py`(v0.1 발음 데모), `apply_korean_opening.py`(오프닝만),
> `apply_korean_full.py`(전체 대사). 최신 릴리즈는 전체 대사 패치입니다.

## 크레딧

컨테이너·코덱·폰트·시나리오 포맷을 처음부터 리버스 엔지니어링했습니다. 툴과 번역은
원저작물이며 MIT 라이선스입니다(`LICENSE` 참고). 컬드셉트 리볼트는
© Omiya Soft / Nintendo. 이 저장소에는 게임 코드나 데이터가 포함되어 있지 않습니다.
