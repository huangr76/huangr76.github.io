# 历史互动课堂

统一课堂入口：<https://huangr76.github.io/>。纯静态 HTML / CSS / JavaScript，无构建服务、外部字体、运行时 GitHub API 或第三方统计。游戏链接直接写入 HTML，即使禁用 JavaScript，学生也可以进入游戏。

## 当前目录

| 项目 | 当前游戏标题 | Pages 地址 |
| --- | --- | --- |
| `chuzhongshiji-siqi` | 走出中世纪 01——你能否逃出庄园？ | <https://huangr76.github.io/chuzhongshiji-siqi/> |
| `siqi-manor-escape` | 走出中世纪 01——你能否逃出庄园？ | <https://huangr76.github.io/siqi-manor-escape/> |
| `charlemagne-800` | 穿越公元800年 · 查理曼帝国实录 | <https://huangr76.github.io/charlemagne-800/> |

前两个项目当前标题和 meta description 相同，因此保留两个独立入口，分别标明「入口一」「入口二」及项目名，不编造不同游戏名称。它们的部署产物并不相同：第一个 HTML 内嵌资源，约 28.2 MB；第二个 HTML 约 101 KB，资源单独加载。卡片插图是本入口的轻量 SVG 装饰，不加载游戏大文件。

## 更新与增加游戏

需要 Python 3.10+，只使用标准库：

```sh
# 在独立分支操作；从 GitHub 与线上 Pages 重新核对所有条目
python3 scripts/sync_games.py
# 检查目录与生成页一致；运行失败保护测试
python3 scripts/sync_games.py --check
python3 -m unittest discover -s tests -v
```

脚本依次读取每个仓库的默认分支当前提交、最新 Pages 工作流、对应 `github-pages` deployment 的成功状态与真实 `environment_url`，下载该提交的 `index.html` 并和线上页面逐字节核对。标题与简介取自页面的 `<title>` 和 `<meta name="description">`。所有项目通过后才更新 `catalog/games.json` 与 `index.html`。目录保存源提交、HTML SHA-256、部署链接和核对时间，便于审查。

部署失败、尚未完成、源分支领先于部署、标题缺失、页面与源码不一致、意外地址或网络失败都会中止更新，不以猜测结果覆盖已核对目录。公开仓库无需 token；遇到 GitHub API 限额时可按本机标准方式提供只读 `GITHUB_TOKEN`，脚本只会将其发往 `api.github.com`。本次核对是静态快照，不代表页面永久可用。

增加游戏：在 `catalog/projects.json` 追加一项，包含 `repo`、课堂区分用的 `label`、`topic`、`theme`（forest / ochre / wine）、`art`（gate / manor / crown），然后运行以上命令并提交 PR。不要手填游戏标题、简介或 Pages 地址。默认支持同一账户下、根目录 `index.html`、`github-pages` 环境、Pages 工作流名称或路径含 `pages` 的项目；其他结构需明确扩展采集规则。页面卡片数自动计算，布局可自动换行。

修改页面设计：编辑 `templates/index.html`、`assets/hub/hub.css` 或 `assets/hub/hub.js`。模板改动后运行 `python3 scripts/sync_games.py --build`，从已核对目录离线重新生成。CI 做离线一致性、失败保护及浏览器检查，不向 master 自动推送，也不更改任何游戏。

浏览器检查覆盖 320、390、768、1280、1440 像素视口、无水平溢出、移动端单列/桌面三列、按钮触控尺寸、二维码加载、Esc 与焦点恢复、剪贴板成功及拒绝时的手动复制，以及禁用 JavaScript 后的三个链接。截图保存在 Actions 的 `classroom-browser-screenshots` artifact。运行前需安装 `playwright==1.51.0` 和 Chromium；执行 `python3 tests/browser_check.py`。

## 本地查看与课堂分享

```sh
python3 -m http.server 8000
```

访问 <http://localhost:8000/>。桌面显示三列，手机显示单列。所有游戏有独立链接和复制按钮；剪贴板权限不足时提供可选中的网址。分享窗口支持 Esc 关闭及键盘焦点限制，展示静态统一入口二维码。二维码指向正式根站，因此合并并部署后才会看到新入口。二维码 SVG 自包含，无外部二维码服务。

入口页不采集作答、不登录、不写入游戏存档。旧站文章、归档、标签、RSS 和资源保持原路径；页脚保留旧站归档入口。只替换根 `index.html`，不要让 Gridea 后续同步再次覆盖它。

## 发布

在 `huangr76/huangr76.github.io` 的功能分支提交 PR，目标为 `master`。此改造不修改 Pages 设置，也不增加自动部署工作流。合并后由仓库现有的 Pages 发布方式发布；若根站未触发发布，需要在 GitHub Pages 设置中核对是否仍从 `master` 根目录提供内容。提交 PR 不等于已经上线。
