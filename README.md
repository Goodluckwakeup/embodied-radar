# 具身研究雷达：从零部署教程

这是可自行部署的起始模板，不是已经上线的服务。你需要一个 GitHub 账号。
第一版采用 JSON 保存历史，适合个人信息流；量变大后再迁移 SQLite 或托管数据库。
包内附有 2026 年 11 月 8 日实测采集的研究快照。首次部署会保留历史并继续补采，不表示定时服务已经启用。

## 1. 准备仓库

1. 解压本压缩包，打开 `embodied-radar` 文件夹。
2. 登录 https://github.com/new ，创建名为 `embodied-radar` 的仓库，默认分支使用 `main`。
3. 使用 GitHub Free 时，把仓库设为 Public，以使用 GitHub Pages。代码和采集结果都将公开，网站没有登录限制。
4. 上传该文件夹里面的全部文件，而不是只上传压缩包。仓库根目录应该直接出现 `README.md`、`config.json`、`scripts`、`site`、`data`。
5. 特别检查隐藏文件 `.github/workflows/daily.yml` 已上传。Windows 资源管理器“查看 → 显示 → 隐藏的项目”可显示 `.github`。
   网页上传若遗漏隐藏目录：在仓库点击 Add file → Create new file，文件名填 `.github/workflows/daily.yml`，复制模板同名文件全部内容并提交。

熟悉 Git 的用户也可以在解压目录使用终端，替换下面的“你的用户名”：

```powershell
git init -b main
git add .
git commit -m "Create embodied research radar"
git remote add origin https://github.com/你的用户名/embodied-radar.git
git push -u origin main
```

请使用 GitHub 自己的登录流程，不要把账号密码或 token 写进这些命令。

## 2. 启用网站和写入权限

在仓库打开：

- Settings → Pages → Build and deployment → Source，选择 **GitHub Actions**。
- Settings → Actions → General → Workflow permissions，选择 **Read and write permissions** 并保存。

先不需要填写任何付费 API 密钥。无密钥模式包含 arXiv、Berkeley AI Research 和 NVIDIA Research 订阅源。
订阅地址可能变动；某个来源失败会在页面显示，不会删除之前的文章。

## 3. 手动跑第一次采集

1. 打开仓库 Actions。
2. 选择左侧 **Daily research update**。
3. 点击 **Run workflow**，分支选 `main`，再次点击 Run workflow。
4. 等待任务结束。成功后打开 Settings → Pages，找到访问地址，一般为 `https://你的用户名.github.io/embodied-radar/`。
5. 打开网站底部“采集状态与覆盖范围”，确认各来源成功情况。绿色工作流只表示代码和部署完成，仍需看来源状态：外部站点可能单独失败。

以后工作流按北京时间每天 **08:07 左右** 自动运行，电脑关机不影响。GitHub 的定时任务可能延迟。
公共仓库长时间没有活动时，GitHub 可能停用定时工作流；不更新时先到 Actions 检查并重新启用。
手动运行也可用于补采；不要重复创建其他定时服务。

## 4. 开启全网搜索补漏（推荐）

1. 在 https://api-dashboard.search.brave.com/ 注册，按账号可用方案启用 Web Search API 并获取密钥。套餐和费用以官网为准。
2. 打开 GitHub 仓库 Settings → Secrets and variables → Actions。
3. 在 **Secrets** 标签点击 **New repository secret**。
4. Name 填 `BRAVE_API_KEY`，Secret 填你的密钥并保存。
5. 回到 Actions 手动运行一次。

每天按 `config.json` 中的 8 组中英文查询检索最近一周结果；每组最多取前 20 条。
这些结果是搜索线索，标记为“待核验”，不假装已经访问、核验原始网页，也不生成中文摘要。
搜索引擎的“最近一周”可能依据网页修改时间；没有确认的发表日期保持空白。

## 5. 开启中文摘要（可选）

1. 在 https://platform.openai.com/ 的 API 平台创建 API 密钥并确认 API 可用额度。不要把聊天产品订阅当作已配置 API 额度。
2. 在相同的 GitHub Secrets 页面新增 `OPENAI_API_KEY`。
3. 切换到 **Variables** 标签 → New repository variable，新增 `OPENAI_MODEL`。
4. 值填你的 API 账号可用、支持 Responses API 的文本模型 ID；例如先在官方 API 平台确认后填写。模板不替你选择收费模型。
5. 手动运行一次。网页会显示基于“论文摘要”或“订阅源摘录”的中文摘要。

每次最多尝试处理 20 篇尚无摘要的文章，后续运行继续补齐；失败请求可能重试，供应商实际账单为准。
修改 `config.json` 的 `max_summaries_per_run` 可以调整上限，填 0 可以暂停摘要。
摘要失败时保留原始摘录；模型不会自动获得 PDF 全文。摘要不作为实验结论的独立证据。
密钥只能放 Secrets，不要写入网页、配置、README 或聊天记录。

## 6. 增加企业、高校来源

仓库打开 `config.json` → 编辑。`feeds` 中每项的格式为：

```json
{"name":"机构名称", "kind":"企业", "url":"https://该机构真实的订阅地址"}
```

`kind` 使用“企业”或“高校”。必须填写真正的 RSS 2.0 / Atom 地址，不能填普通首页。
可从机构网站的 RSS 入口找到地址，再添加。保留 JSON 的英文引号和逗号。
重点关注的企业可从 Physical Intelligence、Google DeepMind、NVIDIA、Figure 起步，高校可按你的研究兴趣增加；不要假设它们都有可用 RSS。
没有 RSS 的网站：先由全网搜索覆盖，再开发专用页面适配器。这个模板没有任意网站正文爬虫。
网页底部会列出搜索发现的候选域名；应人工核验其所属机构、内容质量和订阅地址后再添加，不自动信任新域名。

`search_queries` 是搜索词列表，可增加机构名、中文词和新模型名称。
更完整的版本还需扩展检索分页、会议平台、非 RSS 项目页与人工核验流程；不能保证全网收齐。

## 本地运行（可选）

安装 Python 3.11 或更新版本，无须安装第三方依赖。在模板目录执行：

```powershell
python -m unittest discover -s scripts -p "test_*.py"
python scripts/collect.py --no-ai --no-search
python -m http.server 8000 --directory site
```

浏览器打开 http://localhost:8000 。终端按 Ctrl+C 停止网页服务。直接双击 HTML 不能可靠加载 JSON。
API 密钥不是本地预览的必需项，本地如果要调用 API，请通过安全的环境变量方式设置。
上面的本地命令主动禁用两种 API；GitHub 工作流不带这些参数，会使用你在 Secrets 中设置的密钥。

## 数据、范围与排错

- 历史主数据位于 `data/articles.json`，网站读取 `site/data.json`；工作流自动保存两者。
- 默认回看最近 7 天。中断超过 7 天后，把 `lookback_days` 临时调大再补采。
- arXiv 最多扫描 10 页、每页 100 条；达到上限时显示“部分完成”。可增加 `arxiv_max_pages`，注意运行时间和官方限流。
- arXiv 按 ID 合并版本；同链接、完全归一化标题可合并来源。标题发生大幅变化的企业博客和论文可能仍重复；本模板没有模糊语义合并。
- 首次发现时间和原始发布时间分别保存。“今日发现”可能包含旧论文的新版，或搜索延迟收录的旧文章。
- 机构分类来自配置的订阅源，arXiv 不推测高校/企业所属；搜索结果默认“待核验”。
- 当前主题分类是关键词规则，WAM 范围也包含机器人世界模型、VTLA 范围包含触觉机器人策略，偏向召回；可能误收或漏收。
- 没配置搜索时，“采集状态”会显示部分完成／部分功能未启用；这是刻意保留的覆盖提示。
- Workflow 找不到：检查 `.github/workflows/daily.yml` 和默认分支 `main`。
- Save history 报 403：检查 Actions 写入权限和分支保护；有保护规则时需要为该任务配置合适的写入途径。
- Deploy 报错：检查 Pages 的 Source 已选 GitHub Actions，以及 `github-pages` 环境的分支限制。
- arXiv HTTP 429/503 或连接超时：稍后手动重跑；脚本已有重试并遵守至少 3.1 秒的 arXiv 请求间隔。
- API HTTP 401/403：检查密钥和账号权限；429：检查配额和速率限制。原始错误内容不写入公开网页。
- 若所有外部来源失败，工作流仍可能成功发布失败状态和旧数据，请以网页来源状态为准。
- 仓库是公开的，网页也会公开；需要私有访问时应改用支持身份验证的托管方案。

## 官方参考

- arXiv API：https://info.arxiv.org/help/api/user-manual.html
- arXiv API 使用约定：https://info.arxiv.org/help/api/tou.html
- GitHub Pages 工作流：https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- GitHub 定时任务：https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- Brave Search API：https://api-dashboard.search.brave.com/api-reference/web/search/get
- OpenAI 官方 API 文档：https://developers.openai.com/api/reference/python
