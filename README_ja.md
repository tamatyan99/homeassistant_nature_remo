# Nature Remo - Home Assistant カスタム統合

⭐ この統合が役に立った場合は、GitHubでスターを付けていただけると嬉しいです。

Nature RemoをHome Assistantに連携するためのカスタムインテグレーションです。  
エアコンや照明の操作、温度・湿度などの情報をHome Assistant上でまとめて扱えるようになります。

このリポジトリは [NaNaLinks/homeassistant_nature_remo](https://github.com/NaNaLinks/homeassistant_nature_remo) をフォークしたもので、原作者は [@nanosns](https://github.com/nanosns) です。  
原作者の素晴らしい成果に感謝しつつ、こちらのリポジトリで独自に開発を継続しています。

---

## ⚠️ ご注意

このカスタムインテグレーションは、Nature社およびHome Assistantの**非公式**な統合です。  
利用にあたっては、**自己責任で**ご使用いただきますようお願いいたします。

---

## 主な機能

- Nature Remoに登録された家電（エアコン・照明）の操作
- 温度・湿度・照度・気圧・人感センサーのデータ取得
- Nature Remo E / E Liteによるスマートメーターの電力データ取得
- カスタムサービスによる照明の詳細な制御（モード指定など）
- signals に基づいて生成されたリモートエンティティを使って IR コマンドを送信
- 電源signalsを持つ家電のスイッチエンティティ
- 検出閾値を設定可能な人感バイナリセンサー
- ECHONET Lite 家電対応（蓄電池・太陽光発電・EV充電器・電気温水器）
- climateエンティティでの外部温度・湿度センサーの利用
- ローカルIP経由での直接通信

---

## インストール方法（HACS）

以下のボタンをクリックすると、HACSにこのリポジトリを簡単に追加できます。

[![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tamatyan99&repository=homeassistant_nature_remo&category=integration)

1. Home AssistantでHACSを開きます
2. 右上のメニュー（⋮）をクリックします
3. 「Custom repositories」を選択します
4. 以下のリポジトリURLを追加します  
   `https://github.com/tamatyan99/homeassistant_nature_remo`  
   カテゴリは「Integration」を選択してください
5. 「Nature Remo」をインストールします
6. Home Assistantを再起動します

---

## インストール方法（手動）

1. 本リポジトリを以下のパスに配置してください：

```
<設定フォルダ>/custom_components/nature_remo/
```

2. Home Assistantを再起動してください。

---

## セットアップ手順

1. Home Assistantの「設定 → デバイスとサービス → 統合を追加」から `Nature Remo` を選択します。
2. アクセストークン（APIキー）と統合の名前を入力します。
   - トークンは [Nature公式サイト](https://home.nature.global) から発行できます。
3. 登録済みのデバイスや家電が自動的に追加されます。

---

## オプション設定

- データの更新間隔（秒単位）を指定できます。
  - デフォルトは `60秒` に設定されています。
- 人感検出の閾値（分単位）を指定できます。
  - デフォルトは `5分` に設定されています。
- Nature RemoのローカルIPアドレスを設定できます。
- デバイスごとに外部の温度・湿度センサーを設定できます。

⚠️ Nature Remo Cloud API にはリクエスト制限があります。  
更新間隔を短く設定しすぎると、APIの制限に達する可能性があります。

---

## 対応エンティティ一覧

| 種類          | 説明                                                              |
|---------------|-------------------------------------------------------------------|
| climate       | エアコンの操作（冷房・暖房・除湿・送風・自動）                   |
| light         | 照明の操作（オン／オフ、モード切替、エフェクト）                  |
| sensor        | 温度、湿度、照度、気圧、電力（買電／売電／瞬時電力）             |
| remote        | IR／AC／LIGHTのアプライアンスに定義された signals を送信できる   |
| switch        | 電源signalsを持つ家電のオン／オフ切替                             |
| binary_sensor | 検出閾値を設定可能な人感センサー                                  |

※ 今後、さらに対応デバイスやエンティティを拡張予定です。

---

## サンプル：リモートエンティティの使い方

Nature Remoに定義された `signals` 情報をもとに `remote` エンティティが生成されます。  
Home Assistant上から `remote.send_command` を使って信号を送信できます。

### 例：サービス呼び出し

以下のように `remote.send_command` を使って信号を送信します：

```yaml
service: remote.send_command
target:
  entity_id: remote.living_room_remote  # リモートエンティティID
data:
  command: "電源"  # Remoに登録されたボタン名
```

---

## 外部温度・湿度センサーの利用

デバイスごとに外部の温度・湿度センサーを設定できるようになりました。

Home Assistantの設定画面からエンティティを選択することで、Nature Remoのデフォルト値ではなく、指定したセンサーの値を使用することができます。

### 使い方

- Home Assistantの統合設定を開く
- 対象デバイスを選択
- 温度・湿度のエンティティを選択
- 設定を保存

設定後は、以下に反映されます：

- climateエンティティの温度・湿度表示
- エアコン制御に使用される環境データ

### 注意事項

- 外部センサーが未設定の場合は、従来通りNature Remoの値を使用します
- 温度・湿度の値を持つ任意のセンサーエンティティを使用できます

---

## カスタムサービス

この統合は `nature_remo` ドメインで以下のカスタムサービスを提供しています：

| サービス名            | 説明                                          |
|-----------------------|-----------------------------------------------|
| `send_light_mode`     | ライトエンティティに特定のモードコマンドを送信 |
| `echonetlite_refresh` | ECHONET Lite 家電のプロパティ値を再取得        |
| `learn_signal`        | 赤外線信号の学習を開始                         |

---

## 開発・貢献について

バグ報告、機能要望、プルリクエストを歓迎します！

1. このリポジトリをフォークする
2. 機能ブランチを作成する（`git checkout -b feature/amazing-feature`）
3. 変更をコミットする（`git commit -m 'feat: Add amazing feature'`）
4. ブランチにプッシュする（`git push origin feature/amazing-feature`）
5. プルリクエストを作成する

大きな変更や新機能の追加については、まずissueを立てて方針を相談してください。

---

## 作者情報

- 原作者：[@nanosns](https://github.com/nanosns) (NaNaRin) — [NaNaLinks](https://github.com/NaNaLinks)
- フォーク管理者：[@tamatyan99](https://github.com/tamatyan99)

---

## ライセンス

MIT License
