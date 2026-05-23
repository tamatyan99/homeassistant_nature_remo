# Nature Remo - Home Assistant カスタム統合

⭐ この統合が役に立った場合は、GitHubでスターを付けていただけると嬉しいです。

**このリポジトリは [NaNaLinks/homeassistant_nature_remo](https://github.com/NaNaLinks/homeassistant_nature_remo) のフォークです。**
本家にない追加機能や改善が含まれています。

Nature RemoをHome Assistantに連携するためのカスタムインテグレーションです。  
エアコンや照明の操作、温度・湿度などの情報をHome Assistant上でまとめて扱えるようになります。

---

## ⚠️ ご注意
このカスタムインテグレーションは、Nature社およびHome Assistantの**非公式**な統合です。  
利用にあたっては、**自己責任で**ご使用いただきますようお願いいたします。

---

## v0.4.0 の新機能

- **スイッチプラットフォーム** - ON/OFF信号を持つIR家電をHome Assistantのスイッチとして制御
- **ECHONET Lite対応** - Remo E経由で接続した蓄電池・太陽光・EV充電器・電気温水器のセンサー取得
- **Local API** - 同一LAN内のRemoに直接接続して高速応答（オプション）
- **気圧センサー** - 対応Remoデバイスの`pr`イベントに対応
- **人感センサー閾値** - モーション検出の有効時間を設定可能（1/3/5/10/15分）
- **信号学習サービス** - `nature_remo.learn_signal` で新しい赤外線信号を学習
- **ECHONET Liteリフレッシュサービス** - `nature_remo.echonetlite_refresh` でプロパティ値を再取得
- **エコプリセット** - エアコンのエコプリセットに対応（26°C自動設定）
- **デバイス情報強化** - シリアル番号・MACアドレスをデバイス情報に表示

---

## 主な機能

- Nature Remoに登録された家電（エアコン・照明）の操作
- 温度・湿度・照度・気圧・人感センサーのデータ取得
- Nature Remo E / E Liteによるスマートメーターの電力データ取得
- Remo E経由のECHONET Lite家電データ取得（蓄電池・太陽光・EV充電器・電気温水器）
- カスタムサービスによる照明の詳細な制御（モード指定など）
- signals に基づいて生成されたリモートエンティティを使って IR コマンドを送信
- ON/OFF信号を持つ家電のスイッチプラットフォーム対応
- オプションのLocal APIによる直接LAN通信

---

## インストール方法（HACS）

以下のボタンをクリックすると、HACSにこのリポジトリを簡単に追加できます。

[![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tamatyan99&repository=homeassistant_nature_remo&category=integration)

1. Home AssistantでHACSを開きます
2. 右上のメニュー（⋮）をクリックします
3. 「Custom repositories」を選択します
4. 以下のリポジトリURLを追加します  
   https://github.com/tamatyan99/homeassistant_nature_remo  
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

- **更新間隔** - データの更新間隔（秒単位）を指定できます。
  - デフォルトは `60秒`
  - 範囲: 10〜300秒
- **人感センサー閾値** - モーション検出後の有効時間を設定できます。
  - 選択肢: 1/3/5/10/15分
  - デフォルトは `5分`
- **Local IP** - オプション: RemoのローカルIPアドレスを設定すると直接LAN通信します。
  - 空欄の場合はクラウドAPIを使用（デフォルト）
- **外部センサー** - デバイスごとに外部の温度・湿度センサーを設定できます。

⚠️ Nature Remo Cloud API にはリクエスト制限があります。  
更新間隔を短く設定しすぎると、APIの制限に達する可能性があります。

---

## 対応エンティティ一覧

| 種類          | 説明                                                                     |
|---------------|--------------------------------------------------------------------------|
| climate       | エアコンの操作（冷房・暖房・除湿・送風・自動）+ エコプリセット          |
| light         | 照明の操作（オン／オフ、モード切替）                                     |
| sensor        | 温度、湿度、照度、気圧、人感、電力（買電／売電）                         |
| binary_sensor | 人感センサー（閾値時間設定可能）                                         |
| remote        | IR／AC／LIGHTのアプライアンスに定義された signals を送信できる          |
| switch        | ON/OFF信号を持つIR家電のスイッチ制御                                     |

※ 今後、さらに対応デバイスやエンティティを拡張予定です。

---

## サービス

### nature_remo.send_light_mode
ライトエンティティに特定のボタンモードを送信します。

```yaml
service: nature_remo.send_light_mode
data:
  entity_id: light.living_room_light
  mode: "night"
```

### nature_remo.echonetlite_refresh
ECHONET Lite家電のプロパティ値を再取得します。

```yaml
service: nature_remo.echonetlite_refresh
data:
  appliance_id: "your-appliance-id"
  epcs: "e2,e7"  # オプション: カンマ区切りのEPCリスト
```

### nature_remo.learn_signal
家電の新しい赤外線信号の学習を開始します。

```yaml
service: nature_remo.learn_signal
data:
  appliance_id: "your-appliance-id"
```

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

## 作者情報

- 原作者：[@nanosns](https://github.com/nanosns) (NaNaRin) / [@NaNaLinks](https://github.com/NaNaLinks)
- フォーク管理者：[@tamatyan99](https://github.com/tamatyan99)

---

## ライセンス

MIT License

---

## フォークについて

このリポジトリは [NaNaLinks/homeassistant_nature_remo](https://github.com/NaNaLinks/homeassistant_nature_remo) のフォークです。
本家にはないECHONET Lite対応、スイッチプラットフォーム、Local API、気圧センサー、人感センサー閾値設定、信号学習サービスなどの追加機能と各種バグ修正が含まれています。
オリジナルバージョンをご希望の場合は、上流リポジトリをご利用ください。