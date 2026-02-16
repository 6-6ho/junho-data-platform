DELETE FROM coin_theme_mapping;
DELETE FROM theme_master;

INSERT INTO theme_master (theme_name, exclude_from_rs) VALUES
('신규상장', false), ('구신규상장', false), ('게임테마', false), ('NFT', false),
('중국테마', false), ('밈코인', false), ('저장소', false), ('레이어1', false),
('RWA', false), ('금코인', true), ('수이테마', false), ('솔라나테마', false),
('이더리움테마', false), ('AI', false), ('스테이블', true), ('비트코인형제', false),
('거래소코인', false), ('트론테마', false), ('트럼프테마', false);

-- 신규상장
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'IP', theme_id, '스토리' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ZKP', theme_id, '지케이패스' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BIO', theme_id, '바이오프로토콜' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'DOOD', theme_id, '두들즈' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'TOSHI', theme_id, '토시' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'DEEP', theme_id, '딥북' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'WAL', theme_id, '월러스' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'RAY', theme_id, '레이디움' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SYRUP', theme_id, '메이플파이낸스' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BREV', theme_id, '브레비스' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT '2Z', theme_id, '더블제로' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'PLUME', theme_id, '플룸' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'IN', theme_id, '인피닛' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'CPOOL', theme_id, '클리어풀' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'AERO', theme_id, '에어로드롬파이낸스' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'VIRTUAL', theme_id, '버추얼프로토콜' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SIGN', theme_id, '사인' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'MMT', theme_id, '모멘텀' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'CYBER', theme_id, '사이버' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'OPEN', theme_id, '오픈렛저' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'API3', theme_id, '에이피아이쓰리' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ZORA', theme_id, '조라' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'FLOCK', theme_id, '플록' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ENSO', theme_id, '엔소' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'NOM', theme_id, '노미나' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'LAYER', theme_id, '솔레이어' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SUPER', theme_id, '슈퍼버스' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SAHARA', theme_id, '사하라에이아이' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'F', theme_id, '신퓨처스' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'TREE', theme_id, '트리하우스' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ZBT', theme_id, '제로베이스' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'MIRA', theme_id, '미라네트워크' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'RED', theme_id, '레드스톤' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT '0G', theme_id, '제로지' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ORDER', theme_id, '오덜리' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'KENNEL', theme_id, '커널다오' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'HOLO', theme_id, '홀로월드에이아이' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SOPH', theme_id, '소폰' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BARD', theme_id, '롬바드' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'PROVE', theme_id, '서싱트' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BERA', theme_id, '베라체인' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ERA', theme_id, '칼데라' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'LINEA', theme_id, '리네아' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'G', theme_id, '그래비티' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'FLUID', theme_id, '플루이드' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'FF', theme_id, '팔콘파이낸스' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ZKC', theme_id, '바운드리스' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SOMI', theme_id, '솜니아' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'TRUST', theme_id, '인튜이션' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'WCT', theme_id, '월렛커넥트' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'COW', theme_id, '카우프로토콜' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'OM', theme_id, '만트라' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'XPL', theme_id, '플라즈마' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'MON', theme_id, '모나드' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'PUMP', theme_id, '펌프펀' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'KITE', theme_id, '카이트' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ELSA', theme_id, '헤이엘사' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'LA', theme_id, '라그랑주' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'WET', theme_id, '휴미디파이' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'AVNT', theme_id, '아반티스' FROM theme_master WHERE theme_name='신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'AXL', theme_id, '엑셀라' FROM theme_master WHERE theme_name='신규상장';

-- 구신규상장
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ID', theme_id, '스페이스아이디' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'VTHO', theme_id, '비토르토큰' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'CKB', theme_id, '너보스' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'RVN', theme_id, '레이븐코인' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'MINA', theme_id, '미나' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'MOCA', theme_id, '모카네트워크' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'MOVE', theme_id, '무브먼트' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ME', theme_id, '매직에덴' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'LPT', theme_id, '라이브피어' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ALT', theme_id, '알트레이어' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'PYTH', theme_id, '피스네트워크' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SEI', theme_id, '세이' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BLUR', theme_id, '블러' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'EGLD', theme_id, '멀티버스엑스' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'YGG', theme_id, '일드길드게임즈' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ATH', theme_id, '에이셔' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'KAITO', theme_id, '카이토' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'NXPC', theme_id, '넥스페이스' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'AKT', theme_id, '아카시네트워크' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ZRO', theme_id, '레이어제로' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'STG', theme_id, '스타게이트파이낸스' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'IMX', theme_id, '이뮤터블엑스' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BIGTIME', theme_id, '빅타임' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'W', theme_id, '웜홀' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ASTR', theme_id, '아스타' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SAFE', theme_id, '세이프' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'CARV', theme_id, '카브' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ANIME', theme_id, '애니메' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SONIC', theme_id, '소닉SVM' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'HYPER', theme_id, '하이퍼레인' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'NEWT', theme_id, '뉴턴프로토콜' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'CTC', theme_id, '크레딧코인' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'VANA', theme_id, '바나' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BEAM', theme_id, '빔' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'TAIKO', theme_id, '타이코' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ZETA', theme_id, '제타체인' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'DRIFT', theme_id, '드리프트' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'AGLD', theme_id, '어드벤처골드' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BLAST', theme_id, '블라스트' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'AUCTION', theme_id, '바운스토큰' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'GMT', theme_id, '스테픈' FROM theme_master WHERE theme_name='구신규상장';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'MASK', theme_id, '마스크네트워크' FROM theme_master WHERE theme_name='구신규상장';

-- 게임테마
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'AXS', theme_id, '엑시인피니티' FROM theme_master WHERE theme_name='게임테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SAND', theme_id, '샌드박스' FROM theme_master WHERE theme_name='게임테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'MANA', theme_id, '디센트럴랜드' FROM theme_master WHERE theme_name='게임테마';

-- NFT
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'CHZ', theme_id, '칠리즈' FROM theme_master WHERE theme_name='NFT';

-- 중국테마
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'QTUM', theme_id, '퀸텀' FROM theme_master WHERE theme_name='중국테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'NEO', theme_id, '네오' FROM theme_master WHERE theme_name='중국테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'VET', theme_id, '비체인' FROM theme_master WHERE theme_name='중국테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'VTHO', theme_id, '비토르토큰' FROM theme_master WHERE theme_name='중국테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ZIL', theme_id, '질리카' FROM theme_master WHERE theme_name='중국테마';

-- 밈코인
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'PEPE', theme_id, '페페' FROM theme_master WHERE theme_name='밈코인';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SHIB', theme_id, '시바이누' FROM theme_master WHERE theme_name='밈코인';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'DOGE', theme_id, '도지코인' FROM theme_master WHERE theme_name='밈코인';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'TOSHI', theme_id, '토시' FROM theme_master WHERE theme_name='밈코인';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'PENGU', theme_id, '펏지펭귄' FROM theme_master WHERE theme_name='밈코인';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'DOOD', theme_id, '두들즈' FROM theme_master WHERE theme_name='밈코인';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'TRUMP', theme_id, '오피셜트럼프' FROM theme_master WHERE theme_name='밈코인';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BONK', theme_id, '봉크' FROM theme_master WHERE theme_name='밈코인';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'MOODENG', theme_id, '무뎅' FROM theme_master WHERE theme_name='밈코인';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ORCA', theme_id, '오르카' FROM theme_master WHERE theme_name='밈코인';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'MEW', theme_id, '캣인어독스월드' FROM theme_master WHERE theme_name='밈코인';

-- 저장소
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BAT', theme_id, '베이직어텐션토큰' FROM theme_master WHERE theme_name='저장소';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ANKR', theme_id, '앵커' FROM theme_master WHERE theme_name='저장소';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SC', theme_id, '시아코인' FROM theme_master WHERE theme_name='저장소';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'STORJ', theme_id, '스토리지' FROM theme_master WHERE theme_name='저장소';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'FIL', theme_id, '파일코인' FROM theme_master WHERE theme_name='저장소';

-- 레이어1
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ARB', theme_id, '아비트럼' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'NEAR', theme_id, '니어프로토콜' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'HBAR', theme_id, '헤데라' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ATOM', theme_id, '코스모스' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'POL', theme_id, '폴리곤에코시스템토큰' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ALGO', theme_id, '알고랜드' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ADA', theme_id, '에이다' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'AVAX', theme_id, '아발란체' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'INJ', theme_id, '인젝티브' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'XLM', theme_id, '스텔라루멘' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'DOT', theme_id, '폴카닷' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'TRX', theme_id, '트론' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'IOTA', theme_id, '아이오타' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'CRO', theme_id, '크로노스' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'TIA', theme_id, '셀레스티아' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'A', theme_id, '볼타' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'XRP', theme_id, '리플' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'MON', theme_id, '모나드' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BERA', theme_id, '베라체인' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'STX', theme_id, '스택스' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'APT', theme_id, '앱토스' FROM theme_master WHERE theme_name='레이어1';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'OP', theme_id, '옵티미즘' FROM theme_master WHERE theme_name='레이어1';

-- RWA
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ONDO', theme_id, '온도파이낸스' FROM theme_master WHERE theme_name='RWA';

-- 금코인
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'XAUT', theme_id, '테더골드' FROM theme_master WHERE theme_name='금코인';

-- 수이테마
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SUI', theme_id, '수이' FROM theme_master WHERE theme_name='수이테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'DEEP', theme_id, '딥북' FROM theme_master WHERE theme_name='수이테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'HAEDAL', theme_id, '해달프로토콜' FROM theme_master WHERE theme_name='수이테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'WAL', theme_id, '월러스' FROM theme_master WHERE theme_name='수이테마';

-- 솔라나테마
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'JUP', theme_id, '주피터' FROM theme_master WHERE theme_name='솔라나테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'RAY', theme_id, '레이디움' FROM theme_master WHERE theme_name='솔라나테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ORCA', theme_id, '오르카' FROM theme_master WHERE theme_name='솔라나테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'MET', theme_id, '메테오라' FROM theme_master WHERE theme_name='솔라나테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'RENDER', theme_id, '렌더토큰' FROM theme_master WHERE theme_name='솔라나테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'PYTH', theme_id, '피스네트워크' FROM theme_master WHERE theme_name='솔라나테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'W', theme_id, '웜홀' FROM theme_master WHERE theme_name='솔라나테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'JTO', theme_id, '지토' FROM theme_master WHERE theme_name='솔라나테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'MEW', theme_id, '캣인어독스월드' FROM theme_master WHERE theme_name='솔라나테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'GMT', theme_id, '스테픈' FROM theme_master WHERE theme_name='솔라나테마';

-- 이더리움테마
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ETC', theme_id, '이더리움클래식' FROM theme_master WHERE theme_name='이더리움테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ENS', theme_id, '이더리움네임서비스' FROM theme_master WHERE theme_name='이더리움테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'UNI', theme_id, '유니스왑' FROM theme_master WHERE theme_name='이더리움테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'COMP', theme_id, '컴파운드' FROM theme_master WHERE theme_name='이더리움테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'PENDLE', theme_id, '펜들' FROM theme_master WHERE theme_name='이더리움테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'AAVE', theme_id, '에이브' FROM theme_master WHERE theme_name='이더리움테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'LINK', theme_id, '체인링크' FROM theme_master WHERE theme_name='이더리움테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ENA', theme_id, '에테나' FROM theme_master WHERE theme_name='이더리움테마';

-- AI
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'WLD', theme_id, '월드코인' FROM theme_master WHERE theme_name='AI';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'RENDER', theme_id, '렌더토큰' FROM theme_master WHERE theme_name='AI';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'GRT', theme_id, '더그래프' FROM theme_master WHERE theme_name='AI';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ATH', theme_id, '에이셔' FROM theme_master WHERE theme_name='AI';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'VIRTUAL', theme_id, '버추얼프로토콜' FROM theme_master WHERE theme_name='AI';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'ARKM', theme_id, '아캄' FROM theme_master WHERE theme_name='AI';

-- 스테이블
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'USDT', theme_id, '테더' FROM theme_master WHERE theme_name='스테이블';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'USDC', theme_id, '유에스디코인' FROM theme_master WHERE theme_name='스테이블';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'USD1', theme_id, '월드리버티파이낸셜유에스디' FROM theme_master WHERE theme_name='스테이블';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'USDE', theme_id, '유에스디이' FROM theme_master WHERE theme_name='스테이블';

-- 비트코인형제
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BCH', theme_id, '비트코인캐시' FROM theme_master WHERE theme_name='비트코인형제';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'XEC', theme_id, '이캐시' FROM theme_master WHERE theme_name='비트코인형제';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BTT', theme_id, '비트토렌트' FROM theme_master WHERE theme_name='비트코인형제';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BSV', theme_id, '비트코인에스브이' FROM theme_master WHERE theme_name='비트코인형제';

-- 거래소코인
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr, note) SELECT 'MNT', theme_id, '맨틀', '바이빗' FROM theme_master WHERE theme_name='거래소코인';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr, note) SELECT 'BNB', theme_id, '비앤비', '바이낸스' FROM theme_master WHERE theme_name='거래소코인';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr, note) SELECT 'OKB', theme_id, '오케이비', 'OKX' FROM theme_master WHERE theme_name='거래소코인';

-- 트론테마
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'TRX', theme_id, '트론' FROM theme_master WHERE theme_name='트론테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'JUST', theme_id, '저스트' FROM theme_master WHERE theme_name='트론테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'SUN', theme_id, '썬' FROM theme_master WHERE theme_name='트론테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'BTT', theme_id, '비트토렌트' FROM theme_master WHERE theme_name='트론테마';

-- 트럼프테마
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'TRUMP', theme_id, '오피셜트럼프' FROM theme_master WHERE theme_name='트럼프테마';
INSERT INTO coin_theme_mapping (symbol, theme_id, name_kr) SELECT 'WLFI', theme_id, '월드리버티파이낸셜' FROM theme_master WHERE theme_name='트럼프테마';
