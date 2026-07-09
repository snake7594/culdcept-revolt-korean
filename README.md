# 컬드셉트 리볼트 (3DS) — CULDCEPT.DAT 툴 & 한글 폰트 데모

**컬드셉트 리볼트**(カルドセプト リボルト, 닌텐도 3DS, 타이틀 ID `00040000000F5700`)의
`CULDCEPT.DAT` 아카이브를 분석한 리버스 엔지니어링 툴과, 게임 자체 폰트로 **한글**을
렌더링하는 개념 증명(PoC)입니다.

이 저장소의 목적은, 공개 툴이 전혀 없던 게임의 커스텀 압축 아카이브 `CULDCEPT.DAT`를
열어서 **텍스트와 폰트를 편집**할 수 있게 하여 향후 정식 한글 번역으로 나아가는 것입니다.

## ⚠️ 먼저 읽어주세요

- **게임 데이터는 일절 포함되어 있지 않습니다.** ROM, `CULDCEPT.DAT`, 실행 파일 모두
  없습니다. 게임을 정식으로 소유한 상태에서 **본인의 파일**로 사용하세요.
- **이것은 번역이 아니라 개념 증명입니다.** 데모는 각 *가나 글리프*를 발음이 비슷한
  한글 음절로 바꿀 뿐입니다(예: `の → 노`, `カ → 카`). 실제 텍스트 번역은 다음 단계입니다.
- 연구·개인용. 게임의 저작권을 존중하세요.

## 무엇을 분석했나

- **`CULDCEPT.DAT` 컨테이너** — `(u32 오프셋, u32 크기)` 레코드 테이블 뒤에 엔트리
  데이터가 이어짐. 엔트리 개수 = `첫_오프셋 / 8`.
- **코덱** — 엔트리는 타입 바이트로 선택되는 두 가지 커스텀 압축을 씁니다:
  - `0x08` / `0x0c` — DEFLATE 계열 **canonical Huffman + LZ** (텍스트/폰트 경로).
    디컴프레서 **와** 컴프레서를 순수 파이썬으로 구현.
  - `0x0d` / `0x8d` — 커스텀 프레이밍된 **LZMA 레인지 코더** (폰트에는 불필요).
- **비트맵 폰트** (리소스 `e1054`): CMAP(글리프 인덱스 → Shift-JIS/ASCII 코드) +
  여러 크기 섹션의 고정 셀 **A4(4비트 알파)** 글리프. 각 글리프는 `w×h`,
  `ceil(w/2)*h` 바이트, 위치는 `섹션 + 0xCE + 인덱스*bpg`.

자세한 내용은 [`docs/FORMAT.md`](docs/FORMAT.md) 참고.

## 사용법

필요: 파이썬 3, [Pillow](https://pypi.org/project/Pillow/), 한글 TTF
(윈도우 `malgun.ttf`(맑은 고딕) 또는 나눔고딕).

```bash
pip install pillow
python apply_korean_font.py 원본/CULDCEPT.DAT 출력/CULDCEPT.DAT --font malgun.ttf
```

그 다음 패치된 파일을 **Azahar / Lime3DS / Citra LayeredFS**로 적용:

```
<에뮬레이터 사용자 폴더>/load/mods/00040000000F5700/romfs/CULDCEPT.DAT
```

(적용 확인됨 — 로그에 `LayeredFS replacement file in use for /CULDCEPT.DAT` 출력)
또는 패치된 `CULDCEPT.DAT`를 RomFS에 넣어 ROM/CIA를 재빌드하세요.

편의를 위해 데모의 **xdelta 패치**를 [릴리즈](../../releases)에 첨부했습니다.
본인의 `CULDCEPT.DAT`에 xdelta3 또는 DeltaPatcher로 적용하세요(아래).

## xdelta 패치 적용

릴리즈의 `culdcept-korean-font-demo.xdelta`는 일본판(Rev 2) RomFS의 `CULDCEPT.DAT`
(SHA-1 `87439b18719dcd835a253238c922f76df7c0a76e`)에 대한 **차이(diff)**입니다.
원본 파일 없이는 사용할 수 없습니다.

- **DeltaPatcher**(GUI): Original = 본인 `CULDCEPT.DAT`, Patch = `.xdelta` 선택 → Apply
- **명령줄**:
  ```
  xdelta3 -d -s CULDCEPT.DAT culdcept-korean-font-demo.xdelta out_CULDCEPT.DAT
  ```

## 라이브러리

```python
from culdcept import huffman, dat, font
d = dat.Dat(open("CULDCEPT.DAT", "rb").read())
raw = huffman.decompress(d.entry(1054))     # -> 압축 해제된 폰트 리소스
entry = huffman.compress(raw, typ=0x0c)     # -> 게임이 해독하는 유효 엔트리
```

## 크레딧

컨테이너·코덱·폰트 포맷을 처음부터 리버스 엔지니어링했습니다. 툴은 원저작물이며
MIT 라이선스입니다(`LICENSE` 참고). 컬드셉트 리볼트는 © Omiya Soft / Nintendo.
이 저장소에는 게임 코드나 데이터가 포함되어 있지 않습니다.
