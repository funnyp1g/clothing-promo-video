# clothing-promo-video

从服装或穿搭图片生成朋友圈宣传 MP4 的独立 Codex Skill。保留原照片，通过连续圆角容器形变、LOOK 切换、合集和咨询收尾形成视频；可追加用户指定的品牌图片片尾。

包含完整渲染源码、中文字体及其授权文件。模型负责图片分类与编排，本地 Python / FFmpeg 负责动画、合成配乐、编码和完整解码校验。

## 使用

Skill 入口与调用流程见 [SKILL.md](SKILL.md)，输入格式见 [references/spec.md](references/spec.md)。

```text
使用 $clothing-promo-video，把这些服装图片制作成竖屏宣传视频，开启配乐，输出高清成片。
```

也可直接运行脚本。建议 Python 3.9–3.12，在自己的虚拟环境中安装依赖：

```bash
python -m pip install -r scripts/requirements.txt
python scripts/render_video.py --check
python scripts/render_video.py --spec /absolute/path/promo.json --output /absolute/path/video-output --keyframes
python scripts/render_video.py --spec /absolute/path/promo.json --output /absolute/path/video-output
```

默认 preview 为短边 720 / 30fps；final 为短边 1080 / 60fps。支持 1–12 款、最多一张品牌图片。默认不裁切，不推断服装颜色或未经确认的商品信息。其他画幅将竖版构图等比居中；此渲染器不制作拟真人物走秀或神经网络图生视频。

## 已验证

在 macOS 中实际执行并完整解码：四款无品牌版 720×1280 / 30fps / 15秒；品牌版 720×1280 / 30fps / 13秒；方形静音版 720×720 / 30fps / 10秒；迁移输出源码后生成高清版 1080×1920 / 60fps / 10秒。素材图片比例、关键帧与转场已做视觉检查。

Skill 结构与 ZIP 完整性通过校验；7 个无效输入被拦截，改变规格不会覆盖已有不同版本成片。字体保持原文件，授权与来源说明位于 [assets/fonts](assets/fonts)。
