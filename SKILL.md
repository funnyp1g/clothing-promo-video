---
name: clothing-promo-video
description: "根据服装或穿搭图片制作可下载的朋友圈宣传 MP4，复用连续容器形变、LOOK 款式切换、合集、配乐及可选品牌片尾。用于图片生成服装宣传视频或复用 clothing-morph-v1 动效；拟真人物走秀、换装和神经网络图生视频不在此渲染器能力内。"
---

# 服装图片宣传视频

使用本 Skill 自带的参数化渲染器生成真实 MP4。模型负责看图、分类和编排，脚本负责动画、配乐、编码与完整解码校验。可在任意工作目录运行，无需原网页项目、模型 API Key 或项目专用工具。

## 素材与事实

- 实际查看本次用户提供的图片，区分服装主图、细节图、重复图、品牌图片和参考图。参考图仅用于比较，不进入成片；每张图片都记录分类，未展示的图片说明理由。
- 默认保留服装和人物原貌、原图比例；形变只作用于展示容器。裁切仅在看图确认主体安全后填写边界和理由。
- 此样式使用 LOOK 编号和固定穿搭文案，不根据图片推断颜色、面料成分、功能、价格、优惠、库存、联系方式或品牌授权。不把 LOOK 编号当成真实货号。只有用户明确指定的品牌图片可用于品牌片尾，不能从衣服上的商标或旧素材提取店铺品牌。
- 支持 1–12 款及最多一张片尾品牌图片。默认每个已识别款式都展示；明确片长不足时说明所需时长并让用户选择加长或分组，不擅自丢弃款式。只有品牌图时需要补充服装主图。
- 用户明确要求自定义标题、广告文案、全新动效或拟真走秀时，说明此渲染器的实际范围；不要把被忽略的参数称为已实现。不同画幅仅等比居中保留竖版构图。

## 执行

把下文 `SKILL_DIR` 替换为实际读取到的 Skill 目录，`PYTHON` 替换为具有依赖的 Python 解释器；不要写死原项目路径。

1. 运行 `PYTHON SKILL_DIR/scripts/render_video.py --check`。已有 Python 环境可复用；缺依赖时，在本次工作目录创建虚拟环境并执行 `python -m pip install -r SKILL_DIR/scripts/requirements.txt`。依赖为 Pillow、NumPy、imageio-ffmpeg，建议 Python 3.9–3.12；字体已随 Skill 提供，FFmpeg 由 imageio-ffmpeg 提供。无需安装原项目服务或执行框架。
2. 阅读 [输入规格](references/spec.md)，在本次工作目录写 `promo.json`。默认 `aspect=9:16`、`quality=preview`（720×1280 / 30fps）；用户要求高清或正式成片时选 `final`（1080×1920 / 60fps）。默认开启配乐。四款无品牌为 15 秒，有品牌为 18 秒，其他数量自动计算。
3. 先生成预览图：

   ```text
   PYTHON SKILL_DIR/scripts/render_video.py --spec /absolute/path/promo.json --output /absolute/path/video-output --keyframes
   ```

   实际查看结果返回的 `keyframes` 和 `transitions`，检查款式覆盖、主体比例、文字可读性、转场连续帧及品牌过渡。默认样式为暖灰白画布、深色胶囊、宋体标题、同一个圆角容器连续展开、LOOK 切换、款式合集、咨询收尾；有品牌图时再柔和展开为深色品牌页。检查没有问题即可继续，不额外要求用户批准渲染。
4. 用同一规格和输出目录运行完整渲染：

   ```text
   PYTHON SKILL_DIR/scripts/render_video.py --spec /absolute/path/promo.json --output /absolute/path/video-output
   ```

   运行器复制本次素材和源码，保存 `context.json`、输入规格与 manifest，执行真实渲染，并验证尺寸、帧率、时长、解码帧数以及所需音轨。成功时返回 `stage=completed` 和绝对文件路径。无需 `frame_write_manifest`、`frame_finish_video` 或任何原项目服务。失败时根据输出日志修正规格或环境；同一失败连续两次仍未解决时保留产物并报告具体阻塞。

## 交付与复用

交付成功返回的 MP4，并给出尺寸、时长及帧率；必要时附海报、关键帧或 `verification.json`。只生成关键帧不能称为视频完成。音乐存在且可解码不代表已经听过；未试听时不声称音质已审听。此成片使用原照片与程序化动画，不是人物实拍或神经网络生成的视频。

输出目录包含 `src/render_video.py`、`src/clothing_morph.py`、`src/request.json`、素材和字体。将整个输出目录移到其他机器后，可安装同一 `src/requirements.txt`，再运行 `python src/render_video.py --spec src/request.json --output /new/output/path` 复现。更换款式时编辑规格，不改写基准动画；用户明确修改动效时才另做设计。
