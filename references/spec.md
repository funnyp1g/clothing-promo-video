# 独立运行输入规格

输入是一个 UTF-8 JSON 文件。图片路径可以是绝对路径，或相对于这个 JSON 文件的路径。图片支持 PNG、JPEG、WebP，保留 EXIF 方向和透明通道。

```json
{
  "quality": "preview",
  "aspect": "9:16",
  "music": true,
  "assets": [
    {"id": "look-01", "path": "images/look-01.png", "role": "material"},
    {"id": "look-02", "path": "images/look-02.jpg", "role": "material"},
    {"id": "shop-logo", "path": "images/logo.png", "role": "brand"},
    {"id": "style-reference", "path": "images/reference.jpg", "role": "reference"}
  ],
  "looks": [
    {"asset_id": "look-01", "category": "garment"},
    {"asset_id": "look-02", "category": "suit"}
  ],
  "classification": [
    {"asset_id": "look-01", "role": "garment", "reason": "第一款完整主图"},
    {"asset_id": "look-02", "role": "garment", "reason": "第二款完整主图"},
    {"asset_id": "shop-logo", "role": "logo", "reason": "用户指定品牌片尾"},
    {"asset_id": "style-reference", "role": "reference", "reason": "仅用于风格参考"}
  ],
  "logo_asset_id": "shop-logo"
}
```

## 字段

- `assets`：本次全部图片，ID 非空且唯一。`role` 只能为 `material`（默认）、`brand`、`reference`，表示用户给定的素材用途。品牌图片最多一张，不算服装款式。
- `looks`：1–12 个主图，按展示顺序填写 `asset_id`，不得重复。每个主图必须是 `material`，并在分类中标为 `garment`。不确定品类时用默认 `garment`（日常穿搭）；确实看图确认后可用 `shirt-skirt`（系带衬衫／半裙）、`suit-trousers`（西装／宽松长裤）、`suit`（西装／长裤）、`track-jacket`（立领外套／条纹）。不接受自定义款名、颜色标签或广告卖点字段。
- `classification`：逐张覆盖所有资产，ID 不重复。角色可用 `garment`、`detail`、`duplicate`、`logo`、`store`、`poster`、`other`、`reference`。除 `garment`／`logo` 外必须提供 `reason`，细节图或重复图在理由中写明所属主图。所有 `garment` 必须且仅能在 `looks` 展示一次；品牌用途必须分类为 `logo`，参考用途必须分类为 `reference`。
- `logo_asset_id`：可省略；唯一 `brand` 会自动使用。没有用户指定品牌图片时不要填，不会生成品牌占位或品牌时长。
- `duration`：可选，最终总秒数，包括品牌片尾。默认 `max(10, 3*N+3)` 秒；有品牌再加 3 秒。最低为 `2.4*N+4.5` 秒，有品牌再加 3 秒，最多 300 秒。四款分别为 15／18 秒。
- `music`：JSON 布尔值，默认 `true`。关闭时写 `false`，不能写字符串 `"false"`。配乐是本地合成的轻柔和弦与节奏，不含配音。
- `quality`：`preview`（短边720、30fps）或 `final`（短边1080、60fps），默认 `preview`。
- `aspect`：`9:16`、`16:9`、`1:1`、`4:5`，默认 `9:16`。其他比例等比居中展示竖版设计，保留留白，不重新设计横版布局。
- `looks[].crop`：可选 `[left, top, right, bottom]`，坐标为 0–1，且必须附 `crop_reason`。默认不裁切；先实际看图再决定，不能拉伸人物或服装。

顶层、资产、款式和分类的未知字段会报错，避免将未生效的标题或文案参数当作成功应用。

## 输出

`--keyframes` 只生成关键帧／转场拼图、海报和 manifest 草稿，返回 `stage=keyframes`。

完整运行返回 `stage=completed`、`video`、`poster`、`keyframes`、`transitions`、`manifest`、`verification` 和 `workspace` 绝对路径。`verification.json` 包含实际解码得到的宽高、帧率、帧数、时长和所需音轨校验结果。运行器会验证 H.264 视频、目标尺寸／帧率及全部帧和音频解码；错误日志在 `tmp/renderer.log`、`tmp/encode.log` 或 `tmp/decode.log`。

为保留已交付的版本，不同规格或质量使用不同输出目录；同一规格的关键帧和完整渲染共用一个目录。运行器将输入图片复制到 `inputs/`，源码及可迁移输入放入 `src/`，字体放入 `assets/fonts/`。可重新运行 `src/render_video.py --spec src/request.json --output 新目录`。
