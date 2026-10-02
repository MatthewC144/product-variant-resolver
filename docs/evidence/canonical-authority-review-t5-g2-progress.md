# Canonical Authority Review — T5-G2 progress

Date: 2026-10-01
Mode: Lite / Lean Industrial
Status: **IN PROGRESS — BATCH 1 RECORDED; 3 APPROVED EXACT／17 REVIEWED**

## 結論與邊界

T5-G2 Batch 1 已將 Mazda Autozam 的 packet ordinals `1`、`10`、`16` 由 `reviewed`
推進為 `approved_exact`。每筆只承認 frozen community snapshot 所支持的 casting、
release year、series、collector number、series position 與 toy identifier；`color` 與
`edition` 維持 null。

`approved_exact` 在此表示與特定的 frozen community revision 一致，不是
manufacturer-certified truth。另外 17 筆仍是 `reviewed`，所以 T5-G2 尚未完成；
authority bundle／manifest 未建立，CAR-T5F、CAR-T6 與 RHB-T5 未被授權。本文件不
重述、推導或硬編碼 trusted owner response 或 private identity。

| State / artifact | Count / status |
|---|---:|
| `approved_exact` candidates | 3 |
| Still `reviewed` | 17 |
| Still `staged` | 0 |
| T5-G1 + T5-G2 private batch authorizations | 8 |
| T5-G1 + T5-G2 private attestations | 23 |
| Public historical events | 23 |
| Frozen authority bundle / manifest | absent |
| RHB-T5 authorization | false |

## 稽核鏈與不變性

T5-G2 使用獨立的 private authorization／attestation ledgers，並要求 fresh owner response
hash 不得與對應 T5-G1 hash 相同。公開 event ledger 以 candidate／time／event 穩定排序，
並驗證 `staged -> reviewed -> approved_exact` 狀態鏈連續。

Post-materialization 驗證結果：

- 20 個原有 T5-G1 events 完全保留；
- 17 個非 Batch 1 candidate objects 完全保留；
- 8 個 authorization links、23 個 attestation links 與 20 個 latest-event links 全數成立；
- 三個 exact events 各含六個完整且一致的來源欄位；
- 首次寫入為 `created`，兩次真實 `--check` 均為 `unchanged`。

## QA 與 privacy

Pre-materialization 驗證為 focused T5-G2 `12 passed`、T5-G1 regression `71 passed`、完整
repository `1351 passed, 1 warning`；Ruff、format、strict MyPy、compileall 與 diff check 全部
通過。唯一 warning 是既有 Starlette／AnyIO deprecation。

Private 目錄為 `0700`、private JSON 為 `0600`、public JSON 為 `0644`，新增的 private
ledgers 均命中專用 `.gitignore` 規則。796 個 tracked／unignored 文字檔的真實 owner
response scan 為 0 hits。狀態寫入後未重跑完整 suite。

## Artifact SHA-256

| Artifact | SHA-256 |
|---|---|
| Private T5-G2 batch authorization ledger | `f065618a08ff4dea5c3cc126489ec9eeec83fe0975e89c879d49c417670e1743` |
| Private T5-G2 owner attestation ledger | `6e2bf10176ac8fa2589e8bef28d234f6ffca44e67fc9d93d0f68474562a49cb0` |
| Public authority candidates | `64573183abbfd96c720f3cd0b841c81aabc82699e3c19d6d4669ece836fe0d2f` |
| Public review events | `fd285775893c40c210f517c64014bf7c024ac353c29ee56dd47b94214b77c904` |

## 下一個 Gate

下一步是以全新且明確綁定家族與 toy identifiers 的 T5-G2 owner decision 處理
下一批。不可重用本批、T5-G1 或 catalog-application 的授權；CAR-T5F 只能在
所有餘下 outcomes 完整記錄並對帳後開始。
